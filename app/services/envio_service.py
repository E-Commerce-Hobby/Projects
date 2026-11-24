from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import ReglaNegocioError
from app.domain.envio_schema import (
    ActualizarEstadoEnvioRequest,
    ConfirmarUbicacionRequest,
    GenerarGuiaRequest,
    RegistrarProblemaEnvioRequest,
)
from app.domain.orden_schema import ActualizarEstadoOrdenRequest
from app.repositories import envio_repository, orden_repository
from app.services.orden_service import (
    actualizar_estado_orden,
    notificar_incidencia_envio_orden,
)

TIMEOUT_TRANSPORTADORA_SEGUNDOS = 10.0


def _evaluar_ubicaciones_para_orden(orden: dict) -> tuple[list[dict], list[str]]:
    """
    Evalúa qué ubicaciones cubren TODOS los productos de la orden (sin despachos parciales).
    Retorna (ubicaciones_elegibles_ordenadas, productos_sin_cobertura_global).
    """
    ubicaciones = envio_repository.listar_ubicaciones()
    productos = orden.get("productos", [])

    elegibles: list[dict] = []
    for ubicacion in ubicaciones:
        inventario = ubicacion.get("inventario", {})
        cubre_todo = True
        total_disponible_orden = 0

        for item in productos:
            disponible = inventario.get(item["id_producto"], 0)
            if disponible < item["cantidad"]:
                cubre_todo = False
                break
            total_disponible_orden += disponible

        if cubre_todo:
            elegibles.append(
                {
                    "codigo": ubicacion["codigo"],
                    "nombre": ubicacion["nombre"],
                    "direccion": ubicacion["direccion"],
                    "disponibilidad_total_orden": total_disponible_orden,
                }
            )

    # CA1: Mayor disponibilidad total primero; en empate, menor código alfabético
    elegibles.sort(key=lambda u: (-u["disponibilidad_total_orden"], u["codigo"]))

    if elegibles:
        return elegibles, []

    # CA3: Identificar qué productos no alcanzan en ninguna ubicación
    productos_insuficientes: list[str] = []
    for item in productos:
        id_prod = item["id_producto"]
        cant_req = item["cantidad"]
        alguno_cubre = any(
            u.get("inventario", {}).get(id_prod, 0) >= cant_req for u in ubicaciones
        )
        if not alguno_cubre:
            productos_insuficientes.append(id_prod)

    # Si cada producto existe por separado pero ninguna bodega reúne todos juntos
    if not productos_insuficientes:
        productos_insuficientes = [item["id_producto"] for item in productos]

    return [], productos_insuficientes


def seleccionar_ubicacion_despacho(id_orden: str) -> dict:
    """FUN-7.1.4 (CA1 y CA3): Retorna ubicaciones elegibles y sugiere la mejor."""
    orden = orden_repository.obtener_orden(id_orden)
    if orden is None:
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' no existe.",
            status_code=404,
            data=["id_orden"],
        )

    elegibles, sin_cobertura = _evaluar_ubicaciones_para_orden(orden)

    if not elegibles:
        raise ReglaNegocioError(
            message="Ninguna ubicación cubre todos los productos solicitados en la orden.",
            status_code=409,
            data={
                "id_orden": id_orden,
                "productos_sin_cobertura": sin_cobertura,
            },
        )

    return {
        "id_orden": id_orden,
        "ubicacion_seleccionada": elegibles[0],
        "ubicaciones_disponibles": elegibles,
    }


def confirmar_ubicacion_despacho(
    id_orden: str,
    datos: ConfirmarUbicacionRequest | None = None,
) -> dict:
    """FUN-7.1.4 (CA2): Registra la ubicación de despacho asociada a la orden."""
    seleccion = seleccionar_ubicacion_despacho(id_orden)
    elegibles = seleccion["ubicaciones_disponibles"]

    if datos and datos.codigo_ubicacion:
        codigo_norm = datos.codigo_ubicacion.strip().upper()
        elegida = next((u for u in elegibles if u["codigo"] == codigo_norm), None)
        if elegida is None:
            if envio_repository.obtener_ubicacion(codigo_norm) is None:
                raise ReglaNegocioError(
                    message=f"La ubicación '{codigo_norm}' no existe.",
                    status_code=404,
                    data=["codigo_ubicacion"],
                )
            raise ReglaNegocioError(
                message=f"La ubicación '{codigo_norm}' no tiene stock suficiente para la orden.",
                status_code=409,
                data={"codigo_ubicacion": codigo_norm},
            )
    else:
        elegida = seleccion["ubicacion_seleccionada"]

    envio_actual = envio_repository.obtener_envio(id_orden) or {
        "id_orden": id_orden,
        "estado_envio": "pendiente de despacho",
        "numero_guia": None,
        "transportadora": None,
    }

    envio_actual["ubicacion_despacho"] = {
        "codigo": elegida["codigo"],
        "nombre": elegida["nombre"],
        "direccion": elegida["direccion"],
    }
    envio_actual["actualizado_en"] = datetime.now(timezone.utc).isoformat()

    return envio_repository.guardar_envio(envio_actual)


def _solicitar_guia_con_timeout(
    payload: dict,
    timeout_segundos: float = TIMEOUT_TRANSPORTADORA_SEGUNDOS,
) -> dict:
    """Solicita la guía a la transportadora externa con límite de 10 segundos (CA7)."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(envio_repository.solicitar_guia_transportadora, payload)
    try:
        respuesta = future.result(timeout=timeout_segundos)
    except FuturesTimeoutError:
        future.cancel()
        raise ReglaNegocioError(
            message="La transportadora no respondió en 10 segundos. No se generó ninguna guía.",
            status_code=503,
            data={"guia_guardada": False},
        )
    except Exception:
        raise ReglaNegocioError(
            message="Error al comunicarse con la transportadora externa. No se generó ninguna guía.",
            status_code=503,
            data={"guia_guardada": False},
        )
    finally:
        executor.shutdown(wait=False)

    if not respuesta or not respuesta.get("numero_guia"):
        raise ReglaNegocioError(
            message="La transportadora devolvió una respuesta inválida. No se generó ninguna guía.",
            status_code=503,
            data={"guia_guardada": False},
        )

    return respuesta


def generar_guia_envio(
    id_orden: str,
    datos: GenerarGuiaRequest,
    timeout_segundos: float = TIMEOUT_TRANSPORTADORA_SEGUNDOS,
) -> dict:
    """FUN-7.1.2 (CA4-CA7): Solicita y guarda el número de guía asociado a la orden."""
    orden = orden_repository.obtener_orden(id_orden)
    if orden is None:
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' no existe.",
            status_code=404,
            data=["id_orden"],
        )

    envio = envio_repository.obtener_envio(id_orden)
    orden_pagada = orden.get("estado") == "pagada"
    tiene_ubicacion = envio is not None and envio.get("ubicacion_despacho") is not None

    # CA6: Validar condiciones previas indicando exactamente cuál falta
    if not orden_pagada and not tiene_ubicacion:
        raise ReglaNegocioError(
            message="La orden debe estar en estado 'pagada' y tener ubicación de despacho registrada.",
            status_code=409,
            data={"faltantes": ["estado pagada", "ubicacion de despacho"]},
        )
    if not orden_pagada:
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' no está en estado 'pagada' (estado actual: '{orden.get('estado')}').",
            status_code=409,
            data={"faltantes": ["estado pagada"], "estado_actual": orden.get("estado")},
        )
    if not tiene_ubicacion:
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' no tiene una ubicación de despacho registrada.",
            status_code=409,
            data={"faltantes": ["ubicacion de despacho"]},
        )

    if envio.get("numero_guia"):
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' ya tiene una guía generada ({envio['numero_guia']}).",
            status_code=409,
            data={"numero_guia": envio["numero_guia"]},
        )

    # CA4: Construir solicitud a la transportadora con peso, dimensiones, origen y destino
    payload_transportadora = {
        "id_orden": id_orden,
        "transportadora": datos.transportadora,
        "peso_kg": datos.peso_kg,
        "dimensiones": datos.dimensiones.model_dump(),
        "origen": envio["ubicacion_despacho"]["direccion"],
        "destino": datos.destino,
    }

    # CA7: Timeout de 10 s o error -> HTTP 503 y no guarda ninguna guía
    respuesta_guia = _solicitar_guia_con_timeout(payload_transportadora, timeout_segundos)

    # CA5: Guardar número de guía asociado a la orden
    envio["numero_guia"] = respuesta_guia["numero_guia"]
    envio["transportadora"] = respuesta_guia["transportadora"]
    envio["peso_kg"] = datos.peso_kg
    envio["dimensiones"] = datos.dimensiones.model_dump()
    envio["origen"] = envio["ubicacion_despacho"]["direccion"]
    envio["destino"] = datos.destino
    envio["estado_envio"] = "guía generada"
    envio["guia_generada_en"] = datetime.now(timezone.utc).isoformat()

    return envio_repository.guardar_envio(envio)


def consultar_envio(id_orden: str) -> dict:
    """Consulta la información de despacho y guía de una orden."""
    envio = envio_repository.obtener_envio(id_orden)
    if envio is None:
        raise ReglaNegocioError(
            message=f"No existe información de envío registrada para la orden '{id_orden}'.",
            status_code=404,
            data=["id_orden"],
        )
    return envio

ESTADOS_ENVIO_PERMITIDOS: set[str] = {"despachado", "en tránsito", "entregado"}

MAPEO_ESTADO_ENVIO_A_EVENTO_ORDEN: dict[str, str] = {
    "despachado": "envío despachado",
    "entregado": "envío entregado",
}


def actualizar_estado_envio(datos: ActualizarEstadoEnvioRequest) -> dict:
    """FUN-7.1.3 (CA1-CA4): Actualiza el estado de un envío según reporte de la transportadora."""
    numero_guia = datos.numero_guia.strip()
    estado_norm = datos.estado.strip().lower()
    fecha_hora_iso = datos.fecha_hora.isoformat()
    registrado_en = datetime.now(timezone.utc).isoformat()

    # CA4: Validar que el estado recibido pertenezca a la lista permitida (HTTP 400 + registro)
    if estado_norm not in ESTADOS_ENVIO_PERMITIDOS:
        motivo = (
            f"Estado de envío no permitido: '{datos.estado}'. "
            "Valores válidos: despachado, en tránsito, entregado."
        )
        envio_repository.registrar_actualizacion_envio_rechazada(
            {
                "numero_guia": numero_guia,
                "estado_recibido": datos.estado,
                "fecha_hora": fecha_hora_iso,
                "motivo": motivo,
                "registrado_en": registrado_en,
            }
        )
        raise ReglaNegocioError(
            message=motivo,
            status_code=400,
            data={"numero_guia": numero_guia, "estado": datos.estado},
        )

    # CA1 y CA4: Identificar el pedido asociado a la guía; si no existe, rechazar (404) y registrar
    envio = envio_repository.obtener_envio_por_guia(numero_guia)
    if envio is None:
        motivo = f"No existe ningún envío registrado con el número de guía '{numero_guia}'."
        envio_repository.registrar_actualizacion_envio_rechazada(
            {
                "numero_guia": numero_guia,
                "estado_recibido": estado_norm,
                "fecha_hora": fecha_hora_iso,
                "motivo": motivo,
                "registrado_en": registrado_en,
            }
        )
        raise ReglaNegocioError(
            message=motivo,
            status_code=404,
            data=["numero_guia"],
        )

    id_orden = envio["id_orden"]

    # CA3: Si el nuevo estado es 'despachado' o 'entregado', actualizar la orden vía HU-011
    resultado_orden = None
    orden_actualizada = False
    if estado_norm in MAPEO_ESTADO_ENVIO_A_EVENTO_ORDEN:
        evento_orden = MAPEO_ESTADO_ENVIO_A_EVENTO_ORDEN[estado_norm]
        resultado_orden = actualizar_estado_orden(
            id_orden,
            ActualizarEstadoOrdenRequest(origen="Logística", evento=evento_orden),
        )
        orden_actualizada = True

    # CA2: Guardar el estado del envío con fecha y hora
    envio["estado_envio"] = estado_norm
    envio["fecha_hora_estado"] = fecha_hora_iso
    envio["actualizado_en"] = registrado_en
    historial = envio.setdefault("historial_estados", [])
    historial.append({"estado": estado_norm, "fecha_hora": fecha_hora_iso})
    envio_repository.guardar_envio(envio)

    return {
        "id_orden": id_orden,
        "numero_guia": numero_guia,
        "estado_envio": envio["estado_envio"],
        "fecha_hora": fecha_hora_iso,
        "orden_actualizada": orden_actualizada,
        "estado_orden": (
            resultado_orden["orden"]["estado"]
            if resultado_orden
            else orden_repository.obtener_orden(id_orden)["estado"]
        ),
        "envio": envio,
    }

TIPOS_PROBLEMA_PERMITIDOS: set[str] = {"pérdida", "devolución"}
MAX_LONGITUD_DESCRIPCION_PROBLEMA = 500


def registrar_problema_envio(datos: RegistrarProblemaEnvioRequest) -> dict:
    """FUN-7.1.5 (HU-039 CA1-CA4): Registra un problema de pérdida o devolución en un envío."""
    numero_guia = datos.numero_guia.strip()
    tipo_norm = datos.tipo_problema.strip().lower()
    descripcion = datos.descripcion.strip()
    operador = datos.operador.strip()

    # CA4: Validar tipo de problema permitido
    if tipo_norm not in TIPOS_PROBLEMA_PERMITIDOS:
        raise ReglaNegocioError(
            message="Tipo de problema inválido: debe ser 'pérdida' o 'devolución'.",
            status_code=400,
            data=["tipo_problema"],
        )

    # CA2: Validar descripción no vacía y máximo 500 caracteres
    if not descripcion or len(descripcion) > MAX_LONGITUD_DESCRIPCION_PROBLEMA:
        raise ReglaNegocioError(
            message="La descripción es obligatoria y debe tener máximo 500 caracteres.",
            status_code=400,
            data=["descripcion"],
        )

    # CA1 y CA4: Identificar el pedido asociado a la guía
    envio = envio_repository.obtener_envio_por_guia(numero_guia)
    if envio is None:
        raise ReglaNegocioError(
            message=f"No existe ningún envío registrado con el número de guía '{numero_guia}'.",
            status_code=404,
            data=["numero_guia"],
        )

    id_orden = envio["id_orden"]
    fecha_hora = datetime.now(timezone.utc).isoformat()

    # CA2: Guardar tipo, descripción, operador y fecha y hora
    problema = {
        "id_problema": f"INC-{uuid4().hex[:8].upper()}",
        "id_orden": id_orden,
        "numero_guia": numero_guia,
        "tipo_problema": tipo_norm,
        "descripcion": descripcion,
        "operador": operador,
        "fecha_hora": fecha_hora,
    }
    envio_repository.guardar_problema_envio(problema)

    # CA3: Pasar el envío a 'con incidencia'
    envio["estado_envio"] = "con incidencia"
    envio["fecha_hora_estado"] = fecha_hora
    envio["actualizado_en"] = fecha_hora
    envio.setdefault("historial_estados", []).append(
        {"estado": "con incidencia", "fecha_hora": fecha_hora}
    )
    envio.setdefault("problemas", []).append(problema)
    envio_repository.guardar_envio(envio)

    # CA3: Informar la situación a Ventas mediante la API Estados Orden
    notificacion_ventas = notificar_incidencia_envio_orden(
        id_orden=id_orden,
        numero_guia=numero_guia,
        tipo_problema=tipo_norm,
        descripcion=descripcion,
        fecha_hora=fecha_hora,
    )

    return {
        "problema": problema,
        "estado_envio": envio["estado_envio"],
        "notificacion_ventas": notificacion_ventas,
    }
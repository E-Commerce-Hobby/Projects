from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

from app.core.errors import ReglaNegocioError
from app.domain.envio_schema import ConfirmarUbicacionRequest, GenerarGuiaRequest
from app.repositories import envio_repository, orden_repository

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
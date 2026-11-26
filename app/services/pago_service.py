from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoTimeoutError
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Callable
from uuid import uuid4

from app.core.errors import ReglaNegocioError
from app.domain.pago_schema import (
    ESTADOS_CONFIRMACION_PERMITIDOS,
    METODOS_PAGO_HABILITADOS,
    TIEMPO_ESPERA_PASARELA_SEGUNDOS,
    ConfirmacionPagoEntrada,
    InicioPagoEntrada,
)
from app.repositories.pago_repository import (
    actualizar_estado_pago_orden,
    consultar_orden_para_pago,
    estado_pago,
    guardar_intento_pago,
    obtener_intento_pago,
    registrar_descarte_duplicado,
    registrar_notificacion_ventas,
    registrar_respuesta_descartada,
    registrar_transaccion_si_no_existe,
)

CLAVE_SECRETA_PASARELA = "hobbyvault_pasarela_secreto_2026"


def _simular_solicitud_pasarela(
    id_orden: str,
    monto: int,
    metodo_pago: str,
    simular_timeout: bool = False,
) -> dict:
    """
    Simula el envío de solicitud a la pasarela externa (API-EXT-01: Wompi / PayU).
    Si simular_timeout es True, lanza TimeoutError para validar CA5 sin bloquear 10 s.
    """
    if simular_timeout:
        raise TimeoutError("La pasarela de pagos excedió el tiempo máximo de respuesta.")

    return {
        "aceptada": True,
        "referencia_pasarela": f"PAS-{uuid4().hex[:8].upper()}",
        "id_orden": id_orden,
        "monto_enviado": monto,
        "metodo_enviado": metodo_pago,
    }


def iniciar_pago_orden(
    datos: InicioPagoEntrada,
    pasarela_fn: Callable[..., dict] | None = None,
    tiempo_espera_segundos: float = TIEMPO_ESPERA_PASARELA_SEGUNDOS,
) -> dict:
    """
    HU-014 (FUN-5.1.1): Inicia el pago de una orden ante la pasarela externa.

    CA1: Verifica orden en 'pendiente de pago' y método habilitado, envía monto y método.
    CA2: Si la pasarela acepta, registra el intento con estado 'iniciado' y fecha/hora.
    CA3: Retorna la confirmación de inicio con el ID del intento.
    CA4: Rechaza si la orden no existe (404) o su estado no es 'pendiente de pago' (409).
    CA5: Si la pasarela no responde en 10 s, lanza 503 y NO registra intento 'iniciado'.
    """
    if datos.monto <= 0:
        raise ReglaNegocioError(
            message="El monto del pago debe ser mayor a 0.",
            data=["monto"],
            status_code=400,
        )

    metodo_normalizado = datos.metodo_pago.strip().lower()
    if metodo_normalizado not in METODOS_PAGO_HABILITADOS:
        raise ReglaNegocioError(
            message=(
                f"Método de pago '{datos.metodo_pago}' no habilitado. "
                f"Permitidos: {', '.join(METODOS_PAGO_HABILITADOS)}."
            ),
            data=list(METODOS_PAGO_HABILITADOS),
            status_code=400,
        )

    # CA4: Validar existencia y estado de la orden
    orden = consultar_orden_para_pago(datos.id_orden)
    if orden is None:
        raise ReglaNegocioError(
            message=f"La orden '{datos.id_orden}' no existe.",
            data=[datos.id_orden],
            status_code=404,
        )

    if orden.get("estado") != "pendiente de pago":
        raise ReglaNegocioError(
            message=(
                f"La orden '{datos.id_orden}' no puede pagarse porque su estado actual "
                f"es '{orden.get('estado')}'."
            ),
            data=[{"id_orden": datos.id_orden, "estado_actual": orden.get("estado")}],
            status_code=409,
        )

    # CA1: Validar que el monto coincida con el total de la orden (si ya fue calculado)
    total_orden = orden.get("total")
    if total_orden is not None and datos.monto != total_orden:
        raise ReglaNegocioError(
            message=(
                f"El monto enviado ({datos.monto}) no coincide con el total "
                f"de la orden ({total_orden})."
            ),
            data=["monto"],
            status_code=400,
        )

    # CA1 + CA5: Enviar solicitud a la pasarela con timeout máximo de 10 segundos
    funcion_pasarela = pasarela_fn or _simular_solicitud_pasarela
    try:
        with ThreadPoolExecutor(max_workers=1) as ejecutor:
            futuro = ejecutor.submit(
                funcion_pasarela,
                datos.id_orden,
                datos.monto,
                metodo_normalizado,
                datos.simular_timeout_pasarela,
            )
            respuesta_pasarela = futuro.result(timeout=tiempo_espera_segundos)
    except (TimeoutError, FuturoTimeoutError):
        # CA5: No registrar intento 'iniciado' y devolver HTTP 503
        raise ReglaNegocioError(
            message="La pasarela de pagos no respondió en 10 segundos. Servicio no disponible.",
            data=["pasarela"],
            status_code=503,
        )
    except Exception:
        raise ReglaNegocioError(
            message="La pasarela de pagos no está disponible en este momento.",
            data=["pasarela"],
            status_code=503,
        )

    if not respuesta_pasarela or not respuesta_pasarela.get("aceptada"):
        raise ReglaNegocioError(
            message="La pasarela de pagos no aceptó la solicitud de inicio de pago.",
            data=["pasarela"],
            status_code=503,
        )

    # CA2 + CA3: Registrar intento con estado 'iniciado' y retornar confirmación
    intento = {
        "id_intento": f"PAG-{uuid4().hex[:8].upper()}",
        "id_orden": datos.id_orden,
        "monto": datos.monto,
        "metodo_pago": metodo_normalizado,
        "estado": "iniciado",
        "referencia_pasarela": respuesta_pasarela["referencia_pasarela"],
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
    }
    return guardar_intento_pago(intento)


def consultar_intento_pago(id_intento: str) -> dict:
    """Consulta un intento de pago registrado por su ID."""
    intento = obtener_intento_pago(id_intento)
    if intento is None:
        raise ReglaNegocioError(
            message=f"El intento de pago '{id_intento}' no existe.",
            data=[id_intento],
            status_code=404,
        )
    return intento


# ── HU-015: Confirmación de pago sin duplicados (FUN-5.1.2, FUN-5.1.3) ───────

def calcular_firma_integridad(
    id_transaccion: str,
    id_orden: str,
    estado: str,
    monto: int,
) -> str:
    """Genera la firma SHA-256 esperada para validar respuestas de la pasarela (CA1, CA2)."""
    cadena_base = f"{id_transaccion}|{id_orden}|{estado.strip().lower()}|{monto}|{CLAVE_SECRETA_PASARELA}"
    return hashlib.sha256(cadena_base.encode("utf-8")).hexdigest()


def confirmar_pago_pasarela(datos: ConfirmacionPagoEntrada) -> dict:
    """
    HU-015 (FUN-5.1.2 y FUN-5.1.3): Valida la respuesta de la pasarela y evita duplicados (RN-03).

    CA1: Firma válida + datos completos + monto igual al de la orden -> actualiza pago.
    CA2: Firma inválida, campo faltante o monto distinto -> descarta sin actualizar, registra motivo y lanza 400 (404 si orden no existe).
    CA3: Al actualizar el pago, informa a Ventas (id_orden y estado del pago).
    CA4/CA6/CA7: Si id_transaccion ya fue procesado (control atómico con Lock), descarta sin modificar pago ni re-notificar, registra descarte y retorna 'duplicado' (HTTP 200).
    CA5: Si id_transaccion es nuevo, lo registra y procesa la actualización ('procesada').
    """
    fecha_actual = datetime.now(timezone.utc).isoformat()

    # CA2: Validar presencia de todos los campos obligatorios
    campos_faltantes = []
    if not datos.firma:
        campos_faltantes.append("firma")
    if not datos.id_transaccion:
        campos_faltantes.append("id_transaccion")
    if not datos.id_orden:
        campos_faltantes.append("id_orden")
    if not datos.estado:
        campos_faltantes.append("estado")
    if datos.monto is None or datos.monto <= 0:
        campos_faltantes.append("monto")

    if campos_faltantes:
        motivo = f"Faltan campos obligatorios o inválidos en la respuesta: {', '.join(campos_faltantes)}."
        registrar_respuesta_descartada({
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "motivo": motivo,
            "fecha_hora": fecha_actual,
        })
        raise ReglaNegocioError(message=motivo, data=campos_faltantes, status_code=400)

    # CA2: Validar estado permitido ('aprobado' o 'rechazado')
    estado_normalizado = datos.estado.strip().lower()
    if estado_normalizado not in ESTADOS_CONFIRMACION_PERMITIDOS:
        motivo = (
            f"Estado de pago inválido '{datos.estado}'. "
            f"Permitidos: {', '.join(ESTADOS_CONFIRMACION_PERMITIDOS)}."
        )
        registrar_respuesta_descartada({
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "motivo": motivo,
            "fecha_hora": fecha_actual,
        })
        raise ReglaNegocioError(message=motivo, data=["estado"], status_code=400)

    # CA2: Verificar firma de integridad SHA-256
    firma_esperada = calcular_firma_integridad(
        id_transaccion=datos.id_transaccion,
        id_orden=datos.id_orden,
        estado=estado_normalizado,
        monto=datos.monto,
    )
    if not hmac.compare_digest(datos.firma, firma_esperada):
        motivo = "Firma de integridad inválida. Respuesta descartada sin actualizar el pago."
        registrar_respuesta_descartada({
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "motivo": motivo,
            "fecha_hora": fecha_actual,
        })
        raise ReglaNegocioError(message=motivo, data=["firma"], status_code=400)

    # CA1 / CA2: Verificar que la orden exista y que el monto coincida
    orden = consultar_orden_para_pago(datos.id_orden)
    if orden is None:
        motivo = f"La orden '{datos.id_orden}' no existe."
        registrar_respuesta_descartada({
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "motivo": motivo,
            "fecha_hora": fecha_actual,
        })
        raise ReglaNegocioError(message=motivo, data=[datos.id_orden], status_code=404)

    total_orden = orden.get("total")
    if total_orden is not None and datos.monto != total_orden:
        motivo = (
            f"El monto informado ({datos.monto}) no coincide con el total "
            f"de la orden ({total_orden})."
        )
        registrar_respuesta_descartada({
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "motivo": motivo,
            "fecha_hora": fecha_actual,
        })
        raise ReglaNegocioError(message=motivo, data=["monto"], status_code=400)

    # CA4 / CA5 / CA7 (RN-03): Registro atómico del ID de transacción (a prueba de concurrencia)
    es_nueva = registrar_transaccion_si_no_existe(
        datos.id_transaccion,
        {
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "estado": estado_normalizado,
            "monto": datos.monto,
            "fecha_hora": fecha_actual,
        },
    )
    if not es_nueva:
        # CA4 + CA6: Descartar sin modificar el pago ni volver a informar a Ventas
        registrar_descarte_duplicado({
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "motivo": "Transacción duplicada descartada (RN-03).",
            "fecha_hora": fecha_actual,
        })
        return {
            "resultado": "duplicado",
            "id_transaccion": datos.id_transaccion,
            "id_orden": datos.id_orden,
            "fecha_hora": fecha_actual,
        }

    # CA1: Actualizar el estado del pago a 'aprobado' o 'rechazado'
    pago_actualizado = actualizar_estado_pago_orden(
        id_orden=datos.id_orden,
        estado_nuevo=estado_normalizado,
        id_transaccion=datos.id_transaccion,
        monto=datos.monto,
        fecha_hora=fecha_actual,
    )

    # CA3: Informar resultado a Ventas (API-INT-05)
    notificacion_ventas = registrar_notificacion_ventas({
        "id_orden": datos.id_orden,
        "estado_pago": estado_normalizado,
        "id_transaccion": datos.id_transaccion,
        "fecha_hora": fecha_actual,
    })

    return {
        "resultado": "procesada",
        "id_transaccion": datos.id_transaccion,
        "id_orden": datos.id_orden,
        "estado_pago": pago_actualizado["estado"],
        "monto": datos.monto,
        "notificacion_ventas": notificacion_ventas,
        "fecha_hora": fecha_actual,
    }


def consultar_estado_pago_orden(id_orden: str) -> dict:
    """Consulta el contrato público estado_pago(id_orden) o lanza 404 si no existe."""
    estado = estado_pago(id_orden)
    if estado is None:
        raise ReglaNegocioError(
            message=f"No se encontraron pagos registrados para la orden '{id_orden}'.",
            data=[id_orden],
            status_code=404,
        )
    return estado

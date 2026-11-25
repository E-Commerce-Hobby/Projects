from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoTimeoutError
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from app.core.errors import ReglaNegocioError
from app.domain.pago_schema import (
    METODOS_PAGO_HABILITADOS,
    TIEMPO_ESPERA_PASARELA_SEGUNDOS,
    InicioPagoEntrada,
)
from app.repositories.pago_repository import (
    consultar_orden_para_pago,
    guardar_intento_pago,
    obtener_intento_pago,
)


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

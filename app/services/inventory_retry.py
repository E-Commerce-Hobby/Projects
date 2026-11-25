# app/services/inventory_retry.py
from datetime import datetime, timezone
import time
from typing import Callable, Optional
import uuid
from fastapi import status
from app.core.errors import ReglaNegocioError
from app.domain.inventory_retry import (
    InventoryRetryData,
    InventoryRetryRequest,
    ManualReviewAlert,
)
from app.domain.sincronizacion_inventario_schema import (
    DescuentoInventarioEntrada,
    LineaDescuentoInventario,
)
from app.repositories.inventory_retry import (
    InventoryRetryRepository,
    inventory_retry_repository,
)
from app.services.sincronizacion_inventario_service import aplicar_descuento_por_venta


class TemporaryInventoryError(Exception):
    """Error temporal de comunicación/disponibilidad en la actualización de inventario."""


class InventoryRetryService:
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 30.0

    def __init__(
        self,
        repository: InventoryRetryRepository = inventory_retry_repository,
        discount_executor: Callable[[DescuentoInventarioEntrada], dict] = aplicar_descuento_por_venta,
        sleep_fn: Callable[[float], None] = time.sleep,
        retry_delay_seconds: float = RETRY_DELAY_SECONDS,
    ):
        self.repository = repository
        self.discount_executor = discount_executor
        self.sleep_fn = sleep_fn
        self.retry_delay_seconds = retry_delay_seconds

    def _build_discount_payload(self, payload: InventoryRetryRequest) -> DescuentoInventarioEntrada:
        return DescuentoInventarioEntrada(
            id_venta=payload.sale_id,
            canal=payload.channel,
            lineas=[
                LineaDescuentoInventario(
                    id_producto=line.product_id,
                    ubicacion=line.location,
                    cantidad=line.quantity,
                )
                for line in payload.lines
            ],
        )

    def retry_failed_update(self, payload: InventoryRetryRequest) -> tuple[InventoryRetryData, str]:
        if payload.service_unavailable:
            raise ReglaNegocioError(
                message="Servicio de inventario no disponible para procesar la operación.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        operation_id = (payload.operation_id or "").strip() or f"OP-{uuid.uuid4().hex[:8].upper()}"
        discount_payload = self._build_discount_payload(payload)
        remaining_temp_failures = payload.simulate_temporary_failures

        attempts_used = 0
        last_error_reason: Optional[str] = None
        business_rule_failed = False

        # Intento inicial + hasta 3 reintentos (CA1, CA2, CA3, CA5)
        max_total_attempts = 1 + self.MAX_RETRIES

        for attempt in range(1, max_total_attempts + 1):
            attempts_used = attempt
            try:
                if remaining_temp_failures > 0:
                    remaining_temp_failures -= 1
                    raise TemporaryInventoryError(
                        "Error temporal: tiempo de espera agotado o servicio de inventario no disponible."
                    )

                self.discount_executor(discount_payload)

                # CA2: Éxito -> queda 'exitosa', no se reintenta más y el descuento se aplicó una sola vez
                now = datetime.now(timezone.utc)
                result_data = InventoryRetryData(
                    operation_id=operation_id,
                    sale_id=payload.sale_id,
                    status="exitosa",
                    attempts_used=attempts_used,
                    last_error=None,
                    alert=None,
                )
                self.repository.save_operation({
                    **result_data.model_dump(),
                    "updated_at": now.isoformat(),
                })
                return result_data, "Actualización de inventario completada exitosamente."

            except ReglaNegocioError as exc:
                # CA5 (RN-01): Error de regla de negocio (ej. stock insuficiente) -> NO reintentar
                last_error_reason = exc.message
                business_rule_failed = True
                break

            except TemporaryInventoryError as exc:
                last_error_reason = str(exc)
                # Si aún quedan reintentos dentro del límite de 3, esperar 30s (CA1)
                if attempt < max_total_attempts:
                    self.sleep_fn(self.retry_delay_seconds)

        # CA3 y CA4: Operación 'fallida' + alerta de revisión manual con ID, motivo y fecha/hora
        now = datetime.now(timezone.utc)
        final_reason = last_error_reason or "No fue posible completar la actualización de inventario."
        alert_record = self.repository.create_alert(
            operation_id=operation_id,
            reason=final_reason,
            created_at=now,
        )
        alert_model = ManualReviewAlert(**alert_record)

        failed_data = InventoryRetryData(
            operation_id=operation_id,
            sale_id=payload.sale_id,
            status="fallida",
            attempts_used=attempts_used,
            last_error=final_reason,
            alert=alert_model,
        )
        self.repository.save_operation({
            **failed_data.model_dump(),
            "updated_at": now.isoformat(),
        })

        msg = (
            "Operación registrada como 'fallida' por regla de negocio (RN-01); alerta generada."
            if business_rule_failed
            else "Se agotaron los 3 reintentos; operación 'fallida' y alerta generada."
        )
        return failed_data, msg
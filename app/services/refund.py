# app/services/refund.py
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.core.errors import ReglaNegocioError
from app.core.refund_gateway import (
    RefundGatewayClient,
    RefundGatewayTimeoutError,
    RefundGatewayUnavailableError,
    refund_gateway,
)
from app.domain.refund import RefundCreateRequest, RefundResponseData
from app.repositories.refund import RefundRepository, refund_repository


class RefundService:
    DEFAULT_MAX_REFUND_DAYS: int = 30
    GATEWAY_TIMEOUT_SECONDS: float = 10.0

    def __init__(
        self,
        repository: RefundRepository = refund_repository,
        gateway: RefundGatewayClient = refund_gateway,
        max_refund_days: int = DEFAULT_MAX_REFUND_DAYS,
    ):
        self.repository = repository
        self.gateway = gateway
        self.max_refund_days = max_refund_days

    def process_full_refund(self, payload: RefundCreateRequest) -> RefundResponseData:
        order = self.repository.get_order_by_id(payload.order_id)
        if not order:
            raise ReglaNegocioError(
                f"La orden con ID {payload.order_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA2: Verificar las 3 condiciones de elegibilidad e indicar cuál no se cumple
        if order.get("payment_status") != "aprobado":
            raise ReglaNegocioError(
                "Reembolso rechazado: el pago de la orden no está en estado 'aprobado'.",
                status_code=status.HTTP_409_CONFLICT
            )

        if order.get("order_status") == "reembolsada" or order.get("payment_status") == "reembolsado":
            raise ReglaNegocioError(
                "Reembolso rechazado: la orden ya ha sido reembolsada previamente.",
                status_code=status.HTTP_409_CONFLICT
            )

        paid_at: datetime = order.get("paid_at") or datetime.now(timezone.utc)
        paid_at_aware = paid_at if paid_at.tzinfo else paid_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if (now - paid_at_aware) > timedelta(days=self.max_refund_days):
            raise ReglaNegocioError(
                f"Reembolso rechazado: excedió el plazo máximo de {self.max_refund_days} días.",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA1 y CA4: Enviar solicitud a la pasarela con ID de transacción y monto total pagado
        try:
            gateway_resp = self.gateway.request_full_refund(
                transaction_id=order["transaction_id"],
                amount=order["amount"],
                timeout_seconds=self.GATEWAY_TIMEOUT_SECONDS,
            )
        except (RefundGatewayTimeoutError, RefundGatewayUnavailableError) as exc:
            # CA4: Los estados del pago y de la orden no cambian
            raise ReglaNegocioError(
                f"Reembolso no disponible: {str(exc)}"[:200],
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if not gateway_resp.approved:
            # CA4: Si la pasarela rechaza, los estados del pago y de la orden no cambian
            raise ReglaNegocioError(
                gateway_resp.message[:200],
                status_code=status.HTTP_409_CONFLICT
            )

        # CA3: Confirmado por la pasarela -> pago pasa a 'reembolsado' y orden a 'reembolsada'
        self.repository.update_order_and_payment_status(
            order_id=order["order_id"],
            payment_status="reembolsado",
            order_status="reembolsada",
        )

        saved_refund = self.repository.create_refund({
            "order_id": order["order_id"],
            "transaction_id": order["transaction_id"],
            "refund_reference": gateway_resp.refund_reference,
            "amount": order["amount"],
            "payment_status": "reembolsado",
            "order_status": "reembolsada",
            "refund_status": "reembolsado",
            "processed_at": now,
        })

        return RefundResponseData(**saved_refund)
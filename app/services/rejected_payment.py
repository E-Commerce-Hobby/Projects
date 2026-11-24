# app/services/rejected_payment.py
from datetime import datetime, timezone
from typing import Optional
from fastapi import status
from app.core.errors import ReglaNegocioError
from app.domain.rejected_payment import (
    RejectedPaymentAttemptData,
    RejectedPaymentRequest,
)
from app.repositories.rejected_payment import (
    RejectedPaymentRepository,
    rejected_payment_repository,
)


class RejectedPaymentService:
    DEFAULT_REASON = "sin motivo informado"

    def __init__(self, repository: RejectedPaymentRepository = rejected_payment_repository):
        self.repository = repository

    def _resolve_rejection_reason(
        self,
        code: Optional[str],
        description: Optional[str]
    ) -> tuple[Optional[str], str]:
        """
        CA1: Toma el código y la descripción informados por la pasarela.
        Si no vienen (o vienen vacíos), guarda 'sin motivo informado'.
        """
        clean_code = (code or "").strip() or None
        clean_desc = (description or "").strip() or None

        if clean_code and clean_desc:
            return clean_code, f"[{clean_code}] {clean_desc}"
        if clean_desc:
            return None, clean_desc
        if clean_code:
            return clean_code, f"Código de rechazo: {clean_code}"
        return None, self.DEFAULT_REASON

    def register_rejected_payment(
        self,
        payload: RejectedPaymentRequest
    ) -> RejectedPaymentAttemptData:
        # Verificar que la orden exista (DoD: HTTP 404 ante recurso inexistente)
        order = self.repository.get_order_by_id(payload.order_id)
        if not order:
            raise ReglaNegocioError(
                f"La orden con ID {payload.order_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA1: Identificar motivo del rechazo
        normalized_code, resolved_reason = self._resolve_rejection_reason(
            code=payload.rejection_code,
            description=payload.rejection_description,
        )

        # CA3: Incrementar el contador de intentos fallidos de la orden en 1
        updated_counter = self.repository.increment_order_failed_attempts(payload.order_id)

        # CA2: Registrar el intento fallido con ID de orden, ID de transacción, motivo y fecha/hora
        recorded_at = datetime.now(timezone.utc)
        saved_attempt = self.repository.create_failed_attempt({
            "order_id": payload.order_id,
            "transaction_id": payload.transaction_id,
            "rejection_code": normalized_code,
            "reason": resolved_reason,
            "recorded_at": recorded_at,
            "order_failed_attempts": updated_counter,
        })

        return RejectedPaymentAttemptData(**saved_attempt)
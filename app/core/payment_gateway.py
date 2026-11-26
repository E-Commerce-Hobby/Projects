# app/core/payment_gateway.py
from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass
class PaymentResult:
    approved: bool
    transaction_id: Optional[str]
    reason: str


class PaymentGatewayClient:
    """
    Cliente simulado para API-INT-09 (API Pagos -> API-EXT-01 Wompi / PayU).
    - Si el evento es gratuito (amount == 0), aprueba automáticamente.
    - Si payment_method == 'DECLINED' o 'REJECTED', simula un pago rechazado (CA3).
    - Cualquier otro método válido ('CARD', 'PSE', 'NEQUI', 'CASH') aprueba el pago (CA2).
    """

    def process_payment(
        self,
        client_id: int,
        event_id: int,
        amount: float,
        payment_method: str
    ) -> PaymentResult:
        if amount == 0:
            return PaymentResult(
                approved=True,
                transaction_id=f"FREE-{uuid.uuid4().hex[:8].upper()}",
                reason="Evento gratuito: inscripción sin cobro."
            )

        method_normalized = payment_method.strip().upper()
        if method_normalized in {"DECLINED", "REJECTED", "INSUFFICIENT_FUNDS"}:
            return PaymentResult(
                approved=False,
                transaction_id=None,
                reason="El pago fue rechazado por la pasarela de pagos."
            )

        return PaymentResult(
            approved=True,
            transaction_id=f"TX-{uuid.uuid4().hex[:10].upper()}",
            reason="Pago aprobado exitosamente."
        )


payment_gateway = PaymentGatewayClient()
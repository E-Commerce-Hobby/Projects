# app/core/refund_gateway.py
from dataclasses import dataclass
from typing import Optional
import uuid


class RefundGatewayTimeoutError(Exception):
    """Se lanza cuando la pasarela supera los 10 segundos sin responder (CA4)."""


class RefundGatewayUnavailableError(Exception):
    """Se lanza cuando la pasarela externa no está disponible (HTTP 503)."""


@dataclass
class RefundGatewayResult:
    approved: bool
    refund_reference: Optional[str]
    message: str


class RefundGatewayClient:
    """
    Cliente simulado para API-EXT-01 (Wompi / PayU) - Reembolsos totales.
    - Límite de espera: 10 segundos (CA4).
    """

    MAX_TIMEOUT_SECONDS: float = 10.0

    def __init__(self):
        self.service_available: bool = True
        self.simulated_delay_seconds: float = 0.0
        self.force_decline: bool = False
        self.decline_reason: str = "La pasarela rechazó la solicitud de reembolso."

    def request_full_refund(
        self,
        transaction_id: str,
        amount: float,
        timeout_seconds: float = MAX_TIMEOUT_SECONDS,
    ) -> RefundGatewayResult:
        if not self.service_available:
            raise RefundGatewayUnavailableError(
                "Servicio de pasarela de pagos no disponible para procesar el reembolso."
            )

        if self.simulated_delay_seconds > timeout_seconds:
            raise RefundGatewayTimeoutError(
                f"La pasarela de pagos no respondió dentro de {int(timeout_seconds)} segundos."
            )

        if self.force_decline:
            return RefundGatewayResult(
                approved=False,
                refund_reference=None,
                message=self.decline_reason,
            )

        return RefundGatewayResult(
            approved=True,
            refund_reference=f"REF-{uuid.uuid4().hex[:10].upper()}",
            message="Reembolso total confirmado por la pasarela.",
        )

    def reset(self) -> None:
        self.service_available = True
        self.simulated_delay_seconds = 0.0
        self.force_decline = False
        self.decline_reason = "La pasarela rechazó la solicitud de reembolso."


refund_gateway = RefundGatewayClient()
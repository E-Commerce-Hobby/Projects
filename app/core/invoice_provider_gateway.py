# app/core/invoice_provider_gateway.py
from dataclasses import dataclass
from typing import Optional
import uuid


class InvoiceProviderTimeoutError(Exception):
    """El proveedor autorizado no respondió dentro de los 30 segundos límite (CA8)."""


class InvoiceProviderUnavailableError(Exception):
    """El servicio externo del proveedor autorizado (API-EXT-02) no está disponible (HTTP 503)."""


@dataclass
class ProviderTransmissionResult:
    status: str  # "aceptada" o "rechazada"
    fiscal_uuid: Optional[str] = None
    rejection_code: Optional[str] = None
    rejection_reason: Optional[str] = None


class InvoiceProviderGatewayClient:
    """
    Cliente simulado para API-EXT-02 (API DIAN / Proveedor Autorizado).
    - Tiempo máximo de espera: 30 segundos (CA8).
    - Permite simular aceptación (CA6), rechazo fiscal con código y descripción (CA7),
      timeout > 30s (CA8) e indisponibilidad del proveedor (HTTP 503).
    """

    MAX_TIMEOUT_SECONDS: float = 30.0

    def __init__(self):
        self.service_available: bool = True
        self.simulated_delay_seconds: float = 0.0
        self.force_rejection: bool = False
        self.rejection_code: str = "DIAN-099"
        self.rejection_reason: str = "NIT del adquiriente no registrado o inconsistente en RUT."

    def send_electronic_invoice(
        self,
        invoice_payload: dict,
        timeout_seconds: float = MAX_TIMEOUT_SECONDS,
    ) -> ProviderTransmissionResult:
        if not self.service_available:
            raise InvoiceProviderUnavailableError(
                "El proveedor autorizado de facturación electrónica no está disponible."
            )

        if self.simulated_delay_seconds > timeout_seconds:
            raise InvoiceProviderTimeoutError(
                f"El proveedor autorizado no respondió dentro de {int(timeout_seconds)} segundos."
            )

        # También permite simular rechazo si el NIT del adquiriente es '000000000'
        acquirer_doc = invoice_payload.get("acquirer", {}).get("document_number", "")
        if self.force_rejection or acquirer_doc == "000000000":
            return ProviderTransmissionResult(
                status="rechazada",
                fiscal_uuid=None,
                rejection_code=self.rejection_code,
                rejection_reason=self.rejection_reason,
            )

        return ProviderTransmissionResult(
            status="aceptada",
            fiscal_uuid=f"CUFE-{uuid.uuid4().hex.upper()}",
            rejection_code=None,
            rejection_reason=None,
        )

    def reset(self) -> None:
        self.service_available = True
        self.simulated_delay_seconds = 0.0
        self.force_rejection = False
        self.rejection_code = "DIAN-099"
        self.rejection_reason = "NIT del adquiriente no registrado o inconsistente en RUT."


invoice_provider_gateway = InvoiceProviderGatewayClient()
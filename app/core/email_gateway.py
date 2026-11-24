# app/core/email_gateway.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class EmailDeliveryResult:
    success: bool
    result_status: str  # "enviado" o "fallido"
    recipient_client_id: int
    subject: str
    body: str
    sent_at: datetime
    error_detail: Optional[str] = None


class EmailServiceUnavailableError(Exception):
    """Se lanza cuando el proveedor externo de correo (API-EXT-04) no está disponible."""


class EmailGatewayClient:
    """
    Cliente simulado para API-EXT-04 (API Correo / SendGrid).
    Permite simular:
    - Indisponibilidad total del servicio (HTTP 503).
    - Fallos puntuales por cliente/correo (registra resultado 'fallido' en auditoría).
    - Envío exitoso con nombre, fecha y hora del evento.
    """

    def __init__(self):
        self.service_available: bool = True
        self.failing_client_ids: set[int] = set()
        self.sent_emails: List[dict] = []

    def send_event_reminder(
        self,
        client_id: int,
        event_name: str,
        event_date: datetime,
    ) -> EmailDeliveryResult:
        if not self.service_available:
            raise EmailServiceUnavailableError(
                "El servicio externo de correo electrónico no está disponible."
            )

        now = datetime.now(event_date.tzinfo) if event_date.tzinfo else datetime.now()
        formatted_date = event_date.strftime("%Y-%m-%d %H:%M")
        subject = f"Recordatorio de evento: {event_name}"
        body = (
            f"Hola cliente #{client_id}, te recordamos que el evento '{event_name}' "
            f"iniciará el {formatted_date}."
        )

        if client_id in self.failing_client_ids:
            return EmailDeliveryResult(
                success=False,
                result_status="fallido",
                recipient_client_id=client_id,
                subject=subject,
                body=body,
                sent_at=now,
                error_detail="Fallo al entregar el correo por el proveedor externo."
            )

        record = {
            "client_id": client_id,
            "subject": subject,
            "body": body,
            "sent_at": now,
        }
        self.sent_emails.append(record)

        return EmailDeliveryResult(
            success=True,
            result_status="enviado",
            recipient_client_id=client_id,
            subject=subject,
            body=body,
            sent_at=now,
            error_detail=None
        )

    def reset(self) -> None:
        self.service_available = True
        self.failing_client_ids.clear()
        self.sent_emails.clear()


email_gateway = EmailGatewayClient()
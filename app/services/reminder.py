# app/services/reminder.py
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.core.email_gateway import (
    EmailGatewayClient,
    EmailServiceUnavailableError,
    email_gateway,
)
from app.core.errors import ReglaNegocioError
from app.domain.reminder import ReminderDispatchData, ReminderLogItem
from app.repositories.enrollment import EnrollmentRepository
from app.repositories.event import EventRepository
from app.repositories.reminder import ReminderRepository


class ReminderService:
    def __init__(
        self,
        event_repo: EventRepository,
        enrollment_repo: EnrollmentRepository,
        reminder_repo: ReminderRepository,
        gateway: EmailGatewayClient = email_gateway,
    ):
        self.event_repo = event_repo
        self.enrollment_repo = enrollment_repo
        self.reminder_repo = reminder_repo
        self.gateway = gateway

    def dispatch_reminders(self, force: bool = False) -> ReminderDispatchData:
        if not self.gateway.service_available:
            raise ReglaNegocioError(
                "Servicio interno de eventos o inscripciones no disponible.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        now = datetime.now(timezone.utc)
        last_check = self.reminder_repo.get_last_check_at()

        # CA1: Si ya hubo una revisión previa y no ha pasado al menos 1 hora (y no es forzado)
        if not force and last_check is not None:
            elapsed = now - last_check
            if elapsed < timedelta(hours=1):
                return ReminderDispatchData(
                    evaluated_events_count=0,
                    reminders_sent_count=0,
                    reminders_failed_count=0,
                    last_check_at=last_check,
                    reminders=[]
                )

        # Identificar eventos que inician dentro de las próximas 24 horas
        window_end = now + timedelta(hours=24)
        upcoming_events = []
        for event in getattr(self.event_repo, "_events_db", []):
            ev_date: datetime = event["event_date"]
            ev_date_aware = ev_date if ev_date.tzinfo else ev_date.replace(tzinfo=timezone.utc)
            if now < ev_date_aware <= window_end:
                upcoming_events.append((event, ev_date_aware))

        processed_items: List[ReminderLogItem] = []
        sent_count = 0
        failed_count = 0

        for event, ev_date_aware in upcoming_events:
            # CA1: Consultar inscripciones en estado 'confirmada'
            confirmed_enrollments = self.enrollment_repo.get_confirmed_by_event_id(event["id"])

            for enrollment in confirmed_enrollments:
                enrollment_id = enrollment["id"]

                # CA4: No enviar otro recordatorio si ya fue enviado para esta inscripción
                if self.reminder_repo.has_sent_reminder(enrollment_id=enrollment_id, channel="email"):
                    continue

                # CA2: Enviar correo por inscripción con nombre, fecha y hora del evento
                try:
                    delivery = self.gateway.send_event_reminder(
                        client_id=enrollment["client_id"],
                        event_name=event["name"],
                        event_date=ev_date_aware,
                    )
                except EmailServiceUnavailableError:
                    raise ReglaNegocioError(
                        "Servicio externo de correo no disponible. Intente más tarde.",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                    )

                # CA3: Registrar el envío con ID de inscripción, canal, fecha/hora y resultado
                saved_log = self.reminder_repo.create_log({
                    "enrollment_id": enrollment_id,
                    "event_id": event["id"],
                    "client_id": enrollment["client_id"],
                    "channel": "email",
                    "sent_at": delivery.sent_at,
                    "result": delivery.result_status,
                })

                if delivery.result_status == "enviado":
                    sent_count += 1
                else:
                    failed_count += 1

                processed_items.append(ReminderLogItem(**saved_log))

        self.reminder_repo.set_last_check_at(now)

        return ReminderDispatchData(
            evaluated_events_count=len(upcoming_events),
            reminders_sent_count=sent_count,
            reminders_failed_count=failed_count,
            last_check_at=now,
            reminders=processed_items
        )
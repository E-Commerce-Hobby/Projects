# app/api/reminder.py
from fastapi import APIRouter, status
from app.core.email_gateway import email_gateway
from app.domain.reminder import (
    ReminderDispatchRequest,
    ReminderStandardResponse,
)
from app.repositories.enrollment import enrollment_repository
from app.repositories.event import event_repository
from app.repositories.reminder import reminder_repository
from app.services.reminder import ReminderService

router = APIRouter(
    prefix="/api/v1/events/reminders",
    tags=["Events - Reminders (MOD-06)"]
)

reminder_service = ReminderService(
    event_repo=event_repository,
    enrollment_repo=enrollment_repository,
    reminder_repo=reminder_repository,
    gateway=email_gateway,
)


@router.post(
    "/dispatch",
    response_model=ReminderStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar recordatorios por correo a inscritos en eventos próximos (HU-038)",
    description=(
        "Proceso del sistema (FUN-6.1.5) que identifica eventos que inician en las próximas 24 horas "
        "(cuando ha transcurrido al menos 1 hora desde la última revisión), consulta inscripciones "
        "'confirmadas' sin recordatorio enviado y despacha correos con nombre, fecha y hora del evento."
    ),
    responses={
        200: {
            "description": "Revisión y envío de recordatorios completados exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "evaluated_events_count": 1,
                            "reminders_sent_count": 2,
                            "reminders_failed_count": 0,
                            "last_check_at": "2026-11-23T18:00:00Z",
                            "reminders": [
                                {
                                    "id": 1,
                                    "enrollment_id": 10,
                                    "event_id": 3,
                                    "client_id": 25,
                                    "channel": "email",
                                    "sent_at": "2026-11-23T18:00:01Z",
                                    "result": "enviado"
                                }
                            ]
                        },
                        "message": "Recordatorios procesados correctamente."
                    }
                }
            }
        },
        503: {
            "description": "Servicio interno o externo de correo no disponible",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Servicio externo de correo no disponible. Intente más tarde."
                    }
                }
            }
        }
    }
)
def dispatch_reminders_endpoint(payload: ReminderDispatchRequest = ReminderDispatchRequest()):
    result_data = reminder_service.dispatch_reminders(force=payload.force)
    message = (
        "No hay recordatorios pendientes por enviar."
        if result_data.reminders_sent_count == 0 and result_data.reminders_failed_count == 0
        else "Recordatorios procesados correctamente."
    )
    return ReminderStandardResponse(
        success=True,
        data=result_data,
        message=message
    )
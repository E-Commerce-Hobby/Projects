# app/domain/reminder.py
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ReminderDispatchRequest(BaseModel):
    force: bool = Field(
        default=False,
        description=(
            "Si es true, omite la espera de 1 hora desde la última revisión "
            "(útil para pruebas o ejecución manual)."
        ),
        examples=[False]
    )


class ReminderLogItem(BaseModel):
    id: int = Field(..., description="ID del registro de envío", examples=[1])
    enrollment_id: int = Field(..., description="ID de la inscripción asociada", examples=[10])
    event_id: int = Field(..., description="ID del evento próximo", examples=[3])
    client_id: int = Field(..., description="ID del cliente inscrito", examples=[25])
    channel: Literal["email"] = Field(default="email", description="Canal de envío (solo correo)")
    sent_at: datetime = Field(..., description="Fecha y hora del intento de envío")
    result: Literal["enviado", "fallido"] = Field(..., description="Resultado del envío", examples=["enviado"])


class ReminderDispatchData(BaseModel):
    evaluated_events_count: int = Field(..., description="Cantidad de eventos próximos evaluados", examples=[1])
    reminders_sent_count: int = Field(..., description="Cantidad de recordatorios enviados con éxito", examples=[2])
    reminders_failed_count: int = Field(..., description="Cantidad de envíos fallidos registrados", examples=[0])
    last_check_at: Optional[datetime] = Field(None, description="Marca de tiempo de la última revisión")
    reminders: List[ReminderLogItem] = Field(
        default_factory=list,
        description="Registro detallado de los recordatorios procesados en la ejecución"
    )


class ReminderStandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la ejecución completó sin fallos críticos")
    data: Optional[ReminderDispatchData] = Field(
        None,
        description="Resumen y registro de recordatorios enviados, o null ante error"
    )
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje en español de máximo 200 caracteres"
    )
# app/domain/enrollment.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, StrictInt


class EnrollmentCancelRequest(BaseModel):
    enrollment_id: StrictInt = Field(
        ...,
        gt=0,
        description="ID numérico de la inscripción a cancelar",
        examples=[101]
    )


class EnrollmentCancelResponseData(BaseModel):
    enrollment_id: int = Field(..., description="ID de la inscripción", examples=[101])
    event_id: int = Field(..., description="ID del evento asociado", examples=[1])
    client_id: int = Field(..., description="ID del cliente titular de la inscripción", examples=[10])
    status: str = Field(..., description="Estado actual de la inscripción", examples=["cancelado"])
    available_spots: int = Field(
        ...,
        description="Cupos disponibles actualizados del evento tras liberar el cupo (RN-04)",
        examples=[16]
    )
    cancelled_at: datetime = Field(..., description="Fecha y hora en que se realizó la cancelación")


class EnrollmentStandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    data: Optional[EnrollmentCancelResponseData] = Field(
        None,
        description="Datos de la inscripción cancelada y cupos disponibles, o null si hubo error"
    )
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje descriptivo en español (máximo 200 caracteres)"
    )
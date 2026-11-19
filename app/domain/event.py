# app/domain/event.py
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, StrictInt, field_validator


class EventCreateRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre del torneo o curso (1 a 100 caracteres)",
        examples=["Torneo Nacional de Catan"]
    )
    event_date: datetime = Field(
        ...,
        description="Fecha y hora del evento en formato ISO 8601 (posterior a la actual)",
        examples=["2027-05-15T14:00:00Z"]
    )
    max_capacity: StrictInt = Field(
        ...,
        description="Capacidad máxima de asistentes (entero >= 1, RN-04)",
        examples=[32]
    )
    registration_price: float = Field(
        ...,
        description="Precio de inscripción en COP (>= 0, 0 significa gratuito)",
        examples=[25000.0]
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El nombre del evento no puede estar vacío.")
        return cleaned

    @field_validator("event_date")
    @classmethod
    def validate_future_date(cls, value: datetime) -> datetime:
        now = datetime.now(timezone.utc) if value.tzinfo else datetime.now()
        if value <= now:
            raise ValueError("La fecha es inválida: debe ser posterior al momento actual.")
        return value

    @field_validator("max_capacity")
    @classmethod
    def validate_capacity_rn04(cls, value: int) -> int:
        if value < 1:
            raise ValueError("La capacidad es inválida (RN-04): debe ser un entero mayor o igual a 1.")
        return value

    @field_validator("registration_price")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value < 0:
            raise ValueError("El precio de inscripción no puede ser negativo (debe ser mayor o igual a 0).")
        return value


class EventResponseData(BaseModel):
    id: int = Field(..., description="ID único del evento", examples=[1])
    name: str = Field(..., description="Nombre del evento", examples=["Torneo Nacional de Catan"])
    event_date: datetime = Field(..., description="Fecha y hora programada", examples=["2027-05-15T14:00:00Z"])
    max_capacity: int = Field(..., description="Capacidad máxima del evento", examples=[32])
    available_spots: int = Field(..., description="Cupos disponibles (inicialmente igual a capacidad)", examples=[32])
    registration_price: float = Field(..., description="Precio de inscripción en COP", examples=[25000.0])
    currency: str = Field(default="COP", description="Moneda del precio", examples=["COP"])


class StandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    data: Optional[EventResponseData] = Field(None, description="Datos del evento creado o null en caso de error")
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje descriptivo en español (máximo 200 caracteres)"
    )
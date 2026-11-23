# app/domain/enrollment.py
from datetime import datetime
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, StrictInt, field_validator


# --- Esquemas HU-018 (FUN-6.1.2 y FUN-6.1.3) ---

class EnrollmentCreateRequest(BaseModel):
    event_id: StrictInt = Field(
        ...,
        gt=0,
        description="ID del evento al que desea inscribirse",
        examples=[1]
    )
    client_id: StrictInt = Field(
        ...,
        gt=0,
        description="ID del cliente que realiza la inscripción",
        examples=[10]
    )
    payment_method: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Método de pago (CARD, PSE, NEQUI, CASH, FREE). Use DECLINED para simular rechazo.",
        examples=["PSE"]
    )

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: str) -> str:
        cleaned = value.strip().upper()
        allowed = {"CARD", "PSE", "NEQUI", "CASH", "FREE", "DECLINED", "REJECTED", "INSUFFICIENT_FUNDS"}
        if cleaned not in allowed:
            raise ValueError(
                "Método de pago inválido. Valores permitidos: CARD, PSE, NEQUI, CASH, FREE."
            )
        return cleaned


class EnrollmentCreateResponseData(BaseModel):
    enrollment_id: int = Field(..., description="ID único de la inscripción", examples=[1])
    status: str = Field(..., description="Estado de la inscripción", examples=["confirmada"])
    event_id: int = Field(..., description="ID del evento", examples=[1])
    client_id: int = Field(..., description="ID del cliente", examples=[10])
    amount_paid: float = Field(..., description="Monto cobrado en COP", examples=[25000.0])
    transaction_id: Optional[str] = Field(None, description="Referencia de pago", examples=["TX-9A8B7C6D5E"])
    available_spots: int = Field(..., description="Cupos disponibles restantes en el evento", examples=[31])


class QuotaValidationResponseData(BaseModel):
    event_id: int = Field(..., description="ID del evento evaluado", examples=[1])
    result: Literal["autorizada", "rechazada"] = Field(
        ...,
        description="Resultado de validación de cupo (FUN-6.1.3)",
        examples=["autorizada"]
    )
    reason: str = Field(..., description="Motivo de autorización o rechazo", examples=["Evento disponible con cupos."])
    available_spots: int = Field(..., description="Cupos disponibles actuales", examples=[32])


# --- Esquemas HU-037 (Cancelación) ---

class EnrollmentCancelResponseData(BaseModel):
    enrollment_id: int = Field(..., description="ID de la inscripción", examples=[1])
    event_id: int = Field(..., description="ID del evento asociado", examples=[1])
    client_id: int = Field(..., description="ID del cliente titular", examples=[10])
    status: str = Field(..., description="Estado actual de la inscripción", examples=["cancelado"])
    available_spots: int = Field(..., description="Cupos disponibles actualizados", examples=[16])
    cancelled_at: datetime = Field(..., description="Fecha y hora de cancelación")


# --- Contrato Estándar JSON del Tercer Corte ---

class EnrollmentCreateStandardResponse(BaseModel):
    success: bool
    data: Optional[EnrollmentCreateResponseData] = None
    message: str = Field(..., max_length=200)


class QuotaValidationStandardResponse(BaseModel):
    success: bool
    data: Optional[QuotaValidationResponseData] = None
    message: str = Field(..., max_length=200)


class EnrollmentStandardResponse(BaseModel):
    success: bool
    data: Optional[Union[EnrollmentCancelResponseData, EnrollmentCreateResponseData]] = None
    message: str = Field(..., max_length=200)
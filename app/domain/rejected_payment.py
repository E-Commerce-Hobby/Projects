# app/domain/rejected_payment.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, StrictInt, field_validator


class RejectedPaymentRequest(BaseModel):
    order_id: StrictInt = Field(
        ...,
        gt=0,
        description="ID numérico de la orden asociada al pago rechazado",
        examples=[1001]
    )
    transaction_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Identificador de la transacción entregado por la pasarela (Wompi / PayU)",
        examples=["TX-WOMPI-987654"]
    )
    rejection_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Código de rechazo informado por la pasarela (opcional)",
        examples=["ERR-51"]
    )
    rejection_description: Optional[str] = Field(
        default=None,
        max_length=250,
        description="Descripción del motivo de rechazo informada por la pasarela (opcional)",
        examples=["Fondos insuficientes en la cuenta"]
    )

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El campo 'transaction_id' no puede estar vacío.")
        return cleaned


class RejectedPaymentAttemptData(BaseModel):
    attempt_id: int = Field(..., description="ID único del registro de intento fallido", examples=[1])
    order_id: int = Field(..., description="ID de la orden", examples=[1001])
    transaction_id: str = Field(..., description="ID de la transacción rechazada", examples=["TX-WOMPI-987654"])
    rejection_code: Optional[str] = Field(None, description="Código de rechazo recibido", examples=["ERR-51"])
    reason: str = Field(
        ...,
        description="Motivo consolidado del rechazo o 'sin motivo informado' (CA1)",
        examples=["[ERR-51] Fondos insuficientes en la cuenta"]
    )
    recorded_at: datetime = Field(..., description="Fecha y hora del registro del intento fallido (CA2)")
    order_failed_attempts: int = Field(
        ...,
        description="Contador acumulado de intentos fallidos de la orden tras incrementarse en 1 (CA3)",
        examples=[1]
    )


class RejectedPaymentStandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si el registro fue exitoso")
    data: Optional[RejectedPaymentAttemptData] = Field(
        None,
        description="Datos del intento fallido y contador de la orden, o null si hubo error"
    )
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje descriptivo en español de máximo 200 caracteres"
    )
# app/domain/refund.py
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, StrictInt


class RefundCreateRequest(BaseModel):
    order_id: StrictInt = Field(
        ...,
        gt=0,
        description="ID numérico de la orden pagada a reembolsar totalmente",
        examples=[1001]
    )


class RefundResponseData(BaseModel):
    refund_id: int = Field(..., description="ID único del reembolso registrado", examples=[1])
    order_id: int = Field(..., description="ID de la orden reembolsada", examples=[1001])
    transaction_id: str = Field(..., description="ID de la transacción original", examples=["TX-WOMPI-12345"])
    refund_reference: Optional[str] = Field(None, description="Referencia emitida por la pasarela", examples=["REF-A1B2C3D4E5"])
    amount: float = Field(..., description="Monto total reembolsado en COP", examples=[120000.0])
    payment_status: Literal["aprobado", "reembolsado"] = Field(..., description="Estado actualizado del pago", examples=["reembolsado"])
    order_status: str = Field(..., description="Estado actualizado de la orden", examples=["reembolsada"])
    refund_status: Literal["reembolsado"] = Field(default="reembolsado", description="Estado del reembolso")
    processed_at: datetime = Field(..., description="Fecha y hora del reembolso")


class RefundStandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    data: Optional[RefundResponseData] = Field(
        None,
        description="Datos del reembolso (estado y monto) o null en caso de rechazo/error"
    )
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje descriptivo en español de máximo 200 caracteres"
    )
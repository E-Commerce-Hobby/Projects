# app/domain/inventory_retry.py
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, StrictInt, field_validator


class InventoryRetryLineItem(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=64, examples=["PROD-001"])
    location: str = Field(..., min_length=1, max_length=100, examples=["Bodega Virtual"])
    quantity: StrictInt = Field(..., gt=0, examples=[2])


class InventoryRetryRequest(BaseModel):
    operation_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Identificador de la operación fallida (si se omite, se genera automáticamente)",
        examples=["OP-VENTA-001"]
    )
    sale_id: str = Field(..., min_length=1, max_length=64, examples=["VEN-001"])
    channel: str = Field(..., description="Canal de origen ('virtual' o 'POS')", examples=["virtual"])
    lines: List[InventoryRetryLineItem] = Field(..., min_length=1, description="Líneas a descontar")
    simulate_temporary_failures: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Cantidad de intentos iniciales que fallarán por error temporal (para pruebas/simulación)",
        examples=[0]
    )
    service_unavailable: bool = Field(
        default=False,
        description="Si es true, simula indisponibilidad del servicio requerido (HTTP 503)",
        examples=[False]
    )

    @field_validator("sale_id")
    @classmethod
    def validate_sale_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El campo 'sale_id' no puede estar vacío.")
        return cleaned


class ManualReviewAlert(BaseModel):
    alert_id: int = Field(..., description="ID de la alerta generada", examples=[1])
    operation_id: str = Field(..., description="ID de la operación fallida", examples=["OP-VENTA-001"])
    reason: str = Field(..., description="Motivo del fallo que originó la alerta")
    created_at: datetime = Field(..., description="Fecha y hora de generación de la alerta")


class InventoryRetryData(BaseModel):
    operation_id: str = Field(..., description="ID de la operación procesada", examples=["OP-VENTA-001"])
    sale_id: str = Field(..., description="ID de la venta asociada", examples=["VEN-001"])
    status: Literal["exitosa", "fallida"] = Field(..., description="Estado final de la operación", examples=["exitosa"])
    attempts_used: int = Field(..., description="Intentos ejecutados (incluyendo reintentos)", examples=[1])
    last_error: Optional[str] = Field(None, description="Motivo del último error si quedó fallida")
    alert: Optional[ManualReviewAlert] = Field(None, description="Alerta de revisión manual si quedó fallida (CA4)")


class InventoryRetryStandardResponse(BaseModel):
    success: bool
    data: Optional[InventoryRetryData] = None
    message: str = Field(..., max_length=200)
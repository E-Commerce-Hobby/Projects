"""Domain schemas for inventory registration (HU-003) and adjustments (HU-025)."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

MOTIVOS_AJUSTE_PERMITIDOS = ("entrada", "salida", "conteo físico", "pérdida")


class InventoryCreate(BaseModel):
    """Input schema: data required to register initial inventory."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"product_id": 1, "location_id": 1, "quantity": 50}
        }
    )

    product_id: int = Field(..., gt=0, description="Product identifier")
    location_id: int = Field(..., gt=0, description="Store or warehouse identifier")
    quantity: int = Field(..., description="Initial quantity (integer >= 0)")

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value):
        """CA3: reject negative values and non-integers (including bool and float)."""
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(
                "La cantidad es inválida: debe ser un número entero mayor o igual a 0"
            )
        return value


class InventoryResponse(BaseModel):
    """Response schema: registered inventory confirmation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"product_id": 1, "location_id": 1, "quantity": 50}
        }
    )

    product_id: int = Field(..., description="Product identifier")
    location_id: int = Field(..., description="Store or warehouse identifier")
    quantity: int = Field(..., description="Registered quantity")


class InventoryAdjustmentCreate(BaseModel):
    """Input schema: data required to adjust inventory with a reason (HU-025)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": 1,
                "location_id": 1,
                "quantity": 10,
                "reason": "entrada",
            }
        }
    )

    product_id: int = Field(..., gt=0, description="Product identifier")
    location_id: int = Field(..., gt=0, description="Store or warehouse identifier")
    quantity: int = Field(..., description="Adjustment quantity (integer >= 0)")
    reason: Optional[str] = Field(
        default=None,
        description="Motivo del ajuste: entrada, salida, conteo físico o pérdida.",
    )


class InventoryMovementResponse(BaseModel):
    """Response schema: inventory movement recorded for an adjustment (HU-006 / HU-025)."""

    id: UUID = Field(default_factory=uuid4, description="Movement identifier")
    product_id: int = Field(..., description="Product identifier")
    location_id: int = Field(..., description="Store or warehouse identifier")
    reason: str = Field(..., description="Adjustment reason")
    quantity: int = Field(..., description="Quantity provided in the adjustment")
    previous_quantity: int = Field(..., description="Stock before adjustment")
    new_quantity: int = Field(..., description="Stock after adjustment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the movement was recorded",
    )


class InventoryAdjustmentResponse(BaseModel):
    """Response schema: updated inventory and recorded movement (HU-025)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": 1,
                "location_id": 1,
                "quantity": 60,
                "movement": {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "product_id": 1,
                    "location_id": 1,
                    "reason": "entrada",
                    "quantity": 10,
                    "previous_quantity": 50,
                    "new_quantity": 60,
                    "timestamp": "2026-11-25T21:50:00Z",
                },
            }
        }
    )

    product_id: int = Field(..., description="Product identifier")
    location_id: int = Field(..., description="Store or warehouse identifier")
    quantity: int = Field(..., description="Resulting inventory quantity")
    movement: InventoryMovementResponse = Field(
        ..., description="Recorded inventory movement"
    )


class ErrorResponse(BaseModel):
    """Error schema used to document error responses in Swagger."""

    mensaje: str = Field(..., max_length=200, description="Error description in Spanish")

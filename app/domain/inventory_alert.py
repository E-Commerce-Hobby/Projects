"""Domain schemas for low stock alerts (MOD-02 / FUN-2.1.4 / HU-026)."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

INTERVALO_REVISION_MINUTOS = 60


class MinStockConfigRequest(BaseModel):
    """Input schema: minimum stock configuration for a product."""

    model_config = ConfigDict(json_schema_extra={"example": {"min_stock": 10}})

    min_stock: int = Field(
        ...,
        description="Stock mínimo configurado para el producto (entero >= 0).",
    )


class MinStockConfigResponse(BaseModel):
    """Response schema: confirmed minimum stock configuration."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"product_id": 1, "min_stock": 10}}
    )

    product_id: int = Field(..., description="Product identifier")
    min_stock: int = Field(..., ge=0, description="Configured minimum stock")


class LowStockAlertResponse(BaseModel):
    """Response schema: low stock alert (CA2)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "product_id": 1,
                "current_quantity": 3,
                "min_stock": 10,
                "created_at": "2026-11-25T22:00:00Z",
                "status": "pendiente",
            }
        }
    )

    id: UUID = Field(default_factory=uuid4, description="Alert identifier")
    product_id: int = Field(..., description="Product identifier")
    current_quantity: int = Field(..., description="Current available quantity")
    min_stock: int = Field(..., ge=0, description="Configured minimum stock")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the alert was generated",
    )
    status: str = Field(default="pendiente", description="Alert status")


class AlertCheckResultResponse(BaseModel):
    """Response schema: result of a periodic low-stock check (CA1)."""

    executed: bool = Field(
        ..., description="Indicates whether the 60-minute check ran"
    )
    checked_products: int = Field(
        ..., ge=0, description="Number of products with min stock evaluated"
    )
    generated_alerts: list[LowStockAlertResponse] = Field(
        default_factory=list,
        description="New pending alerts generated during this check",
    )
    last_check_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp of the last executed check"
    )

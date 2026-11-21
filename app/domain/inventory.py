"""Domain schemas for the initial inventory registration (MOD-02 / FUN-2.1.1)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ErrorResponse(BaseModel):
    """Error schema used to document error responses in Swagger."""

    mensaje: str = Field(..., max_length=200, description="Error description in Spanish")
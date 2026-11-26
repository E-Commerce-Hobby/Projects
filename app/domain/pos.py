"""Pydantic schemas for the POS module (barcode search, counter sales, discounts and cash closing)."""
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BARCODE_REGEX = re.compile(r"^[A-Za-z0-9]{1,50}$")
INVALID_BARCODE_MESSAGE = (
    "El código es inválido: debe tener solo letras y números (máximo 50) "
    "y no puede estar vacío."
)


def _validate_barcode(value: str) -> str:
    if not value or not BARCODE_REGEX.fullmatch(value):
        raise ValueError(INVALID_BARCODE_MESSAGE)
    return value


# ---------------------------------------------------------------------------
# Request schemas (input)
# ---------------------------------------------------------------------------
class BarcodeSearchRequest(BaseModel):
    """Query params for FUN-4.2.1."""

    barcode: str = Field(description="Código de barras del producto.", examples=["7701234567890"])

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, value: str) -> str:
        return _validate_barcode(value)


class SaleItemRequest(BaseModel):
    product_code: str = Field(description="Código del producto vendido.", examples=["7701234567890"])
    quantity: int = Field(description="Cantidad vendida (entero mayor a 0).", examples=[2])

    @field_validator("product_code")
    @classmethod
    def validate_product_code(cls, value: str) -> str:
        return _validate_barcode(value)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La cantidad debe ser un entero mayor a 0.")
        return value


class SaleCreateRequest(BaseModel):
    """Body for FUN-4.2.2."""

    cash_register_id: int = Field(description="ID de la caja donde se registra la venta.", examples=[1])
    products: list[SaleItemRequest] = Field(description="Productos vendidos en el mostrador.")
    payment_method: str = Field(
        default="efectivo",
        min_length=1,
        max_length=50,
        description="Medio de pago utilizado en la venta (ej. efectivo, tarjeta, transferencia).",
        examples=["efectivo"],
    )

    @field_validator("cash_register_id")
    @classmethod
    def validate_cash_register_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("El ID de caja debe ser un entero positivo.")
        return value

    @field_validator("products")
    @classmethod
    def validate_products_not_empty(cls, value: list[SaleItemRequest]) -> list[SaleItemRequest]:
        if not value:
            raise ValueError("La venta no tiene productos.")
        return value

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: str) -> str:
        limpio = (value or "").strip().lower()
        if not limpio:
            raise ValueError("El medio de pago no puede estar vacío.")
        return limpio

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cash_register_id": 1,
                "products": [{"product_code": "7701234567890", "quantity": 2}],
                "payment_method": "efectivo",
            }
        }
    )


# ---------------------------------------------------------------------------
# Response schemas (output)
# ---------------------------------------------------------------------------
class ProductInfo(BaseModel):
    code: str
    category: str
    features: dict[str, str]


class ProductSearchResponse(BaseModel):
    product: ProductInfo
    price: float = Field(description="Precio unitario.")
    available_quantity: int = Field(description="Cantidad disponible en el punto de venta.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product": {
                    "code": "7701234567890",
                    "category": "Bebidas",
                    "features": {"marca": "Aqua", "presentacion": "600 ml"},
                },
                "price": 2500.0,
                "available_quantity": 15,
            }
        }
    )


class SaleItemResponse(BaseModel):
    product_code: str
    quantity: int
    unit_price: float
    subtotal: float


class SaleResponse(BaseModel):
    id: int
    products: list[SaleItemResponse]
    total: float
    mensaje: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "products": [
                    {"product_code": "7701234567890", "quantity": 2, "unit_price": 2500.0, "subtotal": 5000.0}
                ],
                "total": 5000.0,
                "mensaje": "Venta registrada correctamente.",
            }
        }
    )


class ErrorResponse(BaseModel):
    mensaje: str = Field(max_length=200, description="Descripción del error en español.")


# ---------------------------------------------------------------------------
# Internal entities (stored by the repository, never exposed directly)
# ---------------------------------------------------------------------------
class ProductRecord(BaseModel):
    code: str
    category: str
    features: dict[str, str]
    price: float


class CashRegisterRecord(BaseModel):
    id: int
    cashier_id: int
    is_open: bool
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SaleLineRecord(BaseModel):
    product_code: str
    quantity: int
    unit_price: float
    subtotal: float


class SaleRecord(BaseModel):
    id: int | None = None
    cash_register_id: int
    cashier_id: int
    lines: list[SaleLineRecord]
    total: float
    created_at: datetime
    payment_method: str = Field(default="efectivo")
    applied_discount_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HU-031 (FUN-4.2.3): Aplicación de descuentos en venta POS
# ---------------------------------------------------------------------------
class ApplyDiscountRequest(BaseModel):
    """Body para FUN-4.2.3: aplicar un descuento vigente a una venta POS."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"example": {"discount_id": "DESC10"}},
    )

    discount_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ID del descuento a aplicar a la venta de mostrador.",
        examples=["DESC10"],
    )

    @field_validator("discount_id")
    @classmethod
    def validate_discount_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El ID de descuento no puede estar vacío.")
        return value.strip().upper()


class AppliedDiscountInfo(BaseModel):
    id: str
    discount_type: Literal["percentage", "fixed"]
    value: float
    amount_discounted: float


class SaleDiscountResponse(BaseModel):
    id: int
    products: list[SaleItemResponse]
    applied_discount: AppliedDiscountInfo
    applied_discount_ids: list[str]
    previous_total: float
    total: float
    mensaje: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "products": [
                    {
                        "product_code": "7701234567890",
                        "quantity": 2,
                        "unit_price": 2500.0,
                        "subtotal": 5000.0,
                    }
                ],
                "applied_discount": {
                    "id": "DESC10",
                    "discount_type": "percentage",
                    "value": 10.0,
                    "amount_discounted": 500.0,
                },
                "applied_discount_ids": ["DESC10"],
                "previous_total": 5000.0,
                "total": 4500.0,
                "mensaje": "Descuento aplicado correctamente a la venta.",
            }
        }
    )


class DiscountRecord(BaseModel):
    id: str
    discount_type: Literal["percentage", "fixed"]
    value: float
    valid_from: datetime
    valid_until: datetime


# ---------------------------------------------------------------------------
# HU-032 (FUN-4.2.4): Cierre de caja
# ---------------------------------------------------------------------------
class CashRegisterClosingRecord(BaseModel):
    id: int | None = None
    cash_register_id: int
    cashier_id: int
    opened_at: datetime
    closed_at: datetime
    totals_by_payment_method: dict[str, float]
    general_total: float
    sales_count: int


class CashRegisterClosingResponse(BaseModel):
    id: int = Field(description="Identificador del cierre de caja registrado.")
    cash_register_id: int = Field(description="ID de la caja cerrada.")
    cashier_id: int = Field(description="ID del cajero responsable del turno.")
    opened_at: datetime = Field(description="Fecha y hora UTC de apertura de la caja.")
    closed_at: datetime = Field(description="Fecha y hora UTC del cierre de la caja.")
    totals_by_payment_method: dict[str, float] = Field(
        description="Total recaudado por cada medio de pago durante el turno."
    )
    general_total: float = Field(
        description="Total general del turno (suma de los totales por medio de pago)."
    )
    sales_count: int = Field(description="Cantidad de ventas consolidadas en el turno.")
    status: str = Field(default="cerrada", description="Estado final de la caja.")
    mensaje: str = Field(description="Confirmación del cierre de caja.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "cash_register_id": 1,
                "cashier_id": 10,
                "opened_at": "2026-11-25T14:00:00Z",
                "closed_at": "2026-11-25T22:00:00Z",
                "totals_by_payment_method": {
                    "efectivo": 5000.0,
                    "tarjeta": 8400.0,
                },
                "general_total": 13400.0,
                "sales_count": 2,
                "status": "cerrada",
                "mensaje": "Cierre de caja registrado correctamente.",
            }
        }
    )

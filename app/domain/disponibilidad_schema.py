from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ItemSolicitudStock(BaseModel):
    """Producto y cantidad solicitada para verificación de venta o carrito."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_producto: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador o código del producto.",
        examples=["PROD-001"],
    )
    cantidad: StrictInt = Field(
        ...,
        gt=0,
        description="Cantidad entera mayor o igual a 1.",
        examples=[2],
    )


class VerificarVentaRequest(BaseModel):
    """Entrada para FUN-2.2.3 (verificación previa al cobro)."""

    canal: Literal["ecommerce", "pos"] = Field(
        default="ecommerce",
        description="Canal de origen de la solicitud de venta.",
        examples=["ecommerce"],
    )
    productos: list[ItemSolicitudStock] = Field(
        ...,
        min_length=1,
        description="Lista de productos y cantidades solicitadas.",
    )


class ValidarCarritoRequest(BaseModel):
    """Entrada para FUN-4.1.2 (validación de disponibilidad del carrito)."""

    productos: list[ItemSolicitudStock] = Field(
        default_factory=list,
        description="Lista de productos del carrito a confirmar.",
    )
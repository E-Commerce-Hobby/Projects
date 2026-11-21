from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CarritoAgregarRequest(BaseModel):
    """Datos de entrada para agregar un producto al carrito (CA1-CA4)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_producto: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador o código del producto.",
        examples=["PROD-001"],
    )
    cantidad: Any = Field(
        ...,
        description="Cantidad entera mayor o igual a 1.",
        examples=[2],
    )


class CarritoModificarRequest(BaseModel):
    """Datos de entrada para modificar la cantidad de un producto en el carrito (CA5-CA7)."""

    nueva_cantidad: Any = Field(
        ...,
        description="Nueva cantidad entera mayor o igual a 1.",
        examples=[3],
    )


class LineaCarritoRespuesta(BaseModel):
    id_producto: str
    nombre: str
    precio_unitario: float
    cantidad: int
    subtotal: float


class CarritoRespuesta(BaseModel):
    lineas: list[LineaCarritoRespuesta]
    valor_total: float
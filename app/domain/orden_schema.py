from pydantic import BaseModel, ConfigDict, Field, StrictInt
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt

class ItemOrdenRequest(BaseModel):
    """Producto y cantidad confirmada para crear la orden."""

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


class CrearOrdenRequest(BaseModel):
    """Entrada para FUN-4.1.3 (creación de orden a partir del carrito)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_cliente: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador del cliente registrado en el módulo Clientes.",
        examples=["CLI-001"],
    )
    productos: list[ItemOrdenRequest] = Field(
        default_factory=list,
        description="Lista de productos confirmados del carrito.",
    )


class CalcularTotalRequest(BaseModel):
    """Entrada opcional para FUN-4.1.4 (códigos de descuento a evaluar)."""

    codigos_descuento: list[str] = Field(
        default_factory=list,
        description="Códigos de descuento a aplicar si están vigentes en la fecha actual.",
        examples=[["DESC10"]],
    )
    
class ActualizarEstadoOrdenRequest(BaseModel):
    """Entrada para FUN-4.1.5 (notificación de Pagos o Logística)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    origen: Literal["Pagos", "Logística"] = Field(
        ...,
        description="Módulo que envía la notificación.",
        examples=["Pagos"],
    )
    evento: Literal[
        "pago aprobado",
        "pago rechazado",
        "envío despachado",
        "envío entregado",
    ] = Field(
        ...,
        description="Evento reportado por el módulo de origen.",
        examples=["pago aprobado"],
    )
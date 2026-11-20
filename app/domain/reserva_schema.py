from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ReservaCreacion(BaseModel):
    """Datos de entrada para solicitar una reserva temporal (HU-004)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_producto: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador o código del producto a reservar.",
        examples=["PROD-001"],
    )
    cantidad: StrictInt = Field(
        ...,
        gt=0,
        description="Cantidad entera mayor a 0 de unidades a reservar.",
        examples=[2],
    )


class ReservaRespuesta(BaseModel):
    """Datos de salida de una reserva temporal confirmada."""

    id: int
    id_producto: str
    cantidad: int
    fecha_expiracion: datetime
    estado: Literal["activa", "expirada", "confirmada"]
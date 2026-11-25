from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class ProductoRegistro(BaseModel):
    """Datos de entrada para registrar un producto (CA1, CA3, CA4)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo: str = Field(
        ...,
        min_length=1,
        max_length=30,
        pattern=r"^[A-Za-z0-9-]+$",
        description="Código único del producto. Máx. 30 caracteres: letras, números y guion.",
        examples=["PROD-001"],
    )
    categoria: str = Field(
        ...,
        min_length=1,
        description="Categoría del producto.",
        examples=["Electrónica"],
    )
    caracteristicas: dict[str, Any] = Field(
        ...,
        min_length=1,
        description="Características del producto (al menos una).",
        examples=[{"color": "negro", "peso_kg": 1.2}],
    )
    estado: Literal["activo", "inactivo"] = Field(
        ...,
        description="Estado del producto.",
        examples=["activo"],
    )


class ProductoActualizacion(BaseModel):
    """Datos de entrada para actualizar parcialmente un producto existente (HU-023)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        pattern=r"^[A-Za-z0-9-]+$",
        description="Nuevo código único del producto. Máx. 30 caracteres: letras, números y guion.",
        examples=["PROD-002"],
    )
    categoria: str | None = Field(
        default=None,
        min_length=1,
        description="Nueva categoría existente del producto.",
        examples=["miniaturas"],
    )
    caracteristicas: dict[str, Any] | None = Field(
        default=None,
        min_length=1,
        description="Nuevas características del producto (al menos una).",
        examples=[{"escala": "32mm", "material": "resina"}],
    )
    estado: Literal["activo", "inactivo"] | None = Field(
        default=None,
        description="Nuevo estado del producto ('activo' o 'inactivo').",
        examples=["activo"],
    )

    @model_validator(mode="after")
    def validar_al_menos_un_campo(self) -> "ProductoActualizacion":
        if (
            self.codigo is None
            and self.categoria is None
            and self.caracteristicas is None
            and self.estado is None
        ):
            raise ValueError("Debe enviar al menos un campo para actualizar el producto.")
        return self


class ProductoRespuesta(BaseModel):
    """Datos de salida: solo los campos que el contrato permite exponer."""

    id: UUID
    codigo: str
    categoria: str
    caracteristicas: dict[str, Any]
    estado: Literal["activo", "inactivo"]


class ErrorRespuesta(BaseModel):
    """Formato provisional de error (pendiente de definición en el tercer corte)."""

    mensaje: str = Field(..., max_length=200)
    campos_faltantes: list[str] | None = None
    campos_invalidos: list[str] | None = None


class RespuestaEstandar(BaseModel, Generic[T]):
    """Formato estándar de respuesta del proyecto."""

    success: bool
    message: str
    data: T | None = None

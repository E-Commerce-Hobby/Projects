from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
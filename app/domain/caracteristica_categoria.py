from threading import Lock
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CaracteristicaDefinida(BaseModel):
    """Característica ya definida para una categoría (solo lectura)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Nombre de la característica definida en la categoría.",
        examples=["escala"],
    )
    tipo_dato: str = Field(
        default="texto",
        min_length=1,
        max_length=40,
        description="Tipo esperado del valor de la característica.",
        examples=["texto", "numero", "booleano"],
    )
    obligatoria: bool = Field(
        default=False,
        description="Indica si la característica es obligatoria en la categoría.",
    )


class CaracteristicaAsociacionItem(BaseModel):
    """Par (nombre, valor) a asociar a un producto."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Nombre de la característica definida para la categoría del producto.",
        examples=["escala"],
    )
    valor: Any = Field(
        ...,
        description="Valor asignado a la característica para el producto.",
        examples=["28mm"],
    )


class AsociarCaracteristicasRequest(BaseModel):
    """Datos de entrada para asociar características a un producto."""

    model_config = ConfigDict(str_strip_whitespace=True)

    caracteristicas: list[CaracteristicaAsociacionItem] = Field(
        ...,
        min_length=1,
        description="Lista de características (nombre, valor) a asociar al producto.",
        examples=[
            [
                {"nombre": "escala", "valor": "28mm"},
                {"nombre": "material", "valor": "resina"},
            ]
        ],
    )


class CaracteristicasCategoriaData(BaseModel):
    """Salida para CA1: características definidas de la categoría del producto."""

    producto_id: UUID
    categoria: str
    caracteristicas: list[CaracteristicaDefinida]


class AsociacionCaracteristicasData(BaseModel):
    """Salida para CA2: confirmación y producto con características asociadas."""

    producto_id: UUID
    codigo: str
    categoria: str
    caracteristicas_asociadas: dict[str, Any]
    caracteristicas_producto: dict[str, Any]


class RegistroAsociacionInterno:
    """Registro interno en memoria de asociaciones por producto."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._asociaciones_por_producto: dict[UUID, dict[str, Any]] = {}

    def guardar(self, producto_id: UUID, valores: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            actuales = dict(self._asociaciones_por_producto.get(producto_id, {}))
            actuales.update(valores)
            self._asociaciones_por_producto[producto_id] = actuales
            return dict(actuales)

    def obtener(self, producto_id: UUID) -> dict[str, Any]:
        with self._lock:
            return dict(self._asociaciones_por_producto.get(producto_id, {}))
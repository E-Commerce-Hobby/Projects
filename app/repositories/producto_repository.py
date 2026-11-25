from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from app.domain.producto import ProductoRegistro, ProductoRespuesta


class ProductoRepository:
    """Repositorio en memoria. Solo acceso a datos, sin lógica de negocio."""

    def __init__(self) -> None:
        self._productos: dict[UUID, ProductoRespuesta] = {}
        self._lock = Lock()

    def crear(self, datos: ProductoRegistro) -> ProductoRespuesta:
        with self._lock:
            producto = ProductoRespuesta(id=uuid4(), **datos.model_dump())
            self._productos[producto.id] = producto
            return producto

    def obtener_por_id(self, producto_id: UUID) -> ProductoRespuesta | None:
        with self._lock:
            return self._productos.get(producto_id)

    def obtener_por_codigo(self, codigo: str) -> ProductoRespuesta | None:
        with self._lock:
            return next(
                (p for p in self._productos.values() if p.codigo == codigo),
                None,
            )

    def listar(self) -> list[ProductoRespuesta]:
        with self._lock:
            return list(self._productos.values())

    def actualizar(
        self, producto_id: UUID, cambios: dict[str, Any]
    ) -> ProductoRespuesta | None:
        with self._lock:
            actual = self._productos.get(producto_id)
            if actual is None:
                return None

            datos_actualizados = actual.model_dump()
            datos_actualizados.update(cambios)
            producto_actualizado = ProductoRespuesta(**datos_actualizados)
            self._productos[producto_id] = producto_actualizado
            return producto_actualizado

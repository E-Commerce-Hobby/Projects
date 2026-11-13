from uuid import UUID, uuid4

from app.domain.producto import ProductoRegistro, ProductoRespuesta


class ProductoRepository:
    """Repositorio en memoria. Solo acceso a datos, sin lógica de negocio."""

    def __init__(self) -> None:
        self._productos: dict[UUID, ProductoRespuesta] = {}

    def crear(self, datos: ProductoRegistro) -> ProductoRespuesta:
        producto = ProductoRespuesta(id=uuid4(), **datos.model_dump())
        self._productos[producto.id] = producto
        return producto

    def obtener_por_id(self, producto_id: UUID) -> ProductoRespuesta | None:
        return self._productos.get(producto_id)

    def obtener_por_codigo(self, codigo: str) -> ProductoRespuesta | None:
        return next(
            (p for p in self._productos.values() if p.codigo == codigo),
            None,
        )

    def listar(self) -> list[ProductoRespuesta]:
        return list(self._productos.values())
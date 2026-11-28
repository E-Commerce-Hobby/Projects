from threading import Lock
from uuid import UUID

from app.domain.imagen_producto import ImagenProductoRespuesta


class ImagenProductoRepository:
    """Repositorio en memoria thread-safe para imágenes asociadas a productos."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._imagenes_por_id: dict[UUID, ImagenProductoRespuesta] = {}
        self._contenidos_por_id: dict[UUID, bytes] = {}
        self._ids_por_producto: dict[UUID, list[UUID]] = {}

    def guardar(
        self, imagen: ImagenProductoRespuesta, contenido: bytes
    ) -> ImagenProductoRespuesta:
        with self._lock:
            self._imagenes_por_id[imagen.id] = imagen
            self._contenidos_por_id[imagen.id] = contenido
            self._ids_por_producto.setdefault(imagen.producto_id, []).append(imagen.id)
            return imagen

    def listar_por_producto(self, producto_id: UUID) -> list[ImagenProductoRespuesta]:
        with self._lock:
            ids = self._ids_por_producto.get(producto_id, [])
            return [self._imagenes_por_id[img_id] for img_id in ids]

    def obtener_por_id(self, imagen_id: UUID) -> ImagenProductoRespuesta | None:
        with self._lock:
            return self._imagenes_por_id.get(imagen_id)

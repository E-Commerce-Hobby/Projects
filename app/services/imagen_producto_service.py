from uuid import UUID

from fastapi import status

from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.imagen_producto import (
    ImagenProductoRespuesta,
    MAX_TAMANO_IMAGEN_BYTES,
)
from app.repositories.imagen_producto_repository import ImagenProductoRepository
from app.repositories.producto_repository import ProductoRepository


def detectar_formato_imagen(contenido: bytes) -> str | None:
    """Detecta el formato real de la imagen inspeccionando sus magic bytes."""
    if len(contenido) >= 3 and contenido[:3] == b"\xff\xd8\xff":
        return "JPG"
    if len(contenido) >= 8 and contenido[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if len(contenido) >= 12 and contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "WEBP"
    return None


class ImagenProductoService:
    """Lógica de negocio para asociar imágenes válidas a un producto (HU-024)."""

    def __init__(
        self,
        producto_repo: ProductoRepository,
        imagen_repo: ImagenProductoRepository,
    ) -> None:
        self._producto_repo = producto_repo
        self._imagen_repo = imagen_repo

    def asociar_imagen(
        self,
        producto_id: UUID,
        contenido: bytes,
        nombre_archivo: str = "imagen",
    ) -> ImagenProductoRespuesta:
        # CA3: Verificar que el producto exista
        producto = self._producto_repo.obtener_por_id(producto_id)
        if producto is None:
            raise RecursoNoEncontradoError(
                f"El producto con id '{producto_id}' no existe."[:200]
            )

        # CA2: Rechazar archivo vacío
        if not contenido:
            raise ReglaNegocioError(
                message="Archivo inválido: el archivo de imagen está vacío.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # CA2: Validar tamaño máximo (5 MB)
        tamano = len(contenido)
        if tamano > MAX_TAMANO_IMAGEN_BYTES:
            raise ReglaNegocioError(
                message=(
                    "Tamaño inválido: la imagen supera el límite máximo permitido de 5 MB."
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # CA1 y CA2: Validar formato real por contenido (magic bytes)
        formato = detectar_formato_imagen(contenido)
        if formato is None:
            raise ReglaNegocioError(
                message=(
                    "Formato inválido: el contenido del archivo no corresponde a una "
                    "imagen JPG, PNG o WEBP."
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        nombre_limpio = (nombre_archivo or "imagen").strip()[:255] or "imagen"
        imagen = ImagenProductoRespuesta(
            producto_id=producto.id,
            nombre_archivo=nombre_limpio,
            formato=formato,
            tamano_bytes=tamano,
        )
        return self._imagen_repo.guardar(imagen, contenido)

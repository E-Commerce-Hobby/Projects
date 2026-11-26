from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

MAX_TAMANO_IMAGEN_BYTES = 5 * 1024 * 1024  # 5 MB
FORMATOS_IMAGEN_PERMITIDOS = ("JPG", "PNG", "WEBP")


class ImagenProductoRespuesta(BaseModel):
    """Datos de una imagen asociada a un producto (HU-024)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Identificador único de la imagen asociada.",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    producto_id: UUID = Field(
        ...,
        description="Identificador del producto al que pertenece la imagen.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    nombre_archivo: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre original del archivo cargado.",
        examples=["miniatura_dragon.png"],
    )
    formato: str = Field(
        ...,
        description="Formato real detectado por contenido (JPG, PNG o WEBP).",
        examples=["PNG"],
    )
    tamano_bytes: int = Field(
        ...,
        ge=1,
        le=MAX_TAMANO_IMAGEN_BYTES,
        description="Tamaño del archivo en bytes (máximo 5 MB).",
        examples=[245760],
    )
    fecha_asociacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha y hora UTC en que se asoció la imagen.",
    )

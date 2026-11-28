from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.domain.caracteristica_categoria import (
    AsociacionCaracteristicasData,
    AsociarCaracteristicasRequest,
    CaracteristicasCategoriaData,
)
from app.domain.imagen_producto import ImagenProductoRespuesta
from app.domain.producto import (
    ProductoActualizacion,
    ProductoRegistro,
    ProductoRespuesta,
    RespuestaEstandar,
)
from app.repositories.imagen_producto_repository import ImagenProductoRepository
from app.repositories.producto_repository import ProductoRepository
from app.services.imagen_producto_service import ImagenProductoService
from app.services.producto_service import ProductoService

try:
    from app.repositories.caracteristica_categoria_repository import (  # type: ignore
        CaracteristicaCategoriaRepository,
    )
    from app.services.caracteristica_categoria_service import (  # type: ignore
        CaracteristicaCategoriaService,
    )
except (ImportError, ModuleNotFoundError):
    CaracteristicaCategoriaRepository = None  # type: ignore
    CaracteristicaCategoriaService = None  # type: ignore

router = APIRouter(prefix="/productos", tags=["Productos"])


@lru_cache
def get_repositorio() -> ProductoRepository:
    return ProductoRepository()


@lru_cache
def get_caracteristica_repositorio() -> Any:
    if CaracteristicaCategoriaRepository is None:
        return None
    return CaracteristicaCategoriaRepository()


@lru_cache
def get_imagen_repositorio() -> ImagenProductoRepository:
    return ImagenProductoRepository()


def get_servicio(
    repositorio: ProductoRepository = Depends(get_repositorio),
    caracteristica_repo: Any = Depends(get_caracteristica_repositorio),
) -> ProductoService:
    try:
        return ProductoService(repositorio, caracteristica_repo=caracteristica_repo)
    except TypeError:
        return ProductoService(repositorio)


def get_caracteristica_servicio(
    producto_repo: ProductoRepository = Depends(get_repositorio),
    caracteristica_repo: Any = Depends(get_caracteristica_repositorio),
) -> Any:
    if CaracteristicaCategoriaService is None or caracteristica_repo is None:
        return None
    return CaracteristicaCategoriaService(
        producto_repo=producto_repo,
        caracteristica_repo=caracteristica_repo,
    )


def get_imagen_servicio(
    producto_repo: ProductoRepository = Depends(get_repositorio),
    imagen_repo: ImagenProductoRepository = Depends(get_imagen_repositorio),
) -> ImagenProductoService:
    return ImagenProductoService(
        producto_repo=producto_repo,
        imagen_repo=imagen_repo,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaEstandar[ProductoRespuesta],
    summary="Registrar un producto nuevo en el catálogo",
)
def registrar_producto(
    datos: ProductoRegistro,
    servicio: ProductoService = Depends(get_servicio),
) -> RespuestaEstandar[ProductoRespuesta]:
    producto = servicio.registrar(datos)
    return RespuestaEstandar[ProductoRespuesta](
        success=True,
        message="Producto registrado exitosamente.",
        data=producto,
    )


@router.patch(
    "/{producto_id}",
    status_code=status.HTTP_200_OK,
    response_model=RespuestaEstandar[ProductoRespuesta],
    summary="Actualizar información de un producto existente (HU-023)",
)
def actualizar_producto(
    producto_id: UUID,
    datos: ProductoActualizacion,
    servicio: ProductoService = Depends(get_servicio),
) -> RespuestaEstandar[ProductoRespuesta]:
    producto = servicio.actualizar(producto_id, datos)
    return RespuestaEstandar[ProductoRespuesta](
        success=True,
        message="Producto actualizado exitosamente.",
        data=producto,
    )


@router.get(
    "/{producto_id}/caracteristicas/categoria",
    status_code=status.HTTP_200_OK,
    response_model=RespuestaEstandar[CaracteristicasCategoriaData],
    summary="Consultar características de la categoría asociada al producto (HU-022)",
)
def consultar_caracteristicas_categoria(
    producto_id: UUID,
    servicio: Any = Depends(get_caracteristica_servicio),
) -> RespuestaEstandar[CaracteristicasCategoriaData]:
    resultado = servicio.consultar_caracteristicas_categoria(producto_id)
    return RespuestaEstandar[CaracteristicasCategoriaData](
        success=True,
        message="Características de la categoría consultadas exitosamente.",
        data=resultado,
    )


@router.post(
    "/{producto_id}/caracteristicas",
    status_code=status.HTTP_200_OK,
    response_model=RespuestaEstandar[AsociacionCaracteristicasData],
    summary="Asociar o actualizar características de un producto (HU-022)",
)
def asociar_caracteristicas_producto(
    producto_id: UUID,
    datos: AsociarCaracteristicasRequest,
    servicio: Any = Depends(get_caracteristica_servicio),
) -> RespuestaEstandar[AsociacionCaracteristicasData]:
    resultado = servicio.asociar_caracteristicas(producto_id, datos)
    return RespuestaEstandar[AsociacionCaracteristicasData](
        success=True,
        message="Características del producto actualizadas exitosamente.",
        data=resultado,
    )


@router.post(
    "/{producto_id}/imagenes",
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaEstandar[ImagenProductoRespuesta],
    summary="Asociar una imagen a un producto existente (HU-024)",
    responses={
        201: {
            "description": "Imagen asociada exitosamente al producto (CA1).",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Imagen asociada exitosamente al producto.",
                        "data": {
                            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "producto_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "nombre_archivo": "miniatura_dragon.png",
                            "formato": "PNG",
                            "tamano_bytes": 245760,
                            "fecha_asociacion": "2026-11-25T21:30:00Z",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Archivo inválido por formato, contenido o tamaño (CA2).",
            "content": {
                "application/json": {
                    "examples": {
                        "formato_invalido": {
                            "summary": "Formato o contenido inválido (CA2)",
                            "value": {
                                "success": False,
                                "message": "Formato inválido: el contenido del archivo no corresponde a una imagen JPG, PNG o WEBP.",
                                "data": None,
                            },
                        },
                        "tamano_excedido": {
                            "summary": "Tamaño superior a 5 MB (CA2)",
                            "value": {
                                "success": False,
                                "message": "Tamaño inválido: la imagen supera el límite máximo permitido de 5 MB.",
                                "data": None,
                            },
                        },
                        "archivo_vacio": {
                            "summary": "Archivo vacío (CA2)",
                            "value": {
                                "success": False,
                                "message": "Archivo inválido: el archivo de imagen está vacío.",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "El producto no existe (CA3).",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto con id '3fa85f64-5717-4562-b3fc-2c963f66afa6' no existe.",
                        "data": None,
                    }
                }
            },
        },
    },
)
async def asociar_imagen_producto(
    producto_id: UUID,
    archivo: UploadFile = File(
        ...,
        description="Archivo de imagen válido (JPG, PNG o WEBP) de máximo 5 MB.",
    ),
    servicio: ImagenProductoService = Depends(get_imagen_servicio),
) -> RespuestaEstandar[ImagenProductoRespuesta]:
    """Asocia una imagen JPG, PNG o WEBP (<= 5 MB) a un producto existente."""
    contenido = await archivo.read()
    imagen = servicio.asociar_imagen(
        producto_id=producto_id,
        contenido=contenido,
        nombre_archivo=archivo.filename or "imagen",
    )
    return RespuestaEstandar[ImagenProductoRespuesta](
        success=True,
        message="Imagen asociada exitosamente al producto.",
        data=imagen,
    )

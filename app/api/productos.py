from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domain.producto import (
    ProductoActualizacion,
    ProductoRegistro,
    ProductoRespuesta,
    RespuestaEstandar,
)
from app.repositories.producto_repository import ProductoRepository
from app.services.producto_service import ProductoService

try:
    from app.domain.caracteristica_categoria import (  # type: ignore
        CaracteristicasCategoriaRespuesta,
        CaracteristicasProductoEntrada,
        CaracteristicasProductoRespuesta,
    )
    from app.repositories.caracteristica_categoria_repository import (  # type: ignore
        CaracteristicaCategoriaRepository,
    )
    from app.services.caracteristica_categoria_service import (  # type: ignore
        CaracteristicaCategoriaService,
    )

    _HU022_DISPONIBLE = True
except (ImportError, ModuleNotFoundError):
    CaracteristicasCategoriaRespuesta = Any  # type: ignore
    CaracteristicasProductoEntrada = Any  # type: ignore
    CaracteristicasProductoRespuesta = Any  # type: ignore
    CaracteristicaCategoriaRepository = None  # type: ignore
    CaracteristicaCategoriaService = None  # type: ignore
    _HU022_DISPONIBLE = False

router = APIRouter(prefix="/productos", tags=["Productos"])


@lru_cache
def get_repositorio() -> ProductoRepository:
    return ProductoRepository()


@lru_cache
def get_caracteristica_repositorio() -> Any:
    if CaracteristicaCategoriaRepository is None:
        return None
    return CaracteristicaCategoriaRepository()


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
        producto_repositorio=producto_repo,
        caracteristica_repositorio=caracteristica_repo,
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


if _HU022_DISPONIBLE:

    @router.get(
        "/{producto_id}/caracteristicas/categoria",
        status_code=status.HTTP_200_OK,
        response_model=RespuestaEstandar[CaracteristicasCategoriaRespuesta],
        summary="Consultar características de la categoría asociada al producto (HU-022)",
    )
    def consultar_caracteristicas_categoria(
        producto_id: UUID,
        servicio: Any = Depends(get_caracteristica_servicio),
    ) -> RespuestaEstandar[CaracteristicasCategoriaRespuesta]:
        resultado = servicio.consultar_caracteristicas_categoria(producto_id)
        return RespuestaEstandar[CaracteristicasCategoriaRespuesta](
            success=True,
            message="Características de la categoría consultadas exitosamente.",
            data=resultado,
        )

    @router.post(
        "/{producto_id}/caracteristicas",
        status_code=status.HTTP_200_OK,
        response_model=RespuestaEstandar[CaracteristicasProductoRespuesta],
        summary="Asociar o actualizar características de un producto (HU-022)",
    )
    def asociar_caracteristicas_producto(
        producto_id: UUID,
        datos: CaracteristicasProductoEntrada,
        servicio: Any = Depends(get_caracteristica_servicio),
    ) -> RespuestaEstandar[CaracteristicasProductoRespuesta]:
        resultado = servicio.asociar_caracteristicas(producto_id, datos)
        return RespuestaEstandar[CaracteristicasProductoRespuesta](
            success=True,
            message="Características del producto actualizadas exitosamente.",
            data=resultado,
        )

from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.domain.caracteristica_categoria import (
    AsociacionCaracteristicasData,
    AsociarCaracteristicasRequest,
    CaracteristicasCategoriaData,
)
from app.domain.producto import (
    ProductoRegistro,
    ProductoRespuesta,
    RespuestaEstandar,
)
from app.repositories.caracteristica_categoria_repository import (
    CaracteristicaCategoriaRepository,
)
from app.repositories.producto_repository import ProductoRepository
from app.services.caracteristica_categoria_service import (
    CaracteristicaCategoriaService,
)
from app.services.producto_service import ProductoService

router = APIRouter(prefix="/productos", tags=["Productos"])


@lru_cache
def get_repositorio() -> ProductoRepository:
    # Instancia única para que los datos en memoria persistan entre peticiones
    return ProductoRepository()


@lru_cache
def get_caracteristica_repositorio() -> CaracteristicaCategoriaRepository:
    return CaracteristicaCategoriaRepository()


def get_servicio(
    repositorio: ProductoRepository = Depends(get_repositorio),
) -> ProductoService:
    return ProductoService(repositorio)


def get_caracteristica_servicio(
    producto_repo: ProductoRepository = Depends(get_repositorio),
    caracteristica_repo: CaracteristicaCategoriaRepository = Depends(
        get_caracteristica_repositorio
    ),
) -> CaracteristicaCategoriaService:
    return CaracteristicaCategoriaService(producto_repo, caracteristica_repo)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RespuestaEstandar[ProductoRespuesta],
    summary="Registrar un producto nuevo en el catálogo",
    responses={
        400: {
            "description": "Campos faltantes o con formato inválido.",
            "content": {
                "application/json": {
                    "examples": {
                        "campos_faltantes": {
                            "summary": "Campos faltantes (CA3)",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Faltan campos obligatorios: categoria, estado.",
                            },
                        },
                        "formato_invalido": {
                            "summary": "Formato inválido (CA4)",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Valor inválido en el campo 'codigo'.",
                            },
                        },
                    }
                }
            },
        },
        409: {
            "description": "El código ya está registrado (RN-02).",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El código ya está registrado.",
                        "data": [],
                    }
                }
            },
        },
    },
)
def registrar_producto(
    datos: ProductoRegistro,
    servicio: ProductoService = Depends(get_servicio),
) -> RespuestaEstandar[ProductoRespuesta]:
    """Registra un producto con su código, categoría, características y estado.

- El **código** debe ser único, de máximo 30 caracteres (letras, números y guion).
- El **estado** solo admite `activo` o `inactivo`.
    """
    producto = servicio.registrar(datos)
    return RespuestaEstandar[ProductoRespuesta](
        success=True,
        message="Producto registrado exitosamente.",
        data=producto,
    )


@router.get(
    "/{producto_id}/caracteristicas/categoria",
    status_code=status.HTTP_200_OK,
    response_model=RespuestaEstandar[CaracteristicasCategoriaData],
    summary="Consultar características definidas para la categoría del producto",
    responses={
        200: {
            "description": "Características definidas de la categoría consultadas.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Características de la categoría consultadas.",
                        "data": {
                            "producto_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "categoria": "miniaturas",
                            "caracteristicas": [
                                {
                                    "nombre": "escala",
                                    "tipo_dato": "texto",
                                    "obligatoria": True,
                                },
                                {
                                    "nombre": "material",
                                    "tipo_dato": "texto",
                                    "obligatoria": True,
                                },
                            ],
                        },
                    }
                }
            },
        },
        400: {
            "description": "Formato de identificador inválido.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Valor inválido en el campo 'producto_id'.",
                    }
                }
            },
        },
        404: {
            "description": "El producto no existe.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "El producto con id '...' no existe.",
                    }
                }
            },
        },
    },
)
def consultar_caracteristicas_categoria(
    producto_id: UUID,
    servicio: CaracteristicaCategoriaService = Depends(get_caracteristica_servicio),
) -> RespuestaEstandar[CaracteristicasCategoriaData]:
    """Retorna la lista de características ya definidas para la categoría del producto."""
    resultado = servicio.consultar_caracteristicas_categoria(producto_id)
    return RespuestaEstandar[CaracteristicasCategoriaData](
        success=True,
        message="Características de la categoría consultadas.",
        data=resultado,
    )


@router.post(
    "/{producto_id}/caracteristicas",
    status_code=status.HTTP_200_OK,
    response_model=RespuestaEstandar[AsociacionCaracteristicasData],
    summary="Asociar características de categoría a un producto",
    responses={
        200: {
            "description": "Características asociadas correctamente al producto.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Características asociadas al producto correctamente.",
                        "data": {
                            "producto_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "codigo": "MIN-001",
                            "categoria": "miniaturas",
                            "caracteristicas_asociadas": {
                                "escala": "28mm",
                                "material": "resina",
                            },
                            "caracteristicas_producto": {
                                "escala": "28mm",
                                "material": "resina",
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Datos faltantes, inválidos o características fuera de categoría.",
            "content": {
                "application/json": {
                    "examples": {
                        "no_pertenecen": {
                            "summary": "Característica no pertenece a la categoría (CA3)",
                            "value": {
                                "success": False,
                                "message": "Operación rechazada: no pertenecen a la categoría 'miniaturas': acabado.",
                                "data": ["acabado"],
                            },
                        },
                        "entrada_invalida": {
                            "summary": "Lista vacía o campo faltante",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Faltan campos obligatorios: caracteristicas.",
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "El producto no existe (CA4).",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "El producto con id '...' no existe.",
                    }
                }
            },
        },
    },
)
def asociar_caracteristicas_producto(
    producto_id: UUID,
    payload: AsociarCaracteristicasRequest,
    servicio: CaracteristicaCategoriaService = Depends(get_caracteristica_servicio),
) -> RespuestaEstandar[AsociacionCaracteristicasData]:
    """Asocia características (nombre, valor) pertenecientes a la categoría del producto."""
    resultado = servicio.asociar_caracteristicas(producto_id, payload)
    return RespuestaEstandar[AsociacionCaracteristicasData](
        success=True,
        message="Características asociadas al producto correctamente.",
        data=resultado,
    )
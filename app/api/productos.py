from functools import lru_cache
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

router = APIRouter(prefix="/productos", tags=["Productos"])


@lru_cache
def get_repositorio() -> ProductoRepository:
    # Instancia única para que los datos en memoria persistan entre peticiones
    return ProductoRepository()


def get_servicio(
    repositorio: ProductoRepository = Depends(get_repositorio),
) -> ProductoService:
    return ProductoService(repositorio)


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


@router.patch(
    "/{producto_id}",
    status_code=status.HTTP_200_OK,
    response_model=RespuestaEstandar[ProductoRespuesta],
    summary="Actualizar información de un producto existente (HU-023)",
    responses={
        200: {
            "description": "Producto actualizado exitosamente.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Producto actualizado exitosamente.",
                        "data": {
                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "codigo": "MIN-001",
                            "categoria": "miniaturas",
                            "caracteristicas": {"escala": "32mm", "material": "resina"},
                            "estado": "activo",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Datos inválidos o categoría inexistente (CA3).",
            "content": {
                "application/json": {
                    "examples": {
                        "categoria_inexistente": {
                            "summary": "Categoría inexistente (CA3)",
                            "value": {
                                "success": False,
                                "message": "Categoría inválida: la categoría indicada no existe.",
                                "data": None,
                            },
                        },
                        "formato_invalido": {
                            "summary": "Campo con formato inválido (CA3)",
                            "value": {
                                "success": False,
                                "message": "Valor inválido en el campo 'codigo'.",
                                "data": None,
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
                        "message": "El producto indicado no existe.",
                        "data": None,
                    }
                }
            },
        },
        409: {
            "description": "Conflicto con código de otro producto (RN-02 / CA2).",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Conflicto de código (RN-02): el código ya pertenece a otro producto.",
                        "data": None,
                    }
                }
            },
        },
    },
)
def actualizar_producto(
    producto_id: UUID,
    datos: ProductoActualizacion,
    servicio: ProductoService = Depends(get_servicio),
) -> RespuestaEstandar[ProductoRespuesta]:
    """Actualiza parcialmente los datos de un producto existente sin romper otros campos."""
    producto = servicio.actualizar(producto_id, datos)
    return RespuestaEstandar[ProductoRespuesta](
        success=True,
        message="Producto actualizado exitosamente.",
        data=producto,
    )

from functools import lru_cache

from fastapi import APIRouter, Depends, status

from app.domain.producto import (
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
from functools import lru_cache

from fastapi import APIRouter, Depends, status

from app.domain.producto import ErrorRespuesta, ProductoRegistro, ProductoRespuesta
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
    response_model=ProductoRespuesta,
    summary="Registrar un producto nuevo en el catálogo",
    responses={
        400: {
            "model": ErrorRespuesta,
            "description": "Campos faltantes o con formato inválido.",
            "content": {
                "application/json": {
                    "examples": {
                        "campos_faltantes": {
                            "summary": "Campos faltantes (CA3)",
                            "value": {
                                "mensaje": "Campos faltantes: categoria, estado.",
                                "campos_faltantes": ["categoria", "estado"],
                                "campos_invalidos": [],
                            },
                        },
                        "formato_invalido": {
                            "summary": "Formato inválido (CA4)",
                            "value": {
                                "mensaje": "Campos con formato inválido: codigo, estado.",
                                "campos_faltantes": [],
                                "campos_invalidos": ["codigo", "estado"],
                            },
                        },
                    }
                }
            },
        },
        409: {
            "model": ErrorRespuesta,
            "description": "El código ya está registrado (RN-02).",
            "content": {
                "application/json": {
                    "example": {"mensaje": "El código ya está registrado."}
                }
            },
        },
    },
)
def registrar_producto(
    datos: ProductoRegistro,
    servicio: ProductoService = Depends(get_servicio),
) -> ProductoRespuesta:
    """Registra un producto con su código, categoría, características y estado.

    - El **código** debe ser único, de máximo 30 caracteres (letras, números y guion).
    - El **estado** solo admite `activo` o `inactivo`.
    """
    return servicio.registrar(datos)
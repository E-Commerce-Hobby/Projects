"""POS endpoints: barcode search, counter sale registration and discounts."""
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.domain.pos import (
    ApplyDiscountRequest,
    ErrorResponse,
    ProductSearchResponse,
    SaleCreateRequest,
    SaleDiscountResponse,
    SaleResponse,
)
from app.repositories.pos_repository import PosRepository
from app.services.pos_service import PosService

router = APIRouter(prefix="/pos", tags=["Punto de Venta (POS)"])


@lru_cache
def get_pos_repository() -> PosRepository:
    """Single in-memory repository instance shared across requests."""
    return PosRepository()


def get_pos_service(
    repository: Annotated[PosRepository, Depends(get_pos_repository)],
) -> PosService:
    return PosService(repository)


@router.get(
    "/products/search",
    response_model=ProductSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar producto por código de barras",
    description=(
        "Retorna el producto, su precio y la cantidad disponible en el punto de venta. "
        "Si el producto no tiene inventario, la cantidad disponible es 0."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Código vacío o con caracteres inválidos.",
            "content": {"application/json": {"example": {
                "mensaje": "El código es inválido: debe tener solo letras y números (máximo 50) y no puede estar vacío."
            }}},
        },
        404: {
            "model": ErrorResponse,
            "description": "El código no existe en el catálogo.",
            "content": {"application/json": {"example": {"mensaje": "El producto no existe."}}},
        },
    },
)
def search_product_by_barcode(
    barcode: Annotated[
        str,
        Query(
            description="Código de barras del producto.",
            max_length=50,
        ),
    ],
    service: Annotated[PosService, Depends(get_pos_service)],
) -> ProductSearchResponse:
    return service.search_product_by_barcode(barcode)


@router.post(
    "/sales",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar venta de mostrador",
    description=(
        "Registra una venta en una caja abierta. Rechaza la venta si no hay caja abierta, "
        "si no tiene productos o si alguna cantidad supera la disponibilidad (RN-01)."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Datos faltantes, con formato inválido o venta sin productos.",
            "content": {"application/json": {"example": {"mensaje": "La venta no tiene productos."}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Algún producto de la venta no existe.",
            "content": {"application/json": {"example": {"mensaje": "El producto ABC999 no existe."}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "No hay caja abierta o la cantidad supera la disponibilidad.",
            "content": {"application/json": {"example": {
                "mensaje": "Cantidad insuficiente para el producto ABC123: solicitada 5, disponible 3."
            }}},
        },
    },
)
def register_sale(
    payload: SaleCreateRequest,
    service: Annotated[PosService, Depends(get_pos_service)],
):
    venta = service.register_sale(payload)
    return {
        "success": True,
        "message": venta.mensaje,
        "data": venta.model_dump(),
    }


@router.post(
    "/sales/{sale_id}/discounts",
    response_model=SaleDiscountResponse,
    status_code=status.HTTP_200_OK,
    summary="Aplicar descuento a una venta de mostrador (HU-031: FUN-4.2.3)",
    description=(
        "Aplica un descuento existente y vigente (porcentaje o valor fijo) a una venta "
        "registrada en POS, recalcula el total asegurando que nunca sea menor que 0 y "
        "evita aplicar el mismo descuento dos veces."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "ID de descuento vacío o formato inválido.",
            "content": {
                "application/json": {
                    "example": {"mensaje": "El ID de descuento no puede estar vacío."}
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "La venta o el descuento no existe.",
            "content": {
                "application/json": {
                    "example": {"mensaje": "El descuento 'DESC999' no existe."}
                }
            },
        },
        409: {
            "model": ErrorResponse,
            "description": "Descuento fuera de vigencia o ya aplicado a esta venta.",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "El descuento 'DESC10' ya fue aplicado a la venta 1."
                    }
                }
            },
        },
    },
)
def apply_discount_to_sale(
    sale_id: Annotated[int, Path(gt=0, description="ID de la venta de mostrador.")],
    payload: ApplyDiscountRequest,
    service: Annotated[PosService, Depends(get_pos_service)],
) -> SaleDiscountResponse:
    return service.apply_discount(sale_id, payload)
"""Inventory router (API-REST-02)."""

from functools import lru_cache

from fastapi import APIRouter, Depends, status

from app.domain.inventory import (
    ErrorResponse,
    InventoryAdjustmentCreate,
    InventoryAdjustmentResponse,
    InventoryCreate,
    InventoryResponse,
)
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@lru_cache
def get_inventory_repository() -> InventoryRepository:
    """Single instance so in-memory data persists between requests."""
    return InventoryRepository()


def get_inventory_service(
    repository: InventoryRepository = Depends(get_inventory_repository),
) -> InventoryService:
    return InventoryService(repository)


@router.post(
    "",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register initial inventory for a product in a location",
    description=(
        "Registers the initial quantity of a product in a store or warehouse. "
        "Later adjustments are out of scope (HU-025)."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Missing, malformed or out-of-range data (e.g. invalid quantity)",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "La cantidad es inválida: debe ser un número entero mayor o igual a 0"
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "Product or location does not exist",
            "content": {"application/json": {"example": {"mensaje": "El producto no existe"}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "Inventory already registered for this product and location",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "Ya existe inventario para este producto en la ubicación; use el ajuste de inventario (HU-025)"
                    }
                }
            },
        },
    },
)
def register_initial_inventory(
    payload: InventoryCreate,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    return service.register_initial_inventory(payload)


@router.post(
    "/adjustments",
    response_model=InventoryAdjustmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Ajustar inventario de un producto en una ubicación (HU-025)",
    description=(
        "Aplica un ajuste de inventario con motivo válido (entrada, salida, "
        "conteo físico o pérdida), actualiza el stock y registra el movimiento (HU-006)."
    ),
    responses={
        200: {
            "model": InventoryAdjustmentResponse,
            "description": "Ajuste aplicado y movimiento registrado (CA1).",
        },
        400: {
            "model": ErrorResponse,
            "description": "Motivo faltante/inválido o cantidad inválida (CA2).",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "El motivo es obligatorio y debe ser uno de: entrada, salida, conteo físico o pérdida."
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "Producto, ubicación o inventario no encontrado.",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "No existe inventario registrado para este producto en la ubicación."
                    }
                }
            },
        },
        409: {
            "model": ErrorResponse,
            "description": "Conflicto con RN-01: el ajuste dejaría saldo negativo (CA3).",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "Ajuste rechazado (RN-01): el inventario no puede quedar negativo. Cantidad actual: 50."
                    }
                }
            },
        },
    },
)
def adjust_inventory(
    payload: InventoryAdjustmentCreate,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryAdjustmentResponse:
    return service.adjust_inventory(payload)

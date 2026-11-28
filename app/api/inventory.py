"""Inventory router (API-REST-02)."""

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.domain.inventory import (
    ErrorResponse,
    InventoryAdjustmentCreate,
    InventoryAdjustmentResponse,
    InventoryCreate,
    InventoryResponse,
)
from app.domain.inventory_alert import (
    AlertCheckResultResponse,
    LowStockAlertResponse,
    MinStockConfigRequest,
    MinStockConfigResponse,
)
from app.repositories.inventory_alert_repository import InventoryAlertRepository
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_alert_service import InventoryAlertService
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@lru_cache
def get_inventory_repository() -> InventoryRepository:
    """Single instance so in-memory data persists between requests."""
    return InventoryRepository()


@lru_cache
def get_inventory_alert_repository() -> InventoryAlertRepository:
    """Single instance so configured min stocks and alerts persist between requests."""
    return InventoryAlertRepository()


def get_inventory_service(
    repository: InventoryRepository = Depends(get_inventory_repository),
) -> InventoryService:
    return InventoryService(repository)


def get_inventory_alert_service(
    inventory_repo: InventoryRepository = Depends(get_inventory_repository),
    alert_repo: InventoryAlertRepository = Depends(get_inventory_alert_repository),
) -> InventoryAlertService:
    return InventoryAlertService(inventory_repo=inventory_repo, alert_repo=alert_repo)


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


@router.put(
    "/products/{product_id}/min-stock",
    response_model=MinStockConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Configurar stock mínimo de un producto (HU-026)",
    description=(
        "Define el stock mínimo (entero >= 0) de un producto para que sea "
        "evaluado en las revisiones periódicas de alertas de inventario bajo."
    ),
    responses={
        200: {
            "model": MinStockConfigResponse,
            "description": "Stock mínimo configurado exitosamente.",
        },
        400: {
            "model": ErrorResponse,
            "description": "Stock mínimo inválido (negativo o no entero).",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "El stock mínimo es inválido: debe ser un entero mayor o igual a 0."
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "El producto no existe.",
            "content": {
                "application/json": {
                    "example": {"mensaje": "El producto no existe."}
                }
            },
        },
    },
)
def configure_product_min_stock(
    product_id: int,
    payload: MinStockConfigRequest,
    service: InventoryAlertService = Depends(get_inventory_alert_service),
) -> MinStockConfigResponse:
    return service.configure_min_stock(product_id, payload.min_stock)


@router.post(
    "/alerts/check",
    response_model=AlertCheckResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar revisión de alertas de inventario bajo (HU-026)",
    description=(
        "Revisa los productos con stock mínimo configurado cada 60 minutos y "
        "genera alertas en estado 'pendiente' cuando la cantidad disponible es "
        "estrictamente menor al mínimo, evitando duplicados."
    ),
    responses={
        200: {
            "model": AlertCheckResultResponse,
            "description": "Resultado de la revisión de inventario bajo (CA1-CA4).",
        },
    },
)
def check_low_stock_alerts(
    force: bool = Query(
        default=False,
        description="Si es true, fuerza la revisión sin esperar 60 minutos.",
    ),
    service: InventoryAlertService = Depends(get_inventory_alert_service),
) -> AlertCheckResultResponse:
    return service.check_low_stock(force=force)


@router.get(
    "/alerts",
    response_model=list[LowStockAlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Consultar alertas de inventario bajo (HU-026)",
    description="Lista las alertas de inventario bajo generadas para revisión del administrador.",
    responses={
        200: {
            "model": list[LowStockAlertResponse],
            "description": "Listado de alertas (puede ser vacío si no hay alertas).",
        },
    },
)
def list_low_stock_alerts(
    estado: Optional[str] = Query(
        default=None,
        description="Filtro opcional por estado de la alerta (ej. 'pendiente').",
    ),
    service: InventoryAlertService = Depends(get_inventory_alert_service),
) -> list[LowStockAlertResponse]:
    return service.list_alerts(status=estado)

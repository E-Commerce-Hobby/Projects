# app/api/inventory_retry.py
from fastapi import APIRouter, status
from app.domain.inventory_retry import (
    InventoryRetryRequest,
    InventoryRetryStandardResponse,
)
from app.repositories.inventory_retry import inventory_retry_repository
from app.services.inventory_retry import InventoryRetryService

router = APIRouter(
    prefix="/api/v1/inventario/reintentos",
    tags=["Sincronización de Inventario - Reintentos (HU-027)"]
)

inventory_retry_service = InventoryRetryService(repository=inventory_retry_repository)


@router.post(
    "",
    response_model=InventoryRetryStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Reintentar actualización de inventario fallida (HU-027 / FUN-2.2.5)",
    description=(
        "Reintenta hasta 3 veces (con 30s de espera entre intentos) actualizaciones de inventario "
        "que fallaron por error temporal. Si falla por regla de negocio (RN-01), no reintenta. "
        "Si queda fallida, genera alerta de revisión manual."
    ),
    responses={
        200: {
            "description": "CA1-CA5 - Operación procesada ('exitosa' o 'fallida' con alerta si aplica)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "operation_id": "OP-VENTA-001",
                            "sale_id": "VEN-001",
                            "status": "exitosa",
                            "attempts_used": 2,
                            "last_error": None,
                            "alert": None
                        },
                        "message": "Actualización de inventario completada exitosamente."
                    }
                }
            }
        },
        503: {
            "description": "Servicio interno o externo requerido no disponible",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Servicio de inventario no disponible para procesar la operación."
                    }
                }
            }
        }
    }
)
def retry_inventory_update_endpoint(payload: InventoryRetryRequest):
    data, msg = inventory_retry_service.retry_failed_update(payload)
    return InventoryRetryStandardResponse(
        success=True,
        data=data,
        message=msg
    )
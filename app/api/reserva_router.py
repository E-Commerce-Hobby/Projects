from fastapi import APIRouter, status
from app.domain.reserva_schema import ReservaCreacion
from app.services.reserva_service import (
    solicitar_reserva_temporal,
    consultar_stock_disponible,
)

router = APIRouter(prefix="/api/v1/reservas", tags=["Reservas"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear reserva temporal de producto (HU-004)",
    description=(
        "Reserva temporalmente las unidades solicitadas de un producto durante 15 minutos "
        "(resta de disponible y suma a reservado). Valida stock disponible (RN-01) y libera "
        "automáticamente reservas vencidas."
    ),
    responses={
        201: {
            "description": "Reserva temporal creada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Reserva temporal creada exitosamente.",
                        "data": {
                            "id": 1,
                            "id_producto": "PROD-001",
                            "cantidad": 2,
                            "fecha_expiracion": "2026-11-20T22:00:00+00:00",
                            "estado": "activa",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Cantidad inválida (menor o igual a 0, no entera) o datos faltantes",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Valor inválido en el campo 'cantidad'.",
                        "data": None,
                    }
                }
            },
        },
        404: {
            "description": "Producto sin inventario registrado",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto solicitado no tiene inventario registrado.",
                        "data": ["id_producto"],
                    }
                }
            },
        },
        409: {
            "description": "Stock insuficiente (RN-01)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Stock insuficiente (RN-01). Cantidad disponible actual: 2.",
                        "data": {
                            "id_producto": "PROD-002",
                            "disponible_actual": 2,
                        },
                    }
                }
            },
        },
    },
)
def crear_reserva_temporal(datos: ReservaCreacion):
    reserva = solicitar_reserva_temporal(datos)
    return {
        "success": True,
        "message": "Reserva temporal creada exitosamente.",
        "data": reserva,
    }


@router.get(
    "/inventario/{id_producto}",
    status_code=status.HTTP_200_OK,
    summary="Consultar stock disponible y reservado de un producto",
    description=(
        "Retorna las unidades disponibles y reservadas del producto tras liberar "
        "cualquier reserva temporal vencida."
    ),
)
def obtener_inventario_producto(id_producto: str):
    stock = consultar_stock_disponible(id_producto)
    return {
        "success": True,
        "message": "Inventario consultado exitosamente.",
        "data": stock,
    }
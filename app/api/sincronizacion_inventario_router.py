from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, status
from app.domain.sincronizacion_inventario_schema import (
    DescuentoInventarioEntrada,
    NotificacionVentaEntrada,
    RegistroMovimientoEntrada,
)
from app.repositories.sincronizacion_inventario_repository import (
    listar_resultados_actualizacion,
)
from app.services.sincronizacion_inventario_service import (
    aplicar_descuento_por_venta,
    consultar_movimientos_producto,
    notificar_venta_a_inventario,
    registrar_movimiento_inventario,
)

router = APIRouter(prefix="/api/v1/inventario", tags=["Sincronización de Inventario"])


# ── FUN-2.2.1: Notificación de venta a Inventario ────────────────────────────

@router.post(
    "/notificaciones-venta",
    status_code=status.HTTP_200_OK,
    summary="Notificar venta confirmada a Inventario (HU-006: FUN-2.2.1)",
    description=(
        "Recibe la confirmación de una venta (virtual o POS) con sus líneas de producto y "
        "la envía al módulo de Inventario. Si Inventario no confirma, la guarda como pendiente "
        "para reintento posterior (HU-027)."
    ),
    responses={
        200: {
            "description": "Notificación enviada exitosamente a Inventario (CA1)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Notificación de venta enviada exitosamente a Inventario.",
                        "data": {
                            "id_notificacion": 1,
                            "id_venta": "VEN-001",
                            "canal": "virtual",
                            "lineas": [
                                {"id_producto": "PROD-001", "ubicacion": "Bodega Virtual", "cantidad": 2}
                            ],
                            "estado_envio": "enviada",
                            "fecha_hora": "2026-11-23T20:00:00+00:00",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Venta sin líneas, cantidad <= 0 o canal inválido (CA2)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Línea 1 inválida (producto 'PROD-001'): la cantidad debe ser mayor a 0.",
                        "data": [{"linea": 1, "id_producto": "PROD-001", "cantidad": 0}],
                    }
                }
            },
        },
        503: {
            "description": "Inventario no confirmó la recepción; guardada como pendiente (CA3)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Inventario no confirmó la recepción. Notificación guardada como pendiente para reintento.",
                        "data": [{"id_notificacion": 2, "id_venta": "VEN-002", "estado_envio": "pendiente"}],
                    }
                }
            },
        },
    },
)
def endpoint_notificar_venta(datos: NotificacionVentaEntrada):
    notificacion = notificar_venta_a_inventario(datos)
    return {
        "success": True,
        "message": "Notificación de venta enviada exitosamente a Inventario.",
        "data": notificacion,
    }


# ── FUN-2.2.2: Descuento atómico de inventario ───────────────────────────────

@router.post(
    "/descuentos",
    status_code=status.HTTP_200_OK,
    summary="Aplicar descuento de inventario por venta confirmada (HU-006: FUN-2.2.2)",
    description=(
        "Descuenta en una sola transacción (todo o nada, RN-01) las cantidades vendidas por producto "
        "y ubicación. Registra el resultado ('exitoso' o 'fallido') y los movimientos de inventario."
    ),
    responses={
        200: {
            "description": "Inventario descontado exitosamente (CA4, CA6, CA7)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Inventario actualizado exitosamente por venta confirmada.",
                        "data": {
                            "id_venta": "VEN-001",
                            "resultado": "exitoso",
                            "fecha_hora": "2026-11-23T20:00:00+00:00",
                            "inventario_actualizado": [
                                {
                                    "id_producto": "PROD-001",
                                    "ubicacion": "Tienda Física",
                                    "cantidad_descontada": 2,
                                    "cantidad_resultante": 2,
                                }
                            ],
                            "movimientos_registrados": [
                                {
                                    "id_movimiento": 1,
                                    "id_producto": "PROD-001",
                                    "ubicacion": "Tienda Física",
                                    "cantidad": -2,
                                    "fecha_hora": "2026-11-23T20:00:00+00:00",
                                    "canal": "virtual",
                                    "tipo": "venta",
                                    "id_referencia": "VEN-001",
                                }
                            ],
                        },
                    }
                }
            },
        },
        400: {
            "description": "Datos inválidos, líneas vacías o cantidad <= 0",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Debe enviar al menos una línea de producto para descontar inventario.",
                        "data": ["lineas"],
                    }
                }
            },
        },
        404: {
            "description": "Producto o ubicación inexistente en inventario",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto 'PROD-999' no existe en el catálogo.",
                        "data": ["PROD-999"],
                    }
                }
            },
        },
        409: {
            "description": "Stock insuficiente (RN-01): no se descuenta ninguna línea (CA5)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Stock insuficiente (RN-01) para 'PROD-002' en 'Bodega Virtual': disponible 2, solicitado 10.",
                        "data": [{"id_resultado": 1, "id_venta": "VEN-002", "resultado": "fallido"}],
                    }
                }
            },
        },
    },
)
def endpoint_aplicar_descuento(datos: DescuentoInventarioEntrada):
    resultado = aplicar_descuento_por_venta(datos)
    return {
        "success": True,
        "message": "Inventario actualizado exitosamente por venta confirmada.",
        "data": resultado,
    }


@router.get(
    "/resultados",
    status_code=status.HTTP_200_OK,
    summary="Consultar resultados de actualización de inventario (HU-006: CA6)",
    description="Lista el historial de intentos de actualización ('exitoso' o 'fallido') con ID de venta y fecha/hora.",
    responses={
        200: {
            "description": "Listado de resultados registrados",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Resultados de actualización consultados exitosamente.",
                        "data": [
                            {
                                "id_resultado": 1,
                                "id_venta": "VEN-001",
                                "resultado": "exitoso",
                                "motivo": None,
                                "fecha_hora": "2026-11-23T20:00:00+00:00",
                            }
                        ],
                    }
                }
            },
        },
    },
)
def endpoint_listar_resultados(
    id_venta: Optional[str] = Query(default=None, description="Filtrar por identificador de venta.")
):
    resultados = listar_resultados_actualizacion(id_venta=id_venta)
    return {
        "success": True,
        "message": "Resultados de actualización consultados exitosamente.",
        "data": resultados,
    }


# ── FUN-2.2.4: Registro y consulta de movimientos inmutables (CA7, CA8, CA9) ─
# Nota CA8: No se exponen operaciones PUT, PATCH ni DELETE sobre /movimientos.

@router.post(
    "/movimientos",
    status_code=status.HTTP_200_OK,
    summary="Registrar movimiento de inventario (HU-006: FUN-2.2.4)",
    description=(
        "Registra un movimiento inmutable de inventario por venta, ajuste o reserva. "
        "Los movimientos solo se crean y se consultan (CA8)."
    ),
    responses={
        200: {
            "description": "Movimiento registrado exitosamente (CA7)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Movimiento de inventario registrado exitosamente.",
                        "data": {
                            "id_movimiento": 1,
                            "id_producto": "PROD-001",
                            "ubicacion": "Tienda Física",
                            "cantidad": -2,
                            "fecha_hora": "2026-11-23T20:00:00+00:00",
                            "canal": "POS",
                            "tipo": "venta",
                            "id_referencia": "VEN-001",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Canal, tipo o cantidad inválidos",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La cantidad del movimiento debe ser distinta de 0 (positiva o negativa).",
                        "data": ["cantidad"],
                    }
                }
            },
        },
        404: {
            "description": "Producto inexistente en el catálogo",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto 'PROD-999' no existe en el catálogo.",
                        "data": ["PROD-999"],
                    }
                }
            },
        },
    },
)
def endpoint_registrar_movimiento(datos: RegistroMovimientoEntrada):
    movimiento = registrar_movimiento_inventario(datos)
    return {
        "success": True,
        "message": "Movimiento de inventario registrado exitosamente.",
        "data": movimiento,
    }


@router.get(
    "/movimientos",
    status_code=status.HTTP_200_OK,
    summary="Consultar movimientos de un producto por rango de fechas (HU-006: CA9)",
    description=(
        "Retorna los movimientos de inventario de un producto dentro del rango de fechas indicado, "
        "ordenados de más reciente a más antiguo."
    ),
    responses={
        200: {
            "description": "Listado de movimientos del producto en el rango indicado (CA9)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Movimientos consultados exitosamente.",
                        "data": [
                            {
                                "id_movimiento": 2,
                                "id_producto": "PROD-001",
                                "ubicacion": "Tienda Física",
                                "cantidad": 5,
                                "fecha_hora": "2026-11-23T20:10:00+00:00",
                                "canal": "administración",
                                "tipo": "ajuste",
                                "id_referencia": None,
                            }
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Producto vacío o rango de fechas inválido",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La fecha de inicio no puede ser posterior a la fecha de fin.",
                        "data": ["fecha_inicio", "fecha_fin"],
                    }
                }
            },
        },
        404: {
            "description": "Producto inexistente en el catálogo",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto 'PROD-999' no existe en el catálogo.",
                        "data": ["PROD-999"],
                    }
                }
            },
        },
    },
)
def endpoint_consultar_movimientos(
    id_producto: str = Query(..., description="Identificador del producto (ej. PROD-001)."),
    fecha_inicio: Optional[datetime] = Query(
        default=None,
        description="Fecha y hora inicial en formato ISO-8601 (opcional).",
    ),
    fecha_fin: Optional[datetime] = Query(
        default=None,
        description="Fecha y hora final en formato ISO-8601 (opcional).",
    ),
):
    movimientos = consultar_movimientos_producto(
        id_producto=id_producto,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    return {
        "success": True,
        "message": "Movimientos consultados exitosamente.",
        "data": movimientos,
    }

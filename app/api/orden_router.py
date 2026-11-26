from fastapi import APIRouter, status
from app.domain.orden_schema import (
    ActualizarEstadoOrdenRequest,
    CalcularTotalRequest,
    CrearOrdenRequest,
)
from app.repositories import orden_repository
from app.services.orden_service import (
    actualizar_estado_orden,
    calcular_total_orden,
    consultar_orden,
    crear_orden,
)

router = APIRouter(prefix="/api/v1/ordenes", tags=["Órdenes"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden a partir del carrito (HU-010: FUN-4.1.3)",
    description=(
        "Verifica que el cliente esté activo (timeout máximo de 5 s) y que el carrito no esté vacío, "
        "creando la orden en estado 'pendiente de pago'."
    ),
    responses={
        201: {
            "description": "Orden creada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Orden creada exitosamente en estado pendiente de pago.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "id_cliente": "CLI-001",
                            "estado": "pendiente de pago",
                            "moneda": "COP",
                            "productos": [
                                {"id_producto": "PROD-001", "cantidad": 2, "precio_unitario": 100000}
                            ],
                            "subtotal": None,
                            "impuestos": None,
                            "descuentos": None,
                            "total": None,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Carrito vacío o datos inválidos",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El carrito está vacío. Debe incluir al menos un producto para crear la orden.",
                        "data": ["productos"],
                    }
                }
            },
        },
        403: {
            "description": "Cliente en estado distinto de activo",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El cliente 'CLI-002' no se encuentra activo para crear órdenes.",
                        "data": ["id_cliente"],
                    }
                }
            },
        },
        404: {
            "description": "Cliente o producto inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El cliente 'CLI-999' no existe.",
                        "data": ["id_cliente"],
                    }
                }
            },
        },
        503: {
            "description": "Módulo Clientes no disponible (timeout de 5 segundos)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Servicio de clientes no disponible. Tiempo de espera agotado (5 s).",
                        "data": {"orden_creada": False},
                    }
                }
            },
        },
    },
)
def registrar_orden(datos: CrearOrdenRequest):
    orden = crear_orden(datos)
    return {
        "success": True,
        "message": "Orden creada exitosamente en estado pendiente de pago.",
        "data": orden,
    }


@router.post(
    "/{id_orden}/calcular-total",
    status_code=status.HTTP_200_OK,
    summary="Calcular y registrar el total de la orden en COP (HU-010: FUN-4.1.4)",
    description=(
        "Calcula subtotal, impuestos (IVA 19%) y descuentos vigentes en la fecha actual. "
        "Registra el total en la orden en COP sin decimales (nunca negativo)."
    ),
    responses={
        200: {
            "description": "Total calculado y registrado en la orden",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Total de la orden calculado y registrado exitosamente.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "id_cliente": "CLI-001",
                            "estado": "pendiente de pago",
                            "moneda": "COP",
                            "subtotal": 200000,
                            "impuestos": 38000,
                            "descuentos": 20000,
                            "total": 218000,
                            "descuentos_aplicados": ["DESC10"],
                        },
                    }
                }
            },
        },
        404: {
            "description": "Orden inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-00000000' no existe.",
                        "data": ["id_orden"],
                    }
                }
            },
        },
    },
)
def calcular_total(id_orden: str, datos: CalcularTotalRequest | None = None):
    orden = calcular_total_orden(id_orden, datos)
    return {
        "success": True,
        "message": "Total de la orden calculado y registrado exitosamente.",
        "data": orden,
    }


@router.get(
    "/{id_orden}",
    status_code=status.HTTP_200_OK,
    summary="Consultar detalle de una orden",
    description="Retorna el estado actual de una orden y sus valores calculados en COP.",
    responses={
        200: {"description": "Orden encontrada"},
        404: {"description": "Orden inexistente"},
    },
)
def obtener_detalle_orden(id_orden: str):
    orden = consultar_orden(id_orden)
    return {
        "success": True,
        "message": "Orden consultada exitosamente.",
        "data": orden,
    }

@router.patch(
    "/{id_orden}/estado",
    status_code=status.HTTP_200_OK,
    summary="Actualizar estado de la orden por notificación (HU-011: FUN-4.1.5)",
    description=(
        "Procesa notificaciones de Pagos o Logística, valida la transición permitida, "
        "actualiza el estado de la orden y publica el evento de cambio de estado."
    ),
    responses={
        200: {
            "description": "Estado actualizado y evento publicado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Estado de la orden actualizado exitosamente.",
                        "data": {
                            "orden": {
                                "id_orden": "ORD-A1B2C3D4",
                                "id_cliente": "CLI-001",
                                "estado": "pagada",
                                "moneda": "COP",
                            },
                            "evento_publicado": {
                                "id_orden": "ORD-A1B2C3D4",
                                "estado_anterior": "pendiente de pago",
                                "estado_nuevo": "pagada",
                                "fecha_hora": "2026-11-23T23:30:00+00:00",
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Datos inválidos o evento incompatible con el origen",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El evento 'envío despachado' no corresponde al origen 'Pagos'.",
                        "data": {"origen": "Pagos", "evento": "envío despachado"},
                    }
                }
            },
        },
        404: {
            "description": "Orden inexistente (notificación registrada como rechazada)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-99999999' no existe.",
                        "data": ["id_orden"],
                    }
                }
            },
        },
        409: {
            "description": "Transición de estado no permitida (estado conservado y rechazo registrado)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Transición no permitida: no se puede pasar de 'pendiente de pago' a 'enviada'.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "estado_actual": "pendiente de pago",
                            "estado_solicitado": "enviada",
                        },
                    }
                }
            },
        },
    },
)
def procesar_notificacion_estado(id_orden: str, datos: ActualizarEstadoOrdenRequest):
    resultado = actualizar_estado_orden(id_orden, datos)
    return {
        "success": True,
        "message": "Estado de la orden actualizado exitosamente.",
        "data": resultado,
    }


@router.get(
    "/{id_orden}/eventos",
    status_code=status.HTTP_200_OK,
    summary="Consultar eventos de cambio de estado publicados para una orden (HU-011: CA3)",
)
def obtener_eventos_orden(id_orden: str):
    return {
        "success": True,
        "message": "Eventos de la orden consultados exitosamente.",
        "data": orden_repository.listar_eventos_orden(id_orden),
    }


@router.get(
    "/{id_orden}/notificaciones-rechazadas",
    status_code=status.HTTP_200_OK,
    summary="Consultar notificaciones rechazadas para una orden (HU-011: CA2 y CA4)",
)
def obtener_notificaciones_rechazadas(id_orden: str):
    return {
        "success": True,
        "message": "Notificaciones rechazadas consultadas exitosamente.",
        "data": orden_repository.listar_notificaciones_rechazadas(id_orden),
    }
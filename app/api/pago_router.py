from typing import Optional
from fastapi import APIRouter, Query, status

from app.domain.pago_schema import ConfirmacionPagoEntrada, InicioPagoEntrada
from app.repositories.pago_repository import (
    listar_duplicados_descartados,
    listar_notificaciones_ventas,
)
from app.services.pago_service import (
    confirmar_pago_pasarela,
    consultar_estado_pago_orden,
    consultar_intento_pago,
    iniciar_pago_orden,
)

router = APIRouter(prefix="/api/v1/pagos", tags=["Pagos"])


@router.post(
    "/iniciar",
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar pago de una orden ante la pasarela (HU-014: FUN-5.1.1)",
    description=(
        "Valida que la orden exista en estado 'pendiente de pago' y que el método de pago esté "
        "habilitado, envía monto y método a la pasarela externa (timeout máximo de 10 segundos), "
        "registra el intento con estado 'iniciado' y retorna el ID del intento."
    ),
    responses={
        201: {
            "description": "Intento de pago iniciado y registrado exitosamente (CA1, CA2, CA3)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Inicio de pago registrado exitosamente.",
                        "data": {
                            "id_intento": "PAG-A1B2C3D4",
                            "id_orden": "ORD-001",
                            "monto": 150000,
                            "metodo_pago": "pse",
                            "estado": "iniciado",
                            "referencia_pasarela": "PAS-9F8E7D6C",
                            "fecha_hora": "2026-11-24T23:20:00+00:00",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Monto inválido, no coincide con la orden o método de pago no habilitado",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Método de pago 'bitcoin' no habilitado. Permitidos: tarjeta_credito, tarjeta_debito, pse, nequi, daviplata.",
                        "data": ["tarjeta_credito", "tarjeta_debito", "pse", "nequi", "daviplata"],
                    }
                }
            },
        },
        404: {
            "description": "La orden indicada no existe (CA4)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-999' no existe.",
                        "data": ["ORD-999"],
                    }
                }
            },
        },
        409: {
            "description": "La orden no se encuentra en estado 'pendiente de pago' (CA4)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-002' no puede pagarse porque su estado actual es 'pagada'.",
                        "data": [{"id_orden": "ORD-002", "estado_actual": "pagada"}],
                    }
                }
            },
        },
        503: {
            "description": "La pasarela de pagos no respondió en 10 segundos (CA5)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La pasarela de pagos no respondió en 10 segundos. Servicio no disponible.",
                        "data": ["pasarela"],
                    }
                }
            },
        },
    },
)
def endpoint_iniciar_pago(datos: InicioPagoEntrada):
    intento = iniciar_pago_orden(datos)
    return {
        "success": True,
        "message": "Inicio de pago registrado exitosamente.",
        "data": intento,
    }


@router.get(
    "/intentos/{id_intento}",
    status_code=status.HTTP_200_OK,
    summary="Consultar un intento de pago por ID (HU-014)",
    description="Retorna el detalle y estado actual de un intento de pago previamente iniciado.",
    responses={
        200: {
            "description": "Intento de pago encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Intento de pago consultado exitosamente.",
                        "data": {
                            "id_intento": "PAG-A1B2C3D4",
                            "id_orden": "ORD-001",
                            "monto": 150000,
                            "metodo_pago": "pse",
                            "estado": "iniciado",
                            "referencia_pasarela": "PAS-9F8E7D6C",
                            "fecha_hora": "2026-11-24T23:20:00+00:00",
                        },
                    }
                }
            },
        },
        404: {
            "description": "El intento de pago no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El intento de pago 'PAG-00000000' no existe.",
                        "data": ["PAG-00000000"],
                    }
                }
            },
        },
    },
)
def endpoint_consultar_intento_pago(id_intento: str):
    intento = consultar_intento_pago(id_intento)
    return {
        "success": True,
        "message": "Intento de pago consultado exitosamente.",
        "data": intento,
    }


# ── HU-015: Confirmación del pago sin duplicados (FUN-5.1.2, FUN-5.1.3) ──────

@router.post(
    "/confirmar",
    status_code=status.HTTP_200_OK,
    summary="Confirmar pago desde la pasarela sin duplicados (HU-015: FUN-5.1.2 y FUN-5.1.3)",
    description=(
        "Valida firma de integridad SHA-256, campos obligatorios y monto contra la orden. "
        "Si el ID de transacción ya fue procesado (RN-03), descarta como 'duplicado' con HTTP 200 "
        "sin modificar el pago ni volver a informar a Ventas. Si es nueva, actualiza el estado "
        "('aprobado' o 'rechazado') e informa a Ventas."
    ),
    responses={
        200: {
            "description": "Confirmación procesada o descartada como duplicada (CA1, CA3, CA4, CA5, CA7)",
            "content": {
                "application/json": {
                    "examples": {
                        "procesada": {
                            "summary": "Confirmación nueva procesada (CA1, CA3, CA5)",
                            "value": {
                                "success": True,
                                "message": "Confirmación de pago procesada exitosamente.",
                                "data": {
                                    "resultado": "procesada",
                                    "id_transaccion": "TXN-001",
                                    "id_orden": "ORD-001",
                                    "estado_pago": "aprobado",
                                    "monto": 150000,
                                    "notificacion_ventas": {
                                        "id_orden": "ORD-001",
                                        "estado_pago": "aprobado",
                                        "id_transaccion": "TXN-001",
                                        "fecha_hora": "2026-11-25T00:05:00+00:00",
                                    },
                                    "fecha_hora": "2026-11-25T00:05:00+00:00",
                                },
                            },
                        },
                        "duplicado": {
                            "summary": "Transacción duplicada descartada (CA4, CA6, RN-03)",
                            "value": {
                                "success": True,
                                "message": "Confirmación descartada por transacción duplicada (RN-03).",
                                "data": {
                                    "resultado": "duplicado",
                                    "id_transaccion": "TXN-001",
                                    "id_orden": "ORD-001",
                                    "fecha_hora": "2026-11-25T00:06:00+00:00",
                                },
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Firma inválida, campo obligatorio faltante, estado inválido o monto distinto (CA2)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Firma de integridad inválida. Respuesta descartada sin actualizar el pago.",
                        "data": ["firma"],
                    }
                }
            },
        },
        404: {
            "description": "La orden indicada en la confirmación no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-999' no existe.",
                        "data": ["ORD-999"],
                    }
                }
            },
        },
    },
)
def endpoint_confirmar_pago(datos: ConfirmacionPagoEntrada):
    resultado = confirmar_pago_pasarela(datos)
    if resultado["resultado"] == "duplicado":
        mensaje = "Confirmación descartada por transacción duplicada (RN-03)."
    else:
        mensaje = "Confirmación de pago procesada exitosamente."
    return {
        "success": True,
        "message": mensaje,
        "data": resultado,
    }


@router.get(
    "/estado/{id_orden}",
    status_code=status.HTTP_200_OK,
    summary="Consultar estado de pago de una orden (Contrato estado_pago)",
    description="Retorna el último estado de pago registrado para la orden indicada.",
    responses={
        200: {
            "description": "Estado de pago encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Estado de pago consultado exitosamente.",
                        "data": {
                            "id_orden": "ORD-001",
                            "id_intento": "PAG-A1B2C3D4",
                            "estado": "aprobado",
                            "monto": 150000,
                            "metodo_pago": "pse",
                            "fecha_hora": "2026-11-25T00:05:00+00:00",
                        },
                    }
                }
            },
        },
        404: {
            "description": "No existen pagos registrados para la orden",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No se encontraron pagos registrados para la orden 'ORD-999'.",
                        "data": ["ORD-999"],
                    }
                }
            },
        },
    },
)
def endpoint_consultar_estado_pago(id_orden: str):
    estado = consultar_estado_pago_orden(id_orden)
    return {
        "success": True,
        "message": "Estado de pago consultado exitosamente.",
        "data": estado,
    }


@router.get(
    "/duplicados",
    status_code=status.HTTP_200_OK,
    summary="Consultar descartes de confirmaciones duplicadas (HU-015: CA6)",
    description="Lista los descartes registrados por transacciones duplicadas (RN-03) con fecha y hora.",
)
def endpoint_listar_duplicados(
    id_transaccion: Optional[str] = Query(default=None, description="Filtrar por ID de transacción.")
):
    duplicados = listar_duplicados_descartados(id_transaccion=id_transaccion)
    return {
        "success": True,
        "message": "Descartes por duplicado consultados exitosamente.",
        "data": duplicados,
    }


@router.get(
    "/notificaciones-ventas",
    status_code=status.HTTP_200_OK,
    summary="Consultar notificaciones de pago enviadas a Ventas (HU-015: CA3)",
    description="Lista las notificaciones enviadas a Ventas (API-INT-05) tras actualizar pagos.",
)
def endpoint_listar_notificaciones_ventas(
    id_orden: Optional[str] = Query(default=None, description="Filtrar por ID de orden.")
):
    notificaciones = listar_notificaciones_ventas(id_orden=id_orden)
    return {
        "success": True,
        "message": "Notificaciones a Ventas consultadas exitosamente.",
        "data": notificaciones,
    }

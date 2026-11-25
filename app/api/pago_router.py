from fastapi import APIRouter, status

from app.domain.pago_schema import InicioPagoEntrada
from app.services.pago_service import consultar_intento_pago, iniciar_pago_orden

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

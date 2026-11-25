# app/api/refund.py
from fastapi import APIRouter, status
from app.core.refund_gateway import refund_gateway
from app.domain.refund import RefundCreateRequest, RefundStandardResponse
from app.repositories.refund import refund_repository
from app.services.refund import RefundService

router = APIRouter(
    prefix="/api/v1/payments/refunds",
    tags=["Payments - Refunds (MOD-05)"]
)

refund_service = RefundService(
    repository=refund_repository,
    gateway=refund_gateway,
)


@router.post(
    "",
    response_model=RefundStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Procesar reembolso total de una orden pagada (HU-034 / FUN-5.1.5)",
    description=(
        "Verifica que la orden tenga pago 'aprobado', no haya sido reembolsada y esté dentro "
        "del plazo máximo de reembolso. Envía el reembolso total a la pasarela (timeout 10s) y "
        "actualiza el pago a 'reembolsado' y la orden a 'reembolsada'."
    ),
    responses={
        200: {
            "description": "CA1, CA3 - Reembolso total confirmado y estados actualizados",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "refund_id": 1,
                            "order_id": 1001,
                            "transaction_id": "TX-WOMPI-12345",
                            "refund_reference": "REF-9876543210",
                            "amount": 120000.0,
                            "payment_status": "reembolsado",
                            "order_status": "reembolsada",
                            "refund_status": "reembolsado",
                            "processed_at": "2026-11-24T13:23:00Z"
                        },
                        "message": "Reembolso total procesado exitosamente."
                    }
                }
            }
        },
        404: {
            "description": "La orden no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "La orden con ID 9999 no existe."
                    }
                }
            }
        },
        409: {
            "description": "CA2 / CA4 - Condición de elegibilidad incumplida o rechazo de pasarela",
            "content": {
                "application/json": {
                    "examples": {
                        "YaReembolsada": {
                            "summary": "CA2 - Orden ya reembolsada",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Reembolso rechazado: la orden ya ha sido reembolsada previamente."
                            }
                        },
                        "PlazoVencido": {
                            "summary": "CA2 - Fuera del plazo máximo",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Reembolso rechazado: excedió el plazo máximo de 30 días."
                            }
                        },
                        "PagoNoAprobado": {
                            "summary": "CA2 - Pago no aprobado",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Reembolso rechazado: el pago de la orden no está en estado 'aprobado'."
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "CA4 - Pasarela no responde en 10 segundos o no está disponible",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Reembolso no disponible: La pasarela de pagos no respondió dentro de 10 segundos."
                    }
                }
            }
        }
    }
)
def create_refund_endpoint(payload: RefundCreateRequest):
    refund_data = refund_service.process_full_refund(payload)
    return RefundStandardResponse(
        success=True,
        data=refund_data,
        message="Reembolso total procesado exitosamente."
    )
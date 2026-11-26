# app/api/rejected_payment.py
from fastapi import APIRouter, status
from app.domain.rejected_payment import (
    RejectedPaymentRequest,
    RejectedPaymentStandardResponse,
)
from app.repositories.rejected_payment import rejected_payment_repository
from app.services.rejected_payment import RejectedPaymentService

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Payments - Rejected Attempts (MOD-05)"]
)

rejected_payment_service = RejectedPaymentService(repository=rejected_payment_repository)


@router.post(
    "/rejected",
    response_model=RejectedPaymentStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar intento de pago rechazado de una orden (HU-033 / FUN-5.1.4)",
    description=(
        "Registra la respuesta de pago rechazado informada por la pasarela (Wompi / PayU) con ID de orden, "
        "ID de transacción, motivo (o 'sin motivo informado' si no viene) y fecha/hora, incrementando en 1 "
        "el contador de intentos fallidos de la orden."
    ),
    responses={
        200: {
            "description": "CA1, CA2, CA3 - Intento fallido registrado y contador incrementado",
            "content": {
                "application/json": {
                    "examples": {
                        "ConMotivoInformado": {
                            "summary": "CA1/CA2/CA3 - Rechazo con código y descripción",
                            "value": {
                                "success": True,
                                "data": {
                                    "attempt_id": 1,
                                    "order_id": 1001,
                                    "transaction_id": "TX-WOMPI-987654",
                                    "rejection_code": "ERR-51",
                                    "reason": "[ERR-51] Fondos insuficientes en la cuenta",
                                    "recorded_at": "2026-11-24T18:07:00Z",
                                    "order_failed_attempts": 1
                                },
                                "message": "Intento de pago rechazado registrado exitosamente."
                            }
                        },
                        "SinMotivoInformado": {
                            "summary": "CA1 - Pasarela no informa código ni descripción",
                            "value": {
                                "success": True,
                                "data": {
                                    "attempt_id": 2,
                                    "order_id": 1001,
                                    "transaction_id": "TX-WOMPI-987655",
                                    "rejection_code": None,
                                    "reason": "sin motivo informado",
                                    "recorded_at": "2026-11-24T18:08:00Z",
                                    "order_failed_attempts": 2
                                },
                                "message": "Intento de pago rechazado registrado exitosamente."
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Datos obligatorios faltantes o formato inválido",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Faltan campos obligatorios: order_id, transaction_id."
                    }
                }
            }
        },
        404: {
            "description": "La orden asociada no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "La orden con ID 9999 no existe."
                    }
                }
            }
        }
    }
)
def register_rejected_payment_endpoint(payload: RejectedPaymentRequest):
    attempt_data = rejected_payment_service.register_rejected_payment(payload)
    return RejectedPaymentStandardResponse(
        success=True,
        data=attempt_data,
        message="Intento de pago rechazado registrado exitosamente."
    )
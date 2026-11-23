# app/api/enrollment.py
from fastapi import APIRouter, Depends, Path, status
from app.core.auth import get_current_client_id
from app.domain.enrollment import (
    EnrollmentCreateRequest,
    EnrollmentCreateStandardResponse,
    EnrollmentStandardResponse,
    QuotaValidationStandardResponse,
)
from app.repositories.enrollment import enrollment_repository
from app.repositories.event import event_repository
from app.services.enrollment import EnrollmentService

router = APIRouter(
    prefix="/api/v1/enrollments",
    tags=["Events - Enrollments (MOD-06)"]
)

enrollment_service = EnrollmentService(
    enrollment_repo=enrollment_repository,
    event_repo=event_repository
)


@router.get(
    "/availability/{event_id}",
    response_model=QuotaValidationStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar disponibilidad de cupo en un evento (HU-018 / FUN-6.1.3)",
    description=(
        "Consulta si un evento existe, tiene fecha futura y cuenta con al menos 1 cupo disponible (RN-04). "
        "Autoriza o rechaza continuar con el proceso de inscripción."
    ),
    responses={
        200: {
            "description": "CA5 - Cupo disponible, inscripción autorizada",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "event_id": 1,
                            "result": "autorizada",
                            "reason": "Evento disponible: fecha válida y cupos disponibles.",
                            "available_spots": 15
                        },
                        "message": "Validación de cupo autorizada."
                    }
                }
            }
        },
        404: {
            "description": "CA8 - El evento no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "El evento con ID 99 no existe."
                    }
                }
            }
        },
        409: {
            "description": "CA6 / CA7 - Cupo agotado (RN-04) o evento ya ocurrido",
            "content": {
                "application/json": {
                    "examples": {
                        "CupoAgotado": {
                            "summary": "CA6 - Cupo agotado (0)",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "El cupo para este evento está agotado (RN-04)."
                            }
                        },
                        "EventoPasado": {
                            "summary": "CA7 - El evento ya ocurrió",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "El evento ya ocurrió y ya no admite inscripciones."
                            }
                        }
                    }
                }
            }
        }
    }
)
def check_event_availability_endpoint(
    event_id: int = Path(..., gt=0, description="ID del evento a consultar", examples=[1])
):
    validation_result = enrollment_service.validate_quota(event_id=event_id)
    return QuotaValidationStandardResponse(
        success=True,
        data=validation_result,
        message="Validación de cupo autorizada."
    )


@router.post(
    "",
    response_model=EnrollmentCreateStandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscribirse a un evento y procesar pago (HU-018 / FUN-6.1.2)",
    description=(
        "Valida disponibilidad de cupo (FUN-6.1.3), solicita el cobro mediante API Pagos (API-INT-09) "
        "y, si es aprobado, registra la inscripción en estado 'confirmada' descontando 1 cupo "
        "con control de concurrencia (RN-04)."
    ),
    responses={
        201: {
            "description": "CA1, CA2 - Pago aprobado e inscripción confirmada",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "enrollment_id": 1,
                            "status": "confirmada",
                            "event_id": 1,
                            "client_id": 10,
                            "amount_paid": 25000.0,
                            "transaction_id": "TX-A1B2C3D4E5",
                            "available_spots": 14
                        },
                        "message": "Inscripción confirmada exitosamente."
                    }
                }
            }
        },
        400: {
            "description": "Datos faltantes, formato inválido o método de pago no soportado",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Faltan campos obligatorios: event_id, client_id, payment_method."
                    }
                }
            }
        },
        404: {
            "description": "CA8 - El evento no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "El evento con ID 99 no existe."
                    }
                }
            }
        },
        409: {
            "description": "CA3, CA4, CA6, CA7 - Pago rechazado, cupo agotado o evento pasado",
            "content": {
                "application/json": {
                    "examples": {
                        "PagoRechazado": {
                            "summary": "CA3 - Pago rechazado por pasarela",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Inscripción rechazada: El pago fue rechazado por la pasarela de pagos."
                            }
                        },
                        "CupoAgotado": {
                            "summary": "CA4 / CA6 - Cupo agotado (RN-04)",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "El cupo para este evento está agotado (RN-04)."
                            }
                        },
                        "EventoPasado": {
                            "summary": "CA7 - El evento ya ocurrió",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "El evento ya ocurrió y ya no admite inscripciones."
                            }
                        }
                    }
                }
            }
        }
    }
)
def create_enrollment_endpoint(payload: EnrollmentCreateRequest):
    created = enrollment_service.enroll_client(payload)
    return EnrollmentCreateStandardResponse(
        success=True,
        data=created,
        message="Inscripción confirmada exitosamente."
    )


@router.patch(
    "/{enrollment_id}/cancel",
    response_model=EnrollmentStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancelar inscripción a un evento (HU-037)",
    description="Cancela una inscripción confirmada con al menos 24 horas de antelación y libera 1 cupo (RN-04)."
)
def cancel_enrollment_endpoint(
    enrollment_id: int = Path(..., gt=0, description="ID de la inscripción a cancelar", examples=[1]),
    client_id: int = Depends(get_current_client_id)
):
    result = enrollment_service.cancel_enrollment(
        enrollment_id=enrollment_id,
        client_id=client_id
    )
    return EnrollmentStandardResponse(
        success=True,
        data=result,
        message="Inscripción cancelada exitosamente y cupo liberado."
    )
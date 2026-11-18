# app/api/enrollment.py
from fastapi import APIRouter, Depends, Path, status
from app.core.auth import get_current_client_id
from app.domain.enrollment import EnrollmentStandardResponse
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


@router.patch(
    "/{enrollment_id}/cancel",
    response_model=EnrollmentStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancelar inscripción a un evento (HU-037)",
    description=(
        "Permite al Cliente autenticado cancelar su inscripción confirmada siempre que falten "
        "al menos 24 horas para el inicio del evento. Libera 1 cupo en el evento sin superar "
        "la capacidad máxima (RN-04)."
    ),
    responses={
        200: {
            "description": "Inscripción cancelada y cupo liberado exitosamente (CA1, CA2)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "enrollment_id": 1,
                            "event_id": 1,
                            "client_id": 10,
                            "status": "cancelado",
                            "available_spots": 16,
                            "cancelled_at": "2026-11-18T17:00:00Z"
                        },
                        "message": "Inscripción cancelada exitosamente y cupo liberado."
                    }
                }
            }
        },
        401: {
            "description": "Usuario no autenticado (token ausente, inválido o vencido)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Usuario no autenticado: token ausente o formato inválido."
                    }
                }
            }
        },
        403: {
            "description": "CA4 - Sin permiso (la inscripción pertenece a otro cliente)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "No tiene permiso para cancelar una inscripción que pertenece a otro cliente."
                    }
                }
            }
        },
        404: {
            "description": "Inscripción o evento inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "No se encontró la inscripción con ID 999."
                    }
                }
            }
        },
        409: {
            "description": "CA3 - Conflicto de regla de negocio (menos de 24h o ya cancelada)",
            "content": {
                "application/json": {
                    "examples": {
                        "MenosDe24Horas": {
                            "summary": "Faltan menos de 24 horas para el evento",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "No se puede cancelar la inscripción porque faltan menos de 24 horas para el evento."
                            }
                        },
                        "YaCancelada": {
                            "summary": "La inscripción ya está cancelada",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "La inscripción ya se encuentra en estado cancelado."
                            }
                        }
                    }
                }
            }
        }
    }
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
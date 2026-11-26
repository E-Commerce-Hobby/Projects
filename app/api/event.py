# app/api/event.py
from fastapi import APIRouter, status
from app.domain.event import EventCreateRequest, StandardResponse
from app.repositories.event import event_repository
from app.services.event import EventService

router = APIRouter(
    prefix="/api/v1/events",
    tags=["Events (MOD-06)"]
)

event_service = EventService(repository=event_repository)


@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo evento (HU-017)",
    description=(
        "Permite al Administrador crear un torneo o curso definiendo su nombre, "
        "fecha y hora futura, capacidad máxima (RN-04: entero >= 1) y precio de inscripción en COP. "
        "Al crearse, los cupos disponibles se asignan automáticamente iguales a la capacidad máxima."
    ),
    responses={
        201: {
            "description": "Evento creado exitosamente (CA1)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": 1,
                            "name": "Torneo Nacional de Catan",
                            "event_date": "2027-05-15T14:00:00Z",
                            "max_capacity": 32,
                            "available_spots": 32,
                            "registration_price": 25000.0,
                            "currency": "COP"
                        },
                        "message": "Evento creado exitosamente."
                    }
                }
            }
        },
        400: {
            "description": "Error de validación o regla de negocio (CA2, CA3, CA4)",
            "content": {
                "application/json": {
                    "examples": {
                        "CA2_FechaInvalida": {
                            "summary": "CA2 - Fecha igual o anterior a la actual",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "La fecha es inválida: debe ser posterior al momento actual."
                            }
                        },
                        "CA3_CapacidadInvalida_RN04": {
                            "summary": "CA3 - Capacidad menor o igual a 0 o no entera (RN-04)",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "La capacidad es inválida (RN-04): debe ser un entero mayor o igual a 1."
                            }
                        },
                        "CA4_CamposFaltantes": {
                            "summary": "CA4 - Campos obligatorios faltantes",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Faltan campos obligatorios: name, max_capacity."
                            }
                        }
                    }
                }
            }
        }
    }
)
def create_event_endpoint(payload: EventCreateRequest):
    created_event = event_service.create_event(payload)
    return StandardResponse(
        success=True,
        data=created_event,
        message="Evento creado exitosamente."
    )
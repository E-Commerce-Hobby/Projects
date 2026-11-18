# app/services/event.py
from datetime import datetime, timezone
from app.core.errors import ReglaNegocioError
from app.domain.event import EventCreateRequest, EventResponseData
from app.repositories.event import EventRepository


class EventService:
    def __init__(self, repository: EventRepository):
        self.repository = repository

    def create_event(self, payload: EventCreateRequest) -> EventResponseData:
        # Verificación de regla de negocio RN-04: Capacidad válida
        if not isinstance(payload.max_capacity, int) or isinstance(payload.max_capacity, bool) or payload.max_capacity < 1:
            raise ReglaNegocioError(
                "La capacidad es inválida (RN-04): debe ser un número entero mayor o igual a 1."
            )

        # Verificación de fecha posterior al momento actual (CA2)
        now = datetime.now(timezone.utc) if payload.event_date.tzinfo else datetime.now()
        if payload.event_date <= now:
            raise ReglaNegocioError(
                "La fecha es inválida: la fecha y hora deben ser posteriores al momento actual."
            )

        # Verificación de precio válido
        if payload.registration_price < 0:
            raise ReglaNegocioError(
                "El precio de inscripción es inválido: debe ser mayor o igual a 0."
            )

        # Validación de duplicados (mismo nombre y misma fecha)
        existing_event = self.repository.get_by_name_and_date(
            name=payload.name,
            event_date=payload.event_date
        )
        if existing_event:
            raise ReglaNegocioError(
                "Ya existe un evento registrado con el mismo nombre y fecha."
            )

        # CA1: Registrar evento con cupos disponibles iguales a la capacidad máxima
        event_to_save = {
            "name": payload.name,
            "event_date": payload.event_date,
            "max_capacity": payload.max_capacity,
            "available_spots": payload.max_capacity,
            "registration_price": payload.registration_price,
            "currency": "COP"
        }

        created_record = self.repository.create(event_to_save)
        return EventResponseData(**created_record)
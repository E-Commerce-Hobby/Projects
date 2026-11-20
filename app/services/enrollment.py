# app/services/enrollment.py
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.core.errors import ReglaNegocioError
from app.domain.enrollment import EnrollmentCancelResponseData
from app.repositories.enrollment import EnrollmentRepository
from app.repositories.event import EventRepository


class EnrollmentService:
    def __init__(self, enrollment_repo: EnrollmentRepository, event_repo: EventRepository):
        self.enrollment_repo = enrollment_repo
        self.event_repo = event_repo

    def cancel_enrollment(self, enrollment_id: int, client_id: int) -> EnrollmentCancelResponseData:
        # 1. Verificar existencia de la inscripción (HTTP 404)
        enrollment = self.enrollment_repo.get_by_id(enrollment_id)
        if not enrollment:
            raise ReglaNegocioError(
                f"No se encontró la inscripción con ID {enrollment_id}.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 2. CA4: Verificar que la inscripción pertenezca al cliente autenticado (HTTP 403)
        if enrollment["client_id"] != client_id:
            raise ReglaNegocioError(
                "No tiene permiso para cancelar una inscripción que pertenece a otro cliente.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 3. CA3: Verificar que la inscripción no esté ya cancelada (HTTP 409)
        if enrollment["status"] == "cancelado":
            raise ReglaNegocioError(
                "La inscripción ya se encuentra en estado cancelado.",
                status_code=status.HTTP_409_CONFLICT
            )

        if enrollment["status"] != "confirmada":
            raise ReglaNegocioError(
                f"No es posible cancelar una inscripción en estado '{enrollment['status']}'.",
                status_code=status.HTTP_409_CONFLICT
            )

        # 4. Consultar el evento asociado (HTTP 404)
        event = self.event_repo.get_by_id(enrollment["event_id"])
        if not event:
            raise ReglaNegocioError(
                "El evento asociado a la inscripción no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 5. CA1 y CA3: Verificar plazo mínimo de 24 horas antes del evento (HTTP 409)
        event_date: datetime = event["event_date"]
        now = datetime.now(timezone.utc) if event_date.tzinfo else datetime.now()
        time_remaining = event_date - now

        if time_remaining < timedelta(hours=24):
            raise ReglaNegocioError(
                "No se puede cancelar la inscripción porque faltan menos de 24 horas para el evento.",
                status_code=status.HTTP_409_CONFLICT
            )

        # 6. CA1: Cambiar estado de la inscripción a 'cancelado'
        cancelled_at = now
        self.enrollment_repo.update_status(
            enrollment_id=enrollment_id,
            new_status="cancelado",
            cancelled_at=cancelled_at
        )

        # 7. CA2 y RN-04: Liberar 1 cupo sin superar la capacidad máxima del evento
        current_spots = event["available_spots"]
        max_capacity = event["max_capacity"]
        updated_spots = min(current_spots + 1, max_capacity)
        self.event_repo.update_available_spots(event_id=event["id"], new_available_spots=updated_spots)

        return EnrollmentCancelResponseData(
            enrollment_id=enrollment["id"],
            event_id=event["id"],
            client_id=enrollment["client_id"],
            status="cancelado",
            available_spots=updated_spots,
            cancelled_at=cancelled_at
        )
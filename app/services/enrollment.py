# app/services/enrollment.py
from datetime import datetime, timedelta, timezone
import threading
from fastapi import status
from app.core.errors import ReglaNegocioError
from app.core.payment_gateway import PaymentGatewayClient, payment_gateway
from app.domain.enrollment import (
    EnrollmentCancelResponseData,
    EnrollmentCreateRequest,
    EnrollmentCreateResponseData,
    QuotaValidationResponseData,
)
from app.repositories.enrollment import EnrollmentRepository
from app.repositories.event import EventRepository


class EnrollmentService:
    def __init__(
        self,
        enrollment_repo: EnrollmentRepository,
        event_repo: EventRepository,
        gateway: PaymentGatewayClient = payment_gateway
    ):
        self.enrollment_repo = enrollment_repo
        self.event_repo = event_repo
        self.gateway = gateway
        # Lock para garantizar exclusión mutua ante inscripciones concurrentes (CA4 / RN-04)
        self._quota_lock = threading.Lock()

    def validate_quota(self, event_id: int) -> QuotaValidationResponseData:
        """
        FUN-6.1.3: Validación de cupo (CA5, CA6, CA7, CA8).
        """
        # CA8: Verificar que el evento exista (HTTP 404)
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise ReglaNegocioError(
                f"El evento con ID {event_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA7: Verificar que la fecha y hora sean posteriores al momento actual (HTTP 409)
        event_date: datetime = event["event_date"]
        now = datetime.now(timezone.utc) if event_date.tzinfo else datetime.now()
        if event_date <= now:
            raise ReglaNegocioError(
                "El evento ya ocurrió y ya no admite inscripciones.",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA6: Verificar que exista al menos 1 cupo disponible (RN-04, HTTP 409)
        if event["available_spots"] <= 0:
            raise ReglaNegocioError(
                "El cupo para este evento está agotado (RN-04).",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA5: Autoriza continuar con la inscripción
        return QuotaValidationResponseData(
            event_id=event["id"],
            result="autorizada",
            reason="Evento disponible: fecha válida y cupos disponibles.",
            available_spots=event["available_spots"]
        )

    def enroll_client(self, payload: EnrollmentCreateRequest) -> EnrollmentCreateResponseData:
        """
        FUN-6.1.2: Inscripción y pago con control de concurrencia (CA1, CA2, CA3, CA4, RN-04).
        """
        with self._quota_lock:
            # 1. Ejecutar validación de cupo (FUN-6.1.3 -> CA5, CA6, CA7, CA8)
            self.validate_quota(payload.event_id)

            event = self.event_repo.get_by_id(payload.event_id)

            # Validar que el cliente no tenga ya una inscripción confirmada en el mismo evento
            existing = self.enrollment_repo.get_active_by_client_and_event(
                client_id=payload.client_id,
                event_id=payload.event_id
            )
            if existing:
                raise ReglaNegocioError(
                    "El cliente ya cuenta con una inscripción confirmada en este evento.",
                    status_code=status.HTTP_409_CONFLICT
                )

            # 2. CA1: Solicitar el pago por el precio del evento mediante API Pagos (API-INT-09)
            payment_result = self.gateway.process_payment(
                client_id=payload.client_id,
                event_id=payload.event_id,
                amount=event["registration_price"],
                payment_method=payload.payment_method
            )

            # 3. CA3: Si el pago es rechazado, no registra la inscripción y los cupos no cambian
            if not payment_result.approved:
                raise ReglaNegocioError(
                    f"Inscripción rechazada: {payment_result.reason}",
                    status_code=status.HTTP_409_CONFLICT
                )

            # 4. CA2 y CA4 (RN-04): Restar 1 cupo asegurando que nunca sea menor que 0
            if event["available_spots"] < 1:
                raise ReglaNegocioError(
                    "El cupo para este evento está agotado (RN-04).",
                    status_code=status.HTTP_409_CONFLICT
                )

            new_available_spots = event["available_spots"] - 1
            self.event_repo.update_available_spots(
                event_id=event["id"],
                new_available_spots=new_available_spots
            )

            # Registrar inscripción con estado 'confirmada'
            created_enrollment = self.enrollment_repo.create({
                "event_id": event["id"],
                "client_id": payload.client_id,
                "status": "confirmada",
                "amount_paid": event["registration_price"],
                "payment_method": payload.payment_method,
                "transaction_id": payment_result.transaction_id,
                "cancelled_at": None
            })

            return EnrollmentCreateResponseData(
                enrollment_id=created_enrollment["id"],
                status=created_enrollment["status"],
                event_id=created_enrollment["event_id"],
                client_id=created_enrollment["client_id"],
                amount_paid=created_enrollment["amount_paid"],
                transaction_id=created_enrollment["transaction_id"],
                available_spots=new_available_spots
            )

    def cancel_enrollment(self, enrollment_id: int, client_id: int) -> EnrollmentCancelResponseData:
        """HU-037: Cancelación de inscripción a evento."""
        with self._quota_lock:
            enrollment = self.enrollment_repo.get_by_id(enrollment_id)
            if not enrollment:
                raise ReglaNegocioError(
                    f"No se encontró la inscripción con ID {enrollment_id}.",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            if enrollment["client_id"] != client_id:
                raise ReglaNegocioError(
                    "No tiene permiso para cancelar una inscripción que pertenece a otro cliente.",
                    status_code=status.HTTP_403_FORBIDDEN
                )

            if enrollment["status"] == "cancelado":
                raise ReglaNegocioError(
                    "La inscripción ya se encuentra en estado cancelado.",
                    status_code=status.HTTP_409_CONFLICT
                )

            event = self.event_repo.get_by_id(enrollment["event_id"])
            if not event:
                raise ReglaNegocioError(
                    "El evento asociado a la inscripción no existe.",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            event_date: datetime = event["event_date"]
            now = datetime.now(timezone.utc) if event_date.tzinfo else datetime.now()
            if (event_date - now) < timedelta(hours=24):
                raise ReglaNegocioError(
                    "No se puede cancelar la inscripción porque faltan menos de 24 horas para el evento.",
                    status_code=status.HTTP_409_CONFLICT
                )

            self.enrollment_repo.update_status(
                enrollment_id=enrollment_id,
                new_status="cancelado",
                cancelled_at=now
            )

            updated_spots = min(event["available_spots"] + 1, event["max_capacity"])
            self.event_repo.update_available_spots(event_id=event["id"], new_available_spots=updated_spots)

            return EnrollmentCancelResponseData(
                enrollment_id=enrollment["id"],
                event_id=event["id"],
                client_id=enrollment["client_id"],
                status="cancelado",
                available_spots=updated_spots,
                cancelled_at=now
            )
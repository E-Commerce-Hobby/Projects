# app/repositories/enrollment.py
from datetime import datetime
from typing import Dict, List, Optional


class EnrollmentRepository:
    def __init__(self):
        self._enrollments_db: List[Dict] = []
        self._id_counter: int = 1

    def create(self, enrollment_data: dict) -> dict:
        new_enrollment = {
            "id": self._id_counter,
            **enrollment_data
        }
        self._enrollments_db.append(new_enrollment)
        self._id_counter += 1
        return new_enrollment

    def get_by_id(self, enrollment_id: int) -> Optional[dict]:
        for enrollment in self._enrollments_db:
            if enrollment["id"] == enrollment_id:
                return enrollment
        return None

    def get_active_by_client_and_event(self, client_id: int, event_id: int) -> Optional[dict]:
        for enrollment in self._enrollments_db:
            if (
                enrollment["client_id"] == client_id
                and enrollment["event_id"] == event_id
                and enrollment["status"] == "confirmada"
            ):
                return enrollment
        return None

    def get_all(self) -> List[Dict]:
        return list(self._enrollments_db)

    def update_status(self, enrollment_id: int, new_status: str, cancelled_at: datetime) -> Optional[dict]:
        enrollment = self.get_by_id(enrollment_id)
        if enrollment:
            enrollment["status"] = new_status
            enrollment["cancelled_at"] = cancelled_at
        return enrollment

    def clear(self) -> None:
        self._enrollments_db.clear()
        self._id_counter = 1


enrollment_repository = EnrollmentRepository()
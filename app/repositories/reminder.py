# app/repositories/reminder.py
from datetime import datetime
from typing import Dict, List, Optional


class ReminderRepository:
    def __init__(self):
        self._logs_db: List[Dict] = []
        self._id_counter: int = 1
        self._last_check_at: Optional[datetime] = None

    def create_log(self, log_data: dict) -> dict:
        entry = {
            "id": self._id_counter,
            **log_data
        }
        self._logs_db.append(entry)
        self._id_counter += 1
        return entry

    def has_sent_reminder(self, enrollment_id: int, channel: str = "email") -> bool:
        for entry in self._logs_db:
            if (
                entry["enrollment_id"] == enrollment_id
                and entry["channel"] == channel
                and entry["result"] == "enviado"
            ):
                return True
        return False

    def get_all_logs(self) -> List[Dict]:
        return list(self._logs_db)

    def get_last_check_at(self) -> Optional[datetime]:
        return self._last_check_at

    def set_last_check_at(self, timestamp: datetime) -> None:
        self._last_check_at = timestamp

    def clear(self) -> None:
        self._logs_db.clear()
        self._id_counter = 1
        self._last_check_at = None


reminder_repository = ReminderRepository()
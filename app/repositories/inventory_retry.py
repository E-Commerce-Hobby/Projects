# app/repositories/inventory_retry.py
from typing import Dict, List, Optional


class InventoryRetryRepository:
    def __init__(self):
        self._operations_db: List[Dict] = []
        self._alerts_db: List[Dict] = []
        self._alert_id_counter: int = 1

    def save_operation(self, operation_record: dict) -> dict:
        for idx, existing in enumerate(self._operations_db):
            if existing["operation_id"] == operation_record["operation_id"]:
                self._operations_db[idx] = operation_record
                return operation_record
        self._operations_db.append(operation_record)
        return operation_record

    def create_alert(self, operation_id: str, reason: str, created_at) -> dict:
        alert = {
            "alert_id": self._alert_id_counter,
            "operation_id": operation_id,
            "reason": reason,
            "created_at": created_at,
        }
        self._alert_id_counter += 1
        self._alerts_db.append(alert)
        return alert

    def list_operations(self) -> List[Dict]:
        return list(self._operations_db)

    def list_alerts(self) -> List[Dict]:
        return list(self._alerts_db)

    def get_alert_by_operation(self, operation_id: str) -> Optional[dict]:
        for alert in self._alerts_db:
            if alert["operation_id"] == operation_id:
                return alert
        return None

    def clear(self) -> None:
        self._operations_db.clear()
        self._alerts_db.clear()
        self._alert_id_counter = 1


inventory_retry_repository = InventoryRetryRepository()
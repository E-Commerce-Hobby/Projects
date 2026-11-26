# app/repositories/rejected_payment.py
from typing import Dict, List, Optional


class RejectedPaymentRepository:
    def __init__(self):
        self._orders_db: Dict[int, Dict] = {}
        self._failed_attempts_db: List[Dict] = []
        self._attempt_id_counter: int = 1

    # --- Operaciones CRUD sobre Órdenes ---
    def register_order(self, order_id: int, failed_attempts_count: int = 0) -> dict:
        order = {
            "order_id": order_id,
            "failed_attempts_count": failed_attempts_count,
        }
        self._orders_db[order_id] = order
        return order

    def get_order_by_id(self, order_id: int) -> Optional[dict]:
        return self._orders_db.get(order_id)

    def increment_order_failed_attempts(self, order_id: int) -> Optional[int]:
        order = self.get_order_by_id(order_id)
        if not order:
            return None
        order["failed_attempts_count"] += 1
        return order["failed_attempts_count"]

    # --- Operaciones CRUD sobre Intentos Fallidos ---
    def create_failed_attempt(self, attempt_data: dict) -> dict:
        record = {
            "attempt_id": self._attempt_id_counter,
            **attempt_data,
        }
        self._failed_attempts_db.append(record)
        self._attempt_id_counter += 1
        return record

    def get_attempts_by_order(self, order_id: int) -> List[Dict]:
        return [item for item in self._failed_attempts_db if item["order_id"] == order_id]

    def get_all_attempts(self) -> List[Dict]:
        return list(self._failed_attempts_db)

    def clear(self) -> None:
        self._orders_db.clear()
        self._failed_attempts_db.clear()
        self._attempt_id_counter = 1


rejected_payment_repository = RejectedPaymentRepository()
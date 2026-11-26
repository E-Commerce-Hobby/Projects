# app/repositories/refund.py
from datetime import datetime, timezone
from typing import Dict, List, Optional


class RefundRepository:
    def __init__(self):
        self._orders_db: Dict[int, Dict] = {}
        self._refunds_db: List[Dict] = []
        self._refund_id_counter: int = 1

    def register_paid_order(
        self,
        order_id: int,
        transaction_id: str,
        amount: float,
        payment_status: str = "aprobado",
        order_status: str = "pagada",
        paid_at: Optional[datetime] = None,
    ) -> dict:
        order = {
            "order_id": order_id,
            "transaction_id": transaction_id,
            "amount": float(amount),
            "payment_status": payment_status,
            "order_status": order_status,
            "paid_at": paid_at or datetime.now(timezone.utc),
        }
        self._orders_db[order_id] = order
        return order

    def get_order_by_id(self, order_id: int) -> Optional[dict]:
        return self._orders_db.get(order_id)

    def update_order_and_payment_status(
        self,
        order_id: int,
        payment_status: str,
        order_status: str,
    ) -> Optional[dict]:
        order = self.get_order_by_id(order_id)
        if order:
            order["payment_status"] = payment_status
            order["order_status"] = order_status
        return order

    def create_refund(self, refund_data: dict) -> dict:
        record = {
            "refund_id": self._refund_id_counter,
            **refund_data,
        }
        self._refunds_db.append(record)
        self._refund_id_counter += 1
        return record

    def list_refunds(self) -> List[Dict]:
        return list(self._refunds_db)

    def clear(self) -> None:
        self._orders_db.clear()
        self._refunds_db.clear()
        self._refund_id_counter = 1


refund_repository = RefundRepository()
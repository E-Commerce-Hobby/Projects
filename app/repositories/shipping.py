# app/repositories/shipping.py
from typing import Dict, List


class ShippingRepository:
    def __init__(self):
        self._quotes_history: List[Dict] = []
        self._id_counter: int = 1

    def save_quote_log(self, quote_data: dict) -> dict:
        record = {
            "id": self._id_counter,
            **quote_data
        }
        self._quotes_history.append(record)
        self._id_counter += 1
        return record

    def get_all_quotes(self) -> List[Dict]:
        return list(self._quotes_history)

    def clear(self) -> None:
        self._quotes_history.clear()
        self._id_counter = 1


shipping_repository = ShippingRepository()
"""In-memory repository for minimum stock thresholds and low-stock alerts (HU-026)."""

from datetime import datetime
from threading import Lock
from typing import Optional

from app.domain.inventory_alert import LowStockAlertResponse


class InventoryAlertRepository:
    """Thread-safe in-memory storage for min stock thresholds and alerts."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._min_stocks: dict[int, int] = {}
        self._alerts: list[LowStockAlertResponse] = []
        self._last_check_at: Optional[datetime] = None

    def set_min_stock(self, product_id: int, min_stock: int) -> dict:
        with self._lock:
            self._min_stocks[product_id] = min_stock
            return {"product_id": product_id, "min_stock": min_stock}

    def get_all_min_stocks(self) -> dict[int, int]:
        with self._lock:
            return dict(self._min_stocks)

    def has_pending_alert(self, product_id: int) -> bool:
        with self._lock:
            return any(
                alert.product_id == product_id and alert.status == "pendiente"
                for alert in self._alerts
            )

    def add_alert(self, alert: LowStockAlertResponse) -> LowStockAlertResponse:
        with self._lock:
            self._alerts.append(alert)
            return alert

    def list_alerts(self, status: Optional[str] = None) -> list[LowStockAlertResponse]:
        with self._lock:
            if status is None:
                return list(self._alerts)
            return [alert for alert in self._alerts if alert.status == status]

    def get_last_check_at(self) -> Optional[datetime]:
        with self._lock:
            return self._last_check_at

    def set_last_check_at(self, timestamp: datetime) -> None:
        with self._lock:
            self._last_check_at = timestamp

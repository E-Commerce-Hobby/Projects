"""Business logic for low-stock alerts (HU-026)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.errors import ReglaNegocioError
from app.domain.inventory_alert import (
    AlertCheckResultResponse,
    INTERVALO_REVISION_MINUTOS,
    LowStockAlertResponse,
    MinStockConfigResponse,
)
from app.repositories.inventory_alert_repository import InventoryAlertRepository
from app.repositories.inventory_repository import InventoryRepository


class InventoryAlertService:
    """Generates and lists low-stock alerts without modifying inventory."""

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        alert_repo: InventoryAlertRepository,
    ) -> None:
        self._inventory_repo = inventory_repo
        self._alert_repo = alert_repo

    def configure_min_stock(
        self, product_id: int, min_stock: int
    ) -> MinStockConfigResponse:
        if self._inventory_repo.get_product_by_id(product_id) is None:
            raise ReglaNegocioError("El producto no existe.", status_code=404)

        if isinstance(min_stock, bool) or not isinstance(min_stock, int) or min_stock < 0:
            raise ReglaNegocioError(
                "El stock mínimo es inválido: debe ser un entero mayor o igual a 0.",
                status_code=400,
            )

        record = self._alert_repo.set_min_stock(product_id, min_stock)
        return MinStockConfigResponse(**record)

    def check_low_stock(
        self, now: Optional[datetime] = None, force: bool = False
    ) -> AlertCheckResultResponse:
        current_time = now or datetime.now(timezone.utc)
        last_check = self._alert_repo.get_last_check_at()

        # CA1: verificar si transcurrieron 60 minutos desde la última revisión
        if (
            not force
            and last_check is not None
            and (current_time - last_check) < timedelta(minutes=INTERVALO_REVISION_MINUTOS)
        ):
            return AlertCheckResultResponse(
                executed=False,
                checked_products=0,
                generated_alerts=[],
                last_check_at=last_check,
            )

        # CA4: solo se evalúan productos con mínimo configurado
        min_stocks = self._alert_repo.get_all_min_stocks()
        generated: list[LowStockAlertResponse] = []

        for product_id, min_stock in min_stocks.items():
            available = self._inventory_repo.get_total_quantity_by_product(product_id)

            # CA2: cantidad disponible estrictamente menor que el mínimo
            if available < min_stock:
                # CA3: no generar alerta nueva si ya tiene una alerta pendiente
                if not self._alert_repo.has_pending_alert(product_id):
                    alert = LowStockAlertResponse(
                        product_id=product_id,
                        current_quantity=available,
                        min_stock=min_stock,
                        created_at=current_time,
                        status="pendiente",
                    )
                    self._alert_repo.add_alert(alert)
                    generated.append(alert)

        self._alert_repo.set_last_check_at(current_time)

        return AlertCheckResultResponse(
            executed=True,
            checked_products=len(min_stocks),
            generated_alerts=generated,
            last_check_at=current_time,
        )

    def list_alerts(self, status: Optional[str] = None) -> list[LowStockAlertResponse]:
        return self._alert_repo.list_alerts(status=status)

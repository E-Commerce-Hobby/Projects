"""In-memory repository for inventory data and movements. CRUD operations only."""

from threading import Lock
from typing import Optional

from app.domain.inventory import InventoryMovementResponse


class InventoryRepository:
    """In-memory thread-safe storage. Replace with a real DB implementation later."""

    def __init__(self) -> None:
        self._lock = Lock()
        # (product_id, location_id) -> quantity
        self._inventory: dict[tuple[int, int], int] = {}
        self._movements: list[InventoryMovementResponse] = []
        # Seed data until the catalog modules are available.
        self._products: dict[int, dict] = {
            1: {"id": 1, "name": "Product 1"},
            2: {"id": 2, "name": "Product 2"},
        }
        self._locations: dict[int, dict] = {
            1: {"id": 1, "name": "Main warehouse"},
            2: {"id": 2, "name": "Store 1"},
        }

    def get_product_by_id(self, product_id: int) -> Optional[dict]:
        return self._products.get(product_id)

    def get_location_by_id(self, location_id: int) -> Optional[dict]:
        return self._locations.get(location_id)

    def get_inventory(self, product_id: int, location_id: int) -> Optional[dict]:
        with self._lock:
            quantity = self._inventory.get((product_id, location_id))
            if quantity is None:
                return None
            return {
                "product_id": product_id,
                "location_id": location_id,
                "quantity": quantity,
            }

    def get_total_quantity_by_product(self, product_id: int) -> int:
        with self._lock:
            return sum(
                qty
                for (prod_id, _), qty in self._inventory.items()
                if prod_id == product_id
            )

    def create_inventory(self, product_id: int, location_id: int, quantity: int) -> dict:
        with self._lock:
            self._inventory[(product_id, location_id)] = quantity
            return {
                "product_id": product_id,
                "location_id": location_id,
                "quantity": quantity,
            }

    def update_inventory(self, product_id: int, location_id: int, quantity: int) -> dict:
        with self._lock:
            self._inventory[(product_id, location_id)] = quantity
            return {
                "product_id": product_id,
                "location_id": location_id,
                "quantity": quantity,
            }

    def record_movement(
        self, movement: InventoryMovementResponse
    ) -> InventoryMovementResponse:
        with self._lock:
            self._movements.append(movement)
            return movement

    def list_movements(
        self, product_id: int, location_id: int
    ) -> list[InventoryMovementResponse]:
        with self._lock:
            return [
                mov
                for mov in self._movements
                if mov.product_id == product_id and mov.location_id == location_id
            ]

"""In-memory repository for inventory data. CRUD operations only."""

from typing import Optional


class InventoryRepository:
    """In-memory storage. Replace with a real DB implementation later."""

    def __init__(self) -> None:
        # (product_id, location_id) -> quantity
        self._inventory: dict[tuple[int, int], int] = {}
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
        quantity = self._inventory.get((product_id, location_id))
        if quantity is None:
            return None
        return {
            "product_id": product_id,
            "location_id": location_id,
            "quantity": quantity,
        }

    def create_inventory(self, product_id: int, location_id: int, quantity: int) -> dict:
        self._inventory[(product_id, location_id)] = quantity
        return {
            "product_id": product_id,
            "location_id": location_id,
            "quantity": quantity,
        }
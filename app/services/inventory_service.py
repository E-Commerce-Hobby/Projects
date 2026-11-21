"""Business logic for the initial inventory registration."""

from app.core.errors import ReglaNegocioError
from app.domain.inventory import InventoryCreate, InventoryResponse
from app.repositories.inventory_repository import InventoryRepository


class InventoryService:
    """Pure business rules. No HTTP or framework concerns."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    def register_initial_inventory(self, data: InventoryCreate) -> InventoryResponse:
        # CA2: product and/or location must exist -> 404
        product_exists = self._repository.get_product_by_id(data.product_id) is not None
        location_exists = self._repository.get_location_by_id(data.location_id) is not None

        if not product_exists and not location_exists:
            raise ReglaNegocioError("El producto y la ubicación no existen", 404)
        if not product_exists:
            raise ReglaNegocioError("El producto no existe", 404)
        if not location_exists:
            raise ReglaNegocioError("La ubicación no existe", 404)

        # CA4: inventory already registered for this pair -> 409
        if self._repository.get_inventory(data.product_id, data.location_id) is not None:
            raise ReglaNegocioError(
                "Ya existe inventario para este producto en la ubicación; "
                "use el ajuste de inventario (HU-025)",
                409,
            )

        # CA1: persist and confirm
        record = self._repository.create_inventory(
            data.product_id, data.location_id, data.quantity
        )
        return InventoryResponse(**record)
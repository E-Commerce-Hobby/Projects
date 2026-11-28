"""Business logic for initial inventory registration (HU-003) and adjustments (HU-025)."""

from app.core.errors import ReglaNegocioError
from app.domain.inventory import (
    InventoryAdjustmentCreate,
    InventoryAdjustmentResponse,
    InventoryCreate,
    InventoryMovementResponse,
    InventoryResponse,
    MOTIVOS_AJUSTE_PERMITIDOS,
)
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
            raise ReglaNegocioError("El producto y la ubicación no existen", status_code=404)
        if not product_exists:
            raise ReglaNegocioError("El producto no existe", status_code=404)
        if not location_exists:
            raise ReglaNegocioError("La ubicación no existe", status_code=404)

        # CA4: inventory already registered for this pair -> 409
        if self._repository.get_inventory(data.product_id, data.location_id) is not None:
            raise ReglaNegocioError(
                "Ya existe inventario para este producto en la ubicación; "
                "use el ajuste de inventario (HU-025)",
                status_code=409,
            )

        # CA1: persist and confirm
        record = self._repository.create_inventory(
            data.product_id, data.location_id, data.quantity
        )
        return InventoryResponse(**record)

    def adjust_inventory(
        self, data: InventoryAdjustmentCreate
    ) -> InventoryAdjustmentResponse:
        # CA2: validar motivo obligatorio y permitido -> 400
        motivo_limpio = (data.reason or "").strip().lower()
        if not motivo_limpio or motivo_limpio not in MOTIVOS_AJUSTE_PERMITIDOS:
            raise ReglaNegocioError(
                "El motivo es obligatorio y debe ser uno de: "
                "entrada, salida, conteo físico o pérdida.",
                status_code=400,
            )

        # Validar cantidad entera >= 0 -> 400
        if (
            isinstance(data.quantity, bool)
            or not isinstance(data.quantity, int)
            or data.quantity < 0
        ):
            raise ReglaNegocioError(
                "La cantidad es inválida: debe ser un número entero mayor o igual a 0.",
                status_code=400,
            )

        # Verificar existencia de producto, ubicación e inventario -> 404
        product_exists = self._repository.get_product_by_id(data.product_id) is not None
        location_exists = self._repository.get_location_by_id(data.location_id) is not None

        if not product_exists and not location_exists:
            raise ReglaNegocioError(
                "El producto y la ubicación no existen.", status_code=404
            )
        if not product_exists:
            raise ReglaNegocioError("El producto no existe.", status_code=404)
        if not location_exists:
            raise ReglaNegocioError("La ubicación no existe.", status_code=404)

        current = self._repository.get_inventory(data.product_id, data.location_id)
        if current is None:
            raise ReglaNegocioError(
                "No existe inventario registrado para este producto en la ubicación.",
                status_code=404,
            )

        previous_quantity = current["quantity"]

        # CA1: calcular nueva cantidad según el motivo
        if motivo_limpio == "entrada":
            new_quantity = previous_quantity + data.quantity
        elif motivo_limpio in ("salida", "pérdida"):
            new_quantity = previous_quantity - data.quantity
        else:  # conteo físico
            new_quantity = data.quantity

        # CA3 (RN-01): ningún ajuste puede dejar saldo negativo -> 409
        if new_quantity < 0:
            raise ReglaNegocioError(
                f"Ajuste rechazado (RN-01): el inventario no puede quedar negativo. "
                f"Cantidad actual: {previous_quantity}.",
                status_code=409,
            )

        # Actualizar inventario y registrar movimiento (HU-006)
        self._repository.update_inventory(data.product_id, data.location_id, new_quantity)
        movement = self._repository.record_movement(
            InventoryMovementResponse(
                product_id=data.product_id,
                location_id=data.location_id,
                reason=motivo_limpio,
                quantity=data.quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
            )
        )

        return InventoryAdjustmentResponse(
            product_id=data.product_id,
            location_id=data.location_id,
            quantity=new_quantity,
            movement=movement,
        )

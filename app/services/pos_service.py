"""Business logic for the POS module."""
"""Business logic for the POS module."""
from collections import defaultdict
from datetime import datetime, timezone

from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.pos import (
    AppliedDiscountInfo,
    ApplyDiscountRequest,
    ProductInfo,
    ProductSearchResponse,
    SaleCreateRequest,
    SaleDiscountResponse,
    SaleItemRequest,
    SaleItemResponse,
    SaleLineRecord,
    SaleRecord,
    SaleResponse,
)
from app.repositories.pos_repository import PosRepository


class PosService:
    def __init__(self, repository: PosRepository) -> None:
        self._repository = repository

    # FUN-4.2.1 -------------------------------------------------------------
    def search_product_by_barcode(self, barcode: str) -> ProductSearchResponse:
        product = self._repository.get_product_by_barcode(barcode)
        if product is None:
            raise RecursoNoEncontradoError("El producto no existe.")

        available = self._repository.get_available_quantity(product.code)
        return ProductSearchResponse(
            product=ProductInfo(
                code=product.code,
                category=product.category,
                features=product.features,
            ),
            price=product.price,
            available_quantity=available,
        )

    # FUN-4.2.2 -------------------------------------------------------------
    def register_sale(self, payload: SaleCreateRequest) -> SaleResponse:
        register = self._repository.get_cash_register(payload.cash_register_id)
        if register is None or not register.is_open:
            raise ReglaNegocioError("No hay una caja abierta para registrar la venta.")

        lines: list[SaleLineRecord] = []
        for product_code, quantity in self._group_quantities(payload.products).items():
            product = self._repository.get_product_by_barcode(product_code)
            if product is None:
                raise RecursoNoEncontradoError(f"El producto {product_code} no existe.")

            available = self._repository.get_available_quantity(product_code)
            if quantity > available:  # RN-01
                raise ReglaNegocioError(
                    f"Cantidad insuficiente para el producto {product_code}: "
                    f"solicitada {quantity}, disponible {available}."
                )

            lines.append(
                SaleLineRecord(
                    product_code=product_code,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=round(product.price * quantity, 2),
                )
            )

        saved = self._repository.create_sale(
            SaleRecord(
                cash_register_id=register.id,
                cashier_id=register.cashier_id,
                lines=lines,
                total=round(sum(line.subtotal for line in lines), 2),
                created_at=datetime.now(timezone.utc),
            )
        )

        return SaleResponse(
            id=saved.id,
            products=[SaleItemResponse(**line.model_dump()) for line in saved.lines],
            total=saved.total,
            mensaje="Venta registrada correctamente.",
        )

    # FUN-4.2.3 (HU-031) ----------------------------------------------------
    def apply_discount(self, sale_id: int, payload: ApplyDiscountRequest) -> SaleDiscountResponse:
        sale = self._repository.get_sale(sale_id)
        if sale is None:
            raise RecursoNoEncontradoError(f"La venta {sale_id} no existe.")

        discount = self._repository.get_discount(payload.discount_id)
        if discount is None:
            raise RecursoNoEncontradoError(
                f"El descuento '{payload.discount_id}' no existe."
            )

        now = datetime.now(timezone.utc)
        if not (discount.valid_from <= now <= discount.valid_until):
            raise ReglaNegocioError(
                f"El descuento '{discount.id}' está fuera de vigencia.",
                status_code=409,
            )

        if discount.id in sale.applied_discount_ids:
            raise ReglaNegocioError(
                f"El descuento '{discount.id}' ya fue aplicado a la venta {sale_id}.",
                status_code=409,
            )

        previous_total = sale.total
        if discount.discount_type == "percentage":
            raw_discount = round(previous_total * (discount.value / 100.0), 2)
        else:
            raw_discount = round(discount.value, 2)

        new_total = round(max(0.0, previous_total - raw_discount), 2)
        amount_discounted = round(previous_total - new_total, 2)

        updated_sale = sale.model_copy(
            update={
                "total": new_total,
                "applied_discount_ids": [*sale.applied_discount_ids, discount.id],
            }
        )
        self._repository.update_sale(updated_sale)

        return SaleDiscountResponse(
            id=updated_sale.id,
            products=[SaleItemResponse(**line.model_dump()) for line in updated_sale.lines],
            applied_discount=AppliedDiscountInfo(
                id=discount.id,
                discount_type=discount.discount_type,
                value=discount.value,
                amount_discounted=amount_discounted,
            ),
            applied_discount_ids=updated_sale.applied_discount_ids,
            previous_total=previous_total,
            total=updated_sale.total,
            mensaje="Descuento aplicado correctamente a la venta.",
        )

    @staticmethod
    def _group_quantities(items: list[SaleItemRequest]) -> dict[str, int]:
        """Sum quantities of repeated products so stock is validated per product."""
        grouped: dict[str, int] = defaultdict(int)
        for item in items:
            grouped[item.product_code] += item.quantity
        return dict(grouped)
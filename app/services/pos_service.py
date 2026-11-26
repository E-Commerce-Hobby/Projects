"""Business logic for the POS module."""
from collections import defaultdict
from datetime import datetime, timezone

from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.pos import (
    AppliedDiscountInfo,
    ApplyDiscountRequest,
    CashRegisterClosingRecord,
    CashRegisterClosingResponse,
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
                payment_method=payload.payment_method,
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

    # FUN-4.2.4 (HU-032) ----------------------------------------------------
    def close_cash_register(self, cash_register_id: int) -> CashRegisterClosingResponse:
        register = self._repository.get_cash_register(cash_register_id)
        if register is None:
            raise RecursoNoEncontradoError(f"La caja {cash_register_id} no existe.")

        # CA4: rechazar si no hay caja abierta
        if not register.is_open:
            raise ReglaNegocioError(
                "No hay una caja abierta para realizar el cierre.",
                status_code=409,
            )

        closed_at = datetime.now(timezone.utc)

        # CA1: consultar todas las ventas desde la apertura hasta el cierre
        turn_sales = self._repository.list_sales_by_register(
            cash_register_id=register.id,
            since=register.opened_at,
            until=closed_at,
        )

        # CA2: calcular totales por medio de pago y total general
        totals: dict[str, float] = defaultdict(float)
        for sale in turn_sales:
            totals[sale.payment_method] = round(
                totals[sale.payment_method] + sale.total, 2
            )

        totals_by_payment_method = dict(totals)
        general_total = round(sum(totals_by_payment_method.values()), 2)

        # CA3: registrar el cierre y marcar la caja como cerrada
        saved_closing = self._repository.create_closing(
            CashRegisterClosingRecord(
                cash_register_id=register.id,
                cashier_id=register.cashier_id,
                opened_at=register.opened_at,
                closed_at=closed_at,
                totals_by_payment_method=totals_by_payment_method,
                general_total=general_total,
                sales_count=len(turn_sales),
            )
        )
        self._repository.close_cash_register(register.id)

        return CashRegisterClosingResponse(
            id=saved_closing.id,
            cash_register_id=saved_closing.cash_register_id,
            cashier_id=saved_closing.cashier_id,
            opened_at=saved_closing.opened_at,
            closed_at=saved_closing.closed_at,
            totals_by_payment_method=saved_closing.totals_by_payment_method,
            general_total=saved_closing.general_total,
            sales_count=saved_closing.sales_count,
            status="cerrada",
            mensaje="Cierre de caja registrado correctamente.",
        )

    @staticmethod
    def _group_quantities(items: list[SaleItemRequest]) -> dict[str, int]:
        """Sum quantities of repeated products so stock is validated per product."""
        grouped: dict[str, int] = defaultdict(int)
        for item in items:
            grouped[item.product_code] += item.quantity
        return dict(grouped)

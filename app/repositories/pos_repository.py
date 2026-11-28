"""In-memory repository for the POS module. CRUD methods only, no business rules."""
from datetime import datetime, timezone
from threading import Lock

from app.domain.pos import (
    CashRegisterClosingRecord,
    CashRegisterRecord,
    DiscountRecord,
    ProductRecord,
    SaleRecord,
)


class PosRepository:
    def __init__(self) -> None:
        self._products: dict[str, ProductRecord] = {
            "7701234567890": ProductRecord(
                code="7701234567890",
                category="Bebidas",
                features={"marca": "Aqua", "presentacion": "600 ml"},
                price=2500.0,
            ),
            "ABC123": ProductRecord(
                code="ABC123",
                category="Snacks",
                features={"marca": "Crunch", "peso": "100 g"},
                price=4200.0,
            ),
            "SINSTOCK1": ProductRecord(
                code="SINSTOCK1",
                category="Aseo",
                features={"marca": "Limpio", "tipo": "Jabón"},
                price=8900.0,
            ),
        }
        self._pos_stock: dict[str, int] = {"7701234567890": 15, "ABC123": 3}
        self._cash_registers: dict[int, CashRegisterRecord] = {
            1: CashRegisterRecord(id=1, cashier_id=10, is_open=True),
            2: CashRegisterRecord(id=2, cashier_id=11, is_open=False),
        }
        self._sales: dict[int, SaleRecord] = {}
        self._closings: dict[int, CashRegisterClosingRecord] = {}
        self._discounts: dict[str, DiscountRecord] = {
            "DESC10": DiscountRecord(
                id="DESC10",
                discount_type="percentage",
                value=10.0,
                valid_from=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                valid_until=datetime(2027, 12, 31, 23, 59, tzinfo=timezone.utc),
            ),
            "DESC2000": DiscountRecord(
                id="DESC2000",
                discount_type="fixed",
                value=2000.0,
                valid_from=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                valid_until=datetime(2027, 12, 31, 23, 59, tzinfo=timezone.utc),
            ),
            "DESC50000": DiscountRecord(
                id="DESC50000",
                discount_type="fixed",
                value=50000.0,
                valid_from=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                valid_until=datetime(2027, 12, 31, 23, 59, tzinfo=timezone.utc),
            ),
            "DESCVENCIDO": DiscountRecord(
                id="DESCVENCIDO",
                discount_type="percentage",
                value=15.0,
                valid_from=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
                valid_until=datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc),
            ),
        }
        self._next_sale_id = 1
        self._next_closing_id = 1
        self._lock = Lock()

    def get_product_by_barcode(self, barcode: str) -> ProductRecord | None:
        return self._products.get(barcode)

    def get_available_quantity(self, product_code: str) -> int:
        """Return the POS stock for a product (0 when there is no inventory)."""
        return self._pos_stock.get(product_code, 0)

    def get_cash_register(self, cash_register_id: int) -> CashRegisterRecord | None:
        with self._lock:
            return self._cash_registers.get(cash_register_id)

    def close_cash_register(self, cash_register_id: int) -> CashRegisterRecord:
        with self._lock:
            register = self._cash_registers[cash_register_id]
            updated = register.model_copy(update={"is_open": False})
            self._cash_registers[cash_register_id] = updated
            return updated

    def create_sale(self, sale: SaleRecord) -> SaleRecord:
        with self._lock:
            saved = sale.model_copy(update={"id": self._next_sale_id})
            self._sales[saved.id] = saved
            self._next_sale_id += 1
        return saved

    def get_sale(self, sale_id: int) -> SaleRecord | None:
        return self._sales.get(sale_id)

    def list_sales_by_register(
        self, cash_register_id: int, since: datetime, until: datetime
    ) -> list[SaleRecord]:
        with self._lock:
            return [
                sale
                for sale in self._sales.values()
                if sale.cash_register_id == cash_register_id
                and since <= sale.created_at <= until
            ]

    def get_discount(self, discount_id: str) -> DiscountRecord | None:
        return self._discounts.get(discount_id)

    def update_sale(self, sale: SaleRecord) -> SaleRecord:
        with self._lock:
            self._sales[sale.id] = sale
        return sale

    def create_closing(
        self, closing: CashRegisterClosingRecord
    ) -> CashRegisterClosingRecord:
        with self._lock:
            saved = closing.model_copy(update={"id": self._next_closing_id})
            self._closings[saved.id] = saved
            self._next_closing_id += 1
        return saved

    def list_closings(
        self, cash_register_id: int | None = None
    ) -> list[CashRegisterClosingRecord]:
        with self._lock:
            if cash_register_id is None:
                return list(self._closings.values())
            return [
                closing
                for closing in self._closings.values()
                if closing.cash_register_id == cash_register_id
            ]

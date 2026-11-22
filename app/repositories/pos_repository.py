"""In-memory repository for the POS module. CRUD methods only, no business rules."""
from threading import Lock

from app.domain.pos import CashRegisterRecord, ProductRecord, SaleRecord


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
        self._next_sale_id = 1
        self._lock = Lock()

    def get_product_by_barcode(self, barcode: str) -> ProductRecord | None:
        return self._products.get(barcode)

    def get_available_quantity(self, product_code: str) -> int:
        """Return the POS stock for a product (0 when there is no inventory)."""
        return self._pos_stock.get(product_code, 0)

    def get_cash_register(self, cash_register_id: int) -> CashRegisterRecord | None:
        return self._cash_registers.get(cash_register_id)

    def create_sale(self, sale: SaleRecord) -> SaleRecord:
        with self._lock:
            saved = sale.model_copy(update={"id": self._next_sale_id})
            self._sales[saved.id] = saved
            self._next_sale_id += 1
        return saved
 
    def get_sale(self, sale_id: int) -> SaleRecord | None:
        return self._sales.get(sale_id)
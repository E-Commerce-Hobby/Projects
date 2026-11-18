from app.domain.product import ProductResponse


class InMemoryProductRepository:
    """In-memory product storage. CRUD methods only."""

    def __init__(self, seed: list[ProductResponse] | None = None) -> None:
        self._products: dict[str, ProductResponse] = {}
        for product in seed if seed is not None else self._default_seed():
            self._products[product.code] = product

    def get_all(self) -> list[ProductResponse]:
        return list(self._products.values())

    def get_by_code(self, code: str) -> ProductResponse | None:
        return self._products.get(code)

    def create(self, product: ProductResponse) -> ProductResponse:
        self._products[product.code] = product
        return product

    def update(self, code: str, product: ProductResponse) -> ProductResponse | None:
        if code not in self._products:
            return None
        self._products[code] = product
        return product

    def delete(self, code: str) -> bool:
        return self._products.pop(code, None) is not None

    @staticmethod
    def _default_seed() -> list[ProductResponse]:
        return [
            ProductResponse(code="P-003", name="Smartphone X", category="Electronics",
                            price=899.9, features=["5G", "NFC", "WiFi"], status="active"),
            ProductResponse(code="P-001", name="Laptop Pro", category="Electronics",
                            price=1500.0, features=["WiFi", "Backlit keyboard"], status="active"),
            ProductResponse(code="P-002", name="Wireless Mouse", category="Accessories",
                            price=25.5, features=["Bluetooth"], status="active"),
            ProductResponse(code="P-004", name="Old Tablet", category="Electronics",
                            price=200.0, features=["WiFi"], status="inactive"),
        ]
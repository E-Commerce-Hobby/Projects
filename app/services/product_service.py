from app.core.errors import ReglaNegocioError
from app.domain.product import ProductFilterParams, ProductResponse
from app.repositories.product_repository import InMemoryProductRepository


class ProductService:
    """Business logic for catalog queries."""

    def __init__(self, repository: InMemoryProductRepository) -> None:
        self._repository = repository

    def search_products(self, filters: ProductFilterParams) -> list[ProductResponse]:
        # Defensive guard: the service must not depend on the caller's validation.
        if (
            filters.min_price is not None
            and filters.max_price is not None
            and filters.min_price > filters.max_price
        ):
            raise ReglaNegocioError(
                "El filtro 'min_price' no puede ser mayor que 'max_price'."
            )

        matches = [
            product
            for product in self._repository.get_all()
            if self._matches(product, filters)
        ]
        return sorted(matches, key=lambda product: product.code)

    @staticmethod
    def _matches(product: ProductResponse, filters: ProductFilterParams) -> bool:
        if product.status != "active":
            return False

        if (
            filters.category is not None
            and product.category.casefold() != filters.category.casefold()
        ):
            return False

        if filters.min_price is not None and product.price < filters.min_price:
            return False

        if filters.max_price is not None and product.price > filters.max_price:
            return False

        if filters.features:
            product_features = {feature.casefold() for feature in product.features}
            requested = {feature.casefold() for feature in filters.features}
            if not requested.issubset(product_features):
                return False

        return True
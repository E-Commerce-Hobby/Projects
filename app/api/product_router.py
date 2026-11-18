from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.domain.product import ProductFilterParams, ProductResponse
from app.repositories.product_repository import InMemoryProductRepository
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Catalog"])

_repository = InMemoryProductRepository()


def get_product_service() -> ProductService:
    return ProductService(_repository)


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="Consultar el catálogo con filtros",
    description=(
        "Devuelve los productos **activos** que cumplen todos los filtros enviados "
        "(categoría, rango de precio y características), ordenados por código "
        "ascendente. Si ninguno coincide, devuelve una lista vacía con HTTP 200."
    ),
    responses={
        400: {
            "description": "Filtro inválido (precio negativo, rango incoherente o formato incorrecto).",
            "content": {
                "application/json": {
                    "example": {"detail": "El filtro 'min_price' no puede ser mayor que 'max_price'."}
                }
            },
        }
    },
)
def search_products(
    filters: Annotated[ProductFilterParams, Query()],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> list[ProductResponse]:
    return service.search_products(filters)
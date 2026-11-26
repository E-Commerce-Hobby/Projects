from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError

from app.core.errors import ReglaNegocioError
from app.domain.product import ProductFilterParams, ProductResponse
from app.repositories.product_repository import InMemoryProductRepository
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Catalog"])

_repository = InMemoryProductRepository()


def get_product_service() -> ProductService:
    return ProductService(_repository)


def get_product_filters(
    category: Annotated[str | None, Query(description="Categoría del producto")] = None,
    min_price: Annotated[float | None, Query(description="Precio mínimo")] = None,
    max_price: Annotated[float | None, Query(description="Precio máximo")] = None,
    features: Annotated[
        list[str] | None, Query(description="Características (repetible)")
    ] = None,
) -> ProductFilterParams:
    try:
        return ProductFilterParams(
            category=category,
            min_price=min_price,
            max_price=max_price,
            features=features,
        )
    except ValidationError as exc:
        primer_error = exc.errors()[0].get("msg", "Filtros de búsqueda inválidos.")
        mensaje = primer_error.replace("Value error, ", "")
        raise ReglaNegocioError(message=mensaje, status_code=400)


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
    filters: Annotated[ProductFilterParams, Depends(get_product_filters)],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> list[ProductResponse]:
    return service.search_products(filters)
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_TEXT_PATTERN = re.compile(r"^[\w\s\-\.]+$", re.UNICODE)


def _validate_text(value: str, field_label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"El filtro '{field_label}' no puede estar vacío.")
    if len(cleaned) > 50:
        raise ValueError(f"El filtro '{field_label}' no puede superar 50 caracteres.")
    if not _TEXT_PATTERN.match(cleaned):
        raise ValueError(f"El filtro '{field_label}' contiene caracteres no permitidos.")
    return cleaned


class ProductFilterParams(BaseModel):
    """Input schema: query filters for the catalog (all optional)."""

    model_config = ConfigDict(extra="forbid")

    category: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    features: list[str] | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        return None if value is None else _validate_text(value, "category")

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [_validate_text(item, "features") for item in value]

    @field_validator("min_price")
    @classmethod
    def validate_min_price(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("El filtro 'min_price' no puede ser negativo.")
        return value

    @field_validator("max_price")
    @classmethod
    def validate_max_price(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("El filtro 'max_price' no puede ser negativo.")
        return value

    @model_validator(mode="after")
    def validate_price_range(self) -> "ProductFilterParams":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError(
                "El filtro 'min_price' no puede ser mayor que 'max_price'."
            )
        return self


class ProductResponse(BaseModel):
    """Output schema: a catalog product."""

    code: str
    name: str
    category: str
    price: float
    features: list[str] = Field(default_factory=list)
    status: Literal["active", "inactive"]
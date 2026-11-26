# app/domain/shipping.py
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ShippingDimensions(BaseModel):
    length_cm: float = Field(..., description="Largo del paquete en cm (> 0)", examples=[30.0])
    width_cm: float = Field(..., description="Ancho del paquete en cm (> 0)", examples=[20.0])
    height_cm: float = Field(..., description="Alto del paquete en cm (> 0)", examples=[15.0])


class ShippingQuoteRequest(BaseModel):
    weight_kg: float = Field(
        ...,
        description="Peso del pedido en kilogramos (debe ser mayor que 0)",
        examples=[2.5]
    )
    dimensions: ShippingDimensions = Field(
        ...,
        description="Dimensiones del paquete en centímetros (largo, ancho y alto > 0)"
    )
    destination_municipality: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Municipio de destino del envío",
        examples=["Bucaramanga"]
    )

    @model_validator(mode="after")
    def validate_positive_measurements(self) -> "ShippingQuoteRequest":
        invalid_fields = []
        if self.weight_kg <= 0:
            invalid_fields.append("weight_kg (debe ser > 0)")
        if self.dimensions.length_cm <= 0:
            invalid_fields.append("length_cm (debe ser > 0)")
        if self.dimensions.width_cm <= 0:
            invalid_fields.append("width_cm (debe ser > 0)")
        if self.dimensions.height_cm <= 0:
            invalid_fields.append("height_cm (debe ser > 0)")

        if invalid_fields:
            raise ValueError(f"Campos numéricos inválidos: {', '.join(invalid_fields)}.")
        return self

    @field_validator("destination_municipality")
    @classmethod
    def validate_destination_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El destino (destination_municipality) no puede estar vacío.")
        return cleaned


class ShippingQuoteResponseData(BaseModel):
    amount: int = Field(..., description="Valor entero del envío en pesos colombianos", examples=[14000])
    currency: Literal["COP"] = Field(default="COP", description="Moneda de la tarifa", examples=["COP"])
    carrier: str = Field(..., description="Nombre de la transportadora externa", examples=["Servientrega"])
    destination_municipality: str = Field(..., description="Municipio destino consultado", examples=["Bucaramanga"])


class ShippingQuoteStandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la consulta de tarifa fue exitosa")
    data: Optional[ShippingQuoteResponseData] = Field(
        None,
        description="Datos de la tarifa cotizada o null si no está disponible / hubo error"
    )
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje descriptivo en español de máximo 200 caracteres"
    )
# app/services/shipping.py
from fastapi import status
from app.core.carrier_gateway import (
    CarrierGatewayClient,
    CarrierTimeoutError,
    CarrierUnavailableError,
    carrier_gateway,
)
from app.core.errors import ReglaNegocioError
from app.domain.shipping import ShippingQuoteRequest, ShippingQuoteResponseData
from app.repositories.shipping import ShippingRepository


class ShippingService:
    def __init__(
        self,
        repository: ShippingRepository,
        gateway: CarrierGatewayClient = carrier_gateway,
    ):
        self.repository = repository
        self.gateway = gateway

    def calculate_shipping_rate(self, payload: ShippingQuoteRequest) -> ShippingQuoteResponseData:
        # Doble verificación de reglas de negocio (CA4)
        invalid_fields = []
        if payload.weight_kg <= 0:
            invalid_fields.append("weight_kg")
        if payload.dimensions.length_cm <= 0:
            invalid_fields.append("length_cm")
        if payload.dimensions.width_cm <= 0:
            invalid_fields.append("width_cm")
        if payload.dimensions.height_cm <= 0:
            invalid_fields.append("height_cm")
        if not payload.destination_municipality.strip():
            invalid_fields.append("destination_municipality")

        if invalid_fields:
            raise ReglaNegocioError(
                f"Datos inválidos en los campos: {', '.join(invalid_fields)}.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # CA1 y CA3: Consultar transportadora externa con timeout máximo de 10 segundos
        try:
            quote = self.gateway.get_shipping_quote(
                weight_kg=payload.weight_kg,
                length_cm=payload.dimensions.length_cm,
                width_cm=payload.dimensions.width_cm,
                height_cm=payload.dimensions.height_cm,
                destination_municipality=payload.destination_municipality,
                timeout_seconds=10.0,
            )
        except (CarrierTimeoutError, CarrierUnavailableError):
            # CA3 y DoD: Informa que la tarifa no está disponible, sin retornar ningún valor (HTTP 503)
            raise ReglaNegocioError(
                "La tarifa de envío no está disponible en este momento. Intente más tarde.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # CA2: Asegurar valor entero en COP junto con moneda y nombre de la transportadora
        amount_int = int(round(quote.amount_cop))

        self.repository.save_quote_log({
            "weight_kg": payload.weight_kg,
            "dimensions": payload.dimensions.model_dump(),
            "destination_municipality": payload.destination_municipality,
            "amount": amount_int,
            "currency": "COP",
            "carrier": quote.carrier_name,
        })

        return ShippingQuoteResponseData(
            amount=amount_int,
            currency="COP",
            carrier=quote.carrier_name,
            destination_municipality=payload.destination_municipality,
        )
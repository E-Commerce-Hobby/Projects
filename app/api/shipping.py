# app/api/shipping.py
from fastapi import APIRouter, status
from app.core.carrier_gateway import carrier_gateway
from app.domain.shipping import (
    ShippingQuoteRequest,
    ShippingQuoteStandardResponse,
)
from app.repositories.shipping import shipping_repository
from app.services.shipping import ShippingService

router = APIRouter(
    prefix="/api/v1/shipping",
    tags=["Logistics - Shipping (MOD-07)"]
)

shipping_service = ShippingService(
    repository=shipping_repository,
    gateway=carrier_gateway,
)


@router.post(
    "/quote",
    response_model=ShippingQuoteStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar tarifa de envío de un pedido (HU-019 / FUN-7.1.1)",
    description=(
        "Consulta el costo de envío con la transportadora externa (API-EXT-03) a partir del peso (kg > 0), "
        "dimensiones en cm (largo, ancho y alto > 0) y municipio de destino. Retorna el valor entero en COP, "
        "la moneda y la transportadora, con un tiempo máximo de espera de 10 segundos."
    ),
    responses={
        200: {
            "description": "CA1, CA2 - Tarifa de envío calculada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "amount": 14000,
                            "currency": "COP",
                            "carrier": "Servientrega",
                            "destination_municipality": "Bucaramanga"
                        },
                        "message": "Tarifa de envío consultada exitosamente."
                    }
                }
            }
        },
        400: {
            "description": "CA4 - Datos faltantes, formato inválido o valores menores o iguales a 0",
            "content": {
                "application/json": {
                    "examples": {
                        "ValoresNoPositivos": {
                            "summary": "CA4 - Peso o dimensiones <= 0",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Campos numéricos inválidos: weight_kg (debe ser > 0), height_cm (debe ser > 0)."
                            }
                        },
                        "CamposFaltantes": {
                            "summary": "CA4 - Campos obligatorios faltantes",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "Faltan campos obligatorios: weight_kg, dimensions, destination_municipality."
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "CA3 - Transportadora no responde en 10s o devuelve error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "La tarifa de envío no está disponible en este momento. Intente más tarde."
                    }
                }
            }
        }
    }
)
def quote_shipping_rate_endpoint(payload: ShippingQuoteRequest):
    quote_data = shipping_service.calculate_shipping_rate(payload)
    return ShippingQuoteStandardResponse(
        success=True,
        data=quote_data,
        message="Tarifa de envío consultada exitosamente."
    )
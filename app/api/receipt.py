"""POS endpoint: receipt generation for a counter sale."""
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.pos import get_pos_repository
from app.domain.pos import ErrorResponse
from app.domain.receipt import ReceiptResponse
from app.repositories.pos_repository import PosRepository
from app.repositories.receipt_repository import BillingClient, ReceiptRepository
from app.services.receipt_service import ReceiptService

router = APIRouter(prefix="/pos", tags=["Punto de Venta (POS)"])


@lru_cache
def get_receipt_repository() -> ReceiptRepository:
    return ReceiptRepository()


@lru_cache
def get_billing_client() -> BillingClient:
    return BillingClient()


def get_receipt_service(
    pos_repository: Annotated[PosRepository, Depends(get_pos_repository)],
    receipt_repository: Annotated[ReceiptRepository, Depends(get_receipt_repository)],
    billing_client: Annotated[BillingClient, Depends(get_billing_client)],
) -> ReceiptService:
    return ReceiptService(pos_repository, receipt_repository, billing_client)


@router.post(
    "/sales/{sale_id}/receipt",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar comprobante de una venta de mostrador",
    description=(
        "Solicita el documento fiscal a Facturación con el ID de la venta, almacena la "
        "referencia y retorna número y referencia del comprobante. Si Facturación no "
        "responde en 10 segundos o devuelve error, la venta sigue registrada sin "
        "comprobante y la solicitud se puede repetir."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "El ID de la venta tiene formato inválido.",
            "content": {"application/json": {"example": {
                "mensaje": "El campo 'sale_id' tiene un formato inválido."
            }}},
        },
        404: {
            "model": ErrorResponse,
            "description": "La venta no existe.",
            "content": {"application/json": {"example": {"mensaje": "La venta no existe."}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "La venta ya tiene un comprobante generado.",
            "content": {"application/json": {"example": {
                "mensaje": "La venta ya tiene un comprobante generado."
            }}},
        },
        503: {
            "model": ErrorResponse,
            "description": "Facturación no responde en 10 segundos o devuelve error.",
            "content": {"application/json": {"example": {
                "mensaje": "No se pudo generar el comprobante porque Facturación no está disponible. La venta sigue registrada; intente nuevamente."
            }}},
        },
    },
)
def generate_receipt(
    sale_id: Annotated[
        int, Path(gt=0, description="ID de la venta de mostrador confirmada.", examples=[1])
    ],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> ReceiptResponse:
    return service.generate_receipt(sale_id)
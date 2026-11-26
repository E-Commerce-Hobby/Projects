"""Business logic for the POS receipt module."""
from datetime import datetime, timezone

from app.core.errors import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
    ServicioNoDisponibleError,
)
from app.domain.receipt import ReceiptRecord, ReceiptResponse
from app.repositories.pos_repository import PosRepository
from app.repositories.receipt_repository import (
    BILLING_TIMEOUT_SECONDS,
    BillingClient,
    BillingServiceError,
    ReceiptRepository,
)


class ReceiptService:
    def __init__(
        self,
        pos_repository: PosRepository,
        receipt_repository: ReceiptRepository,
        billing_client: BillingClient,
    ) -> None:
        self._pos_repository = pos_repository
        self._receipt_repository = receipt_repository
        self._billing_client = billing_client

    def generate_receipt(self, sale_id: int) -> ReceiptResponse:
        sale = self._pos_repository.get_sale(sale_id)
        if sale is None:
            raise RecursoNoEncontradoError("La venta no existe.")

        if self._receipt_repository.get_by_sale_id(sale_id) is not None:
            raise ReglaNegocioError("La venta ya tiene un comprobante generado.")

        # CA1: request the fiscal document with the sale ID (10 s timeout)
        try:
            billing_data = self._billing_client.request_receipt(
                sale_id, BILLING_TIMEOUT_SECONDS
            )
        except BillingServiceError as exc:
            # CA4: nothing is stored, the sale stays registered and can be retried
            raise ServicioNoDisponibleError(
                "No se pudo generar el comprobante porque Facturación no está "
                "disponible. La venta sigue registrada; intente nuevamente."
            ) from exc

        # CA2: store the reference associated with the sale ID
        saved = self._receipt_repository.create(
            ReceiptRecord(
                sale_id=sale_id,
                receipt_number=billing_data.receipt_number,
                reference=billing_data.reference,
                created_at=datetime.now(timezone.utc),
            )
        )

        # CA3: return number and reference for the customer
        return ReceiptResponse(
            sale_id=saved.sale_id,
            receipt_number=saved.receipt_number,
            reference=saved.reference,
            mensaje="Comprobante generado correctamente.",
        )
# app/services/invoice.py
from datetime import datetime, timezone
from fastapi import status
from app.core.errors import ReglaNegocioError
from app.core.invoice_provider_gateway import (
    InvoiceProviderGatewayClient,
    InvoiceProviderTimeoutError,
    InvoiceProviderUnavailableError,
    invoice_provider_gateway,
)
from app.domain.invoice import InvoiceGenerateRequest, InvoiceResponseData
from app.repositories.invoice import InvoiceRepository


class InvoiceService:
    def __init__(
        self,
        repository: InvoiceRepository,
        provider_gateway: InvoiceProviderGatewayClient = invoice_provider_gateway,
    ):
        self.repository = repository
        self.provider_gateway = provider_gateway

    def generate_invoice(self, payload: InvoiceGenerateRequest) -> InvoiceResponseData:
        """
        FUN-5.2.1: Generación de la factura (CA1, CA2, CA3, CA4).
        """
        # CA4: Verificar que la venta exista (HTTP 404)
        sale = self.repository.get_sale_by_id(payload.sale_id)
        if not sale:
            raise ReglaNegocioError(
                f"La venta con ID {payload.sale_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA4: Verificar que la venta esté en estado 'confirmada' (HTTP 409)
        if sale["status"] != "confirmada":
            raise ReglaNegocioError(
                f"La venta con ID {payload.sale_id} no está confirmada (estado actual: {sale['status']}).",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA3: Verificar que la venta no tenga ya una factura asociada (HTTP 409)
        existing_invoice = self.repository.get_invoice_by_sale_id(payload.sale_id)
        if existing_invoice:
            raise ReglaNegocioError(
                f"La venta con ID {payload.sale_id} ya tiene la factura #{existing_invoice['invoice_id']} registrada.",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA1: Reunir emisor, adquiriente, líneas, impuestos y total
        subtotal = 0.0
        total_tax = 0.0
        for item in payload.items:
            line_subtotal = round(item.quantity * item.unit_price, 2)
            line_tax = round(line_subtotal * item.tax_rate, 2)
            subtotal += line_subtotal
            total_tax += line_tax

        subtotal = round(subtotal, 2)
        total_tax = round(total_tax, 2)
        total_amount = round(subtotal + total_tax, 2)

        now = datetime.now(timezone.utc)

        # CA2: Registrar la factura con estado 'generado', ID de factura y ID de venta asociada
        invoice_record = self.repository.create_invoice({
            "sale_id": payload.sale_id,
            "origin": payload.origin,
            "status": "generado",
            "pending_resend": False,
            "issuer": payload.issuer.model_dump(),
            "acquirer": payload.acquirer.model_dump(),
            "items": [item.model_dump() for item in payload.items],
            "provider_extra_data": payload.provider_extra_data or {},
            "subtotal": subtotal,
            "total_tax": total_tax,
            "total_amount": total_amount,
            "rejection_code": None,
            "rejection_reason": None,
            "created_at": now,
        })

        return InvoiceResponseData(**invoice_record)

    def send_invoice_to_provider(self, invoice_id: int) -> tuple[InvoiceResponseData, str]:
        """
        FUN-5.2.2: Envío al proveedor autorizado (CA5, CA6, CA7, CA8).
        Retorna (InvoiceResponseData, mensaje_en_espanol).
        """
        # Verificar que la factura exista (HTTP 404)
        invoice = self.repository.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ReglaNegocioError(
                f"La factura con ID {invoice_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Verificar que la factura esté en estado 'generado' (CA5 -> HTTP 409)
        if invoice["status"] != "generado":
            raise ReglaNegocioError(
                f"Solo se pueden enviar facturas en estado 'generado' (estado actual: '{invoice['status']}').",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA5: Transmitir al proveedor autorizado (API DIAN / Proveedor) con timeout de 30s
        try:
            provider_result = self.provider_gateway.send_electronic_invoice(
                invoice_payload=invoice,
                timeout_seconds=30.0
            )
        except InvoiceProviderUnavailableError:
            # DoD: HTTP 503 ante servicio externo requerido no disponible
            raise ReglaNegocioError(
                "El proveedor autorizado de facturación no está disponible.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except InvoiceProviderTimeoutError:
            # CA8: Si no responde en 30s, conserva estado 'generado' y queda marcada para reenvío
            updated = self.repository.update_invoice(
                invoice_id=invoice_id,
                updates={"status": "generado", "pending_resend": True}
            )
            return (
                InvoiceResponseData(**updated),
                "El proveedor no respondió en 30 segundos; factura marcada para reenvío."
            )

        # CA6: Si el proveedor responde aceptada, pasa a 'aceptada'
        if provider_result.status == "aceptada":
            updated = self.repository.update_invoice(
                invoice_id=invoice_id,
                updates={
                    "status": "aceptada",
                    "pending_resend": False,
                    "rejection_code": None,
                    "rejection_reason": None,
                }
            )
            return (
                InvoiceResponseData(**updated),
                "Factura aceptada por el proveedor autorizado."
            )

        # CA7: Si el proveedor responde rechazada, pasa a 'rechazada' y guarda código y descripción
        updated = self.repository.update_invoice(
            invoice_id=invoice_id,
            updates={
                "status": "rechazada",
                "pending_resend": False,
                "rejection_code": provider_result.rejection_code,
                "rejection_reason": provider_result.rejection_reason,
            }
        )
        return (
            InvoiceResponseData(**updated),
            "Factura rechazada por el proveedor autorizado; motivo registrado."
        )
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
from app.domain.invoice import (
    InvoiceGenerateRequest, 
    InvoiceResponseData, 
    FiscalInfoResponseData, 
    FiscalInfoUpdateRequest,
    OrderFiscalQueryResponseData,
)    
from app.repositories.invoice import InvoiceRepository


# Se agrega en app/services/invoice.py para HU-036
CORRECTABLE_ERROR_CODES = {
    "DIAN-099",  # NIT / documento del adquiriente inconsistente o con ceros inválidos
    "DIAN-104",  # Formato de correo electrónico del adquiriente inválido
    "ERR-TAX-01",  # Redondeo de impuesto en línea corregible automáticamente
}


class InvoiceService:
    MAX_AUTO_RETRIES: int = 3 # HU-036

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

    # Implementacion HU-036
    def _apply_automatic_corrections(self, invoice: dict) -> list[str]:
        """
        Corrige los campos señalados por el código/motivo de rechazo y retorna
        la lista de campos modificados.
        """
        code = (invoice.get("rejection_code") or "").strip().upper()
        corrected: list[str] = []
        acquirer = dict(invoice.get("acquirer") or {})

        if code == "DIAN-099":
            doc_num = str(acquirer.get("document_number", "")).strip()
            if not doc_num or set(doc_num) == {"0"}:
                acquirer["document_number"] = "1000000001"
                corrected.append("acquirer.document_number")

        if code == "DIAN-104":
            email = str(acquirer.get("email", "")).strip().lower()
            if "@" not in email:
                acquirer["email"] = "facturacion.cliente@hobbyvault.co"
                corrected.append("acquirer.email")

        if code == "ERR-TAX-01":
            items = []
            for item in invoice.get("items", []):
                updated_item = dict(item)
                rate = float(updated_item.get("tax_rate", 0.0))
                if rate < 0 or rate > 1:
                    updated_item["tax_rate"] = 0.19
                    corrected.append("items.tax_rate")
                items.append(updated_item)
            if corrected:
                invoice["items"] = items

        if "acquirer.document_number" in corrected or "acquirer.email" in corrected:
            invoice["acquirer"] = acquirer

        return corrected

    def retry_rejected_invoice(self, invoice_id: int) -> tuple[InvoiceResponseData, str]:
        """
        FUN-5.2.4: Corrige y reenvía automáticamente una factura rechazada (CA1, CA2, CA3).
        """
        # Verificar existencia de la factura (HTTP 404)
        invoice = self.repository.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ReglaNegocioError(
                f"La factura con ID {invoice_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Verificar que la factura esté en estado 'rechazada' (HTTP 409)
        if invoice["status"] != "rechazada":
            raise ReglaNegocioError(
                f"Solo se pueden reintentar facturas en estado 'rechazada' (estado actual: '{invoice['status']}').",
                status_code=status.HTTP_409_CONFLICT
            )

        # CA1: Leer código y descripción del motivo de rechazo
        rejection_code = (invoice.get("rejection_code") or "").strip().upper()
        _rejection_reason = invoice.get("rejection_reason") or ""
        current_retries = int(invoice.get("retry_count", 0))

        is_correctable = rejection_code in CORRECTABLE_ERROR_CODES
        has_retries_left = current_retries < self.MAX_AUTO_RETRIES

        # CA3: Si el código no es corregible o ya alcanzó 3 reenvíos -> 'requiere revisión manual'
        if not is_correctable or not has_retries_left:
            updated = self.repository.update_invoice(
                invoice_id=invoice_id,
                updates={
                    "status": "requiere revisión manual",
                    "pending_resend": False,
                }
            )
            reason_msg = (
                "Se alcanzó el límite de 3 reenvíos automáticos."
                if not has_retries_left
                else f"El código '{rejection_code or 'SIN_CODIGO'}' no es corregible automáticamente."
            )
            return (
                InvoiceResponseData(**updated),
                f"Factura marcada como 'requiere revisión manual': {reason_msg}"
            )

        # CA2: Aplicar corrección automática e incrementar contador de reenvíos
        corrected_fields = self._apply_automatic_corrections(invoice)
        new_retry_count = current_retries + 1

        try:
            provider_result = self.provider_gateway.send_electronic_invoice(
                invoice_payload=invoice,
                timeout_seconds=30.0
            )
        except InvoiceProviderUnavailableError:
            raise ReglaNegocioError(
                "El proveedor autorizado de facturación no está disponible para el reenvío.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except InvoiceProviderTimeoutError:
            updated = self.repository.update_invoice(
                invoice_id=invoice_id,
                updates={
                    "status": "generado",
                    "retry_count": new_retry_count,
                    "corrected_fields": corrected_fields,
                    "pending_resend": True,
                }
            )
            return (
                InvoiceResponseData(**updated),
                "El proveedor no respondió en 30 segundos; factura conservada para reenvío."
            )

        if provider_result.status == "aceptada":
            updated = self.repository.update_invoice(
                invoice_id=invoice_id,
                updates={
                    "acquirer": invoice["acquirer"],
                    "items": invoice["items"],
                    "status": "aceptada",
                    "retry_count": new_retry_count,
                    "corrected_fields": corrected_fields,
                    "pending_resend": False,
                    "rejection_code": None,
                    "rejection_reason": None,
                }
            )
            return (
                InvoiceResponseData(**updated),
                "Factura corregida, reenviada y aceptada por el proveedor autorizado."
            )

        # Si el proveedor la vuelve a rechazar, actualiza motivo y contador
        updated = self.repository.update_invoice(
            invoice_id=invoice_id,
            updates={
                "acquirer": invoice["acquirer"],
                "items": invoice["items"],
                "status": "rechazada",
                "retry_count": new_retry_count,
                "corrected_fields": corrected_fields,
                "pending_resend": False,
                "rejection_code": provider_result.rejection_code,
                "rejection_reason": provider_result.rejection_reason,
            }
        )
        return (
            InvoiceResponseData(**updated),
            "Factura corregida y reenviada, pero fue nuevamente rechazada por el proveedor."
        )

    # Dentro de la clase InvoiceService para HU-035:
    def register_fiscal_info(
        self,
        invoice_id: int,
        payload: FiscalInfoUpdateRequest
    ) -> FiscalInfoResponseData:
        """
        FUN-5.2.3: Registra identificador fiscal y estado de validación ('aceptada' o 'rechazada').
        """
        # CA2: Validar campos explícitamente sin alterar nada si son inválidos (HTTP 400)
        invalid_fields = []
        clean_identifier = (payload.fiscal_identifier or "").strip()
        if not clean_identifier:
            invalid_fields.append("fiscal_identifier")
        if payload.validation_status not in {"aceptada", "rechazada"}:
            invalid_fields.append("validation_status")

        if invalid_fields:
            raise ReglaNegocioError(
                f"Campos inválidos: {', '.join(invalid_fields)}.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # CA3: Verificar que la factura exista (HTTP 404)
        invoice = self.repository.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ReglaNegocioError(
                f"La factura con ID {invoice_id} no existe.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA1: Guardar identificador y estado asociados a la factura
        now = datetime.now(timezone.utc)
        updated = self.repository.update_invoice(
            invoice_id=invoice_id,
            updates={
                "fiscal_identifier": clean_identifier,
                "status": payload.validation_status,
                "updated_at": now,
            }
        )

        return FiscalInfoResponseData(
            invoice_id=updated["invoice_id"],
            sale_id=updated["sale_id"],
            fiscal_identifier=updated["fiscal_identifier"],
            status=updated["status"],
            updated_at=now,
        )

    def get_invoice_by_order(self, order_id: int) -> OrderFiscalQueryResponseData:
        """
        FUN-5.2.5: Consulta ID de factura, identificador fiscal y estado actual por ID de orden.
        """
        # CA6: Verificar existencia de la orden (HTTP 404)
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise ReglaNegocioError(
                "La orden no existe",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA5: Verificar si la orden tiene una factura asociada (HTTP 404)
        invoice = self.repository.get_invoice_by_sale_id(order_id)
        if not invoice:
            raise ReglaNegocioError(
                "La orden no tiene factura asociada",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # CA4: Retornar ID de factura, identificador fiscal y estado actual
        return OrderFiscalQueryResponseData(
            order_id=order_id,
            invoice_id=invoice["invoice_id"],
            fiscal_identifier=invoice.get("fiscal_identifier"),
            status=invoice["status"],
        )
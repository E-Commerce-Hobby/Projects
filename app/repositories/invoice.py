# app/repositories/invoice.py
from typing import Dict, List, Optional


class InvoiceRepository:
    def __init__(self):
        self._sales_db: Dict[int, Dict] = {}
        self._invoices_db: List[Dict] = []
        self._invoice_id_counter: int = 1

    # --- Operaciones CRUD sobre Ventas (para validar CA1, CA3, CA4) ---
    def register_sale(self, sale_id: int, status: str = "confirmada", origin: str = "PAGOS") -> dict:
        sale = {
            "sale_id": sale_id,
            "status": status,
            "origin": origin
        }
        self._sales_db[sale_id] = sale
        return sale

    def get_sale_by_id(self, sale_id: int) -> Optional[dict]:
        return self._sales_db.get(sale_id)

    # --- Operaciones CRUD sobre Facturas ---
    # En InvoiceRepository.create_invoice (app/repositories/invoice.py) para HU-036
    def create_invoice(self, invoice_data: dict) -> dict:
        new_invoice = {
            "invoice_id": self._invoice_id_counter,
            "retry_count": 0,
            "corrected_fields": [],
            **invoice_data
        }
        self._invoices_db.append(new_invoice)
        self._invoice_id_counter += 1
        return new_invoice

    def get_invoice_by_id(self, invoice_id: int) -> Optional[dict]:
        for invoice in self._invoices_db:
            if invoice["invoice_id"] == invoice_id:
                return invoice
        return None

    def get_invoice_by_sale_id(self, sale_id: int) -> Optional[dict]:
        for invoice in self._invoices_db:
            if invoice["sale_id"] == sale_id:
                return invoice
        return None

    def update_invoice(self, invoice_id: int, updates: dict) -> Optional[dict]:
        invoice = self.get_invoice_by_id(invoice_id)
        if invoice:
            invoice.update(updates)
        return invoice

    def clear(self) -> None:
        self._sales_db.clear()
        self._invoices_db.clear()
        self._invoice_id_counter = 1


invoice_repository = InvoiceRepository()
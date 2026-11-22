"""Pydantic schemas for the POS receipt module (FUN-4.2.5)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Response schemas (output)
# ---------------------------------------------------------------------------
class ReceiptResponse(BaseModel):
    sale_id: int = Field(description="ID de la venta asociada al comprobante.")
    receipt_number: str = Field(description="Número del comprobante.")
    reference: str = Field(description="Referencia del comprobante generada por Facturación.")
    mensaje: str = Field(description="Confirmación en español.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sale_id": 1,
                "receipt_number": "CMP-000001",
                "reference": "7f3c2a1e-5b8d-4c0a-9e21-3d4f6a7b8c9d",
                "mensaje": "Comprobante generado correctamente.",
            }
        }
    )


# ---------------------------------------------------------------------------
# Data returned by the billing module (external contract, never exposed directly)
# ---------------------------------------------------------------------------
class BillingReceiptData(BaseModel):
    receipt_number: str
    reference: str


# ---------------------------------------------------------------------------
# Internal entity (stored by the repository)
# ---------------------------------------------------------------------------
class ReceiptRecord(BaseModel):
    sale_id: int
    receipt_number: str
    reference: str
    created_at: datetime
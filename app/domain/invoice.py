# app/domain/invoice.py
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, StrictInt, field_validator


class IssuerInfo(BaseModel):
    nit: str = Field(default="901234567-8", description="NIT del emisor (HobbyVault)", examples=["901234567-8"])
    business_name: str = Field(default="HobbyVault S.A.S.", description="Razón social del emisor")
    tax_regime: str = Field(default="Responsable de IVA", description="Régimen tributario del emisor")


class AcquirerInfo(BaseModel):
    document_type: str = Field(..., description="Tipo de documento (CC, NIT, CE)", examples=["CC"])
    document_number: str = Field(..., min_length=3, max_length=20, description="Número de documento", examples=["1098765432"])
    full_name: str = Field(..., min_length=2, max_length=120, description="Nombre o razón social", examples=["Carlos Mendoza"])
    email: str = Field(..., description="Correo electrónico para recepción de factura", examples=["carlos@example.com"])

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("El correo electrónico del adquiriente no tiene un formato válido.")
        return value.strip()


class InvoiceLineItem(BaseModel):
    product_id: StrictInt = Field(..., gt=0, description="ID del producto", examples=[101])
    product_name: str = Field(..., min_length=1, max_length=120, description="Nombre del producto", examples=["Set Dados Poliedricos"])
    quantity: StrictInt = Field(..., gt=0, description="Cantidad vendida", examples=[2])
    unit_price: float = Field(..., ge=0, description="Valor unitario antes de impuestos en COP", examples=[25000.0])
    tax_rate: float = Field(default=0.19, ge=0, le=1, description="Tarifa de impuesto (ej. 0.19 para IVA 19%)", examples=[0.19])


class InvoiceGenerateRequest(BaseModel):
    sale_id: StrictInt = Field(..., gt=0, description="ID de la venta confirmada", examples=[501])
    origin: Literal["PAGOS", "POS"] = Field(
        ...,
        description="Origen de la venta confirmada (PAGOS o POS)",
        examples=["PAGOS"]
    )
    issuer: IssuerInfo = Field(default_factory=IssuerInfo, description="Datos del emisor")
    acquirer: AcquirerInfo = Field(..., description="Datos del adquiriente")
    items: List[InvoiceLineItem] = Field(..., min_length=1, description="Líneas de la factura (producto, cantidad, valor)")
    provider_extra_data: Optional[dict] = Field(
        default_factory=dict,
        description="Datos adicionales exigidos por el proveedor autorizado"
    )


# Actualizaciones en app/domain/invoice.py para HU-036
# En InvoiceResponseData:
class InvoiceResponseData(BaseModel):
    invoice_id: int = Field(..., description="ID único de la factura generada", examples=[1])
    sale_id: int = Field(..., description="ID de la venta asociada", examples=[501])
    origin: str = Field(..., description="Origen de la venta (PAGOS o POS)", examples=["PAGOS"])
    status: Literal["generado", "aceptada", "rechazada", "requiere revisión manual"] = Field(
        ...,
        description="Estado actual de la factura",
        examples=["aceptada"]
    )
    retry_count: int = Field(
        default=0,
        description="Cantidad de reintentos automáticos realizados (máximo 3)",
        examples=[1]
    )
    corrected_fields: List[str] = Field(
        default_factory=list,
        description="Campos corregidos automáticamente según el motivo de rechazo",
        examples=[["acquirer.document_number"]]
    )
    pending_resend: bool = Field(
        default=False,
        description="Indica si quedó marcada para reenvío por timeout del proveedor"
    )
    issuer: IssuerInfo
    acquirer: AcquirerInfo
    items: List[InvoiceLineItem]
    subtotal: float = Field(..., description="Subtotal antes de impuestos en COP", examples=[50000.0])
    total_tax: float = Field(..., description="Total de impuestos en COP", examples=[9500.0])
    total_amount: float = Field(..., description="Valor total de la factura en COP", examples=[59500.0])
    rejection_code: Optional[str] = Field(None, description="Código de rechazo del proveedor", examples=["DIAN-099"])
    rejection_reason: Optional[str] = Field(None, description="Descripción del motivo de rechazo")
    created_at: datetime


class InvoiceStandardResponse(BaseModel):
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    data: Optional[InvoiceResponseData] = Field(
        None,
        description="Datos de la factura o null en caso de error"
    )
    message: str = Field(
        ...,
        max_length=200,
        description="Mensaje descriptivo en español de máximo 200 caracteres"
    )
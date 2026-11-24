# app/api/invoice.py
from fastapi import APIRouter, Path, status
from app.core.invoice_provider_gateway import invoice_provider_gateway
from app.domain.invoice import (
    InvoiceGenerateRequest,
    InvoiceStandardResponse,
)
from app.repositories.invoice import invoice_repository
from app.services.invoice import InvoiceService

router = APIRouter(
    prefix="/api/v1/invoices",
    tags=["Billing - Electronic Invoices (MOD-05)"]
)

invoice_service = InvoiceService(
    repository=invoice_repository,
    provider_gateway=invoice_provider_gateway,
)


@router.post(
    "",
    response_model=InvoiceStandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar factura electrónica de una venta confirmada (FUN-5.2.1)",
    description=(
        "Reúne emisor, adquiriente, líneas, impuestos y total de una venta confirmada (desde Pagos o POS) "
        "y registra la factura electrónica en estado 'generado'."
    ),
    responses={
        201: {
            "description": "CA1, CA2 - Factura generada exitosamente en estado 'generado'",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "invoice_id": 1,
                            "sale_id": 501,
                            "origin": "PAGOS",
                            "status": "generado",
                            "pending_resend": False,
                            "subtotal": 50000.0,
                            "total_tax": 9500.0,
                            "total_amount": 59500.0
                        },
                        "message": "Factura generada exitosamente en estado 'generado'."
                    }
                }
            }
        },
        404: {
            "description": "CA4 - La venta asociada no existe",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "La venta con ID 999 no existe."
                    }
                }
            }
        },
        409: {
            "description": "CA3 / CA4 - La venta ya tiene factura o no está confirmada",
            "content": {
                "application/json": {
                    "examples": {
                        "FacturaDuplicada": {
                            "summary": "CA3 - Venta ya facturada",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "La venta con ID 501 ya tiene la factura #1 registrada."
                            }
                        },
                        "VentaNoConfirmada": {
                            "summary": "CA4 - Venta no confirmada",
                            "value": {
                                "success": False,
                                "data": None,
                                "message": "La venta con ID 502 no está confirmada (estado actual: pendiente)."
                            }
                        }
                    }
                }
            }
        }
    }
)
def generate_invoice_endpoint(payload: InvoiceGenerateRequest):
    invoice_data = invoice_service.generate_invoice(payload)
    return InvoiceStandardResponse(
        success=True,
        data=invoice_data,
        message="Factura generada exitosamente en estado 'generado'."
    )


@router.post(
    "/{invoice_id}/send",
    response_model=InvoiceStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar factura generada al proveedor autorizado DIAN (FUN-5.2.2)",
    description=(
        "Transmite una factura en estado 'generado' al proveedor autorizado (API-EXT-02) con espera máxima de 30s. "
        "Actualiza su estado a 'aceptada', 'rechazada' (con código y motivo) o conserva 'generado' marcada para reenvío."
    ),
    responses={
        200: {
            "description": "CA5, CA6, CA7, CA8 - Respuesta del proveedor procesada o marcada para reenvío",
            "content": {
                "application/json": {
                    "examples": {
                        "CA6_Aceptada": {
                            "summary": "CA6 - Factura aceptada",
                            "value": {
                                "success": True,
                                "data": {"invoice_id": 1, "sale_id": 501, "status": "aceptada", "pending_resend": False},
                                "message": "Factura aceptada por el proveedor autorizado."
                            }
                        },
                        "CA7_Rechazada": {
                            "summary": "CA7 - Factura rechazada con código y motivo",
                            "value": {
                                "success": True,
                                "data": {
                                    "invoice_id": 1,
                                    "sale_id": 501,
                                    "status": "rechazada",
                                    "rejection_code": "DIAN-099",
                                    "rejection_reason": "NIT del adquiriente no registrado o inconsistente en RUT."
                                },
                                "message": "Factura rechazada por el proveedor autorizado; motivo registrado."
                            }
                        },
                        "CA8_Timeout30s": {
                            "summary": "CA8 - Timeout de 30s, marcada para reenvío",
                            "value": {
                                "success": True,
                                "data": {"invoice_id": 1, "sale_id": 501, "status": "generado", "pending_resend": True},
                                "message": "El proveedor no respondió en 30 segundos; factura marcada para reenvío."
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Factura inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "La factura con ID 999 no existe."
                    }
                }
            }
        },
        409: {
            "description": "La factura no está en estado 'generado'",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Solo se pueden enviar facturas en estado 'generado' (estado actual: 'aceptada')."
                    }
                }
            }
        },
        503: {
            "description": "Proveedor autorizado no disponible",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "El proveedor autorizado de facturación no está disponible."
                    }
                }
            }
        }
    }
)
def send_invoice_endpoint(
    invoice_id: int = Path(..., gt=0, description="ID de la factura en estado 'generado'", examples=[1])
):
    updated_invoice, msg = invoice_service.send_invoice_to_provider(invoice_id=invoice_id)
    return InvoiceStandardResponse(
        success=True,
        data=updated_invoice,
        message=msg
    )

# Agregar en app/api/invoice.py
@router.post(
    "/{invoice_id}/retry",
    response_model=InvoiceStandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Corregir y reenviar automáticamente una factura rechazada (HU-036 / FUN-5.2.4)",
    description=(
        "Procesa una factura en estado 'rechazada'. Si el código de rechazo es corregible y tiene "
        "menos de 3 reenvíos, corrige los campos afectados y reenvía al proveedor autorizado. "
        "Si no es corregible o ya tiene 3 reenvíos, marca la factura como 'requiere revisión manual'."
    ),
    responses={
        200: {
            "description": "CA1, CA2, CA3 - Reenvío procesado o factura marcada como 'requiere revisión manual'",
            "content": {
                "application/json": {
                    "examples": {
                        "CA2_CorregidaYAceptada": {
                            "summary": "CA2 - Error corregible, reenviada y aceptada",
                            "value": {
                                "success": True,
                                "data": {
                                    "invoice_id": 1,
                                    "sale_id": 501,
                                    "status": "aceptada",
                                    "retry_count": 1,
                                    "corrected_fields": ["acquirer.document_number"]
                                },
                                "message": "Factura corregida, reenviada y aceptada por el proveedor autorizado."
                            }
                        },
                        "CA3_RevisionManual": {
                            "summary": "CA3 - Error no corregible o 3 reenvíos alcanzados",
                            "value": {
                                "success": True,
                                "data": {
                                    "invoice_id": 1,
                                    "sale_id": 501,
                                    "status": "requiere revisión manual",
                                    "retry_count": 3
                                },
                                "message": "Factura marcada como 'requiere revisión manual': Se alcanzó el límite de 3 reenvíos automáticos."
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Factura inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "La factura con ID 999 no existe."
                    }
                }
            }
        },
        409: {
            "description": "La factura no está en estado 'rechazada'",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "Solo se pueden reintentar facturas en estado 'rechazada' (estado actual: 'aceptada')."
                    }
                }
            }
        },
        503: {
            "description": "Proveedor autorizado no disponible",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "message": "El proveedor autorizado de facturación no está disponible para el reenvío."
                    }
                }
            }
        }
    }
)
def retry_invoice_endpoint(
    invoice_id: int = Path(..., gt=0, description="ID de la factura rechazada a procesar", examples=[1])
):
    updated_invoice, msg = invoice_service.retry_rejected_invoice(invoice_id=invoice_id)
    return InvoiceStandardResponse(
        success=True,
        data=updated_invoice,
        message=msg
    )
# tests/test_hu036_invoice_retry.py
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest
from main import app
from app.core.invoice_provider_gateway import invoice_provider_gateway
from app.repositories.invoice import invoice_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    invoice_repository.clear()
    invoice_provider_gateway.reset()


def _seed_rejected_invoice(
    sale_id: int = 701,
    rejection_code: str = "DIAN-099",
    rejection_reason: str = "NIT del adquiriente inválido o en ceros.",
    retry_count: int = 0,
    doc_number: str = "000000000",
):
    invoice_repository.register_sale(sale_id=sale_id, status="confirmada", origin="PAGOS")
    return invoice_repository.create_invoice({
        "sale_id": sale_id,
        "origin": "PAGOS",
        "status": "rechazada",
        "retry_count": retry_count,
        "corrected_fields": [],
        "pending_resend": False,
        "issuer": {
            "nit": "901234567-8",
            "business_name": "HobbyVault S.A.S.",
            "tax_regime": "Responsable de IVA",
        },
        "acquirer": {
            "document_type": "CC",
            "document_number": doc_number,
            "full_name": "Andrés Rojas",
            "email": "andres@example.com",
        },
        "items": [
            {
                "product_id": 5,
                "product_name": "Tablero Modular",
                "quantity": 1,
                "unit_price": 80000.0,
                "tax_rate": 0.19,
            }
        ],
        "provider_extra_data": {},
        "subtotal": 80000.0,
        "total_tax": 15200.0,
        "total_amount": 95200.0,
        "rejection_code": rejection_code,
        "rejection_reason": rejection_reason,
        "created_at": datetime.now(timezone.utc),
    })


def test_ca1_and_ca2_corrects_field_resends_and_updates_status():
    """CA1 & CA2: Lee código/motivo, corrige campo si es corregible y retry_count < 3, reenvía y actualiza estado."""
    invoice = _seed_rejected_invoice(
        sale_id=701,
        rejection_code="DIAN-099",
        retry_count=0,
        doc_number="000000000",
    )

    response = client.post(f"/api/v1/invoices/{invoice['invoice_id']}/retry")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "aceptada"
    assert body["data"]["retry_count"] == 1
    assert "acquirer.document_number" in body["data"]["corrected_fields"]
    assert body["data"]["acquirer"]["document_number"] != "000000000"
    assert len(body["message"]) <= 200


def test_ca3_non_correctable_error_marks_manual_review():
    """CA3: Si el código de rechazo no es corregible, no reenvía y marca 'requiere revisión manual'."""
    invoice = _seed_rejected_invoice(
        sale_id=702,
        rejection_code="DIAN-999",
        rejection_reason="Emisor no habilitado en resolución vigente.",
        retry_count=0,
    )

    response = client.post(f"/api/v1/invoices/{invoice['invoice_id']}/retry")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "requiere revisión manual"
    assert body["data"]["retry_count"] == 0
    assert "requiere revisión manual" in body["data"]["status"]


def test_ca3_max_three_retries_reached_marks_manual_review():
    """CA3: Si la factura ya tiene 3 reenvíos, no reenvía y marca 'requiere revisión manual'."""
    invoice = _seed_rejected_invoice(
        sale_id=703,
        rejection_code="DIAN-099",
        retry_count=3,
    )

    response = client.post(f"/api/v1/invoices/{invoice['invoice_id']}/retry")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "requiere revisión manual"
    assert body["data"]["retry_count"] == 3


def test_reject_not_found_404_and_invalid_state_409():
    """DoD: Retorna 404 si no existe y 409 si la factura no está en estado 'rechazada'."""
    res_404 = client.post("/api/v1/invoices/99999/retry")
    assert res_404.status_code == 404
    assert res_404.json()["data"] in (None, [])

    accepted = _seed_rejected_invoice(sale_id=704, rejection_code="DIAN-099", retry_count=0, doc_number="1020304050")
    invoice_repository.update_invoice(accepted["invoice_id"], {"status": "aceptada"})

    res_409 = client.post(f"/api/v1/invoices/{accepted['invoice_id']}/retry")
    assert res_409.status_code == 409
    assert res_409.json()["data"] in (None, [])


def test_provider_unavailable_returns_503():
    """DoD: Retorna HTTP 503 si el proveedor externo no está disponible durante el reenvío."""
    invoice = _seed_rejected_invoice(sale_id=705, rejection_code="DIAN-099", retry_count=0, doc_number="1020304050")
    invoice_provider_gateway.service_available = False

    response = client.post(f"/api/v1/invoices/{invoice['invoice_id']}/retry")
    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["data"] in (None, [])
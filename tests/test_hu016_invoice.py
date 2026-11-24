# tests/test_hu014_invoice.py
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


def _sample_invoice_payload(sale_id: int = 501, origin: str = "PAGOS", doc_number: str = "1098765432"):
    return {
        "sale_id": sale_id,
        "origin": origin,
        "acquirer": {
            "document_type": "CC",
            "document_number": doc_number,
            "full_name": "Laura Gómez",
            "email": "laura@example.com"
        },
        "items": [
            {
                "product_id": 10,
                "product_name": "Mazo Commander Magic",
                "quantity": 2,
                "unit_price": 100000.0,
                "tax_rate": 0.19
            }
        ],
        "provider_extra_data": {"resolution_number": "18764000001234"}
    }


def test_ca1_and_ca2_generate_invoice_success():
    """CA1 & CA2: Reúne emisor, adquiriente, líneas, impuestos y total; registra estado 'generado' (HTTP 201)."""
    invoice_repository.register_sale(sale_id=501, status="confirmada", origin="PAGOS")

    response = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=501, origin="PAGOS"))
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["invoice_id"] == 1
    assert body["data"]["sale_id"] == 501
    assert body["data"]["status"] == "generado"
    assert body["data"]["subtotal"] == 200000.0
    assert body["data"]["total_tax"] == 38000.0
    assert body["data"]["total_amount"] == 238000.0
    assert len(body["message"]) <= 200


def test_ca3_reject_duplicate_invoice_for_same_sale():
    """CA3: Rechaza con HTTP 409 si la venta ya tiene una factura registrada."""
    invoice_repository.register_sale(sale_id=502, status="confirmada", origin="POS")

    first = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=502, origin="POS"))
    assert first.status_code == 201

    second = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=502, origin="POS"))
    assert second.status_code == 409
    assert "ya tiene la factura" in second.json()["message"].lower()


def test_ca4_reject_nonexistent_or_unconfirmed_sale():
    """CA4: Rechaza con HTTP 404 si la venta no existe y HTTP 409 si no está confirmada."""
    # Venta inexistente
    res_not_found = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=999))
    assert res_not_found.status_code == 404

    # Venta pendiente (no confirmada)
    invoice_repository.register_sale(sale_id=503, status="pendiente", origin="PAGOS")
    res_unconfirmed = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=503))
    assert res_unconfirmed.status_code == 409
    assert "no está confirmada" in res_unconfirmed.json()["message"].lower()


def test_ca5_and_ca6_send_invoice_accepted_by_provider():
    """CA5 & CA6: Envía factura en estado 'generado' y pasa a 'aceptada' cuando el proveedor aprueba."""
    invoice_repository.register_sale(sale_id=504, status="confirmada")
    created = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=504)).json()
    invoice_id = created["data"]["invoice_id"]

    response = client.post(f"/api/v1/invoices/{invoice_id}/send")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "aceptada"
    assert body["data"]["pending_resend"] is False


def test_ca7_send_invoice_rejected_by_provider_saves_reason():
    """CA7: Cuando el proveedor rechaza, pasa a 'rechazada' y guarda código y descripción del motivo."""
    invoice_repository.register_sale(sale_id=505, status="confirmada")
    created = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=505)).json()
    invoice_id = created["data"]["invoice_id"]

    invoice_provider_gateway.force_rejection = True
    response = client.post(f"/api/v1/invoices/{invoice_id}/send")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "rechazada"
    assert body["data"]["rejection_code"] == "DIAN-099"
    assert body["data"]["rejection_reason"] is not None


def test_ca8_provider_timeout_30s_keeps_generated_and_marks_resend():
    """CA8: Si el proveedor no responde en 30s, conserva estado 'generado' y queda marcada para reenvío."""
    invoice_repository.register_sale(sale_id=506, status="confirmada")
    created = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=506)).json()
    invoice_id = created["data"]["invoice_id"]

    invoice_provider_gateway.simulated_delay_seconds = 31.0
    response = client.post(f"/api/v1/invoices/{invoice_id}/send")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "generado"
    assert body["data"]["pending_resend"] is True


def test_provider_unavailable_returns_503():
    """DoD: Si el proveedor externo no está disponible, devuelve HTTP 503."""
    invoice_repository.register_sale(sale_id=507, status="confirmada")
    created = client.post("/api/v1/invoices", json=_sample_invoice_payload(sale_id=507)).json()
    invoice_id = created["data"]["invoice_id"]

    invoice_provider_gateway.service_available = False
    response = client.post(f"/api/v1/invoices/{invoice_id}/send")
    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["data"] is None


def test_empty_payload_returns_400():
    """DoD: Entrada vacía {} devuelve HTTP 400."""
    response = client.post("/api/v1/invoices", json={})
    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["data"] is None
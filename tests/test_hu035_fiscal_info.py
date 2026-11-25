# tests/test_hu035_fiscal_info.py
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest
from main import app
from app.repositories.invoice import invoice_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    invoice_repository.clear()


def _seed_invoice_for_order(order_id: int = 801):
    invoice_repository.register_order(order_id=order_id, status="confirmada", origin="PAGOS")
    return invoice_repository.create_invoice({
        "sale_id": order_id,
        "origin": "PAGOS",
        "status": "generado",
        "fiscal_identifier": None,
        "retry_count": 0,
        "corrected_fields": [],
        "pending_resend": False,
        "issuer": {"nit": "901234567-8", "business_name": "HobbyVault S.A.S.", "tax_regime": "Responsable de IVA"},
        "acquirer": {"document_type": "CC", "document_number": "1098765432", "full_name": "Cliente Prueba", "email": "cliente@test.com"},
        "items": [],
        "provider_extra_data": {},
        "subtotal": 10000.0,
        "total_tax": 1900.0,
        "total_amount": 11900.0,
        "rejection_code": None,
        "rejection_reason": None,
        "created_at": datetime.now(timezone.utc),
    })


def test_ca1_register_fiscal_info_success():
    """CA1: Factura existe, identificador no vacío y estado 'aceptada' o 'rechazada' -> guarda y confirma."""
    inv = _seed_invoice_for_order(order_id=801)
    response = client.patch(
        f"/api/v1/invoices/{inv['invoice_id']}/fiscal",
        json={"fiscal_identifier": "CUFE-99887766", "validation_status": "aceptada"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["fiscal_identifier"] == "CUFE-99887766"
    assert body["data"]["status"] == "aceptada"
    assert len(body["message"]) <= 200


def test_ca2_reject_empty_identifier_or_invalid_status_without_saving():
    """CA2: Rechaza con HTTP 400 si identificador está vacío o estado no es 'aceptada'/'rechazada'."""
    inv = _seed_invoice_for_order(order_id=802)

    res_empty_id = client.patch(
        f"/api/v1/invoices/{inv['invoice_id']}/fiscal",
        json={"fiscal_identifier": "   ", "validation_status": "aceptada"}
    )
    assert res_empty_id.status_code == 400
    assert "fiscal_identifier" in res_empty_id.json()["message"]
    assert invoice_repository.get_invoice_by_id(inv["invoice_id"])["fiscal_identifier"] is None

    res_bad_status = client.patch(
        f"/api/v1/invoices/{inv['invoice_id']}/fiscal",
        json={"fiscal_identifier": "CUFE-123", "validation_status": "pendiente"}
    )
    assert res_bad_status.status_code == 400
    assert res_bad_status.json()["data"] in (None, [])


def test_ca3_reject_nonexistent_invoice_404():
    """CA3: Si la factura no existe, rechaza con HTTP 404."""
    response = client.patch(
        "/api/v1/invoices/9999/fiscal",
        json={"fiscal_identifier": "CUFE-123", "validation_status": "aceptada"}
    )
    assert response.status_code == 404
    assert response.json()["data"] in (None, [])


def test_ca4_query_by_order_returns_invoice_fiscal_and_status():
    """CA4: Orden existe y tiene factura asociada -> retorna ID factura, identificador fiscal y estado."""
    inv = _seed_invoice_for_order(order_id=803)
    invoice_repository.update_invoice(
        inv["invoice_id"],
        {"fiscal_identifier": "CUFE-ORDEN-803", "status": "aceptada"}
    )

    response = client.get(
        "/api/v1/invoices/by-order/803",
        headers={"Authorization": "Bearer client-1", "X-User-Role": "cajero"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["invoice_id"] == inv["invoice_id"]
    assert body["data"]["fiscal_identifier"] == "CUFE-ORDEN-803"
    assert body["data"]["status"] == "aceptada"


def test_ca5_order_exists_without_invoice_returns_404():
    """CA5: Orden existe pero no tiene factura asociada -> responde 'La orden no tiene factura asociada'."""
    invoice_repository.register_order(order_id=804, status="confirmada")

    response = client.get(
        "/api/v1/invoices/by-order/804",
        headers={"Authorization": "Bearer client-1", "X-User-Role": "administrador"}
    )
    assert response.status_code == 404
    assert response.json()["message"] == "La orden no tiene factura asociada"


def test_ca6_order_does_not_exist_returns_404():
    """CA6: Orden no existe -> responde 'La orden no existe'."""
    response = client.get(
        "/api/v1/invoices/by-order/99999",
        headers={"Authorization": "Bearer client-1", "X-User-Role": "administrador"}
    )
    assert response.status_code == 404
    assert response.json()["message"] == "La orden no existe"


def test_ca7_unauthorized_role_returns_403_and_missing_token_401():
    """CA7 & DoD: Sin rol 'administrador'/'cajero' devuelve 403; sin token devuelve 401."""
    _seed_invoice_for_order(order_id=805)

    res_403 = client.get(
        "/api/v1/invoices/by-order/805",
        headers={"Authorization": "Bearer client-1", "X-User-Role": "cliente"}
    )
    assert res_403.status_code == 403
    assert res_403.json()["data"] in (None, [])

    res_401 = client.get("/api/v1/invoices/by-order/805")
    assert res_401.status_code == 401


def test_empty_fiscal_payload_returns_400():
    """DoD: Entrada vacía {} en registro fiscal devuelve HTTP 400."""
    inv = _seed_invoice_for_order(order_id=806)
    response = client.patch(f"/api/v1/invoices/{inv['invoice_id']}/fiscal", json={})
    assert response.status_code == 400
    assert response.json()["data"] in (None, [])
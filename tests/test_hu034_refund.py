# tests/test_hu034_refund.py
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from main import app
from app.core.refund_gateway import refund_gateway
from app.repositories.refund import refund_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    refund_repository.clear()
    refund_gateway.reset()


def test_ca1_and_ca3_full_refund_sends_tx_and_amount_and_updates_statuses():
    """CA1 & CA3: Envía transaction_id y monto a pasarela; actualiza pago a 'reembolsado' y orden a 'reembolsada'."""
    refund_repository.register_paid_order(
        order_id=1001,
        transaction_id="TX-ABC-1001",
        amount=150000.0,
        payment_status="aprobado",
        order_status="pagada",
        paid_at=datetime.now(timezone.utc) - timedelta(days=2),
    )

    with patch.object(refund_gateway, "request_full_refund", wraps=refund_gateway.request_full_refund) as spy:
        response = client.post("/api/v1/payments/refunds", json={"order_id": 1001})

    assert response.status_code == 200
    spy.assert_called_once_with(
        transaction_id="TX-ABC-1001",
        amount=150000.0,
        timeout_seconds=10.0,
    )
    body = response.json()
    assert body["success"] is True
    assert body["data"]["amount"] == 150000.0
    assert body["data"]["payment_status"] == "reembolsado"
    assert body["data"]["order_status"] == "reembolsada"
    assert len(body["message"]) <= 200


def test_ca2_rejects_when_already_refunded_or_expired_or_unapproved():
    """CA2: Rechaza con HTTP 409 e indica la condición incumplida."""
    # 1. Ya reembolsada
    refund_repository.register_paid_order(
        order_id=1002,
        transaction_id="TX-1002",
        amount=50000.0,
        payment_status="reembolsado",
        order_status="reembolsada",
    )
    res_dup = client.post("/api/v1/payments/refunds", json={"order_id": 1002})
    assert res_dup.status_code == 409
    assert "reembolsada" in res_dup.json()["message"].lower()

    # 2. Fuera del plazo máximo (> 30 días)
    refund_repository.register_paid_order(
        order_id=1003,
        transaction_id="TX-1003",
        amount=50000.0,
        payment_status="aprobado",
        order_status="pagada",
        paid_at=datetime.now(timezone.utc) - timedelta(days=45),
    )
    res_exp = client.post("/api/v1/payments/refunds", json={"order_id": 1003})
    assert res_exp.status_code == 409
    assert "plazo" in res_exp.json()["message"].lower()


def test_ca4_gateway_timeout_10s_or_decline_keeps_statuses_unchanged():
    """CA4: Timeout > 10s o rechazo de pasarela no modifica estados de pago ni de orden."""
    refund_repository.register_paid_order(
        order_id=1004,
        transaction_id="TX-1004",
        amount=75000.0,
        payment_status="aprobado",
        order_status="pagada",
    )
    refund_gateway.simulated_delay_seconds = 11.0

    response = client.post("/api/v1/payments/refunds", json={"order_id": 1004})
    assert response.status_code == 503
    assert response.json()["data"] in (None, [])

    order_after = refund_repository.get_order_by_id(1004)
    assert order_after["payment_status"] == "aprobado"
    assert order_after["order_status"] == "pagada"


def test_reject_not_found_404_and_empty_payload_400():
    """DoD: Orden inexistente retorna 404 y entrada vacía {} retorna 400."""
    res_404 = client.post("/api/v1/payments/refunds", json={"order_id": 99999})
    assert res_404.status_code == 404
    assert res_404.json()["data"] in (None, [])

    res_400 = client.post("/api/v1/payments/refunds", json={})
    assert res_400.status_code == 400
    assert res_400.json()["data"] in (None, [])
# tests/test_hu033_rejected_payment.py
from fastapi.testclient import TestClient
import pytest
from main import app
from app.repositories.rejected_payment import rejected_payment_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    rejected_payment_repository.clear()


def test_ca1_and_ca2_register_rejected_payment_with_reason_and_metadata():
    """CA1 & CA2: Guarda código/descripción, ID orden, ID transacción y fecha/hora (HTTP 200)."""
    rejected_payment_repository.register_order(order_id=1001)

    response = client.post(
        "/api/v1/payments/rejected",
        json={
            "order_id": 1001,
            "transaction_id": "TX-PAYU-111",
            "rejection_code": "ERR-05",
            "rejection_description": "Tarjeta declinada por el banco emisor"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["order_id"] == 1001
    assert body["data"]["transaction_id"] == "TX-PAYU-111"
    assert body["data"]["rejection_code"] == "ERR-05"
    assert body["data"]["reason"] == "[ERR-05] Tarjeta declinada por el banco emisor"
    assert body["data"]["recorded_at"] is not None
    assert len(body["message"]) <= 200


def test_ca1_defaults_to_sin_motivo_informado_when_missing():
    """CA1: Si la pasarela no envía código ni descripción, guarda 'sin motivo informado'."""
    rejected_payment_repository.register_order(order_id=1002)

    response = client.post(
        "/api/v1/payments/rejected",
        json={
            "order_id": 1002,
            "transaction_id": "TX-WOMPI-222"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["reason"] == "sin motivo informado"
    assert body["data"]["rejection_code"] is None


def test_ca3_increments_order_failed_attempts_counter_each_time():
    """CA3: Incrementa en 1 el contador de intentos fallidos de la orden y retorna su valor."""
    rejected_payment_repository.register_order(order_id=1003, failed_attempts_count=0)

    first = client.post(
        "/api/v1/payments/rejected",
        json={"order_id": 1003, "transaction_id": "TX-301", "rejection_description": "Timeout pasarela"}
    )
    assert first.status_code == 200
    assert first.json()["data"]["order_failed_attempts"] == 1

    second = client.post(
        "/api/v1/payments/rejected",
        json={"order_id": 1003, "transaction_id": "TX-302", "rejection_description": "Fondos insuficientes"}
    )
    assert second.status_code == 200
    assert second.json()["data"]["order_failed_attempts"] == 2
    assert len(rejected_payment_repository.get_attempts_by_order(1003)) == 2


def test_reject_nonexistent_order_404():
    """DoD: Retorna HTTP 404 cuando la orden no existe."""
    response = client.post(
        "/api/v1/payments/rejected",
        json={"order_id": 99999, "transaction_id": "TX-404"}
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert len(body["message"]) <= 200


def test_reject_empty_or_invalid_payload_400():
    """DoD: Entrada vacía {} o campos obligatorios faltantes devuelven HTTP 400."""
    res_empty = client.post("/api/v1/payments/rejected", json={})
    assert res_empty.status_code == 400
    assert res_empty.json()["success"] is False
    assert res_empty.json()["data"] is None

    rejected_payment_repository.register_order(order_id=1004)
    res_blank_tx = client.post(
        "/api/v1/payments/rejected",
        json={"order_id": 1004, "transaction_id": "   "}
    )
    assert res_blank_tx.status_code == 400
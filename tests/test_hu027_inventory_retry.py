# tests/test_hu027_inventory_retry.py
from fastapi.testclient import TestClient
import pytest
from main import app
from app.api.inventory_retry import inventory_retry_service
from app.repositories.inventory_retry import inventory_retry_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    inventory_retry_repository.clear()
    inventory_retry_service.sleep_fn = lambda _sec: None
    inventory_retry_service.retry_delay_seconds = 30.0


def test_ca1_and_ca2_retries_temporary_error_and_succeeds_once():
    """CA1 & CA2: Reintenta hasta 3 veces con 30s de espera ante error temporal; aplica descuento una sola vez."""
    sleep_calls = []
    discount_calls = []

    inventory_retry_service.sleep_fn = lambda sec: sleep_calls.append(sec)

    def fake_executor(payload):
        discount_calls.append(payload.id_venta)
        return {"resultado": "exitoso"}

    original_executor = inventory_retry_service.discount_executor
    inventory_retry_service.discount_executor = fake_executor
    try:
        response = client.post(
            "/api/v1/inventario/reintentos",
            json={
                "operation_id": "OP-101",
                "sale_id": "VEN-101",
                "channel": "virtual",
                "lines": [{"product_id": "PROD-001", "location": "Bodega Virtual", "quantity": 1}],
                "simulate_temporary_failures": 2
            }
        )
    finally:
        inventory_retry_service.discount_executor = original_executor

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "exitosa"
    assert body["data"]["attempts_used"] == 3
    assert len(discount_calls) == 1
    assert sleep_calls == [30.0, 30.0]


def test_ca3_and_ca4_exhausts_3_retries_marks_failed_and_creates_alert():
    """CA3 & CA4: Tras agotar 3 reintentos, marca 'fallida' con último motivo y genera alerta con ID, motivo y fecha."""
    response = client.post(
        "/api/v1/inventario/reintentos",
        json={
            "operation_id": "OP-102",
            "sale_id": "VEN-102",
            "channel": "POS",
            "lines": [{"product_id": "PROD-001", "location": "Tienda Física", "quantity": 1}],
            "simulate_temporary_failures": 5
        }
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "fallida"
    assert body["data"]["last_error"] is not None
    assert body["data"]["alert"]["operation_id"] == "OP-102"
    assert body["data"]["alert"]["reason"] == body["data"]["last_error"]
    assert body["data"]["alert"]["created_at"] is not None


def test_ca5_business_rule_failure_does_not_retry_rn01():
    """CA5 (RN-01): Si falla por regla de negocio (ej. stock insuficiente), no reintenta y marca 'fallida'."""
    sleep_calls = []
    inventory_retry_service.sleep_fn = lambda sec: sleep_calls.append(sec)

    def fake_rn01_fail(_payload):
        raise ReglaNegocioError(message="Stock insuficiente (RN-01)", status_code=409)

    from app.core.errors import ReglaNegocioError
    original_executor = inventory_retry_service.discount_executor
    inventory_retry_service.discount_executor = fake_rn01_fail
    try:
        response = client.post(
            "/api/v1/inventario/reintentos",
            json={
                "operation_id": "OP-103",
                "sale_id": "VEN-103",
                "channel": "virtual",
                "lines": [{"product_id": "PROD-001", "location": "Bodega Virtual", "quantity": 999999}],
                "simulate_temporary_failures": 0
            }
        )
    finally:
        inventory_retry_service.discount_executor = original_executor

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "fallida"
    assert body["data"]["attempts_used"] == 1
    assert sleep_calls == []
    assert body["data"]["alert"] is not None


def test_empty_payload_returns_400_and_service_unavailable_returns_503():
    """DoD: Entrada vacía devuelve 400 y servicio no disponible devuelve 503."""
    res_400 = client.post("/api/v1/inventario/reintentos", json={})
    assert res_400.status_code == 400

    res_503 = client.post(
        "/api/v1/inventario/reintentos",
        json={
            "sale_id": "VEN-104",
            "channel": "virtual",
            "lines": [{"product_id": "PROD-001", "location": "Bodega Virtual", "quantity": 1}],
            "service_unavailable": True
        }
    )
    assert res_503.status_code == 503
    assert res_503.json()["data"] is None
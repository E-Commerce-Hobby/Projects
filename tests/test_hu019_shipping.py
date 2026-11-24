# tests/test_hu019_shipping.py
from fastapi.testclient import TestClient
import pytest
from main import app
from app.core.carrier_gateway import carrier_gateway
from app.repositories.shipping import shipping_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    shipping_repository.clear()
    carrier_gateway.reset()


def test_ca1_and_ca2_quote_shipping_rate_success():
    """CA1 & CA2: Consulta tarifa con datos válidos y retorna valor entero en COP, moneda y transportadora."""
    response = client.post(
        "/api/v1/shipping/quote",
        json={
            "weight_kg": 2.5,
            "dimensions": {
                "length_cm": 30,
                "width_cm": 20,
                "height_cm": 15
            },
            "destination_municipality": "Bucaramanga"
        }
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"]["amount"], int)
    assert body["data"]["amount"] > 0
    assert body["data"]["currency"] == "COP"
    assert body["data"]["carrier"] == "Servientrega"
    assert len(body["message"]) <= 200


def test_ca3_reject_when_carrier_timeout_exceeds_10s():
    """CA3: Si la transportadora supera 10 segundos sin responder, retorna HTTP 503 y data=None."""
    carrier_gateway.simulated_delay_seconds = 11.0

    response = client.post(
        "/api/v1/shipping/quote",
        json={
            "weight_kg": 1.2,
            "dimensions": {"length_cm": 20, "width_cm": 15, "height_cm": 10},
            "destination_municipality": "Bogotá"
        }
    )
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert "no está disponible" in body["message"].lower()


def test_ca3_reject_when_carrier_returns_error():
    """CA3: Si la transportadora externa falla, retorna HTTP 503 sin valor de tarifa."""
    carrier_gateway.force_error = True

    response = client.post(
        "/api/v1/shipping/quote",
        json={
            "weight_kg": 3.0,
            "dimensions": {"length_cm": 25, "width_cm": 25, "height_cm": 20},
            "destination_municipality": "Medellín"
        }
    )
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None


def test_ca4_reject_zero_or_negative_measurements():
    """CA4: Rechaza con HTTP 400 cuando peso o dimensiones son <= 0 indicando cada campo inválido."""
    response = client.post(
        "/api/v1/shipping/quote",
        json={
            "weight_kg": 0,
            "dimensions": {
                "length_cm": 20,
                "width_cm": -5,
                "height_cm": 0
            },
            "destination_municipality": "Cali"
        }
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert "weight_kg" in body["message"]
    assert "width_cm" in body["message"]
    assert "height_cm" in body["message"]


def test_ca4_reject_missing_fields_and_empty_payload():
    """CA4 & DoD: Rechaza entrada vacía {} o campos faltantes con HTTP 400."""
    response = client.post("/api/v1/shipping/quote", json={})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert "Faltan campos obligatorios" in body["message"]
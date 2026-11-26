# test_hu017_event.py
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from main import app
from app.repositories.event import event_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    event_repository.clear()


def test_ca1_create_event_success():
    """CA1: Datos válidos registran el evento con available_spots == max_capacity y HTTP 201."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    response = client.post(
        "/api/v1/events",
        json={
            "name": "Curso de Pintura de Miniaturas",
            "event_date": future_date,
            "max_capacity": 15,
            "registration_price": 0.0
        }
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["max_capacity"] == 15
    assert body["data"]["available_spots"] == 15
    assert body["data"]["currency"] == "COP"
    assert len(body["message"]) <= 200


def test_ca2_reject_past_or_current_date():
    """CA2: Fecha igual o anterior al momento actual rechaza la creación con HTTP 400."""
    past_date = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    response = client.post(
        "/api/v1/events",
        json={
            "name": "Torneo Yu-Gi-Oh",
            "event_date": past_date,
            "max_capacity": 20,
            "registration_price": 15000
        }
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert "fecha es inválida" in body["message"].lower()


def test_ca3_reject_invalid_capacity_zero_or_decimal():
    """CA3: Capacidad <= 0 o no entera rechaza la creación indicando RN-04."""
    future_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    
    # Caso capacidad <= 0
    res_zero = client.post(
        "/api/v1/events",
        json={
            "name": "Torneo Magic",
            "event_date": future_date,
            "max_capacity": 0,
            "registration_price": 10000
        }
    )
    assert res_zero.status_code == 400
    assert "RN-04" in res_zero.json()["message"]

    # Caso capacidad decimal
    res_float = client.post(
        "/api/v1/events",
        json={
            "name": "Torneo Magic",
            "event_date": future_date,
            "max_capacity": 10.5,
            "registration_price": 10000
        }
    )
    assert res_float.status_code == 400
    assert "RN-04" in res_float.json()["message"]


def test_ca4_reject_missing_fields_and_empty_payload():
    """CA4: Datos faltantes o entrada vacía devuelven HTTP 400 indicando los campos faltantes."""
    # Entrada completamente vacía {}
    res_empty = client.post("/api/v1/events", json={})
    assert res_empty.status_code == 400
    body = res_empty.json()
    assert body["success"] is False
    assert "Faltan campos obligatorios" in body["message"]
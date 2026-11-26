# test_hu018_enrollment.py
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from main import app
from app.core.payment_gateway import payment_gateway
from app.repositories.event import event_repository
from app.repositories.enrollment import enrollment_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_databases():
    event_repository.clear()
    enrollment_repository.clear()


def _create_sample_event(days_ahead: int = 5, max_capacity: int = 10, available_spots: int = 10, price: float = 30000.0):
    return event_repository.create({
        "name": "Torneo Abierto de Magic",
        "event_date": datetime.now(timezone.utc) + timedelta(days=days_ahead),
        "max_capacity": max_capacity,
        "available_spots": available_spots,
        "registration_price": price,
        "currency": "COP"
    })


def test_ca1_and_ca2_enroll_and_pay_approved():
    """CA1 & CA2: Solicita el pago por el precio del evento, registra 'confirmada' y resta 1 cupo (HTTP 201)."""
    event = _create_sample_event(available_spots=5, price=35000.0)

    with patch.object(payment_gateway, "process_payment", wraps=payment_gateway.process_payment) as spy_payment:
        response = client.post(
            "/api/v1/enrollments",
            json={
                "event_id": event["id"],
                "client_id": 101,
                "payment_method": "PSE"
            }
        )

    assert response.status_code == 201
    # CA1: Verifica que se invocó API Pagos con el precio exacto del evento
    spy_payment.assert_called_once_with(
        client_id=101,
        event_id=event["id"],
        amount=35000.0,
        payment_method="PSE"
    )
    # CA2: Verifica estado confirmada y descuento de cupo
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "confirmada"
    assert body["data"]["client_id"] == 101
    assert body["data"]["event_id"] == event["id"]
    assert body["data"]["available_spots"] == 4
    assert len(body["message"]) <= 200


def test_ca3_payment_rejected_does_not_enroll_or_reduce_spots():
    """CA3: Si el pago es rechazado, no registra inscripción y los cupos permanecen intactos (HTTP 409)."""
    event = _create_sample_event(available_spots=5, price=35000.0)

    response = client.post(
        "/api/v1/enrollments",
        json={
            "event_id": event["id"],
            "client_id": 102,
            "payment_method": "DECLINED"
        }
    )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert "rechazado" in body["message"].lower()
    # Verificar que no se creó registro y los cupos siguen en 5
    assert len(enrollment_repository.get_all()) == 0
    assert event_repository.get_by_id(event["id"])["available_spots"] == 5


def test_ca4_concurrent_enrollments_last_spot_rn04():
    """CA4: Si 5 clientes se inscriben simultáneamente cuando queda 1 cupo, solo 1 queda confirmada y cupos >= 0."""
    event = _create_sample_event(max_capacity=1, available_spots=1, price=20000.0)

    def attempt_enroll(cid: int):
        return client.post(
            "/api/v1/enrollments",
            json={
                "event_id": event["id"],
                "client_id": cid,
                "payment_method": "CARD"
            }
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(attempt_enroll, [201, 202, 203, 204, 205]))

    status_codes = [r.status_code for r in responses]
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 4
    assert event_repository.get_by_id(event["id"])["available_spots"] == 0
    assert len(enrollment_repository.get_all()) == 1


def test_ca5_quota_validation_authorized():
    """CA5: Evento existente, fecha futura y cupos >= 1 autoriza la inscripción (HTTP 200)."""
    event = _create_sample_event(days_ahead=3, available_spots=8)

    response = client.get(f"/api/v1/enrollments/availability/{event['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["result"] == "autorizada"
    assert body["data"]["available_spots"] == 8


def test_ca6_reject_when_no_available_spots():
    """CA6: Rechaza cuando el evento tiene 0 cupos disponibles indicando RN-04 (HTTP 409)."""
    event = _create_sample_event(days_ahead=3, available_spots=0)

    response = client.post(
        "/api/v1/enrollments",
        json={
            "event_id": event["id"],
            "client_id": 105,
            "payment_method": "NEQUI"
        }
    )
    assert response.status_code == 409
    assert "agotado" in response.json()["message"].lower()
    assert "RN-04" in response.json()["message"]


def test_ca7_reject_when_event_already_occurred():
    """CA7: Rechaza cuando el evento ya ocurrió (HTTP 409)."""
    event = _create_sample_event(days_ahead=-2, available_spots=10)

    response = client.post(
        "/api/v1/enrollments",
        json={
            "event_id": event["id"],
            "client_id": 106,
            "payment_method": "CARD"
        }
    )
    assert response.status_code == 409
    assert "ya ocurrió" in response.json()["message"].lower()


def test_ca8_reject_when_event_does_not_exist():
    """CA8: Rechaza cuando el evento no existe (HTTP 404)."""
    response = client.post(
        "/api/v1/enrollments",
        json={
            "event_id": 99999,
            "client_id": 107,
            "payment_method": "CARD"
        }
    )
    assert response.status_code == 404
    assert "no existe" in response.json()["message"].lower()


def test_reject_empty_payload_400():
    """DoD: Entrada vacía {} devuelve HTTP 400 indicando campos faltantes."""
    response = client.post("/api/v1/enrollments", json={})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "Faltan campos obligatorios" in body["message"]
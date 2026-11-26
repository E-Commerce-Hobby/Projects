# test_hu037_enrollment_cancel.py
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from main import app
from app.repositories.event import event_repository
from app.repositories.enrollment import enrollment_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_databases():
    event_repository.clear()
    enrollment_repository.clear()


def _seed_event_and_enrollment(hours_until_event: int = 48, status: str = "confirmada", available_spots: int = 15, max_capacity: int = 16, client_id: int = 10):
    event = event_repository.create({
        "name": "Torneo Regional Pokémon TCG",
        "event_date": datetime.now(timezone.utc) + timedelta(hours=hours_until_event),
        "max_capacity": max_capacity,
        "available_spots": available_spots,
        "registration_price": 20000.0,
        "currency": "COP"
    })
    enrollment = enrollment_repository.create({
        "event_id": event["id"],
        "client_id": client_id,
        "status": status,
        "cancelled_at": None
    })
    return event, enrollment


def test_ca1_and_ca2_cancel_enrollment_success_and_release_spot():
    """CA1 & CA2: Cancela inscripción confirmada con >= 24h de antelación y libera 1 cupo (HTTP 200)."""
    event, enrollment = _seed_event_and_enrollment(hours_until_event=30, available_spots=15, max_capacity=16, client_id=10)

    response = client.patch(
        f"/api/v1/enrollments/{enrollment['id']}/cancel",
        headers={"Authorization": "Bearer client-10"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "cancelado"
    assert body["data"]["available_spots"] == 16
    assert len(body["message"]) <= 200


def test_ca2_rn04_never_exceed_max_capacity():
    """RN-04: Al liberar cupo nunca supera max_capacity."""
    event, enrollment = _seed_event_and_enrollment(hours_until_event=30, available_spots=16, max_capacity=16, client_id=10)

    response = client.patch(
        f"/api/v1/enrollments/{enrollment['id']}/cancel",
        headers={"Authorization": "Bearer client-10"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["available_spots"] == 16


def test_ca3_reject_less_than_24_hours():
    """CA3: Rechaza con HTTP 409 si faltan menos de 24 horas para el evento."""
    _, enrollment = _seed_event_and_enrollment(hours_until_event=12, client_id=10)

    response = client.patch(
        f"/api/v1/enrollments/{enrollment['id']}/cancel",
        headers={"Authorization": "Bearer client-10"}
    )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert "24 horas" in body["message"]


def test_ca3_reject_already_cancelled():
    """CA3: Rechaza con HTTP 409 si la inscripción ya está cancelada."""
    _, enrollment = _seed_event_and_enrollment(hours_until_event=48, status="cancelado", client_id=10)

    response = client.patch(
        f"/api/v1/enrollments/{enrollment['id']}/cancel",
        headers={"Authorization": "Bearer client-10"}
    )

    assert response.status_code == 409
    assert "cancelado" in response.json()["message"].lower()


def test_ca4_reject_wrong_owner_forbidden():
    """CA4: Rechaza con HTTP 403 si la inscripción pertenece a otro cliente."""
    _, enrollment = _seed_event_and_enrollment(hours_until_event=48, client_id=10)

    response = client.patch(
        f"/api/v1/enrollments/{enrollment['id']}/cancel",
        headers={"Authorization": "Bearer client-99"}
    )

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert "permiso" in body["message"].lower()


def test_reject_unauthenticated_401():
    """DoD: Devuelve HTTP 401 si no hay token de autenticación."""
    _, enrollment = _seed_event_and_enrollment(hours_until_event=48, client_id=10)

    response = client.patch(f"/api/v1/enrollments/{enrollment['id']}/cancel")
    assert response.status_code == 401


def test_reject_not_found_404_empty_result():
    """DoD: Devuelve HTTP 404 cuando el ID de inscripción no existe."""
    response = client.patch(
        "/api/v1/enrollments/9999/cancel",
        headers={"Authorization": "Bearer client-10"}
    )
    assert response.status_code == 404
    assert response.json()["success"] is False
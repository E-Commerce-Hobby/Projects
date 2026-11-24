# tests/test_hu038_reminder.py
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from main import app
from app.core.email_gateway import email_gateway
from app.repositories.event import event_repository
from app.repositories.enrollment import enrollment_repository
from app.repositories.reminder import reminder_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    event_repository.clear()
    enrollment_repository.clear()
    reminder_repository.clear()
    email_gateway.reset()


def _seed_upcoming_event_with_enrollments(hours_ahead: int = 12, client_ids=(10, 20)):
    event = event_repository.create({
        "name": "Torneo Relámpago de Ajedrez",
        "event_date": datetime.now(timezone.utc) + timedelta(hours=hours_ahead),
        "max_capacity": 20,
        "available_spots": 18,
        "registration_price": 15000.0,
        "currency": "COP"
    })
    created_enrollments = []
    for cid in client_ids:
        enr = enrollment_repository.create({
            "event_id": event["id"],
            "client_id": cid,
            "status": "confirmada",
            "cancelled_at": None
        })
        created_enrollments.append(enr)
    return event, created_enrollments


def test_ca1_ca2_ca3_send_reminders_and_register_log():
    """CA1, CA2, CA3: Identifica evento próximo (<24h), envía correo con datos del evento y registra envío."""
    event, enrollments = _seed_upcoming_event_with_enrollments(hours_ahead=10, client_ids=(11, 22))

    response = client.post("/api/v1/events/reminders/dispatch", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["evaluated_events_count"] == 1
    assert body["data"]["reminders_sent_count"] == 2
    assert len(body["data"]["reminders"]) == 2

    for item in body["data"]["reminders"]:
        assert item["channel"] == "email"
        assert item["result"] == "enviado"
        assert item["sent_at"] is not None

    # Verifica que el correo incluye nombre del evento y fecha/hora
    assert len(email_gateway.sent_emails) == 2
    assert "Torneo Relámpago de Ajedrez" in email_gateway.sent_emails[0]["body"]


def test_ca4_do_not_resend_if_already_sent():
    """CA4: Si la inscripción ya tiene recordatorio enviado, no envía otro en revisiones posteriores."""
    _seed_upcoming_event_with_enrollments(hours_ahead=8, client_ids=(30,))

    first_run = client.post("/api/v1/events/reminders/dispatch", json={"force": True})
    assert first_run.status_code == 200
    assert first_run.json()["data"]["reminders_sent_count"] == 1
    assert len(email_gateway.sent_emails) == 1

    # Segunda revisión forzada: no debe volver a enviar
    second_run = client.post("/api/v1/events/reminders/dispatch", json={"force": True})
    assert second_run.status_code == 200
    assert second_run.json()["data"]["reminders_sent_count"] == 0
    assert len(email_gateway.sent_emails) == 1


def test_ca1_interval_one_hour_respected():
    """CA1: Si no ha transcurrido 1 hora desde la última revisión y force=False, no re-evalúa."""
    _seed_upcoming_event_with_enrollments(hours_ahead=6, client_ids=(40,))
    reminder_repository.set_last_check_at(datetime.now(timezone.utc) - timedelta(minutes=20))

    response = client.post("/api/v1/events/reminders/dispatch", json={"force": False})
    assert response.status_code == 200
    assert response.json()["data"]["evaluated_events_count"] == 0
    assert response.json()["data"]["reminders_sent_count"] == 0


def test_ca3_registers_failed_delivery_status():
    """CA3: Si el envío falla para un cliente, registra resultado 'fallido' con canal y fecha."""
    _seed_upcoming_event_with_enrollments(hours_ahead=5, client_ids=(50,))
    email_gateway.failing_client_ids.add(50)

    response = client.post("/api/v1/events/reminders/dispatch", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["reminders_sent_count"] == 0
    assert body["data"]["reminders_failed_count"] == 1
    assert body["data"]["reminders"][0]["result"] == "fallido"
    assert body["data"]["reminders"][0]["channel"] == "email"


def test_empty_or_no_upcoming_events_returns_200():
    """DoD: Sin eventos próximos o sin inscripciones confirmadas retorna HTTP 200 sin envíos."""
    response = client.post("/api/v1/events/reminders/dispatch", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["evaluated_events_count"] == 0
    assert body["data"]["reminders_sent_count"] == 0
    assert len(body["message"]) <= 200


def test_service_unavailable_returns_503():
    """DoD: Si el servicio externo de correo no está disponible, devuelve HTTP 503."""
    _seed_upcoming_event_with_enrollments(hours_ahead=4, client_ids=(60,))
    email_gateway.service_available = False

    response = client.post("/api/v1/events/reminders/dispatch", json={})
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert len(body["message"]) <= 200
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ReglaNegocioError
from app.repositories.inventory_alert_repository import InventoryAlertRepository
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_alert_service import InventoryAlertService
from main import app


@pytest.fixture
def entorno_alertas():
    inv_repo = InventoryRepository()
    alert_repo = InventoryAlertRepository()
    servicio = InventoryAlertService(inv_repo, alert_repo)
    return inv_repo, alert_repo, servicio


def test_ca1_revision_respeta_intervalo_de_60_minutos(entorno_alertas):
    inv_repo, _, servicio = entorno_alertas
    inv_repo.create_inventory(1, 1, 5)
    servicio.configure_min_stock(1, 10)

    t0 = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
    r1 = servicio.check_low_stock(now=t0)
    assert r1.executed is True
    assert r1.checked_products == 1

    # A los 30 minutos no debe volver a ejecutarse
    r2 = servicio.check_low_stock(now=t0 + timedelta(minutes=30))
    assert r2.executed is False
    assert r2.checked_products == 0

    # A los 60 minutos sí vuelve a ejecutarse
    r3 = servicio.check_low_stock(now=t0 + timedelta(minutes=60))
    assert r3.executed is True
    assert r3.checked_products == 1


def test_ca2_genera_alerta_pendiente_cuando_stock_menor_al_minimo(entorno_alertas):
    inv_repo, _, servicio = entorno_alertas
    inv_repo.create_inventory(1, 1, 4)
    servicio.configure_min_stock(1, 10)

    t0 = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
    res = servicio.check_low_stock(now=t0)

    assert len(res.generated_alerts) == 1
    alerta = res.generated_alerts[0]
    assert alerta.product_id == 1
    assert alerta.current_quantity == 4
    assert alerta.min_stock == 10
    assert alerta.status == "pendiente"
    assert alerta.created_at == t0

    consultables = servicio.list_alerts(status="pendiente")
    assert len(consultables) == 1
    assert consultables[0].id == alerta.id


def test_ca3_no_duplica_alerta_si_ya_existe_pendiente(entorno_alertas):
    inv_repo, _, servicio = entorno_alertas
    inv_repo.create_inventory(1, 1, 2)
    servicio.configure_min_stock(1, 10)

    t0 = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
    r1 = servicio.check_low_stock(now=t0)
    assert len(r1.generated_alerts) == 1

    # 60 minutos después sigue bajo el mínimo, pero ya tiene alerta pendiente
    r2 = servicio.check_low_stock(now=t0 + timedelta(minutes=60))
    assert r2.executed is True
    assert r2.generated_alerts == []
    assert len(servicio.list_alerts()) == 1


def test_ca4_no_genera_alerta_sin_minimo_configurado_y_sin_resultados(entorno_alertas):
    inv_repo, _, servicio = entorno_alertas
    inv_repo.create_inventory(2, 1, 0)  # Sin mínimo configurado

    res = servicio.check_low_stock()
    assert res.executed is True
    assert res.checked_products == 0
    assert res.generated_alerts == []
    assert servicio.list_alerts() == []


def test_rechazos_configuracion_minimo_producto_inexistente_o_valor_invalido(entorno_alertas):
    _, _, servicio = entorno_alertas

    with pytest.raises(ReglaNegocioError) as exc_404:
        servicio.configure_min_stock(999, 5)
    assert exc_404.value.status_code == 404
    assert len(exc_404.value.message) <= 200

    with pytest.raises(ReglaNegocioError) as exc_400:
        servicio.configure_min_stock(1, -1)
    assert exc_400.value.status_code == 400
    assert len(exc_400.value.message) <= 200


def test_endpoints_alertas_inventario_flujo_completo():
    client = TestClient(app)

    # Producto inexistente -> 404
    resp_404 = client.put("/api/v1/inventory/products/999/min-stock", json={"min_stock": 5})
    assert resp_404.status_code == 404

    # Configurar mínimo para producto 1 -> 200
    resp_cfg = client.put("/api/v1/inventory/products/1/min-stock", json={"min_stock": 100})
    assert resp_cfg.status_code == 200
    assert resp_cfg.json()["min_stock"] == 100

    # Ejecutar revisión forzada -> 200
    resp_check = client.post("/api/v1/inventory/alerts/check?force=true")
    assert resp_check.status_code == 200
    assert resp_check.json()["executed"] is True

    # Consultar alertas -> 200
    resp_list = client.get("/api/v1/inventory/alerts?estado=pendiente")
    assert resp_list.status_code == 200
    assert isinstance(resp_list.json(), list)

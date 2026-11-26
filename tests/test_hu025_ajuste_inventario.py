import pytest
from fastapi.testclient import TestClient

from app.core.errors import ReglaNegocioError
from app.domain.inventory import InventoryAdjustmentCreate, InventoryCreate
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService
from main import app


@pytest.fixture
def entorno_inventario():
    repo = InventoryRepository()
    servicio = InventoryService(repo)
    servicio.register_initial_inventory(
        InventoryCreate(product_id=1, location_id=1, quantity=50)
    )
    return repo, servicio


def test_ca1_ajustes_validos_actualizan_stock_y_registran_movimientos(entorno_inventario):
    repo, servicio = entorno_inventario

    # entrada: 50 + 10 = 60
    r_entrada = servicio.adjust_inventory(
        InventoryAdjustmentCreate(product_id=1, location_id=1, quantity=10, reason="entrada")
    )
    assert r_entrada.quantity == 60
    assert r_entrada.movement.previous_quantity == 50
    assert r_entrada.movement.new_quantity == 60

    # salida: 60 - 15 = 45
    r_salida = servicio.adjust_inventory(
        InventoryAdjustmentCreate(product_id=1, location_id=1, quantity=15, reason="salida")
    )
    assert r_salida.quantity == 45

    # pérdida: 45 - 5 = 40
    r_perdida = servicio.adjust_inventory(
        InventoryAdjustmentCreate(product_id=1, location_id=1, quantity=5, reason="pérdida")
    )
    assert r_perdida.quantity == 40

    # conteo físico: fija en 25
    r_conteo = servicio.adjust_inventory(
        InventoryAdjustmentCreate(
            product_id=1, location_id=1, quantity=25, reason="conteo físico"
        )
    )
    assert r_conteo.quantity == 25
    assert len(repo.list_movements(1, 1)) == 4


def test_ca2_rechaza_motivo_faltante_o_invalido(entorno_inventario):
    _, servicio = entorno_inventario

    for motivo in (None, "", "   ", "regalo"):
        with pytest.raises(ReglaNegocioError) as exc_info:
            servicio.adjust_inventory(
                InventoryAdjustmentCreate(
                    product_id=1, location_id=1, quantity=5, reason=motivo
                )
            )
        assert exc_info.value.status_code == 400
        assert "motivo" in exc_info.value.message.lower()
        assert len(exc_info.value.message) <= 200


def test_ca3_rechaza_saldo_negativo_sin_modificar_stock_e_informa_actual(entorno_inventario):
    repo, servicio = entorno_inventario

    with pytest.raises(ReglaNegocioError) as exc_info:
        servicio.adjust_inventory(
            InventoryAdjustmentCreate(
                product_id=1, location_id=1, quantity=60, reason="salida"
            )
        )

    assert exc_info.value.status_code == 409
    assert "50" in exc_info.value.message
    assert len(exc_info.value.message) <= 200
    assert repo.get_inventory(1, 1)["quantity"] == 50
    assert repo.list_movements(1, 1) == []


def test_rechaza_inventario_o_recurso_inexistente(entorno_inventario):
    _, servicio = entorno_inventario

    # Producto 2 en ubicación 2 no tiene inventario registrado
    with pytest.raises(ReglaNegocioError) as exc_info:
        servicio.adjust_inventory(
            InventoryAdjustmentCreate(
                product_id=2, location_id=2, quantity=5, reason="entrada"
            )
        )
    assert exc_info.value.status_code == 404
    assert len(exc_info.value.message) <= 200


def test_endpoint_ajuste_inventario_flujo_completo():
    client = TestClient(app)

    # Registrar inventario inicial en (2, 1) si no existe aún
    client.post(
        "/api/v1/inventory",
        json={"product_id": 2, "location_id": 1, "quantity": 20},
    )

    # CA1: ajuste válido -> 200
    resp_ok = client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": 2, "location_id": 1, "quantity": 5, "reason": "entrada"},
    )
    assert resp_ok.status_code == 200
    body_ok = resp_ok.json()
    assert body_ok["quantity"] >= 25
    assert body_ok["movement"]["reason"] == "entrada"

    # CA2: motivo vacío -> 400
    resp_400 = client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": 2, "location_id": 1, "quantity": 5, "reason": ""},
    )
    assert resp_400.status_code == 400

    # CA3: saldo negativo -> 409
    resp_409 = client.post(
        "/api/v1/inventory/adjustments",
        json={"product_id": 2, "location_id": 1, "quantity": 9999, "reason": "pérdida"},
    )
    assert resp_409.status_code == 409

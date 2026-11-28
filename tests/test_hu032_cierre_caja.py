import pytest
from fastapi.testclient import TestClient

from app.api.pos import get_pos_repository
from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.pos import SaleCreateRequest, SaleItemRequest
from app.repositories.pos_repository import PosRepository
from app.services.pos_service import PosService
from main import app


@pytest.fixture
def entorno_pos():
    repo = PosRepository()
    servicio = PosService(repo)
    return repo, servicio


def test_ca1_ca2_ca3_cierre_calcula_totales_guarda_cierre_y_bloquea_nuevas_ventas(entorno_pos):
    repo, servicio = entorno_pos

    # Registrar 2 ventas en efectivo y 1 con tarjeta en caja 1 (abierta)
    servicio.register_sale(
        SaleCreateRequest(
            cash_register_id=1,
            products=[SaleItemRequest(product_code="7701234567890", quantity=2)],
            payment_method="efectivo",
        )
    )  # 5000.0
    servicio.register_sale(
        SaleCreateRequest(
            cash_register_id=1,
            products=[SaleItemRequest(product_code="ABC123", quantity=1)],
            payment_method="tarjeta",
        )
    )  # 4200.0
    servicio.register_sale(
        SaleCreateRequest(
            cash_register_id=1,
            products=[SaleItemRequest(product_code="7701234567890", quantity=1)],
            payment_method="efectivo",
        )
    )  # 2500.0

    cierre = servicio.close_cash_register(1)

    # CA1 y CA2: totales por medio de pago y total general
    assert cierre.cash_register_id == 1
    assert cierre.cashier_id == 10
    assert cierre.sales_count == 3
    assert cierre.totals_by_payment_method == {
        "efectivo": 7500.0,
        "tarjeta": 4200.0,
    }
    assert cierre.general_total == 11700.0
    assert cierre.opened_at <= cierre.closed_at

    # CA3: cierre guardado y caja cerrada rechaza nuevas ventas (HU-012)
    assert cierre.status == "cerrada"
    assert len(repo.list_closings(1)) == 1
    assert repo.get_cash_register(1).is_open is False

    with pytest.raises(ReglaNegocioError) as exc_venta:
        servicio.register_sale(
            SaleCreateRequest(
                cash_register_id=1,
                products=[SaleItemRequest(product_code="7701234567890", quantity=1)],
            )
        )
    assert "caja abierta" in exc_venta.value.message.lower()


def test_cierre_sin_ventas_retorna_totales_vacios_y_cero(entorno_pos):
    _, servicio = entorno_pos

    cierre = servicio.close_cash_register(1)
    assert cierre.sales_count == 0
    assert cierre.totals_by_payment_method == {}
    assert cierre.general_total == 0.0
    assert cierre.status == "cerrada"


def test_ca4_rechaza_cierre_cuando_no_hay_caja_abierta(entorno_pos):
    _, servicio = entorno_pos

    # Caja 2 está cerrada en el seed
    with pytest.raises(ReglaNegocioError) as exc_info:
        servicio.close_cash_register(2)

    assert exc_info.value.status_code == 409
    assert "no hay una caja abierta" in exc_info.value.message.lower()
    assert len(exc_info.value.message) <= 200


def test_rechaza_cierre_de_caja_inexistente(entorno_pos):
    _, servicio = entorno_pos

    with pytest.raises(RecursoNoEncontradoError) as exc_info:
        servicio.close_cash_register(999)

    assert "no existe" in exc_info.value.mensaje.lower()
    assert len(exc_info.value.mensaje) <= 200


def test_endpoint_cierre_caja_flujo_completo():
    # Usar repositorio limpio para no afectar otros tests del módulo POS
    repo_aislado = PosRepository()
    app.dependency_overrides[get_pos_repository] = lambda: repo_aislado
    try:
        client = TestClient(app)

        # Registrar una venta en caja 1
        resp_venta = client.post(
            "/api/v1/pos/sales",
            json={
                "cash_register_id": 1,
                "products": [{"product_code": "7701234567890", "quantity": 2}],
                "payment_method": "transferencia",
            },
        )
        assert resp_venta.status_code == 201

        # Cerrar caja 1 -> 201
        resp_close = client.post("/api/v1/pos/cash-registers/1/close")
        assert resp_close.status_code == 201
        body = resp_close.json()
        assert body["totals_by_payment_method"] == {"transferencia": 5000.0}
        assert body["general_total"] == 5000.0
        assert body["status"] == "cerrada"

        # Intentar cerrar de nuevo -> 409 (CA4)
        resp_409 = client.post("/api/v1/pos/cash-registers/1/close")
        assert resp_409.status_code == 409

        # Caja inexistente -> 404
        resp_404 = client.post("/api/v1/pos/cash-registers/999/close")
        assert resp_404.status_code == 404
    finally:
        app.dependency_overrides.pop(get_pos_repository, None)

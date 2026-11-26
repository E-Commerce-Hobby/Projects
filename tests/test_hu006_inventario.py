from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.repositories import disponibilidad_repository
from app.repositories import sincronizacion_inventario_repository as repo
from main import app

cliente = TestClient(app)

INVENTARIO_BASE = {
    "PROD-001": [
        {"ubicacion": "Tienda Física", "disponible": 4, "reservado": 2},
        {"ubicacion": "Bodega Virtual", "disponible": 6, "reservado": 1},
    ],
    "PROD-002": [
        {"ubicacion": "Bodega Virtual", "disponible": 2, "reservado": 0},
    ],
}


@pytest.fixture(autouse=True)
def limpiar_estado_inventario():
    """Restaura los almacenes en memoria antes y después de cada prueba."""
    disponibilidad_repository.inventario_ubicaciones_db.clear()
    disponibilidad_repository.inventario_ubicaciones_db.update(deepcopy(INVENTARIO_BASE))
    repo.notificaciones_enviadas_db.clear()
    repo.notificaciones_pendientes_db.clear()
    repo.resultados_actualizacion_db.clear()
    repo.movimientos_inventario_db.clear()
    repo.contador_notificacion_id = 1
    repo.contador_resultado_id = 1
    repo.contador_movimiento_id = 1
    yield


def test_ca1_notificacion_venta_valida_envia_a_inventario():
    """CA1: Venta virtual o POS con líneas válidas se envía a Inventario."""
    respuesta = cliente.post(
        "/api/v1/inventario/notificaciones-venta",
        json={
            "id_venta": "VEN-001",
            "canal": "POS",
            "lineas": [
                {"id_producto": "PROD-001", "ubicacion": "Tienda Física", "cantidad": 2},
                {"id_producto": "PROD-002", "ubicacion": "Bodega Virtual", "cantidad": 1},
            ],
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    assert cuerpo["data"]["id_venta"] == "VEN-001"
    assert cuerpo["data"]["canal"] == "POS"
    assert cuerpo["data"]["estado_envio"] == "enviada"
    assert len(cuerpo["data"]["lineas"]) == 2
    assert len(repo.notificaciones_enviadas_db) == 1


def test_ca2_rechaza_notificacion_sin_lineas_o_cantidad_invalida():
    """CA2: Rechaza con HTTP 400 sin líneas o con cantidad <= 0 sin enviar nada."""
    res_vacia = cliente.post(
        "/api/v1/inventario/notificaciones-venta",
        json={"id_venta": "VEN-002", "canal": "virtual", "lineas": []},
    )
    assert res_vacia.status_code == 400
    assert res_vacia.json()["success"] is False

    res_cero = cliente.post(
        "/api/v1/inventario/notificaciones-venta",
        json={
            "id_venta": "VEN-003",
            "canal": "virtual",
            "lineas": [
                {"id_producto": "PROD-001", "cantidad": 1},
                {"id_producto": "PROD-002", "cantidad": 0},
            ],
        },
    )
    assert res_cero.status_code == 400
    assert "Línea 2" in res_cero.json()["message"]
    assert len(repo.notificaciones_enviadas_db) == 0


def test_ca3_fallo_inventario_guarda_notificacion_pendiente_para_reintento():
    """CA3: Si Inventario no confirma, queda pendiente (HU-027) y retorna 503."""
    respuesta = cliente.post(
        "/api/v1/inventario/notificaciones-venta",
        json={
            "id_venta": "VEN-004",
            "canal": "virtual",
            "lineas": [{"id_producto": "PROD-001", "cantidad": 1}],
            "simular_fallo_inventario": True,
        },
    )

    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["success"] is False
    pendientes = repo.listar_notificaciones_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0]["id_venta"] == "VEN-004"
    assert pendientes[0]["estado_envio"] == "pendiente"


def test_ca4_descuento_atomico_exitoso_y_cantidades_resultantes():
    """CA4: Descuenta todas las líneas en bloque y retorna cantidades resultantes."""
    respuesta = cliente.post(
        "/api/v1/inventario/descuentos",
        json={
            "id_venta": "VEN-005",
            "canal": "POS",
            "lineas": [
                {"id_producto": "PROD-001", "ubicacion": "Tienda Física", "cantidad": 2},
                {"id_producto": "PROD-002", "ubicacion": "Bodega Virtual", "cantidad": 1},
            ],
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    assert cuerpo["data"]["resultado"] == "exitoso"
    actualizados = cuerpo["data"]["inventario_actualizado"]
    assert actualizados[0]["cantidad_resultante"] == 2
    assert actualizados[1]["cantidad_resultante"] == 1
    assert repo.obtener_registro_ubicacion("PROD-001", "Tienda Física")["disponible"] == 2
    assert repo.obtener_registro_ubicacion("PROD-002", "Bodega Virtual")["disponible"] == 1


def test_ca5_stock_insuficiente_no_descuenta_ninguna_linea_rn01():
    """CA5 (RN-01): Todo o nada; si falla una línea no descuenta ninguna y registra fallido."""
    respuesta = cliente.post(
        "/api/v1/inventario/descuentos",
        json={
            "id_venta": "VEN-006",
            "canal": "virtual",
            "lineas": [
                {"id_producto": "PROD-001", "ubicacion": "Tienda Física", "cantidad": 2},
                {"id_producto": "PROD-002", "ubicacion": "Bodega Virtual", "cantidad": 50},
            ],
        },
    )

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["success"] is False
    assert "RN-01" in cuerpo["message"]
    # La primera línea NO se descontó
    assert repo.obtener_registro_ubicacion("PROD-001", "Tienda Física")["disponible"] == 4
    resultados = repo.listar_resultados_actualizacion("VEN-006")
    assert len(resultados) == 1
    assert resultados[0]["resultado"] == "fallido"


def test_ca6_registra_resultados_exitoso_y_fallido_con_fecha_hora():
    """CA6: Todo intento queda registrado con id_venta, resultado y fecha_hora."""
    cliente.post(
        "/api/v1/inventario/descuentos",
        json={
            "id_venta": "VEN-OK",
            "canal": "virtual",
            "lineas": [{"id_producto": "PROD-001", "ubicacion": "Bodega Virtual", "cantidad": 1}],
        },
    )
    cliente.post(
        "/api/v1/inventario/descuentos",
        json={
            "id_venta": "VEN-FAIL",
            "canal": "virtual",
            "lineas": [{"id_producto": "PROD-002", "ubicacion": "Bodega Virtual", "cantidad": 99}],
        },
    )

    respuesta = cliente.get("/api/v1/inventario/resultados")
    assert respuesta.status_code == 200
    datos = respuesta.json()["data"]
    assert len(datos) == 2
    assert {r["id_venta"]: r["resultado"] for r in datos} == {
        "VEN-OK": "exitoso",
        "VEN-FAIL": "fallido",
    }
    assert all("fecha_hora" in r and r["fecha_hora"] for r in datos)


def test_ca7_registro_movimiento_con_campos_obligatorios():
    """CA7: Registra movimiento con producto, ubicación, cantidad (+/-), fecha y canal."""
    respuesta = cliente.post(
        "/api/v1/inventario/movimientos",
        json={
            "id_producto": "PROD-001",
            "ubicacion": "Tienda Física",
            "cantidad": 5,
            "canal": "administración",
            "tipo": "ajuste",
            "id_referencia": "AJ-001",
        },
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()["data"]
    assert datos["id_producto"] == "PROD-001"
    assert datos["ubicacion"] == "Tienda Física"
    assert datos["cantidad"] == 5
    assert datos["canal"] == "administración"
    assert datos["fecha_hora"]


def test_ca8_movimientos_no_permiten_modificar_ni_eliminar():
    """CA8: La API no ofrece PUT, PATCH ni DELETE sobre movimientos."""
    assert cliente.put("/api/v1/inventario/movimientos", json={}).status_code == 405
    assert cliente.patch("/api/v1/inventario/movimientos", json={}).status_code == 405
    assert cliente.delete("/api/v1/inventario/movimientos").status_code == 405


def test_ca9_consulta_movimientos_por_rango_ordenados_descendente_y_sin_resultados():
    """CA9: Filtra por producto y rango de fechas, orden más reciente a más antiguo."""
    t1 = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    t2 = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    t3 = datetime.now(timezone.utc).isoformat()

    repo.guardar_movimiento({
        "id_producto": "PROD-001", "ubicacion": "Tienda Física",
        "cantidad": -1, "fecha_hora": t1, "canal": "POS", "tipo": "venta", "id_referencia": "V1",
    })
    repo.guardar_movimiento({
        "id_producto": "PROD-001", "ubicacion": "Tienda Física",
        "cantidad": 3, "fecha_hora": t2, "canal": "administración", "tipo": "ajuste", "id_referencia": "A1",
    })
    repo.guardar_movimiento({
        "id_producto": "PROD-001", "ubicacion": "Bodega Virtual",
        "cantidad": -2, "fecha_hora": t3, "canal": "virtual", "tipo": "venta", "id_referencia": "V2",
    })

    res = cliente.get(
        "/api/v1/inventario/movimientos",
        params={"id_producto": "PROD-001", "fecha_inicio": t1, "fecha_fin": t3},
    )
    assert res.status_code == 200
    movimientos = res.json()["data"]
    assert [m["id_movimiento"] for m in movimientos] == [3, 2, 1]

    # Caso sin resultados (rango futuro)
    futuro = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    res_vacio = cliente.get(
        "/api/v1/inventario/movimientos",
        params={"id_producto": "PROD-001", "fecha_inicio": futuro},
    )
    assert res_vacio.status_code == 200
    assert res_vacio.json()["data"] == []


def test_rechazos_entrada_vacia_y_producto_inexistente():
    """DoD: Entrada vacía retorna 400 y producto inexistente retorna 404."""
    assert cliente.post("/api/v1/inventario/notificaciones-venta", json={}).status_code == 400
    assert cliente.get("/api/v1/inventario/movimientos", params={"id_producto": "PROD-999"}).status_code == 404

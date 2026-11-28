from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.productos import router as productos_router
from app.core.errors import ReglaNegocioError
from app.domain.producto import ProductoActualizacion, ProductoRegistro
from app.repositories.producto_repository import ProductoRepository
from app.services.producto_service import ProductoService


def _crear_app_prueba() -> FastAPI:
    app_test = FastAPI()
    app_test.include_router(productos_router, prefix="/api/v1")
    return app_test


def _crear_servicio() -> tuple[ProductoService, ProductoRepository]:
    repo = ProductoRepository()
    return ProductoService(repo), repo


def test_ca1_actualiza_solo_campos_enviados() -> None:
    servicio, _ = _crear_servicio()
    creado = servicio.registrar(
        ProductoRegistro(
            codigo="MIN-100",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm", "material": "resina"},
            estado="activo",
        )
    )

    actualizado = servicio.actualizar(
        creado.id,
        ProductoActualizacion(estado="inactivo"),
    )

    assert actualizado.id == creado.id
    assert actualizado.codigo == "MIN-100"
    assert actualizado.categoria == "miniaturas"
    assert actualizado.caracteristicas == {"escala": "28mm", "material": "resina"}
    assert actualizado.estado == "inactivo"


def test_ca2_rechaza_codigo_duplicado_rn02_sin_modificar() -> None:
    servicio, repo = _crear_servicio()
    p1 = servicio.registrar(
        ProductoRegistro(
            codigo="MIN-201",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )
    p2 = servicio.registrar(
        ProductoRegistro(
            codigo="MIN-202",
            categoria="miniaturas",
            caracteristicas={"escala": "32mm"},
            estado="activo",
        )
    )

    try:
        servicio.actualizar(
            p2.id,
            ProductoActualizacion(codigo="MIN-201", estado="inactivo"),
        )
        assert False, "Debió lanzar ReglaNegocioError por RN-02"
    except ReglaNegocioError as exc:
        assert exc.status_code == 409
        assert len(exc.message) <= 200

    actual_p2 = repo.obtener_por_id(p2.id)
    assert actual_p2 is not None
    assert actual_p2.codigo == "MIN-202"
    assert actual_p2.estado == "activo"
    assert repo.obtener_por_id(p1.id).codigo == "MIN-201"


def test_ca3_rechaza_categoria_inexistente_sin_modificar() -> None:
    servicio, repo = _crear_servicio()
    creado = servicio.registrar(
        ProductoRegistro(
            codigo="MIN-301",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )

    try:
        servicio.actualizar(
            creado.id,
            ProductoActualizacion(categoria="no-existe", estado="inactivo"),
        )
        assert False, "Debió lanzar ReglaNegocioError por categoría inexistente"
    except ReglaNegocioError as exc:
        assert exc.status_code == 400
        assert len(exc.message) <= 200

    actual = repo.obtener_por_id(creado.id)
    assert actual is not None
    assert actual.categoria == "miniaturas"
    assert actual.estado == "activo"


def test_ca4_producto_no_existe_retorna_404() -> None:
    servicio, _ = _crear_servicio()

    try:
        servicio.actualizar(
            uuid4(),
            ProductoActualizacion(estado="inactivo"),
        )
        assert False, "Debió lanzar ReglaNegocioError 404"
    except ReglaNegocioError as exc:
        assert exc.status_code == 404
        assert len(exc.message) <= 200


def test_endpoint_patch_flujo_y_payload_vacio() -> None:
    client = TestClient(_crear_app_prueba())

    resp_crear = client.post(
        "/api/v1/productos",
        json={
            "codigo": "JUE-401",
            "categoria": "juegos",
            "caracteristicas": {"jugadores": "2-4"},
            "estado": "activo",
        },
    )
    assert resp_crear.status_code == 201
    prod_id = resp_crear.json()["data"]["id"]

    # Payload vacío -> rechazado por validación (422 en app limpia o 400 con handler global)
    resp_vacio = client.patch(f"/api/v1/productos/{prod_id}", json={})
    assert resp_vacio.status_code in (400, 422)

    # Actualización válida -> 200
    resp_ok = client.patch(
        f"/api/v1/productos/{prod_id}",
        json={"estado": "inactivo"},
    )
    assert resp_ok.status_code == 200
    cuerpo = resp_ok.json()
    assert cuerpo["success"] is True
    assert cuerpo["data"]["estado"] == "inactivo"
    assert cuerpo["data"]["codigo"] == "JUE-401"

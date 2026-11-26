from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.caracteristica_categoria import (
    AsociarCaracteristicasRequest,
    CaracteristicaAsociacionItem,
)
from app.domain.producto import ProductoRegistro
from app.repositories.caracteristica_categoria_repository import (
    CaracteristicaCategoriaRepository,
)
from app.repositories.producto_repository import ProductoRepository
from app.services.caracteristica_categoria_service import (
    CaracteristicaCategoriaService,
)
from main import app


@pytest.fixture
def repos_y_servicio():
    prod_repo = ProductoRepository()
    car_repo = CaracteristicaCategoriaRepository()
    servicio = CaracteristicaCategoriaService(prod_repo, car_repo)
    return prod_repo, car_repo, servicio


def test_ca1_consultar_caracteristicas_categoria(repos_y_servicio):
    prod_repo, _, servicio = repos_y_servicio
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="MIN-101",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )

    resultado = servicio.consultar_caracteristicas_categoria(producto.id)
    nombres = [c.nombre for c in resultado.caracteristicas]
    assert resultado.categoria == "miniaturas"
    assert "escala" in nombres
    assert "material" in nombres


def test_ca1_categoria_sin_caracteristicas_definidas(repos_y_servicio):
    prod_repo, _, servicio = repos_y_servicio
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="SIN-001",
            categoria="categoria_sin_definiciones",
            caracteristicas={"base": "estandar"},
            estado="activo",
        )
    )

    resultado = servicio.consultar_caracteristicas_categoria(producto.id)
    assert resultado.caracteristicas == []


def test_ca2_asociar_caracteristicas_validas(repos_y_servicio):
    prod_repo, _, servicio = repos_y_servicio
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="PINT-201",
            categoria="pinturas",
            caracteristicas={"acabado": "mate"},
            estado="activo",
        )
    )

    req = AsociarCaracteristicasRequest(
        caracteristicas=[
            CaracteristicaAsociacionItem(nombre="acabado", valor="satinado"),
            CaracteristicaAsociacionItem(nombre="volumen_ml", valor=18),
        ]
    )
    resp = servicio.asociar_caracteristicas(producto.id, req)
    assert resp.caracteristicas_asociadas == {"acabado": "satinado", "volumen_ml": 18}
    assert resp.caracteristicas_producto["volumen_ml"] == 18


def test_ca3_rechaza_toda_operacion_si_alguna_no_pertenece(repos_y_servicio):
    prod_repo, _, servicio = repos_y_servicio
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="JUEG-301",
            categoria="juegos",
            caracteristicas={"jugadores": "2-4"},
            estado="activo",
        )
    )

    req = AsociarCaracteristicasRequest(
        caracteristicas=[
            CaracteristicaAsociacionItem(nombre="jugadores", valor="1-5"),
            CaracteristicaAsociacionItem(nombre="escala", valor="28mm"),
        ]
    )

    with pytest.raises(ReglaNegocioError) as exc:
        servicio.asociar_caracteristicas(producto.id, req)

    assert exc.value.status_code == 400
    assert "escala" in exc.value.message
    assert len(exc.value.message) <= 200
    assert producto.caracteristicas["jugadores"] == "2-4"


def test_ca4_producto_no_existe_en_consulta_y_asociacion(repos_y_servicio):
    _, _, servicio = repos_y_servicio
    id_inexistente = uuid4()

    with pytest.raises(RecursoNoEncontradoError):
        servicio.consultar_caracteristicas_categoria(id_inexistente)

    with pytest.raises(RecursoNoEncontradoError):
        servicio.asociar_caracteristicas(
            id_inexistente,
            AsociarCaracteristicasRequest(
                caracteristicas=[CaracteristicaAsociacionItem(nombre="escala", valor="28mm")]
            ),
        )


def test_endpoint_entrada_vacia_retorna_400():
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/productos/{uuid4()}/caracteristicas",
        json={"caracteristicas": []},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert len(body["message"]) <= 200

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.imagen_producto import MAX_TAMANO_IMAGEN_BYTES
from app.domain.producto import ProductoRegistro
from app.repositories.imagen_producto_repository import ImagenProductoRepository
from app.repositories.producto_repository import ProductoRepository
from app.services.imagen_producto_service import ImagenProductoService
from main import app

JPG_VALIDO = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG_VALIDO = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP_VALIDO = b"RIFF\x24\x00\x00\x00WEBP" + b"\x00" * 32


@pytest.fixture
def entorno_imagenes():
    prod_repo = ProductoRepository()
    img_repo = ImagenProductoRepository()
    servicio = ImagenProductoService(prod_repo, img_repo)
    return prod_repo, img_repo, servicio


def test_ca1_asociar_imagenes_jpg_png_webp_exitoso(entorno_imagenes):
    prod_repo, img_repo, servicio = entorno_imagenes
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="MIN-501",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )

    img_jpg = servicio.asociar_imagen(producto.id, JPG_VALIDO, "foto.jpg")
    img_png = servicio.asociar_imagen(producto.id, PNG_VALIDO, "foto.png")
    img_webp = servicio.asociar_imagen(producto.id, WEBP_VALIDO, "foto.webp")

    assert img_jpg.id is not None
    assert img_jpg.producto_id == producto.id
    assert img_jpg.formato == "JPG"
    assert img_png.formato == "PNG"
    assert img_webp.formato == "WEBP"
    assert len(img_repo.listar_por_producto(producto.id)) == 3


def test_ca2_rechaza_formato_invalido_o_extension_falsa(entorno_imagenes):
    prod_repo, img_repo, servicio = entorno_imagenes
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="MIN-502",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )

    contenido_falso = b"esto no es una imagen real"
    with pytest.raises(ReglaNegocioError) as exc_info:
        servicio.asociar_imagen(producto.id, contenido_falso, "falsa.jpg")

    assert exc_info.value.status_code == 400
    assert "formato" in exc_info.value.message.lower()
    assert len(exc_info.value.message) <= 200
    assert img_repo.listar_por_producto(producto.id) == []


def test_ca2_rechaza_imagen_mayor_a_5mb(entorno_imagenes):
    prod_repo, img_repo, servicio = entorno_imagenes
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="MIN-503",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )

    contenido_grande = PNG_VALIDO + (b"\x00" * (MAX_TAMANO_IMAGEN_BYTES + 1))
    with pytest.raises(ReglaNegocioError) as exc_info:
        servicio.asociar_imagen(producto.id, contenido_grande, "grande.png")

    assert exc_info.value.status_code == 400
    assert "tamaño" in exc_info.value.message.lower()
    assert len(exc_info.value.message) <= 200
    assert img_repo.listar_por_producto(producto.id) == []


def test_ca2_rechaza_archivo_vacio(entorno_imagenes):
    prod_repo, img_repo, servicio = entorno_imagenes
    producto = prod_repo.crear(
        ProductoRegistro(
            codigo="MIN-504",
            categoria="miniaturas",
            caracteristicas={"escala": "28mm"},
            estado="activo",
        )
    )

    with pytest.raises(ReglaNegocioError) as exc_info:
        servicio.asociar_imagen(producto.id, b"", "vacio.png")

    assert exc_info.value.status_code == 400
    assert len(exc_info.value.message) <= 200
    assert img_repo.listar_por_producto(producto.id) == []


def test_ca3_rechaza_producto_inexistente(entorno_imagenes):
    _, _, servicio = entorno_imagenes
    with pytest.raises(RecursoNoEncontradoError) as exc_info:
        servicio.asociar_imagen(uuid4(), PNG_VALIDO, "foto.png")

    assert "no existe" in exc_info.value.mensaje.lower()
    assert len(exc_info.value.mensaje) <= 200


def test_endpoint_asociar_imagen_flujo_completo():
    client = TestClient(app)

    # Crear producto
    resp_prod = client.post(
        "/api/v1/productos",
        json={
            "codigo": f"IMG-{uuid4().hex[:8].upper()}",
            "categoria": "miniaturas",
            "caracteristicas": {"escala": "32mm"},
            "estado": "activo",
        },
    )
    assert resp_prod.status_code == 201
    prod_id = resp_prod.json()["data"]["id"]

    # CA1: Subir imagen válida -> 201
    resp_ok = client.post(
        f"/api/v1/productos/{prod_id}/imagenes",
        files={"archivo": ("dragon.png", PNG_VALIDO, "image/png")},
    )
    assert resp_ok.status_code == 201
    body_ok = resp_ok.json()
    assert body_ok["success"] is True
    assert body_ok["data"]["producto_id"] == prod_id
    assert body_ok["data"]["formato"] == "PNG"
    assert body_ok["data"]["id"]

    # CA2: Archivo vacío -> 400
    resp_vacio = client.post(
        f"/api/v1/productos/{prod_id}/imagenes",
        files={"archivo": ("vacio.png", b"", "image/png")},
    )
    assert resp_vacio.status_code == 400
    assert resp_vacio.json()["success"] is False

    # CA3: Producto inexistente -> 404
    resp_404 = client.post(
        f"/api/v1/productos/{uuid4()}/imagenes",
        files={"archivo": ("dragon.png", PNG_VALIDO, "image/png")},
    )
    assert resp_404.status_code == 404
    assert resp_404.json()["success"] is False


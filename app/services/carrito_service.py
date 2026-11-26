from typing import Any
from app.core.errors import ReglaNegocioError
from app.repositories import carrito_repository


def _es_entero_positivo(valor: Any) -> bool:
    """Valida que el valor sea un entero real (no bool, no float) >= 1."""
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 1


def agregar_producto_carrito(id_producto: str, cantidad: Any) -> dict:
    # CA4: Cantidad <= 0 o no entera
    if not _es_entero_positivo(cantidad):
        raise ReglaNegocioError(
            message="Cantidad inválida: debe ser un número entero mayor o igual a 1.",
            status_code=400,
            data=["cantidad"],
        )

    # CA3: Producto no existe en el catálogo
    producto = carrito_repository.obtener_producto_catalogo(id_producto)
    if producto is None:
        raise ReglaNegocioError(
            message="El producto solicitado no existe en el catálogo.",
            status_code=404,
            data=["id_producto"],
        )

    # CA1 y CA2: Si ya existe en el carrito, suma las cantidades en una sola línea
    linea_existente = carrito_repository.obtener_linea_carrito(id_producto)
    nueva_cantidad = (linea_existente["cantidad"] + cantidad) if linea_existente else cantidad

    carrito_repository.guardar_linea_carrito(
        id_producto=producto["id_producto"],
        nombre=producto["nombre"],
        precio_unitario=producto["precio"],
        cantidad=nueva_cantidad,
    )

    return carrito_repository.construir_carrito_completo()


def modificar_cantidad_carrito(id_producto: str, nueva_cantidad: Any) -> dict:
    # CA7: Cantidad <= 0 o no entera -> indicar que use la eliminación
    if not _es_entero_positivo(nueva_cantidad):
        raise ReglaNegocioError(
            message="Cantidad inválida. Para quitar el producto del carrito debe usar la eliminación.",
            status_code=400,
            data=["nueva_cantidad"],
        )

    # CA6: Producto no está en el carrito
    linea_existente = carrito_repository.obtener_linea_carrito(id_producto)
    if linea_existente is None:
        raise ReglaNegocioError(
            message="El producto no se encuentra en el carrito.",
            status_code=404,
            data=["id_producto"],
        )

    # CA5: Reemplaza la cantidad y recalcula el total
    carrito_repository.guardar_linea_carrito(
        id_producto=linea_existente["id_producto"],
        nombre=linea_existente["nombre"],
        precio_unitario=linea_existente["precio_unitario"],
        cantidad=nueva_cantidad,
    )

    return carrito_repository.construir_carrito_completo()


def eliminar_producto_carrito(id_producto: str) -> dict:
    # CA9: Producto no está en el carrito
    linea_existente = carrito_repository.obtener_linea_carrito(id_producto)
    if linea_existente is None:
        raise ReglaNegocioError(
            message="El producto no se encuentra en el carrito.",
            status_code=404,
            data=["id_producto"],
        )

    # CA8 y CA10: Quita la línea completa (si era el único, queda con 0 líneas y total 0)
    carrito_repository.eliminar_linea_carrito(id_producto)
    return carrito_repository.construir_carrito_completo()


def obtener_carrito_actual() -> dict:
    return carrito_repository.construir_carrito_completo()

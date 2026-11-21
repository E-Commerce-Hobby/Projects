# Catálogo base en memoria con precios para pruebas funcionales de HU-009
catalogo_productos_db: dict[str, dict] = {
    "PROD-001": {"id_producto": "PROD-001", "nombre": "Set Miniaturas Dark Angels", "precio": 150000.0},
    "PROD-002": {"id_producto": "PROD-002", "nombre": "Pintura Citadel Caliban Green", "precio": 25000.0},
    "PROD-003": {"id_producto": "PROD-003", "nombre": "Pincel Detalle Fino", "precio": 18000.0},
}

# Carrito en memoria: { id_producto: {"id_producto", "nombre", "precio_unitario", "cantidad"} }
carrito_db: dict[str, dict] = {}


def obtener_producto_catalogo(id_producto: str) -> dict | None:
    return catalogo_productos_db.get(id_producto)


def obtener_linea_carrito(id_producto: str) -> dict | None:
    return carrito_db.get(id_producto)


def guardar_linea_carrito(id_producto: str, nombre: str, precio_unitario: float, cantidad: int) -> None:
    carrito_db[id_producto] = {
        "id_producto": id_producto,
        "nombre": nombre,
        "precio_unitario": precio_unitario,
        "cantidad": cantidad,
    }


def eliminar_linea_carrito(id_producto: str) -> None:
    carrito_db.pop(id_producto, None)


def construir_carrito_completo() -> dict:
    """Construye las líneas del carrito y recalcula el valor total."""
    lineas = []
    valor_total = 0.0

    for item in carrito_db.values():
        subtotal = round(item["precio_unitario"] * item["cantidad"], 2)
        valor_total = round(valor_total + subtotal, 2)
        lineas.append(
            {
                "id_producto": item["id_producto"],
                "nombre": item["nombre"],
                "precio_unitario": item["precio_unitario"],
                "cantidad": item["cantidad"],
                "subtotal": subtotal,
            }
        )

    return {
        "lineas": lineas,
        "valor_total": valor_total,
    }
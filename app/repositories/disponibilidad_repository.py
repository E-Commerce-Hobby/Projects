# Productos registrados en el catálogo (PROD-003 existe pero no tiene inventario registrado -> CA2)
catalogo_existente_db: set[str] = {"PROD-001", "PROD-002", "PROD-003"}

# Inventario por producto y ubicación (las unidades 'reservado' NO cuentan en la disponibilidad)
inventario_ubicaciones_db: dict[str, list[dict]] = {
    "PROD-001": [
        {"ubicacion": "Tienda Física", "disponible": 4, "reservado": 2},
        {"ubicacion": "Bodega Virtual", "disponible": 6, "reservado": 1},
    ],
    "PROD-002": [
        {"ubicacion": "Bodega Virtual", "disponible": 2, "reservado": 0},
    ],
}


def producto_existe(id_producto: str) -> bool:
    return id_producto in catalogo_existente_db


def obtener_inventario_por_ubicaciones(id_producto: str) -> list[dict]:
    """Retorna el listado de ubicaciones con stock del producto (vacío si no tiene registros)."""
    return inventario_ubicaciones_db.get(id_producto, [])
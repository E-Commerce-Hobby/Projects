from datetime import datetime, timedelta, timezone

# Simulación del módulo Clientes (API Usuarios)
clientes_db: dict[str, dict] = {
    "CLI-001": {"id_cliente": "CLI-001", "nombre": "Cliente Activo", "estado": "activo"},
    "CLI-002": {"id_cliente": "CLI-002", "nombre": "Cliente Inactivo", "estado": "inactivo"},
}

# Precios unitarios en COP (sin decimales)
precios_productos_db: dict[str, int] = {
    "PROD-001": 100000,
    "PROD-002": 50000,
    "PROD-003": 25000,
}

# Almacenamiento en memoria de órdenes creadas
ordenes_db: dict[str, dict] = {}


def obtener_cliente(id_cliente: str) -> dict | None:
    """Consulta el cliente en el módulo Clientes."""
    return clientes_db.get(id_cliente)


def obtener_precio_producto(id_producto: str) -> int | None:
    """Retorna el precio unitario en COP del producto o None si no existe."""
    return precios_productos_db.get(id_producto)


def obtener_descuentos_disponibles() -> dict[str, dict]:
    """Descuentos con vigencias dinámicas respecto a la fecha/hora actual (UTC)."""
    ahora = datetime.now(timezone.utc)
    return {
        "DESC10": {
            "codigo": "DESC10",
            "tipo": "porcentaje",
            "valor": 10,
            "vigencia_inicio": ahora - timedelta(days=1),
            "vigencia_fin": ahora + timedelta(days=30),
        },
        "DESC_VENCIDO": {
            "codigo": "DESC_VENCIDO",
            "tipo": "fijo",
            "valor": 20000,
            "vigencia_inicio": ahora - timedelta(days=15),
            "vigencia_fin": ahora - timedelta(days=1),
        },
        "MEGA_BONO": {
            "codigo": "MEGA_BONO",
            "tipo": "fijo",
            "valor": 500000,
            "vigencia_inicio": ahora - timedelta(days=1),
            "vigencia_fin": ahora + timedelta(days=30),
        },
    }


def guardar_orden(orden: dict) -> dict:
    ordenes_db[orden["id_orden"]] = orden
    return orden


def obtener_orden(id_orden: str) -> dict | None:
    return ordenes_db.get(id_orden)
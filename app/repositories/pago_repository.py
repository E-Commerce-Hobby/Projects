from app.repositories.orden_repository import obtener_orden

# Órdenes de prueba en memoria para pruebas directas en Swagger si no se creó una orden previa en HU-010
ordenes_prueba_pago_db: dict[str, dict] = {
    "ORD-001": {
        "id_orden": "ORD-001",
        "id_cliente": "CLI-001",
        "estado": "pendiente de pago",
        "total": 150000,
    },
    "ORD-002": {
        "id_orden": "ORD-002",
        "id_cliente": "CLI-001",
        "estado": "pagada",
        "total": 80000,
    },
}

# Almacén en memoria de intentos de pago (clave -> id_intento)
intentos_pago_db: dict[str, dict] = {}


def consultar_orden_para_pago(id_orden: str) -> dict | None:
    """
    Consulta primero el módulo real de Órdenes (HU-010: obtener_orden).
    Si no existe allí, busca en las órdenes de prueba locales.
    """
    orden_real = obtener_orden(id_orden)
    if orden_real is not None:
        return orden_real
    return ordenes_prueba_pago_db.get(id_orden)


def guardar_intento_pago(intento: dict) -> dict:
    """Registra o actualiza un intento de pago en memoria (CA2)."""
    intentos_pago_db[intento["id_intento"]] = intento
    return intento


def obtener_intento_pago(id_intento: str) -> dict | None:
    """Busca un intento de pago por su identificador."""
    return intentos_pago_db.get(id_intento)


def listar_intentos_por_orden(id_orden: str) -> list[dict]:
    """Retorna todos los intentos de pago asociados a una orden."""
    return [
        intento
        for intento in intentos_pago_db.values()
        if intento["id_orden"] == id_orden
    ]


def estado_pago(id_orden: str) -> dict | None:
    """
    Contrato público (tanda 4): retorna el último estado de pago conocido
    para una orden (usado por HU-011 y POS; actualizado por HU-015).
    """
    intentos = listar_intentos_por_orden(id_orden)
    if not intentos:
        return None
    ultimo = intentos[-1]
    return {
        "id_orden": id_orden,
        "id_intento": ultimo["id_intento"],
        "estado": ultimo["estado"],
        "monto": ultimo["monto"],
        "metodo_pago": ultimo["metodo_pago"],
        "fecha_hora": ultimo["fecha_hora"],
    }

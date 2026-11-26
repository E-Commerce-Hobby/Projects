import threading

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


# ── HU-015: Almacenes de confirmación, duplicados y notificaciones a Ventas ──

bloqueo_transacciones = threading.Lock()        # CA7: control atómico de concurrencia
transacciones_procesadas_db: dict[str, dict] = {}  # CA4, CA5: clave -> id_transaccion
duplicados_descartados_db: list[dict] = []      # CA6: historial de duplicados descartados
respuestas_descartadas_db: list[dict] = []      # CA2: historial de respuestas inválidas
notificaciones_ventas_db: list[dict] = []       # CA3: notificaciones enviadas a Ventas


def registrar_transaccion_si_no_existe(id_transaccion: str, datos_transaccion: dict) -> bool:
    """
    CA4, CA5, CA7 (RN-03): Operación atómica protegida por Lock.
    Retorna True si la transacción era nueva y quedó registrada;
    retorna False si ya existía (duplicado).
    """
    with bloqueo_transacciones:
        if id_transaccion in transacciones_procesadas_db:
            return False
        transacciones_procesadas_db[id_transaccion] = datos_transaccion
        return True


def actualizar_estado_pago_orden(
    id_orden: str,
    estado_nuevo: str,
    id_transaccion: str,
    monto: int,
    fecha_hora: str,
) -> dict:
    """
    CA1: Actualiza el estado del pago ('aprobado' o 'rechazado') del último intento
    de la orden (o crea el registro confirmado si no había intento previo en memoria).
    """
    intentos = listar_intentos_por_orden(id_orden)
    if intentos:
        pago = intentos[-1]
        pago["estado"] = estado_nuevo
        pago["id_transaccion"] = id_transaccion
        pago["fecha_actualizacion"] = fecha_hora
        return pago

    nuevo_registro = {
        "id_intento": f"PAG-{id_transaccion}",
        "id_orden": id_orden,
        "monto": monto,
        "metodo_pago": "pasarela",
        "estado": estado_nuevo,
        "id_transaccion": id_transaccion,
        "fecha_hora": fecha_hora,
        "fecha_actualizacion": fecha_hora,
    }
    return guardar_intento_pago(nuevo_registro)


def registrar_descarte_duplicado(registro: dict) -> dict:
    """CA6: Registra un descarte por duplicado con ID de transacción y fecha/hora."""
    duplicados_descartados_db.append(registro)
    return registro


def listar_duplicados_descartados(id_transaccion: str | None = None) -> list[dict]:
    if id_transaccion is None:
        return list(duplicados_descartados_db)
    return [d for d in duplicados_descartados_db if d["id_transaccion"] == id_transaccion]


def registrar_respuesta_descartada(registro: dict) -> dict:
    """CA2: Registra una respuesta descartada (firma inválida, campo faltante o monto distinto)."""
    respuestas_descartadas_db.append(registro)
    return registro


def listar_respuestas_descartadas() -> list[dict]:
    return list(respuestas_descartadas_db)


def registrar_notificacion_ventas(registro: dict) -> dict:
    """CA3: Registra la notificación enviada a Ventas (API-INT-05) con id_orden y estado_pago."""
    notificaciones_ventas_db.append(registro)
    return registro


def listar_notificaciones_ventas(id_orden: str | None = None) -> list[dict]:
    if id_orden is None:
        return list(notificaciones_ventas_db)
    return [n for n in notificaciones_ventas_db if n["id_orden"] == id_orden]

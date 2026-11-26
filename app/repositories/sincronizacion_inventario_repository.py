from datetime import datetime
from app.repositories.disponibilidad_repository import (
    inventario_ubicaciones_db,
    producto_existe,
)

# ── Almacenes en memoria (HU-006 / base para HU-027) ─────────────────────────

notificaciones_enviadas_db: list[dict] = []
notificaciones_pendientes_db: list[dict] = []   # CA3: cola de reintentos para HU-027
resultados_actualizacion_db: list[dict] = []    # CA6: historial exitoso / fallido
movimientos_inventario_db: list[dict] = []      # CA7-CA9: solo creación y consulta (inmutable)

contador_notificacion_id = 1
contador_resultado_id = 1
contador_movimiento_id = 1


# ── Lectura y actualización de inventario por ubicación ──────────────────────

def obtener_registro_ubicacion(id_producto: str, ubicacion: str) -> dict | None:
    """Busca el registro de inventario de un producto en una ubicación exacta."""
    registros = inventario_ubicaciones_db.get(id_producto, [])
    ubicacion_normalizada = ubicacion.strip().lower()
    for registro in registros:
        if registro["ubicacion"].strip().lower() == ubicacion_normalizada:
            return registro
    return None


def aplicar_descuentos_en_bloque(lineas_validadas: list[dict]) -> list[dict]:
    """
    CA4: Aplica los descuentos en memoria sobre líneas ya validadas.
    Retorna la lista con producto, ubicación y cantidad resultante.
    """
    resultados: list[dict] = []
    for linea in lineas_validadas:
        registro = obtener_registro_ubicacion(linea["id_producto"], linea["ubicacion"])
        registro["disponible"] -= linea["cantidad"]
        resultados.append({
            "id_producto": linea["id_producto"],
            "ubicacion": registro["ubicacion"],
            "cantidad_descontada": linea["cantidad"],
            "cantidad_resultante": registro["disponible"],
        })
    return resultados


# ── FUN-2.2.1: Notificaciones enviadas y pendientes (HU-027) ─────────────────

def guardar_notificacion_enviada(datos_notificacion: dict) -> dict:
    """Registra una notificación enviada exitosamente a Inventario (CA1)."""
    global contador_notificacion_id
    registro = {"id_notificacion": contador_notificacion_id, **datos_notificacion}
    contador_notificacion_id += 1
    notificaciones_enviadas_db.append(registro)
    return registro


def guardar_notificacion_pendiente(datos_notificacion: dict) -> dict:
    """Registra una notificación pendiente para reintento posterior en HU-027 (CA3)."""
    global contador_notificacion_id
    registro = {"id_notificacion": contador_notificacion_id, **datos_notificacion}
    contador_notificacion_id += 1
    notificaciones_pendientes_db.append(registro)
    return registro


def listar_notificaciones_pendientes() -> list[dict]:
    """Retorna la lista de notificaciones pendientes de reintento (contrato para HU-027)."""
    return list(notificaciones_pendientes_db)


# ── FUN-2.2.2: Resultados de actualización (CA6) ─────────────────────────────

def guardar_resultado_actualizacion(datos_resultado: dict) -> dict:
    """Guarda el resultado ('exitoso' o 'fallido') de un intento de actualización (CA6)."""
    global contador_resultado_id
    registro = {"id_resultado": contador_resultado_id, **datos_resultado}
    contador_resultado_id += 1
    resultados_actualizacion_db.append(registro)
    return registro


def listar_resultados_actualizacion(id_venta: str | None = None) -> list[dict]:
    """Consulta el historial de resultados, opcionalmente filtrado por id_venta."""
    if id_venta is None:
        return list(resultados_actualizacion_db)
    return [r for r in resultados_actualizacion_db if r["id_venta"] == id_venta]


# ── FUN-2.2.4: Movimientos inmutables (CA7, CA8, CA9) ────────────────────────

def guardar_movimiento(datos_movimiento: dict) -> dict:
    """
    Registra un movimiento de inventario.
    CA8: Solo se crean y consultan; no existen funciones de edición ni eliminación.
    """
    global contador_movimiento_id
    registro = {"id_movimiento": contador_movimiento_id, **datos_movimiento}
    contador_movimiento_id += 1
    movimientos_inventario_db.append(registro)
    return registro


def consultar_movimientos_por_producto(
    id_producto: str,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
) -> list[dict]:
    """
    CA9: Filtra movimientos por producto y rango de fechas,
    ordenados de más reciente a más antiguo.
    """
    filtrados = []
    for mov in movimientos_inventario_db:
        if mov["id_producto"] != id_producto:
            continue
        fecha_mov = datetime.fromisoformat(mov["fecha_hora"])
        if fecha_inicio and fecha_mov < fecha_inicio:
            continue
        if fecha_fin and fecha_mov > fecha_fin:
            continue
        filtrados.append(mov)

    filtrados.sort(key=lambda m: (m["fecha_hora"], m["id_movimiento"]), reverse=True)
    return filtrados

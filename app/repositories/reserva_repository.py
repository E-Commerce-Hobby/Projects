from datetime import datetime, timedelta, timezone

# Duración configurable de la reserva (en minutos)
DURACION_RESERVA_MINUTOS = 15

# Inventario base en memoria para pruebas funcionales y de integración
inventario_db: dict[str, dict[str, int]] = {
    "PROD-001": {"disponible": 10, "reservado": 0},
    "PROD-002": {"disponible": 2, "reservado": 0},
}

reservas_db: dict[int, dict] = {}
reserva_id_counter = 1


def obtener_stock_producto(id_producto: str) -> dict[str, int] | None:
    return inventario_db.get(id_producto)


def crear_reserva(
    id_producto: str,
    cantidad: int,
    ahora: datetime | None = None,
) -> dict:
    """Descuenta de disponible, suma a reservado y registra la reserva."""
    global reserva_id_counter

    momento_actual = ahora or datetime.now(timezone.utc)
    expiracion = momento_actual + timedelta(minutes=DURACION_RESERVA_MINUTOS)

    stock = inventario_db[id_producto]
    stock["disponible"] -= cantidad
    stock["reservado"] += cantidad

    reserva = {
        "id": reserva_id_counter,
        "id_producto": id_producto,
        "cantidad": cantidad,
        "fecha_expiracion": expiracion,
        "estado": "activa",
    }
    reservas_db[reserva_id_counter] = reserva
    reserva_id_counter += 1
    return reserva


def liberar_reservas_vencidas(ahora: datetime | None = None) -> list[dict]:
    """
    Devuelve a 'disponible' las unidades de todas las reservas activas
    cuya fecha de expiración ya se cumplió (CA3).
    """
    momento_actual = ahora or datetime.now(timezone.utc)
    liberadas: list[dict] = []

    for reserva in reservas_db.values():
        if (
            reserva["estado"] == "activa"
            and reserva["fecha_expiracion"] <= momento_actual
        ):
            stock = inventario_db.get(reserva["id_producto"])
            if stock:
                stock["reservado"] = max(0, stock["reservado"] - reserva["cantidad"])
                stock["disponible"] += reserva["cantidad"]
            reserva["estado"] = "expirada"
            liberadas.append(reserva)

    return liberadas
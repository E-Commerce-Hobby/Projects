from app.core.errors import ReglaNegocioError
from app.domain.reserva_schema import ReservaCreacion
from app.repositories import reserva_repository


def solicitar_reserva_temporal(datos: ReservaCreacion) -> dict:
    # CA3: Liberar reservas vencidas antes de evaluar disponibilidad
    reserva_repository.liberar_reservas_vencidas()

    stock = reserva_repository.obtener_stock_producto(datos.id_producto)
    if stock is None:
        raise ReglaNegocioError(
            message="El producto solicitado no tiene inventario registrado.",
            status_code=404,
            data=["id_producto"],
        )

    disponible = stock["disponible"]

    # CA2 (RN-01): Stock insuficiente -> rechaza sin modificar cantidades
    if disponible < datos.cantidad:
        raise ReglaNegocioError(
            message=(
                f"Stock insuficiente (RN-01). "
                f"Cantidad disponible actual: {disponible}."
            ),
            status_code=409,
            data={"id_producto": datos.id_producto, "disponible_actual": disponible},
        )

    # CA1: Reserva exitosa (resta disponible, suma reservado, +15 min)
    reserva = reserva_repository.crear_reserva(datos.id_producto, datos.cantidad)
    return {
        "id": reserva["id"],
        "id_producto": reserva["id_producto"],
        "cantidad": reserva["cantidad"],
        "fecha_expiracion": reserva["fecha_expiracion"].isoformat(),
        "estado": reserva["estado"],
    }


def consultar_stock_disponible(id_producto: str) -> dict:
    reserva_repository.liberar_reservas_vencidas()

    stock = reserva_repository.obtener_stock_producto(id_producto)
    if stock is None:
        raise ReglaNegocioError(
            message="El producto solicitado no tiene inventario registrado.",
            status_code=404,
            data=["id_producto"],
        )

    return {
        "id_producto": id_producto,
        "disponible": stock["disponible"],
        "reservado": stock["reservado"],
    }
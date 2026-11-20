from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from app.core.errors import ReglaNegocioError
from app.domain.disponibilidad_schema import (
    ItemSolicitudStock,
    ValidarCarritoRequest,
    VerificarVentaRequest,
)
from app.repositories import disponibilidad_repository

TIMEOUT_INVENTARIO_SEGUNDOS = 5.0


def consultar_disponibilidad_total(id_producto: str) -> dict:
    """FUN-2.1.5: Consulta disponibilidad total y detalle por ubicación (CA1, CA2, CA3)."""
    # CA3: Producto no existe
    if not disponibilidad_repository.producto_existe(id_producto):
        raise ReglaNegocioError(
            message=f"El producto '{id_producto}' no existe en el catálogo.",
            status_code=404,
            data=["id_producto"],
        )

    registros = disponibilidad_repository.obtener_inventario_por_ubicaciones(id_producto)

    # CA2: Existe pero no tiene inventario registrado -> total 0 con HTTP 200
    if not registros:
        return {
            "id_producto": id_producto,
            "total_disponible": 0,
            "ubicaciones": [],
        }

    # CA1: Suma solo 'disponible' (excluye 'reservado') y retorna detalle por ubicación
    detalle_ubicaciones = [
        {
            "ubicacion": item["ubicacion"],
            "disponible": item["disponible"],
        }
        for item in registros
    ]
    total_disponible = sum(item["disponible"] for item in registros)

    return {
        "id_producto": id_producto,
        "total_disponible": total_disponible,
        "ubicaciones": detalle_ubicaciones,
    }


def _evaluar_faltantes(productos: list[ItemSolicitudStock]) -> list[dict]:
    """Compara cada producto solicitado contra su disponibilidad total."""
    faltantes: list[dict] = []

    for item in productos:
        if not disponibilidad_repository.producto_existe(item.id_producto):
            raise ReglaNegocioError(
                message=f"El producto '{item.id_producto}' no existe en el catálogo.",
                status_code=404,
                data=["id_producto"],
            )

        disponibilidad = consultar_disponibilidad_total(item.id_producto)
        disponible_actual = disponibilidad["total_disponible"]

        if item.cantidad > disponible_actual:
            faltantes.append(
                {
                    "id_producto": item.id_producto,
                    "cantidad_solicitada": item.cantidad,
                    "cantidad_disponible": disponible_actual,
                }
            )

    return faltantes


def verificar_disponibilidad_venta(datos: VerificarVentaRequest) -> dict:
    """FUN-2.2.3: Verifica disponibilidad antes de iniciar el cobro (CA4, CA5, CA6)."""
    faltantes = _evaluar_faltantes(datos.productos)

    # CA5 (RN-01): Rechaza toda la solicitud e informa cada producto sin disponibilidad
    if faltantes:
        raise ReglaNegocioError(
            message="Stock insuficiente para completar la venta (RN-01).",
            status_code=409,
            data={
                "resultado": "rechazada",
                "puede_continuar_cobro": False,
                "productos_sin_disponibilidad": faltantes,
            },
        )

    # CA4 y CA6: Confirma la operación y autoriza continuar con el cobro
    return {
        "canal": datos.canal,
        "resultado": "confirmada",
        "puede_continuar_cobro": True,
    }


def validar_disponibilidad_carrito(
    datos: ValidarCarritoRequest,
    timeout_segundos: float = TIMEOUT_INVENTARIO_SEGUNDOS,
) -> dict:
    """FUN-4.1.2: Valida disponibilidad del carrito antes de crear la orden (CA7-CA10)."""
    # CA9: Carrito vacío
    if not datos.productos:
        raise ReglaNegocioError(
            message="El carrito está vacío. Debe incluir al menos un producto para confirmar.",
            status_code=400,
            data=["productos"],
        )

    # CA10: Control de tiempo máximo de espera a Inventario (5 segundos)
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_evaluar_faltantes, datos.productos)
    try:
        faltantes = future.result(timeout=timeout_segundos)
    except FuturesTimeoutError:
        future.cancel()
        raise ReglaNegocioError(
            message="Servicio de inventario no disponible. Tiempo de espera agotado (5 s).",
            status_code=503,
            data={"autorizado": False},
        )
    finally:
        executor.shutdown(wait=False)

    # CA8 (RN-01): Al menos un producto supera disponibilidad
    if faltantes:
        raise ReglaNegocioError(
            message="No hay disponibilidad suficiente para confirmar el carrito (RN-01).",
            status_code=409,
            data={
                "autorizado": False,
                "productos_sin_disponibilidad": faltantes,
            },
        )

    # CA7: Autoriza continuar con la creación de la orden
    return {
        "autorizado": True,
        "puede_crear_orden": True,
    }
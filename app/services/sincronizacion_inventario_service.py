from datetime import datetime, timezone
from app.core.errors import ReglaNegocioError
from app.domain.sincronizacion_inventario_schema import (
    CANALES_MOVIMIENTO_PERMITIDOS,
    CANALES_VENTA_PERMITIDOS,
    TIPOS_MOVIMIENTO_PERMITIDOS,
    DescuentoInventarioEntrada,
    NotificacionVentaEntrada,
    RegistroMovimientoEntrada,
)
from app.repositories.sincronizacion_inventario_repository import (
    aplicar_descuentos_en_bloque,
    consultar_movimientos_por_producto,
    guardar_movimiento,
    guardar_notificacion_enviada,
    guardar_notificacion_pendiente,
    guardar_resultado_actualizacion,
    obtener_registro_ubicacion,
    producto_existe,
)


def _normalizar_fecha_utc(fecha: datetime | None) -> datetime | None:
    """Asegura que una fecha tenga zona horaria UTC para comparaciones consistentes."""
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


# ── FUN-2.2.1: Notificación de venta a Inventario (CA1, CA2, CA3) ────────────

def notificar_venta_a_inventario(datos: NotificacionVentaEntrada) -> dict:
    """
    CA1: Envía a Inventario el ID de venta, canal y líneas válidas.
    CA2: Rechaza (400) si no trae líneas o alguna tiene cantidad <= 0.
    CA3: Si Inventario no confirma, registra la notificación como pendiente (HU-027) y retorna 503.
    """
    if datos.canal not in CANALES_VENTA_PERMITIDOS:
        raise ReglaNegocioError(
            message=f"Canal inválido '{datos.canal}'. Permitidos: {', '.join(CANALES_VENTA_PERMITIDOS)}.",
            data=["canal"],
            status_code=400,
        )

    # CA2: Validar presencia de líneas
    if not datos.lineas:
        raise ReglaNegocioError(
            message="La venta confirmada debe incluir al menos una línea de producto.",
            data=["lineas"],
            status_code=400,
        )

    # CA2: Validar que todas las cantidades sean > 0 antes de enviar nada
    for indice, linea in enumerate(datos.lineas, start=1):
        if linea.cantidad <= 0:
            raise ReglaNegocioError(
                message=(
                    f"Línea {indice} inválida (producto '{linea.id_producto}'): "
                    "la cantidad debe ser mayor a 0."
                ),
                data=[{"linea": indice, "id_producto": linea.id_producto, "cantidad": linea.cantidad}],
                status_code=400,
            )

    fecha_actual = datetime.now(timezone.utc).isoformat()
    lineas_serializadas = [
        {
            "id_producto": linea.id_producto,
            "ubicacion": linea.ubicacion or "Bodega Virtual",
            "cantidad": linea.cantidad,
        }
        for linea in datos.lineas
    ]

    # CA3: Si Inventario no confirma la recepción, queda pendiente para reintento (HU-027)
    if datos.simular_fallo_inventario:
        pendiente = guardar_notificacion_pendiente({
            "id_venta": datos.id_venta,
            "canal": datos.canal,
            "lineas": lineas_serializadas,
            "estado_envio": "pendiente",
            "fecha_hora": fecha_actual,
            "motivo": "Inventario no confirmó la recepción de la venta.",
        })
        raise ReglaNegocioError(
            message="Inventario no confirmó la recepción. Notificación guardada como pendiente para reintento.",
            data=[pendiente],
            status_code=503,
        )

    # CA1: Envío confirmado a Inventario
    return guardar_notificacion_enviada({
        "id_venta": datos.id_venta,
        "canal": datos.canal,
        "lineas": lineas_serializadas,
        "estado_envio": "enviada",
        "fecha_hora": fecha_actual,
    })


# ── FUN-2.2.2: Descuento atómico de inventario (CA4, CA5, CA6) ───────────────

def aplicar_descuento_por_venta(datos: DescuentoInventarioEntrada) -> dict:
    """
    CA4: Descuenta todas las líneas en una sola operación si todas tienen stock suficiente.
    CA5 (RN-01): Si alguna línea falla, no descuenta ninguna (todo o nada) y registra 'fallido'.
    CA6: Siempre registra el resultado ('exitoso' o 'fallido') con id_venta y fecha_hora.
    CA7: Registra automáticamente un movimiento inmutable por cada línea descontada.
    """
    if datos.canal not in CANALES_VENTA_PERMITIDOS:
        raise ReglaNegocioError(
            message=f"Canal inválido '{datos.canal}'. Permitidos: {', '.join(CANALES_VENTA_PERMITIDOS)}.",
            data=["canal"],
            status_code=400,
        )

    if not datos.lineas:
        raise ReglaNegocioError(
            message="Debe enviar al menos una línea de producto para descontar inventario.",
            data=["lineas"],
            status_code=400,
        )

    for indice, linea in enumerate(datos.lineas, start=1):
        if linea.cantidad <= 0:
            raise ReglaNegocioError(
                message=(
                    f"Línea {indice} inválida (producto '{linea.id_producto}'): "
                    "la cantidad a descontar debe ser mayor a 0."
                ),
                data=[{"linea": indice, "id_producto": linea.id_producto}],
                status_code=400,
            )

    fecha_actual = datetime.now(timezone.utc).isoformat()

    # Fase 1: Validar TODAS las líneas antes de tocar el inventario (todo o nada)
    acumulado_por_ubicacion: dict[tuple[str, str], int] = {}
    for linea in datos.lineas:
        if not producto_existe(linea.id_producto):
            motivo = f"El producto '{linea.id_producto}' no existe en el catálogo."
            guardar_resultado_actualizacion({
                "id_venta": datos.id_venta,
                "resultado": "fallido",
                "motivo": motivo,
                "fecha_hora": fecha_actual,
            })
            raise ReglaNegocioError(message=motivo, data=[linea.id_producto], status_code=404)

        registro = obtener_registro_ubicacion(linea.id_producto, linea.ubicacion)
        if registro is None:
            motivo = f"No existe inventario del producto '{linea.id_producto}' en '{linea.ubicacion}'."
            guardar_resultado_actualizacion({
                "id_venta": datos.id_venta,
                "resultado": "fallido",
                "motivo": motivo,
                "fecha_hora": fecha_actual,
            })
            raise ReglaNegocioError(
                message=motivo,
                data=[{"id_producto": linea.id_producto, "ubicacion": linea.ubicacion}],
                status_code=404,
            )

        clave = (linea.id_producto, registro["ubicacion"])
        acumulado_por_ubicacion[clave] = acumulado_por_ubicacion.get(clave, 0) + linea.cantidad

        # CA5 / RN-01: Stock insuficiente -> no descontar nada
        if acumulado_por_ubicacion[clave] > registro["disponible"]:
            motivo = (
                f"Stock insuficiente (RN-01) para '{linea.id_producto}' en '{registro['ubicacion']}': "
                f"disponible {registro['disponible']}, solicitado {acumulado_por_ubicacion[clave]}."
            )
            resultado_fallido = guardar_resultado_actualizacion({
                "id_venta": datos.id_venta,
                "resultado": "fallido",
                "motivo": motivo,
                "fecha_hora": fecha_actual,
            })
            raise ReglaNegocioError(
                message=motivo,
                data=[resultado_fallido],
                status_code=409,
            )

    # Fase 2: Aplicar todos los descuentos en una sola operación (CA4)
    lineas_dict = [
        {"id_producto": l.id_producto, "ubicacion": l.ubicacion, "cantidad": l.cantidad}
        for l in datos.lineas
    ]
    inventario_actualizado = aplicar_descuentos_en_bloque(lineas_dict)

    # CA7: Registrar un movimiento negativo por cada línea descontada
    movimientos_registrados = []
    for item in inventario_actualizado:
        mov = guardar_movimiento({
            "id_producto": item["id_producto"],
            "ubicacion": item["ubicacion"],
            "cantidad": -item["cantidad_descontada"],
            "fecha_hora": fecha_actual,
            "canal": datos.canal,
            "tipo": "venta",
            "id_referencia": datos.id_venta,
        })
        movimientos_registrados.append(mov)

    # CA6: Registrar resultado exitoso con id_venta y fecha_hora
    resultado_ok = guardar_resultado_actualizacion({
        "id_venta": datos.id_venta,
        "resultado": "exitoso",
        "motivo": None,
        "fecha_hora": fecha_actual,
    })

    return {
        "id_venta": datos.id_venta,
        "resultado": resultado_ok["resultado"],
        "fecha_hora": resultado_ok["fecha_hora"],
        "inventario_actualizado": inventario_actualizado,
        "movimientos_registrados": movimientos_registrados,
    }


# ── FUN-2.2.4: Registro y consulta de movimientos (CA7, CA8, CA9) ────────────

def registrar_movimiento_inventario(datos: RegistroMovimientoEntrada) -> dict:
    """CA7: Registra un movimiento inmutable de inventario por venta, ajuste o reserva."""
    if datos.canal not in CANALES_MOVIMIENTO_PERMITIDOS:
        raise ReglaNegocioError(
            message=f"Canal inválido '{datos.canal}'. Permitidos: {', '.join(CANALES_MOVIMIENTO_PERMITIDOS)}.",
            data=["canal"],
            status_code=400,
        )

    if datos.tipo not in TIPOS_MOVIMIENTO_PERMITIDOS:
        raise ReglaNegocioError(
            message=f"Tipo inválido '{datos.tipo}'. Permitidos: {', '.join(TIPOS_MOVIMIENTO_PERMITIDOS)}.",
            data=["tipo"],
            status_code=400,
        )

    if datos.cantidad == 0:
        raise ReglaNegocioError(
            message="La cantidad del movimiento debe ser distinta de 0 (positiva o negativa).",
            data=["cantidad"],
            status_code=400,
        )

    if not producto_existe(datos.id_producto):
        raise ReglaNegocioError(
            message=f"El producto '{datos.id_producto}' no existe en el catálogo.",
            data=[datos.id_producto],
            status_code=404,
        )

    return guardar_movimiento({
        "id_producto": datos.id_producto,
        "ubicacion": datos.ubicacion,
        "cantidad": datos.cantidad,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "canal": datos.canal,
        "tipo": datos.tipo,
        "id_referencia": datos.id_referencia,
    })


def consultar_movimientos_producto(
    id_producto: str,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
) -> list[dict]:
    """CA9: Retorna los movimientos de un producto en el rango de fechas, de más reciente a más antiguo."""
    if not id_producto or not id_producto.strip():
        raise ReglaNegocioError(
            message="Debe indicar un identificador de producto válido.",
            data=["id_producto"],
            status_code=400,
        )

    id_limpio = id_producto.strip()
    if not producto_existe(id_limpio):
        raise ReglaNegocioError(
            message=f"El producto '{id_limpio}' no existe en el catálogo.",
            data=[id_limpio],
            status_code=404,
        )

    inicio_utc = _normalizar_fecha_utc(fecha_inicio)
    fin_utc = _normalizar_fecha_utc(fecha_fin)

    if inicio_utc and fin_utc and inicio_utc > fin_utc:
        raise ReglaNegocioError(
            message="La fecha de inicio no puede ser posterior a la fecha de fin.",
            data=["fecha_inicio", "fecha_fin"],
            status_code=400,
        )

    return consultar_movimientos_por_producto(id_limpio, inicio_utc, fin_utc)

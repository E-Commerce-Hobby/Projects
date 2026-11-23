from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from app.core.errors import ReglaNegocioError
from app.domain.orden_schema import (
    ActualizarEstadoOrdenRequest,
    CalcularTotalRequest,
    CrearOrdenRequest,
)
from app.repositories import orden_repository

TIMEOUT_CLIENTES_SEGUNDOS = 5.0
TASA_IMPUESTO = Decimal("0.19")  # IVA estándar en Colombia (19%)

EVENTOS_POR_ORIGEN: dict[str, set[str]] = {
    "Pagos": {"pago aprobado", "pago rechazado"},
    "Logística": {"envío despachado", "envío entregado"},
}

MAPEO_EVENTO_ESTADO: dict[str, str] = {
    "pago aprobado": "pagada",
    "pago rechazado": "pago rechazado",
    "envío despachado": "enviada",
    "envío entregado": "entregada",
}

TRANSICIONES_PERMITIDAS: dict[str, set[str]] = {
    "pendiente de pago": {"pagada", "pago rechazado"},
    "pagada": {"enviada"},
    "enviada": {"entregada"},
    "pago rechazado": set(),
    "entregada": set(),
}


def _redondear_cop(valor: Decimal) -> int:
    """Redondea al peso colombiano más cercano sin decimales."""
    return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _consultar_cliente_con_timeout(
    id_cliente: str,
    timeout_segundos: float = TIMEOUT_CLIENTES_SEGUNDOS,
) -> dict | None:
    """Consulta el módulo Clientes respetando el tiempo límite de 5 segundos (CA4)."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(orden_repository.obtener_cliente, id_cliente)
    try:
        return future.result(timeout=timeout_segundos)
    except FuturesTimeoutError:
        future.cancel()
        raise ReglaNegocioError(
            message="Servicio de clientes no disponible. Tiempo de espera agotado (5 s).",
            status_code=503,
            data={"orden_creada": False},
        )
    finally:
        executor.shutdown(wait=False)


def crear_orden(
    datos: CrearOrdenRequest,
    timeout_segundos: float = TIMEOUT_CLIENTES_SEGUNDOS,
) -> dict:
    """FUN-4.1.3: Crea una orden en estado 'pendiente de pago' (CA1-CA4)."""
    # CA3: Carrito vacío
    if not datos.productos:
        raise ReglaNegocioError(
            message="El carrito está vacío. Debe incluir al menos un producto para crear la orden.",
            status_code=400,
            data=["productos"],
        )

    # CA4: Consulta al módulo Clientes con timeout de 5 segundos
    cliente = _consultar_cliente_con_timeout(datos.id_cliente, timeout_segundos)

    # CA2: Cliente inexistente (404) o estado distinto de 'activo' (403)
    if cliente is None:
        raise ReglaNegocioError(
            message=f"El cliente '{datos.id_cliente}' no existe.",
            status_code=404,
            data=["id_cliente"],
        )

    if cliente.get("estado") != "activo":
        raise ReglaNegocioError(
            message=f"El cliente '{datos.id_cliente}' no se encuentra activo para crear órdenes.",
            status_code=403,
            data=["id_cliente"],
        )

    # Resolver precios unitarios de cada línea de producto
    items_orden: list[dict] = []
    for item in datos.productos:
        precio = orden_repository.obtener_precio_producto(item.id_producto)
        if precio is None:
            raise ReglaNegocioError(
                message=f"El producto '{item.id_producto}' no existe en el catálogo.",
                status_code=404,
                data=["id_producto"],
            )
        items_orden.append(
            {
                "id_producto": item.id_producto,
                "cantidad": item.cantidad,
                "precio_unitario": precio,
            }
        )

    # CA1: Registrar la orden con estado inicial 'pendiente de pago'
    id_orden = f"ORD-{uuid4().hex[:8].upper()}"
    nueva_orden = {
        "id_orden": id_orden,
        "id_cliente": datos.id_cliente,
        "estado": "pendiente de pago",
        "moneda": "COP",
        "productos": items_orden,
        "subtotal": None,
        "impuestos": None,
        "descuentos": None,
        "total": None,
        "creada_en": datetime.now(timezone.utc).isoformat(),
    }

    return orden_repository.guardar_orden(nueva_orden)


def calcular_total_orden(
    id_orden: str,
    datos: CalcularTotalRequest | None = None,
    ahora: datetime | None = None,
) -> dict:
    """FUN-4.1.4: Calcula y registra subtotal, impuestos, descuentos vigentes y total en COP (CA5-CA8)."""
    orden = orden_repository.obtener_orden(id_orden)
    if orden is None:
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' no existe.",
            status_code=404,
            data=["id_orden"],
        )

    # CA5: Subtotal = suma(precio_unitario * cantidad)
    subtotal_dec = sum(
        Decimal(item["precio_unitario"]) * Decimal(item["cantidad"])
        for item in orden["productos"]
    )
    subtotal_cop = _redondear_cop(subtotal_dec)

    # CA6: Impuestos (19% sobre subtotal, redondeado al peso más cercano)
    impuestos_cop = _redondear_cop(subtotal_dec * TASA_IMPUESTO)

    # CA6: Solo aplicar descuentos cuya vigencia incluya la fecha y hora actual
    fecha_actual = ahora or datetime.now(timezone.utc)
    catalogo_descuentos = orden_repository.obtener_descuentos_disponibles()
    codigos_solicitados = datos.codigos_descuento if datos else []

    descuento_dec = Decimal("0")
    descuentos_aplicados: list[str] = []

    for codigo in codigos_solicitados:
        codigo_norm = codigo.strip().upper()
        promo = catalogo_descuentos.get(codigo_norm)
        if not promo:
            continue
        if promo["vigencia_inicio"] <= fecha_actual <= promo["vigencia_fin"]:
            if promo["tipo"] == "porcentaje":
                descuento_dec += subtotal_dec * (Decimal(promo["valor"]) / Decimal("100"))
            else:
                descuento_dec += Decimal(promo["valor"])
            descuentos_aplicados.append(codigo_norm)

    descuentos_cop = _redondear_cop(descuento_dec)

    # CA6 y CA7: total = subtotal + impuestos - descuentos; nunca negativo (mínimo 0)
    total_cop = max(0, subtotal_cop + impuestos_cop - descuentos_cop)

    # CA8: Registrar el cálculo en la orden en COP sin decimales y retornar
    orden["subtotal"] = subtotal_cop
    orden["impuestos"] = impuestos_cop
    orden["descuentos"] = descuentos_cop
    orden["total"] = total_cop
    orden["descuentos_aplicados"] = descuentos_aplicados

    orden_repository.guardar_orden(orden)
    return orden


def consultar_orden(id_orden: str) -> dict:
    """Consulta una orden registrada por su ID."""
    orden = orden_repository.obtener_orden(id_orden)
    if orden is None:
        raise ReglaNegocioError(
            message=f"La orden '{id_orden}' no existe.",
            status_code=404,
            data=["id_orden"],
        )
    return orden


def actualizar_estado_orden(
    id_orden: str,
    datos: ActualizarEstadoOrdenRequest,
) -> dict:
    """FUN-4.1.5: Actualiza el estado de una orden según notificaciones de Pagos o Logística (CA1-CA4)."""
    fecha_hora = datetime.now(timezone.utc).isoformat()

    # Validar correspondencia entre origen y evento (HTTP 400)
    if datos.evento not in EVENTOS_POR_ORIGEN[datos.origen]:
        motivo = (
            f"El evento '{datos.evento}' no corresponde al origen '{datos.origen}'."
        )
        orden_repository.registrar_notificacion_rechazada(
            {
                "id_orden": id_orden,
                "origen": datos.origen,
                "evento": datos.evento,
                "motivo": motivo,
                "fecha_hora": fecha_hora,
            }
        )
        raise ReglaNegocioError(
            message=motivo,
            status_code=400,
            data={"origen": datos.origen, "evento": datos.evento},
        )

    # CA4: Orden inexistente -> rechaza (404), informa motivo y registra
    orden = orden_repository.obtener_orden(id_orden)
    if orden is None:
        motivo = f"La orden '{id_orden}' no existe."
        orden_repository.registrar_notificacion_rechazada(
            {
                "id_orden": id_orden,
                "origen": datos.origen,
                "evento": datos.evento,
                "motivo": motivo,
                "fecha_hora": fecha_hora,
            }
        )
        raise ReglaNegocioError(
            message=motivo,
            status_code=404,
            data=["id_orden"],
        )

    estado_anterior = orden["estado"]
    estado_nuevo = MAPEO_EVENTO_ESTADO[datos.evento]

    # CA2: Validar transición permitida -> si no, rechaza (409), conserva estado y registra
    if estado_nuevo not in TRANSICIONES_PERMITIDAS.get(estado_anterior, set()):
        motivo = (
            f"Transición no permitida: no se puede pasar de '{estado_anterior}' a '{estado_nuevo}'."
        )
        orden_repository.registrar_notificacion_rechazada(
            {
                "id_orden": id_orden,
                "origen": datos.origen,
                "evento": datos.evento,
                "estado_actual": estado_anterior,
                "estado_solicitado": estado_nuevo,
                "motivo": motivo,
                "fecha_hora": fecha_hora,
            }
        )
        raise ReglaNegocioError(
            message=motivo,
            status_code=409,
            data={
                "id_orden": id_orden,
                "estado_actual": estado_anterior,
                "estado_solicitado": estado_nuevo,
            },
        )

    # CA1: Actualizar y guardar el nuevo estado
    orden["estado"] = estado_nuevo
    orden["actualizada_en"] = fecha_hora
    orden_repository.guardar_orden(orden)

    # CA3: Publicar evento de cambio de estado
    evento_publicado = {
        "id_orden": id_orden,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "fecha_hora": fecha_hora,
    }
    orden_repository.registrar_evento_orden(evento_publicado)

    return {
        "orden": orden,
        "evento_publicado": evento_publicado,
    }
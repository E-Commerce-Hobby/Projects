from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, StrictInt

# Canales y tipos permitidos según HU-006
CANALES_VENTA_PERMITIDOS = ("virtual", "POS")
CANALES_MOVIMIENTO_PERMITIDOS = ("virtual", "POS", "administración")
TIPOS_MOVIMIENTO_PERMITIDOS = ("venta", "ajuste", "reserva")


# ── FUN-2.2.1: Notificación de venta a Inventario ────────────────────────────

class LineaVentaNotificacion(BaseModel):
    """Línea individual de producto en una venta confirmada (CA1, CA2)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_producto: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador del producto.",
        examples=["PROD-001"],
    )
    cantidad: StrictInt = Field(
        ...,
        description="Cantidad vendida (debe ser mayor a 0; validado en el servicio para CA2).",
        examples=[2],
    )
    ubicacion: Optional[str] = Field(
        default="Bodega Virtual",
        min_length=1,
        max_length=100,
        description="Ubicación de inventario asociada a la línea.",
        examples=["Bodega Virtual"],
    )


class NotificacionVentaEntrada(BaseModel):
    """Datos de entrada para notificar una venta confirmada a Inventario (CA1-CA3)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_venta: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador único de la venta confirmada.",
        examples=["VEN-001"],
    )
    canal: str = Field(
        ...,
        description="Canal de origen de la venta: 'virtual' o 'POS'.",
        examples=["virtual"],
    )
    lineas: list[LineaVentaNotificacion] = Field(
        default_factory=list,
        description="Lista de productos y cantidades vendidas.",
    )
    simular_fallo_inventario: bool = Field(
        default=False,
        description="Bandera para simular que Inventario no confirma la recepción (CA3 / HU-027).",
        examples=[False],
    )


# ── FUN-2.2.2: Descuento de inventario ───────────────────────────────────────

class LineaDescuentoInventario(BaseModel):
    """Línea de descuento con ubicación explícita (CA4, CA5)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_producto: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador del producto.",
        examples=["PROD-001"],
    )
    ubicacion: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Ubicación de inventario donde se descuenta el producto.",
        examples=["Tienda Física"],
    )
    cantidad: StrictInt = Field(
        ...,
        description="Cantidad a descontar (debe ser mayor a 0).",
        examples=[2],
    )


class DescuentoInventarioEntrada(BaseModel):
    """Datos de entrada para aplicar el descuento atómico de inventario (CA4-CA6)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_venta: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador de la venta confirmada.",
        examples=["VEN-001"],
    )
    canal: str = Field(
        default="virtual",
        description="Canal de origen de la venta: 'virtual' o 'POS'.",
        examples=["virtual"],
    )
    lineas: list[LineaDescuentoInventario] = Field(
        default_factory=list,
        description="Líneas a descontar en una sola operación (todo o nada, RN-01).",
    )


# ── FUN-2.2.4: Registro y consulta de movimientos ────────────────────────────

class RegistroMovimientoEntrada(BaseModel):
    """Datos de entrada para registrar un movimiento inmutable de inventario (CA7, CA8)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_producto: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador del producto.",
        examples=["PROD-001"],
    )
    ubicacion: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Ubicación donde ocurre el cambio de inventario.",
        examples=["Tienda Física"],
    )
    cantidad: StrictInt = Field(
        ...,
        description="Cantidad modificada (positiva o negativa, distinta de 0).",
        examples=[-2],
    )
    canal: str = Field(
        ...,
        description="Canal de origen: 'virtual', 'POS' o 'administración'.",
        examples=["POS"],
    )
    tipo: str = Field(
        default="ajuste",
        description="Motivo del movimiento: 'venta', 'ajuste' o 'reserva'.",
        examples=["venta"],
    )
    id_referencia: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Identificador de venta, reserva o ajuste asociado.",
        examples=["VEN-001"],
    )

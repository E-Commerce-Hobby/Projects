from pydantic import BaseModel, ConfigDict, Field, StrictInt

# Métodos de pago habilitados en la pasarela (CA1)
METODOS_PAGO_HABILITADOS = (
    "tarjeta_credito",
    "tarjeta_debito",
    "pse",
    "nequi",
    "daviplata",
)

# Tiempo máximo de espera a la pasarela externa en segundos (CA5)
TIEMPO_ESPERA_PASARELA_SEGUNDOS = 10


class InicioPagoEntrada(BaseModel):
    """Datos de entrada para iniciar el pago de una orden (HU-014: FUN-5.1.1)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_orden: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identificador de la orden a pagar (debe estar en estado 'pendiente de pago').",
        examples=["ORD-001"],
    )
    monto: StrictInt = Field(
        ...,
        description="Monto en COP correspondiente al total de la orden (debe ser mayor a 0).",
        examples=[150000],
    )
    metodo_pago: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Método de pago habilitado: tarjeta_credito, tarjeta_debito, pse, nequi o daviplata.",
        examples=["pse"],
    )
    simular_timeout_pasarela: bool = Field(
        default=False,
        description="Bandera para simular que la pasarela supera el timeout de 10 segundos (CA5).",
        examples=[False],
    )


# ── HU-015: Confirmación de pago sin duplicados (FUN-5.1.2, FUN-5.1.3) ───────

ESTADOS_CONFIRMACION_PERMITIDOS = ("aprobado", "rechazado")


class ConfirmacionPagoEntrada(BaseModel):
    """
    Datos de entrada enviados por la pasarela al confirmar un pago (CA1-CA7).
    Los campos se permiten opcionales en Pydantic para que el servicio registre el
    descarte con motivo (CA2) y responda HTTP 400 mediante ReglaNegocioError.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    firma: str | None = Field(
        default=None,
        description="Firma de integridad SHA-256 generada por la pasarela.",
        examples=["f1e2d3c4..."],
    )
    id_transaccion: str | None = Field(
        default=None,
        description="Identificador único de la transacción en la pasarela (RN-03).",
        examples=["TXN-001"],
    )
    id_orden: str | None = Field(
        default=None,
        description="Identificador de la orden asociada al pago.",
        examples=["ORD-001"],
    )
    estado: str | None = Field(
        default=None,
        description="Estado informado por la pasarela: 'aprobado' o 'rechazado'.",
        examples=["aprobado"],
    )
    monto: StrictInt | None = Field(
        default=None,
        description="Monto en COP informado por la pasarela (debe coincidir con la orden).",
        examples=[150000],
    )

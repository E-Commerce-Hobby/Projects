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

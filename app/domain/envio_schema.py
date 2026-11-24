from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ConfirmarUbicacionRequest(BaseModel):
    """Entrada opcional para FUN-7.1.4 (CA2): confirmar la ubicación sugerida o una elegible."""

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo_ubicacion: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description=(
            "Código de la ubicación a confirmar. Si se omite, el sistema registra "
            "automáticamente la ubicación recomendada por mayor disponibilidad."
        ),
        examples=["BOD-002"],
    )


class DimensionesPaquete(BaseModel):
    """Dimensiones físicas del paquete en centímetros."""

    largo_cm: float = Field(..., gt=0, description="Largo en cm.", examples=[30.0])
    ancho_cm: float = Field(..., gt=0, description="Ancho en cm.", examples=[20.0])
    alto_cm: float = Field(..., gt=0, description="Alto en cm.", examples=[15.0])


class GenerarGuiaRequest(BaseModel):
    """Entrada para FUN-7.1.2 (CA4-CA7): solicitud de guía a la transportadora."""

    model_config = ConfigDict(str_strip_whitespace=True)

    transportadora: Literal["Servientrega", "Coordinadora"] = Field(
        ...,
        description="Transportadora externa encargada del envío.",
        examples=["Servientrega"],
    )
    peso_kg: float = Field(
        ...,
        gt=0,
        description="Peso total del paquete en kilogramos.",
        examples=[2.5],
    )
    dimensiones: DimensionesPaquete = Field(
        ...,
        description="Dimensiones del paquete en centímetros.",
    )
    destino: str = Field(
        ...,
        min_length=5,
        max_length=150,
        description="Dirección y ciudad de destino del pedido.",
        examples=["Calle 45 # 28-15, Bucaramanga, Santander"],
    )

class ActualizarEstadoEnvioRequest(BaseModel):
    """Entrada para FUN-7.1.3 (actualización de estado enviada por la transportadora)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    numero_guia: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Número de guía asignado por la transportadora.",
        examples=["SRV-1234567890"],
    )
    estado: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="Estado reportado por la transportadora ('despachado', 'en tránsito', 'entregado').",
        examples=["despachado"],
    )
    fecha_hora: datetime = Field(
        ...,
        description="Fecha y hora del evento reportado en formato ISO 8601.",
        examples=["2026-11-24T00:15:00+00:00"],
    )
    
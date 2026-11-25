# app/core/carrier_gateway.py
from dataclasses import dataclass
import math
import time


class CarrierTimeoutError(Exception):
    """Se lanza cuando la transportadora supera los 10 segundos sin responder."""


class CarrierUnavailableError(Exception):
    """Se lanza cuando la transportadora externa retorna un error o no está disponible."""


@dataclass
class CarrierQuoteResult:
    carrier_name: str
    amount_cop: int
    currency: str = "COP"


class CarrierGatewayClient:
    """
    Cliente simulado para API-EXT-03 (Servientrega / Coordinadora).
    - Calcula tarifa según peso real, peso volumétrico y municipio destino.
    - Respeta el límite máximo de espera de 10 segundos (CA3).
    """

    MAX_TIMEOUT_SECONDS: float = 10.0

    def __init__(self):
        self.carrier_name: str = "Servientrega"
        self.force_error: bool = False
        self.simulated_delay_seconds: float = 0.0

    def get_shipping_quote(
        self,
        weight_kg: float,
        length_cm: float,
        width_cm: float,
        height_cm: float,
        destination_municipality: str,
        timeout_seconds: float = MAX_TIMEOUT_SECONDS,
    ) -> CarrierQuoteResult:
        # Simulación de latencia / timeout de 10 segundos (CA3)
        if self.simulated_delay_seconds > timeout_seconds:
            raise CarrierTimeoutError(
                f"La transportadora {self.carrier_name} no respondió dentro de {int(timeout_seconds)} segundos."
            )

        if self.simulated_delay_seconds > 0:
            time.sleep(min(self.simulated_delay_seconds, 0.05))

        if self.force_error:
            raise CarrierUnavailableError(
                f"Error de comunicación con la transportadora {self.carrier_name}."
            )

        # Cálculo realista de tarifa entera en COP (peso real vs volumétrico + tarifa base por destino)
        volumetric_weight = (length_cm * width_cm * height_cm) / 5000.0
        billable_weight = max(weight_kg, volumetric_weight)

        dest_normalized = destination_municipality.strip().lower()
        local_municipalities = {"bucaramanga", "floridablanca", "girón", "giron", "piedecuesta"}
        base_rate = 8500 if dest_normalized in local_municipalities else 14500

        total_cop = int(math.ceil(base_rate + (billable_weight * 2200)))

        return CarrierQuoteResult(
            carrier_name=self.carrier_name,
            amount_cop=total_cop,
            currency="COP"
        )

    def reset(self) -> None:
        self.carrier_name = "Servientrega"
        self.force_error = False
        self.simulated_delay_seconds = 0.0


carrier_gateway = CarrierGatewayClient()
from threading import Lock
from uuid import UUID

from app.domain.caracteristica_categoria import (
    CaracteristicaDefinida,
    RegistroAsociacionInterno,
)


class CaracteristicaCategoriaRepository:
    """Repositorio en memoria (thread-safe) de características por categoría y asociaciones."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._definiciones_por_categoria: dict[str, list[CaracteristicaDefinida]] = {
            "miniaturas": [
                CaracteristicaDefinida(nombre="escala", tipo_dato="texto", obligatoria=True),
                CaracteristicaDefinida(nombre="material", tipo_dato="texto", obligatoria=True),
                CaracteristicaDefinida(nombre="peana_mm", tipo_dato="numero", obligatoria=False),
            ],
            "pinturas": [
                CaracteristicaDefinida(nombre="acabado", tipo_dato="texto", obligatoria=True),
                CaracteristicaDefinida(nombre="volumen_ml", tipo_dato="numero", obligatoria=True),
                CaracteristicaDefinida(nombre="codigo_color", tipo_dato="texto", obligatoria=False),
            ],
            "juegos": [
                CaracteristicaDefinida(nombre="jugadores", tipo_dato="texto", obligatoria=True),
                CaracteristicaDefinida(nombre="duracion_min", tipo_dato="numero", obligatoria=False),
                CaracteristicaDefinida(nombre="idioma", tipo_dato="texto", obligatoria=False),
            ],
            "electrónica": [
                CaracteristicaDefinida(nombre="color", tipo_dato="texto", obligatoria=False),
                CaracteristicaDefinida(nombre="peso_kg", tipo_dato="numero", obligatoria=False),
            ],
        }
        self._asociaciones = RegistroAsociacionInterno()

    @staticmethod
    def _normalizar_categoria(categoria: str) -> str:
        return categoria.strip().lower()

    def obtener_definiciones_por_categoria(
        self, categoria: str
    ) -> list[CaracteristicaDefinida]:
        clave = self._normalizar_categoria(categoria)
        with self._lock:
            definiciones = self._definiciones_por_categoria.get(clave, [])
            return [item.model_copy() for item in definiciones]

    def guardar_asociaciones_producto(
        self, producto_id: UUID, valores: dict[str, object]
    ) -> dict[str, object]:
        return self._asociaciones.guardar(producto_id, valores)

    def obtener_asociaciones_producto(self, producto_id: UUID) -> dict[str, object]:
        return self._asociaciones.obtener(producto_id)

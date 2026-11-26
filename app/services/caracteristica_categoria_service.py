from typing import Any
from uuid import UUID

from fastapi import status

from app.core.errors import RecursoNoEncontradoError, ReglaNegocioError
from app.domain.caracteristica_categoria import (
    AsociacionCaracteristicasData,
    AsociarCaracteristicasRequest,
    CaracteristicasCategoriaData,
)
from app.domain.producto import ProductoRespuesta
from app.repositories.caracteristica_categoria_repository import (
    CaracteristicaCategoriaRepository,
)
from app.repositories.producto_repository import ProductoRepository


class CaracteristicaCategoriaService:
    """Lógica de negocio para consultar y asociar características de categoría a un producto."""

    def __init__(
        self,
        producto_repo: ProductoRepository,
        caracteristica_repo: CaracteristicaCategoriaRepository,
    ) -> None:
        self._producto_repo = producto_repo
        self._caracteristica_repo = caracteristica_repo

    def _obtener_producto_o_error(self, producto_id: UUID) -> ProductoRespuesta:
        producto = self._producto_repo.obtener_por_id(producto_id)
        if producto is None:
            raise RecursoNoEncontradoError(
                f"El producto con id '{producto_id}' no existe."[:200]
            )
        return producto

    def consultar_caracteristicas_categoria(
        self, producto_id: UUID
    ) -> CaracteristicasCategoriaData:
        producto = self._obtener_producto_o_error(producto_id)
        definiciones = self._caracteristica_repo.obtener_definiciones_por_categoria(
            producto.categoria
        )
        return CaracteristicasCategoriaData(
            producto_id=producto.id,
            categoria=producto.categoria,
            caracteristicas=definiciones,
        )

    def asociar_caracteristicas(
        self, producto_id: UUID, payload: AsociarCaracteristicasRequest
    ) -> AsociacionCaracteristicasData:
        producto = self._obtener_producto_o_error(producto_id)
        definiciones = self._caracteristica_repo.obtener_definiciones_por_categoria(
            producto.categoria
        )
        mapa_definiciones = {
            item.nombre.strip().lower(): item.nombre for item in definiciones
        }

        no_pertenecen: list[str] = []
        valores_invalidos: list[str] = []
        a_asociar: dict[str, Any] = {}

        for item in payload.caracteristicas:
            clave = item.nombre.strip().lower()
            if clave not in mapa_definiciones:
                no_pertenecen.append(item.nombre)
                continue

            if item.valor is None or (
                isinstance(item.valor, str) and not item.valor.strip()
            ):
                valores_invalidos.append(item.nombre)
                continue

            nombre_canonico = mapa_definiciones[clave]
            a_asociar[nombre_canonico] = (
                item.valor.strip() if isinstance(item.valor, str) else item.valor
            )

        if no_pertenecen:
            unicos_no_pertenecen = list(dict.fromkeys(no_pertenecen))
            lista_str = ", ".join(unicos_no_pertenecen)
            raise ReglaNegocioError(
                message=(
                    f"Operación rechazada: no pertenecen a la categoría "
                    f"'{producto.categoria}': {lista_str}."
                )[:200],
                data=unicos_no_pertenecen,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if valores_invalidos:
            unicos_invalidos = list(dict.fromkeys(valores_invalidos))
            lista_inv = ", ".join(unicos_invalidos)
            raise ReglaNegocioError(
                message=(
                    f"Valor inválido o vacío en características: {lista_inv}."
                )[:200],
                data=unicos_invalidos,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        asociaciones_guardadas = (
            self._caracteristica_repo.guardar_asociaciones_producto(
                producto.id, a_asociar
            )
        )

        caracteristicas_actualizadas = dict(producto.caracteristicas)
        caracteristicas_actualizadas.update(asociaciones_guardadas)
        producto.caracteristicas = caracteristicas_actualizadas

        return AsociacionCaracteristicasData(
            producto_id=producto.id,
            codigo=producto.codigo,
            categoria=producto.categoria,
            caracteristicas_asociadas=a_asociar,
            caracteristicas_producto=caracteristicas_actualizadas,
        )

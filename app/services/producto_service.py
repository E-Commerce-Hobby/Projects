from typing import Any
from uuid import UUID

from fastapi import status

from app.core.errors import ReglaNegocioError
from app.domain.producto import (
    ProductoActualizacion,
    ProductoRegistro,
    ProductoRespuesta,
)
from app.repositories.producto_repository import ProductoRepository


class ProductoService:
    """Lógica de negocio del registro y actualización de productos."""

    def __init__(
        self,
        repositorio: ProductoRepository,
        caracteristica_repo: Any | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._caracteristica_repo = caracteristica_repo

    def registrar(self, datos: ProductoRegistro) -> ProductoRespuesta:
        # RN-02: el código debe ser único dentro del catálogo (CA2)
        if self._repositorio.obtener_por_codigo(datos.codigo) is not None:
            raise ReglaNegocioError(
                "El código ya está registrado.",
                status_code=status.HTTP_409_CONFLICT,
            )

        # CA1: guardar y devolver el producto con su identificador
        return self._repositorio.crear(datos)

    def _es_categoria_valida(self, categoria: str) -> bool:
        categoria_limpia = categoria.strip().lower()
        if not categoria_limpia:
            return False

        if self._caracteristica_repo is not None:
            categorias_registradas = getattr(
                self._caracteristica_repo, "_definiciones_por_categoria", {}
            )
            if categorias_registradas:
                return any(
                    str(cat).strip().lower() == categoria_limpia
                    for cat in categorias_registradas.keys()
                )

        return categoria_limpia in {
            "miniaturas",
            "pinturas",
            "juegos",
            "electrónica",
            "electronica",
        }

    def actualizar(
        self, producto_id: UUID, datos: ProductoActualizacion
    ) -> ProductoRespuesta:
        # CA4: el producto debe existir antes de aplicar cambios
        producto_actual = self._repositorio.obtener_por_id(producto_id)
        if producto_actual is None:
            raise ReglaNegocioError(
                message="El producto indicado no existe.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        cambios = datos.model_dump(exclude_none=True)
        if not cambios:
            raise ReglaNegocioError(
                message="Debe enviar al menos un campo válido para actualizar.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # CA3: validar que la categoría exista si se intenta modificar
        if "categoria" in cambios and not self._es_categoria_valida(
            str(cambios["categoria"])
        ):
            raise ReglaNegocioError(
                message="Categoría inválida: la categoría indicada no existe.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # CA2 / RN-02: rechazar si el código ya pertenece a otro producto
        if "codigo" in cambios and cambios["codigo"] != producto_actual.codigo:
            existente_codigo = self._repositorio.obtener_por_codigo(
                str(cambios["codigo"])
            )
            if existente_codigo is not None and existente_codigo.id != producto_id:
                raise ReglaNegocioError(
                    message="Conflicto de código (RN-02): el código ya pertenece a otro producto.",
                    status_code=status.HTTP_409_CONFLICT,
                )

        # CA1: actualizar solo los campos enviados
        cambios_limpios: dict[str, Any] = dict(cambios)
        actualizado = self._repositorio.actualizar(producto_id, cambios_limpios)
        if actualizado is None:
            raise ReglaNegocioError(
                message="El producto indicado no existe.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return actualizado
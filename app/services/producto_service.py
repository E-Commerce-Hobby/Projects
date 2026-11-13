from app.core.errors import ReglaNegocioError
from app.domain.producto import ProductoRegistro, ProductoRespuesta
from app.repositories.producto_repository import ProductoRepository


class ProductoService:
    """Lógica de negocio del registro de productos."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repositorio = repositorio

    def registrar(self, datos: ProductoRegistro) -> ProductoRespuesta:
        # RN-02: el código debe ser único dentro del catálogo (CA2)
        if self._repositorio.obtener_por_codigo(datos.codigo) is not None:
            raise ReglaNegocioError("El código ya está registrado.")

        # CA1: guardar y devolver el producto con su identificador
        return self._repositorio.crear(datos)
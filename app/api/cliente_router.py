from fastapi import APIRouter, status
from app.domain.cliente_schema import ClienteRegistro
# Importamos la función exacta
from app.services.cliente_service import registrar_nuevo_cliente

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"])

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo cliente"
)
def registrar_cliente(datos: ClienteRegistro):
    # Usamos la función directa
    cliente_creado = registrar_nuevo_cliente(datos)

    # Copia sin el hash de la contraseña: nunca se expone un dato sensible.
    # No se modifica el registro guardado porque el login lo necesita.
    datos_publicos = {clave: valor for clave, valor in cliente_creado.items() if clave != "contrasena"}

    return {
        "success": True,
        "message": "Cliente registrado exitosamente",
        "data": datos_publicos
    }
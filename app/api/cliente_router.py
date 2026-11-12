from fastapi import APIRouter, status
from app.domain.cliente_schema import ClienteRegistro, ClienteRespuesta
from app.services.cliente_service import registrar_nuevo_cliente

# Creamos el enrutador para la URL /clientes
router = APIRouter(prefix="/clientes", tags=["Clientes"])

@router.post(
    "/",
    response_model=ClienteRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo cliente",
    description="Crea una cuenta de cliente validando que el correo no exista previamente (RN-05)."
)
def registrar_cliente(datos: ClienteRegistro):
    """
    Recibe los datos del cliente, los envía al servicio para validación y registro,
    y retorna los datos creados sin la contraseña.
    """
    cliente_creado = registrar_nuevo_cliente(datos)
    return cliente_creado
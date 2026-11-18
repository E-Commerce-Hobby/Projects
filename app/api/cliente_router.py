from fastapi import APIRouter, status
from app.domain.cliente_schema import ClienteRegistro, ClienteRespuesta
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"])
cliente_service = ClienteService()

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo cliente"
)
def registrar_cliente(datos: ClienteRegistro):
    cliente_creado = cliente_service.registrar_cliente(datos)
    
    return {
        "success": True,
        "message": "Cliente registrado exitosamente",
        "data": cliente_creado
    }
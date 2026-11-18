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
    
    return {
        "success": True,
        "message": "Cliente registrado exitosamente",
        "data": cliente_creado
    }
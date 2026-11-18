from fastapi import APIRouter, status
from app.domain.auth_schema import LoginPeticion
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])
auth_service = AuthService()

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión"
)
def iniciar_sesion(credenciales: LoginPeticion):
    datos_token = auth_service.autenticar_usuario(credenciales)
    
    return {
        "success": True,
        "message": "Inicio de sesión exitoso",
        "data": datos_token.model_dump()
    }
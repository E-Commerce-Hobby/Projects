from fastapi import APIRouter, status
from app.domain.auth_schema import LoginPeticion, SolicitudRecuperacion
from app.services.auth_service import autenticar_usuario, solicitar_recuperacion_contrasena

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

# ── HU-008: Inicio de sesión ──────────────────────────────────────────────────

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description="Valida las credenciales del cliente y retorna un token JWT con vigencia de 60 minutos."
)
def iniciar_sesion(credenciales: LoginPeticion):
    """HU-008: Endpoint para iniciar sesión y obtener un token JWT."""
    datos_token = autenticar_usuario(credenciales)

    return {
        "success": True,
        "message": "Inicio de sesión exitoso",
        "data": datos_token.model_dump()
    }

# ── HU-029: Recuperación de contraseña ───────────────────────────────────────

@router.post(
    "/recuperar-contrasena",
    status_code=status.HTTP_200_OK,
    summary="Solicitar recuperación de contraseña",
    description=(
        "Recibe el correo del cliente y, si está registrado, genera un token de un solo uso "
        "con vigencia de 30 minutos y simula el envío al correo. "
        "Siempre responde con un mensaje genérico (HTTP 200) para no revelar si el correo existe."
    )
)
def recuperar_contrasena(datos: SolicitudRecuperacion):
    """
    HU-029: Endpoint para solicitar la recuperación de contraseña.
    CA1: Correo registrado → genera token y simula envío.
    CA3: Correo no registrado → misma respuesta genérica (HTTP 200).
    CA4: Correo inválido → HTTP 400 automático por EmailStr.
    """
    resultado = solicitar_recuperacion_contrasena(datos)

    return {
        "success": True,
        "message": "Solicitud recibida",
        "data": resultado
    }
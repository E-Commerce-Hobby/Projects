from fastapi import APIRouter, Depends, status
from app.domain.auth_schema import LoginPeticion, SolicitudRecuperacion, AsignacionRol
from app.services.auth_service import (
    autenticar_usuario,
    solicitar_recuperacion_contrasena,
    asignar_rol_usuario,
)
from app.core.security import obtener_usuario_actual

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

# ── HU-030: Asignación de roles a usuarios ───────────────────────────────────

@router.patch(
    "/roles",
    status_code=status.HTTP_200_OK,
    summary="Asignar rol a un usuario",
    description=(
        "Permite a un administrador asignar uno de los roles permitidos "
        "(cliente, cajero o administrador) a un usuario existente. "
        "Requiere autenticación Bearer con rol administrador."
    ),
    responses={
        200: {
            "description": "Rol actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Rol actualizado exitosamente",
                        "data": {
                            "id_usuario": 2,
                            "correo": "usuario@correo.com",
                            "rol_anterior": "cliente",
                            "rol_nuevo": "cajero"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Rol inválido o intento de quitar el último administrador",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El rol no es válido. Roles permitidos: cliente, cajero, administrador.",
                        "data": ["cliente", "cajero", "administrador"]
                    }
                }
            }
        },
        401: {
            "description": "Token ausente, inválido o vencido",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Petición no autenticada, falta el token",
                        "data": []
                    }
                }
            }
        },
        403: {
            "description": "Usuario autenticado sin rol administrador",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No tienes permiso para asignar roles. Se requiere rol «administrador».",
                        "data": []
                    }
                }
            }
        },
        404: {
            "description": "Usuario destino no encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El usuario indicado no existe.",
                        "data": []
                    }
                }
            }
        }
    }
)
def asignar_rol(
    datos: AsignacionRol,
    usuario_actual: dict = Depends(obtener_usuario_actual)
):
    """HU-030: Endpoint para asignar un rol a un usuario (solo administradores)."""
    resultado = asignar_rol_usuario(datos, usuario_actual)

    return {
        "success": True,
        "message": "Rol actualizado exitosamente",
        "data": resultado.model_dump()
    }
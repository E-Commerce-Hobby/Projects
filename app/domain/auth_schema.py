from pydantic import BaseModel, EmailStr
from datetime import datetime

# ── HU-008: Inicio de sesión ──────────────────────────────────────────────────

class LoginPeticion(BaseModel):
    correo: EmailStr
    contrasena: str

class TokenRespuesta(BaseModel):
    token_acceso: str
    rol: str
    fecha_vencimiento: datetime

# ── HU-029: Recuperación de contraseña ───────────────────────────────────────

class SolicitudRecuperacion(BaseModel):
    """
    Datos de entrada para solicitar la recuperación de contraseña.
    CA4: EmailStr valida automáticamente el formato del correo (HTTP 400 si es inválido).
    """
    correo: EmailStr

# ── HU-030: Asignación de roles a usuarios ──────────────────────────────────

# Roles permitidos en el sistema (CA3). Se usan en minúscula en todo el proyecto.
ROLES_PERMITIDOS = ("cliente", "cajero", "administrador")


class AsignacionRol(BaseModel):
    """
    Datos de entrada para asignar un rol a un usuario.
    El rol se valida en el servicio para devolver el mensaje con los roles permitidos (CA3).
    """
    id_usuario: int
    rol: str


class RolAsignadoRespuesta(BaseModel):
    """Datos de salida al asignar un rol con éxito (CA1)."""
    id_usuario: int
    correo: str
    rol_anterior: str
    rol_nuevo: str


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
from pydantic import BaseModel, EmailStr
from datetime import datetime

class LoginPeticion(BaseModel):
    correo: EmailStr
    contrasena: str

class TokenRespuesta(BaseModel):
    token_acceso: str
    rol: str
    fecha_vencimiento: datetime
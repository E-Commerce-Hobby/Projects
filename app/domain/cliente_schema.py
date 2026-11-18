from pydantic import BaseModel, Field, field_validator
import re

class ClienteRegistro(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    correo: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    contrasena: str = Field(..., min_length=8)

    @field_validator('contrasena')
    @classmethod
    def validar_contrasena(cls, v: str) -> str:
        # Valida que tenga al menos una letra y un número
        if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
            raise ValueError('La contraseña debe tener al menos una letra y un número')
        return v

class ClienteRespuesta(BaseModel):
    id: int
    nombre: str
    correo: str
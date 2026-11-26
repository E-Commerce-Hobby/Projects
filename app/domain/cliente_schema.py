from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class ClienteRegistro(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    correo: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    contrasena: str = Field(..., min_length=8)

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, v: str) -> str:
        # Valida que tenga al menos una letra y un número
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("La contraseña debe tener al menos una letra y un número")
        return v


class ClienteRespuesta(BaseModel):
    id: int
    nombre: str
    correo: str


# ── HU-028: Esquemas de Gestión de Perfil ─────────────────────────────────────

class PreferenciasPerfil(BaseModel):
    notificaciones_correo: bool = True
    categorias_favoritas: list[str] = Field(default_factory=list)
    idioma: str = Field(default="es", pattern=r"^(es|en)$")


class PerfilActualizacion(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    correo: Optional[str] = Field(default=None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    direcciones: Optional[list[str]] = Field(default=None)
    preferencias: Optional[PreferenciasPerfil] = Field(default=None)

    @field_validator("nombre")
    @classmethod
    def validar_nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío o contener solo espacios.")
        return v.strip() if v is not None else None

    @field_validator("direcciones")
    @classmethod
    def validar_direcciones(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        direcciones_limpias = []
        for direccion in v:
            limpia = direccion.strip()
            if len(limpia) < 5 or len(limpia) > 200:
                raise ValueError("Cada dirección debe tener entre 5 y 200 caracteres.")
            direcciones_limpias.append(limpia)
        return direcciones_limpias


class PerfilRespuesta(BaseModel):
    id: int
    nombre: str
    correo: str
    direcciones: list[str] = Field(default_factory=list)
    preferencias: PreferenciasPerfil = Field(default_factory=PreferenciasPerfil)
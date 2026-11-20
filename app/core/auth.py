# app/core/auth.py
from typing import Optional
from fastapi import Header, status
from app.core.errors import ReglaNegocioError


def get_current_client_id(authorization: Optional[str] = Header(None)) -> int:
    """
    Dependencia de autenticación simulada para extraer el ID del cliente desde el token.
    Formato esperado en Swagger/Headers: 'Bearer client-1' (donde 1 es el ID del cliente).
    Si el header falta, está vacío o tiene formato inválido, lanza HTTP 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise ReglaNegocioError(
            "Usuario no autenticado: token ausente o formato inválido.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise ReglaNegocioError(
            "Usuario no autenticado: token vacío o vencido.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Esperamos un token simulado tipo 'client-10' o numérico '10'
    client_part = token.replace("client-", "")
    if not client_part.isdigit() or int(client_part) <= 0:
        raise ReglaNegocioError(
            "Usuario no autenticado: token inválido o vencido.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    return int(client_part)
# app/core/auth.py
from typing import Optional
from fastapi import Header, Depends, status
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

def require_staff_role(
    _client_id: int = Depends(get_current_client_id),
    x_user_role: Optional[str] = Header(default="administrador", alias="X-User-Role"),
) -> str:
    """
    Valida que el usuario autenticado tenga rol 'administrador' o 'cajero' (CA7).
    - Si el rol no está en {'administrador', 'cajero'}, lanza ReglaNegocioError con HTTP 403.
    """
    role_normalized = (x_user_role or "").strip().lower()
    if role_normalized not in {"administrador", "cajero"}:
        raise ReglaNegocioError(
            "Acceso denegado: se requiere rol 'administrador' o 'cajero' para consultar por orden.",
            status_code=status.HTTP_403_FORBIDDEN
        )
    return role_normalized
import jwt
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.errors import ReglaNegocioError

SECRET_KEY = "mi_clave_secreta_super_segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security_bearer = HTTPBearer(auto_error=False)

def verificar_contrasena(contrasena_plana: str, contrasena_hash: str) -> bool:
    # Hasheamos la que entra en el login para compararla con la base de datos
    hash_intento = hashlib.sha256(contrasena_plana.encode('utf-8')).hexdigest()
    return hash_intento == contrasena_hash 

def crear_token_acceso(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token_codificado = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token_codificado, expire

def obtener_usuario_actual(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)):
    if not credentials:
        raise ReglaNegocioError(message="Petición no autenticada, falta el token", status_code=401)
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        rol: str = payload.get("rol")
        if usuario_id is None or rol is None:
            raise ReglaNegocioError(message="Token alterado o inválido", status_code=401)
        return {"usuario_id": usuario_id, "rol": rol}
    except jwt.ExpiredSignatureError:
        raise ReglaNegocioError(message="El token está vencido", status_code=401)
    except jwt.PyJWTError:
        raise ReglaNegocioError(message="Token no autenticado", status_code=401)
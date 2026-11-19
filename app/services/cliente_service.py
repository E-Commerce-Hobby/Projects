import hashlib
from app.domain.cliente_schema import ClienteRegistro, ClienteRespuesta
from app.repositories.cliente_repository import obtener_cliente_por_correo, guardar_cliente
from app.core.errors import ReglaNegocioError

def hashear_contrasena(contrasena: str) -> str:
    """Genera un hash básico para cumplir el CA3 (Nunca guardar en texto plano)."""
    # Nota: En producción usaríamos librerías como bcrypt o Argon2.
    return hashlib.sha256(contrasena.encode('utf-8')).hexdigest()

def registrar_nuevo_cliente(datos: ClienteRegistro) -> dict:
    """Valida las reglas de negocio y coordina el registro del cliente."""
    
    # CA2 / RN-05: Verificar que el correo no esté registrado
    cliente_existente = obtener_cliente_por_correo(datos.correo)
    if cliente_existente:
        raise ReglaNegocioError(
            message="El correo ingresado ya se encuentra registrado.",
            data=["correo"],
            status_code=409 
        )
    
    # CA3: Hashear la contraseña antes de enviarla a la base de datos
    contrasena_hash = hashear_contrasena(datos.contrasena)
    
    # Enviar al repositorio para guardar
    cliente_creado = guardar_cliente(
        nombre=datos.nombre,
        correo=datos.correo,
        contrasena_hash=contrasena_hash
    )
    

    return ClienteRespuesta(**cliente_creado).model_dump()
import secrets
from datetime import datetime, timedelta, timezone

from app.domain.auth_schema import (
    LoginPeticion,
    TokenRespuesta,
    SolicitudRecuperacion,
    AsignacionRol,
    RolAsignadoRespuesta,
    ROLES_PERMITIDOS
)
from app.repositories.cliente_repository import (
    obtener_cliente_por_correo,
    guardar_token_recuperacion,
    obtener_cliente_por_id,
    cliente_existe,
    actualizar_rol
)
from app.core.security import verificar_contrasena, crear_token_acceso
from app.core.errors import ReglaNegocioError

# Vigencia del token de recuperación según HU-029 (CA1)
VIGENCIA_TOKEN_MINUTOS = 30

def autenticar_usuario(credenciales: LoginPeticion) -> TokenRespuesta:
    """HU-008: Valida las credenciales del cliente y retorna un token JWT."""
    # Buscamos el cliente por correo en el repositorio
    cliente = obtener_cliente_por_correo(credenciales.correo)

    # CA2: Si falla el correo o la clave, lanzamos el error estricto (401)
    if not cliente or not verificar_contrasena(credenciales.contrasena, cliente["contrasena"]):
        raise ReglaNegocioError(message="Credenciales inválidas", status_code=401)

    # Asumimos el rol por defecto si no lo tiene guardado
    rol_usuario = cliente.get("rol", "cliente")

    token, fecha_expiracion = crear_token_acceso(
        data={"sub": str(cliente["id"]), "rol": rol_usuario}
    )

    return TokenRespuesta(
        token_acceso=token,
        rol=rol_usuario,
        fecha_vencimiento=fecha_expiracion
    )

# ── HU-029: Recuperación de contraseña ───────────────────────────────────────

def solicitar_recuperacion_contrasena(datos: SolicitudRecuperacion) -> dict:
    """
    HU-029: Procesa la solicitud de recuperación de contraseña.

    CA1: Si el correo existe → genera token de un solo uso con vigencia de 30 min.
    CA2: Simula el envío del token al correo registrado (API-EXT-04 / SendGrid).
    CA3: Si el correo NO existe → respuesta idéntica al caso exitoso (seguridad).
    CA4: Cubierto por EmailStr en el schema (HTTP 400 automático).
    """
    cliente = obtener_cliente_por_correo(datos.correo)

    # CA1: Solo actuamos si el cliente existe (CA3: si no existe, ignoramos silenciosamente)
    if cliente:
        # Generamos token criptográficamente seguro de un solo uso
        token = secrets.token_urlsafe(32)
        expiracion = datetime.now(timezone.utc) + timedelta(minutes=VIGENCIA_TOKEN_MINUTOS)

        # Persistimos el token en memoria
        guardar_token_recuperacion(
            correo=datos.correo,
            token=token,
            expiracion=expiracion
        )

        # CA2: Simulamos el envío al servicio externo de correo (API-EXT-04)
        try:
            _simular_envio_correo(correo=cliente["correo"], token=token)
        except Exception:
            # HTTP 503 si el servicio de correo falla
            raise ReglaNegocioError(
                message="El servicio de envío de correo no está disponible. Intenta más tarde.",
                status_code=503
            )

    # CA1 + CA3: Respuesta genérica siempre. Nunca revelar si el correo existe o no.
    return {"confirmacion": "Si el correo está registrado, recibirás las instrucciones en breve."}


def _simular_envio_correo(correo: str, token: str) -> None:
    """
    Simulación del servicio externo de correo (API-EXT-04 / SendGrid).
    TODO: Reemplazar con integración real cuando API-EXT-04 esté disponible.
    """
    # Solo caracteres compatibles con la consola de Windows (cp1252)
    print("[SIMULACIÓN CORREO] -----------------------------")
    print(f"[SIMULACIÓN CORREO] Destinatario : {correo}")
    print(f"[SIMULACIÓN CORREO] Token        : {token}")
    print(f"[SIMULACIÓN CORREO] Enlace       : https://mi-app.com/restablecer?token={token}")
    print("[SIMULACIÓN CORREO] -----------------------------")


# ── HU-030: Asignación de roles a usuarios ──────────────────────────────────

def asignar_rol_usuario(datos: AsignacionRol, usuario_actual: dict) -> RolAsignadoRespuesta:
    """
    HU-030: Asigna un rol a un usuario.

    CA2: Solo un «administrador» puede asignar roles (403).
    CA3: El rol debe ser «cliente», «cajero» o «administrador» (400).
    CA4: El usuario debe existir (404).
    CA1: Actualiza el rol y retorna el rol anterior y el nuevo.
         Los tokens emitidos desde ahora llevan el rol nuevo (el login lee el rol guardado).
    """
    # CA2: Verificar que quien asigna sea administrador
    if usuario_actual.get("rol") != "administrador":
        raise ReglaNegocioError(
            message="No tienes permiso para asignar roles. Se requiere rol «administrador».",
            status_code=403
        )

    # CA3: Normalizar y validar el rol solicitado
    rol_nuevo = datos.rol.strip().lower()
    if rol_nuevo not in ROLES_PERMITIDOS:
        raise ReglaNegocioError(
            message=f"El rol no es válido. Roles permitidos: {', '.join(ROLES_PERMITIDOS)}.",
            data=list(ROLES_PERMITIDOS),
            status_code=400
        )

    # CA4: Verificar que el usuario exista
    if not cliente_existe(datos.id_usuario):
        raise ReglaNegocioError(message="El usuario indicado no existe.", status_code=404)

    # CA1: Actualizar el rol y confirmar
    rol_anterior = obtener_cliente_por_id(datos.id_usuario).get("rol", "cliente")
    usuario_actualizado = actualizar_rol(datos.id_usuario, rol_nuevo)

    return RolAsignadoRespuesta(
        id_usuario=usuario_actualizado["id"],
        correo=usuario_actualizado["correo"],
        rol_anterior=rol_anterior,
        rol_nuevo=rol_nuevo
    )
import hashlib
from app.domain.cliente_schema import (
    ClienteRegistro,
    ClienteRespuesta,
    PerfilActualizacion,
    PerfilRespuesta,
)
from app.repositories.cliente_repository import (
    obtener_cliente_por_correo,
    obtener_cliente_por_id,
    guardar_cliente,
    actualizar_perfil_cliente,
)
from app.core.errors import ReglaNegocioError


def hashear_contrasena(contrasena: str) -> str:
    """Genera un hash básico para cumplir el CA3 (Nunca guardar en texto plano)."""
    # Nota: En producción usaríamos librerías como bcrypt o Argon2.
    return hashlib.sha256(contrasena.encode("utf-8")).hexdigest()


def registrar_nuevo_cliente(datos: ClienteRegistro) -> dict:
    """Valida las reglas de negocio y coordina el registro del cliente."""

    # CA2 / RN-05: Verificar que el correo no esté registrado
    cliente_existente = obtener_cliente_por_correo(datos.correo)
    if cliente_existente:
        raise ReglaNegocioError(
            message="El correo ingresado ya se encuentra registrado.",
            data=["correo"],
            status_code=409  # Explícito: no depende del valor por defecto de errors.py
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


# ── HU-028: Gestión de perfil ─────────────────────────────────────────────────

def _formatear_perfil(cliente: dict) -> dict:
    """Construye la respuesta pública del perfil sin exponer la contraseña."""
    return PerfilRespuesta(
        id=cliente["id"],
        nombre=cliente["nombre"],
        correo=cliente["correo"],
        direcciones=cliente.get("direcciones", []),
        preferencias=cliente.get("preferencias", {}),
    ).model_dump()


def consultar_perfil_cliente(id_usuario: int, id_usuario_autenticado: int) -> dict:
    """Consulta el perfil propio del cliente autenticado (CA1, CA2)."""
    if id_usuario != id_usuario_autenticado:
        raise ReglaNegocioError(
            message="No tienes permiso para consultar el perfil de otro usuario.",
            data=["id_usuario"],
            status_code=403
        )

    cliente = obtener_cliente_por_id(id_usuario)
    if not cliente:
        raise ReglaNegocioError(
            message="El cliente solicitado no existe.",
            data=["id_usuario"],
            status_code=404
        )

    return _formatear_perfil(cliente)


def actualizar_perfil_usuario(
    id_usuario: int,
    id_usuario_autenticado: int,
    datos: PerfilActualizacion
) -> dict:
    """Actualiza parcialmente el perfil propio del cliente (CA4, CA5, CA6, CA7)."""
    if id_usuario != id_usuario_autenticado:
        raise ReglaNegocioError(
            message="No tienes permiso para modificar el perfil de otro usuario.",
            data=["id_usuario"],
            status_code=403
        )

    cliente = obtener_cliente_por_id(id_usuario)
    if not cliente:
        raise ReglaNegocioError(
            message="El cliente solicitado no existe.",
            data=["id_usuario"],
            status_code=404
        )

    campos_enviados = {
        clave: valor
        for clave, valor in datos.model_dump(exclude_unset=True).items()
        if valor is not None
    }

    if not campos_enviados:
        raise ReglaNegocioError(
            message="Debe enviar al menos un campo válido para actualizar el perfil.",
            data=[],
            status_code=400
        )

    # CA6 / RN-05: Verificar que el correo nuevo no pertenezca a otra cuenta
    if "correo" in campos_enviados:
        existente = obtener_cliente_por_correo(campos_enviados["correo"])
        if existente and existente["id"] != id_usuario:
            raise ReglaNegocioError(
                message="El correo ingresado ya está registrado en otra cuenta (RN-05).",
                data=["correo"],
                status_code=409
            )

    cliente_actualizado = actualizar_perfil_cliente(id_usuario, campos_enviados)
    return _formatear_perfil(cliente_actualizado)
import hashlib
from datetime import datetime

# ── HU-007 / HU-008: Almacén de clientes ─────────────────────────────────────

# Simulador de base de datos en memoria
clientes_db = []
cliente_id_counter = 1

def obtener_cliente_por_correo(correo: str):
    """Busca si el correo ya está registrado (sin distinguir mayúsculas/minúsculas)."""
    correo_busqueda = correo.lower()
    for cliente in clientes_db:
        if cliente["correo"].lower() == correo_busqueda:
            return cliente
    return None

def guardar_cliente(nombre: str, correo: str, contrasena_hash: str, rol: str = "cliente") -> dict:
    """Guarda el cliente simulando una base de datos y retorna los datos."""
    global cliente_id_counter

    nuevo_cliente = {
        "id": cliente_id_counter,
        "nombre": nombre,
        "correo": correo,
        "contrasena": contrasena_hash,  # CA3: Se guarda el hash, nunca el texto plano
        "rol": rol  # HU-030: todo cliente nuevo inicia con rol «cliente»
    }

    clientes_db.append(nuevo_cliente)
    cliente_id_counter += 1

    return nuevo_cliente

# ── HU-029: Almacén de tokens de recuperación ────────────────────────────────

# Estructura por entrada:
# clave  → token (str)
# valor  → { "correo": str, "expiracion": datetime, "usado": bool }
tokens_recuperacion_db: dict = {}

def guardar_token_recuperacion(correo: str, token: str, expiracion: datetime) -> dict:
    """
    Almacena el token de recuperación generado asociado al correo del cliente.
    Si ya existía un token previo para ese correo, lo sobreescribe (un solo uso activo).
    """
    # Eliminamos cualquier token anterior del mismo correo
    tokens_a_eliminar = [
        clave for clave, valor in tokens_recuperacion_db.items()
        if valor["correo"].lower() == correo.lower()
    ]
    for clave in tokens_a_eliminar:
        del tokens_recuperacion_db[clave]

    # Guardamos el nuevo token
    registro = {
        "correo": correo.lower(),
        "expiracion": expiracion,
        "usado": False
    }
    tokens_recuperacion_db[token] = registro
    return registro

def obtener_token_recuperacion(token: str) -> dict | None:
    """
    Busca y retorna el registro del token de recuperación.
    Retorna None si el token no existe.
    """
    return tokens_recuperacion_db.get(token)

# ── HU-030: Roles de usuario ────────────────────────────────────────────────

def obtener_cliente_por_id(id_cliente: int) -> dict | None:
    """Busca un cliente por su id."""
    for cliente in clientes_db:
        if cliente["id"] == id_cliente:
            return cliente
    return None


def cliente_existe(id_cliente: int) -> bool:
    """Contrato público (tanda 1): indica si existe un cliente con ese id."""
    return obtener_cliente_por_id(id_cliente) is not None


def actualizar_rol(id_cliente: int, rol_nuevo: str) -> dict:
    """Actualiza el rol del cliente y retorna el registro actualizado."""
    cliente = obtener_cliente_por_id(id_cliente)
    cliente["rol"] = rol_nuevo
    return cliente


def contar_administradores() -> int:
    """Cuenta cuántos usuarios tienen rol «administrador»."""
    return sum(1 for cliente in clientes_db if cliente.get("rol") == "administrador")


def crear_administrador_inicial() -> None:
    """
    Crea un administrador por defecto para poder asignar roles (HU-030).
    Sin él nadie podría asignar el primer rol de administrador.
    """
    if obtener_cliente_por_correo("admin@hobbyvault.com"):
        return
    guardar_cliente(
        nombre="Administrador",
        correo="admin@hobbyvault.com",
        contrasena_hash=hashlib.sha256("Admin123!".encode("utf-8")).hexdigest(),
        rol="administrador"
    )


crear_administrador_inicial()
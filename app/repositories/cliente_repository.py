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

def guardar_cliente(nombre: str, correo: str, contrasena_hash: str) -> dict:
    """Guarda el cliente simulando una base de datos y retorna los datos."""
    global cliente_id_counter

    nuevo_cliente = {
        "id": cliente_id_counter,
        "nombre": nombre,
        "correo": correo,
        "contrasena": contrasena_hash  # CA3: Se guarda el hash, nunca el texto plano
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
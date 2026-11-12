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
from uuid import uuid4

# Simulación de API Bodegas (API-INT-10)
ubicaciones_db: dict[str, dict] = {
    "BOD-001": {
        "codigo": "BOD-001",
        "nombre": "Bodega Central Bucaramanga",
        "direccion": "Carrera 27 # 50-10, Bucaramanga",
        "inventario": {
            "PROD-001": 10,
            "PROD-002": 8,
            "PROD-003": 5,
        },
    },
    "BOD-002": {
        "codigo": "BOD-002",
        "nombre": "Tienda Cabecera",
        "direccion": "Calle 52 # 35-20, Bucaramanga",
        "inventario": {
            "PROD-001": 15,
            "PROD-002": 2,
            "PROD-003": 5,
        },
    },
    "BOD-003": {
        "codigo": "BOD-003",
        "nombre": "Bodega Floridablanca",
        "direccion": "Anillo Vial Km 3, Floridablanca",
        "inventario": {
            "PROD-001": 10,
            "PROD-002": 8,
            "PROD-003": 0,
        },
    },
}

# Registros de despacho/envío por id_orden
envios_db: dict[str, dict] = {}


def listar_ubicaciones() -> list[dict]:
    """Retorna todas las bodegas/tiendas registradas."""
    return list(ubicaciones_db.values())


def obtener_ubicacion(codigo: str) -> dict | None:
    return ubicaciones_db.get(codigo)


def obtener_envio(id_orden: str) -> dict | None:
    return envios_db.get(id_orden)


def guardar_envio(envio: dict) -> dict:
    envios_db[envio["id_orden"]] = envio
    return envio


def solicitar_guia_transportadora(payload: dict) -> dict:
    """Simulación de API externa Servientrega / Coordinadora (API-EXT-03)."""
    prefijo = "SRV" if payload["transportadora"] == "Servientrega" else "CRD"
    numero_guia = f"{prefijo}-{uuid4().hex[:10].upper()}"
    return {
        "numero_guia": numero_guia,
        "transportadora": payload["transportadora"],
    }

# Registro en memoria de actualizaciones de envío rechazadas (HU-021: CA4)
actualizaciones_envio_rechazadas_db: list[dict] = []


def obtener_envio_por_guia(numero_guia: str) -> dict | None:
    """Busca un registro de envío por su número de guía (CA1)."""
    for envio in envios_db.values():
        if envio.get("numero_guia") == numero_guia:
            return envio
    return None


def registrar_actualizacion_envio_rechazada(registro: dict) -> dict:
    actualizaciones_envio_rechazadas_db.append(registro)
    return registro


def listar_actualizaciones_envio_rechazadas(numero_guia: str | None = None) -> list[dict]:
    if numero_guia is None:
        return list(actualizaciones_envio_rechazadas_db)
    return [
        r for r in actualizaciones_envio_rechazadas_db if r["numero_guia"] == numero_guia
    ]

# Registro en memoria de problemas/incidencias de envío (HU-039)
problemas_envio_db: list[dict] = []


def guardar_problema_envio(problema: dict) -> dict:
    """Guarda un problema de envío registrado por el operador logístico (CA2)."""
    problemas_envio_db.append(problema)
    return problema


def listar_problemas_envio(numero_guia: str | None = None) -> list[dict]:
    """Lista los problemas registrados, opcionalmente filtrados por número de guía."""
    if numero_guia is None:
        return list(problemas_envio_db)
    return [p for p in problemas_envio_db if p["numero_guia"] == numero_guia]
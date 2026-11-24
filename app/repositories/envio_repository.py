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
from fastapi import APIRouter, status
from app.domain.envio_schema import ConfirmarUbicacionRequest, GenerarGuiaRequest
from app.services.envio_service import (
    confirmar_ubicacion_despacho,
    consultar_envio,
    generar_guia_envio,
    seleccionar_ubicacion_despacho,
)

router = APIRouter(prefix="/api/v1/envios", tags=["Envíos y Logística"])


@router.get(
    "/{id_orden}/ubicaciones-disponibles",
    status_code=status.HTTP_200_OK,
    summary="Consultar y elegir ubicación de despacho (HU-020: FUN-7.1.4 CA1, CA3)",
    description=(
        "Retorna las bodegas/tiendas que cubren todos los productos de la orden y elige "
        "la de mayor cantidad total disponible (en empate, menor código)."
    ),
    responses={
        200: {
            "description": "Ubicaciones disponibles y ubicación seleccionada",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Ubicación de despacho evaluada exitosamente.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "ubicacion_seleccionada": {
                                "codigo": "BOD-002",
                                "nombre": "Tienda Cabecera",
                                "direccion": "Calle 52 # 35-20, Bucaramanga",
                                "disponibilidad_total_orden": 15,
                            },
                            "ubicaciones_disponibles": [],
                        },
                    }
                }
            },
        },
        404: {
            "description": "Orden inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-99999999' no existe.",
                        "data": ["id_orden"],
                    }
                }
            },
        },
        409: {
            "description": "Ninguna ubicación cubre todos los productos de la orden",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Ninguna ubicación cubre todos los productos solicitados en la orden.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "productos_sin_cobertura": ["PROD-001"],
                        },
                    }
                }
            },
        },
    },
)
def obtener_ubicaciones_despacho(id_orden: str):
    resultado = seleccionar_ubicacion_despacho(id_orden)
    return {
        "success": True,
        "message": "Ubicación de despacho evaluada exitosamente.",
        "data": resultado,
    }


@router.post(
    "/{id_orden}/ubicacion",
    status_code=status.HTTP_200_OK,
    summary="Confirmar y registrar ubicación de despacho (HU-020: FUN-7.1.4 CA2)",
    description="Registra la ubicación elegida asociada a la orden.",
    responses={
        200: {"description": "Ubicación de despacho registrada exitosamente"},
        404: {"description": "Orden o ubicación inexistente"},
        409: {"description": "Ubicación sin stock suficiente para la orden"},
    },
)
def registrar_ubicacion_despacho(
    id_orden: str,
    datos: ConfirmarUbicacionRequest | None = None,
):
    envio = confirmar_ubicacion_despacho(id_orden, datos)
    return {
        "success": True,
        "message": "Ubicación de despacho registrada exitosamente.",
        "data": envio,
    }


@router.post(
    "/{id_orden}/guia",
    status_code=status.HTTP_201_CREATED,
    summary="Generar guía de envío con transportadora externa (HU-020: FUN-7.1.2 CA4-CA7)",
    description=(
        "Verifica que la orden esté en estado 'pagada' y tenga ubicación registrada, "
        "solicita la guía a la transportadora (timeout 10 s) y la guarda asociada a la orden."
    ),
    responses={
        201: {
            "description": "Guía generada y guardada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Guía de envío generada y registrada exitosamente.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "numero_guia": "SRV-1234567890",
                            "transportadora": "Servientrega",
                            "estado_envio": "guía generada",
                        },
                    }
                }
            },
        },
        404: {"description": "Orden inexistente"},
        409: {
            "description": "Orden no pagada o sin ubicación de despacho registrada",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La orden 'ORD-A1B2C3D4' no está en estado 'pagada' (estado actual: 'pendiente de pago').",
                        "data": {"faltantes": ["estado pagada"]},
                    }
                }
            },
        },
        503: {
            "description": "Transportadora no disponible o tiempo de espera agotado (10 s)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "La transportadora no respondió en 10 segundos. No se generó ninguna guía.",
                        "data": {"guia_guardada": False},
                    }
                }
            },
        },
    },
)
def crear_guia_envio(id_orden: str, datos: GenerarGuiaRequest):
    envio = generar_guia_envio(id_orden, datos)
    return {
        "success": True,
        "message": "Guía de envío generada y registrada exitosamente.",
        "data": envio,
    }


@router.get(
    "/{id_orden}",
    status_code=status.HTTP_200_OK,
    summary="Consultar información de despacho y guía de una orden",
    responses={
        200: {"description": "Información de envío encontrada"},
        404: {"description": "No existe registro de envío para la orden"},
    },
)
def obtener_detalle_envio(id_orden: str):
    envio = consultar_envio(id_orden)
    return {
        "success": True,
        "message": "Información de envío consultada exitosamente.",
        "data": envio,
    }
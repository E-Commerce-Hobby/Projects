from fastapi import APIRouter, status
from app.domain.envio_schema import (
    ActualizarEstadoEnvioRequest,
    ConfirmarUbicacionRequest,
    GenerarGuiaRequest,
    RegistrarProblemaEnvioRequest,
)
from app.repositories import envio_repository
from app.services.envio_service import (
    actualizar_estado_envio,
    confirmar_ubicacion_despacho,
    consultar_envio,
    generar_guia_envio,
    registrar_problema_envio,
    seleccionar_ubicacion_despacho,
)

router = APIRouter(prefix="/api/v1/envios", tags=["Envíos y Logística"])

@router.post(
    "/problemas",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar problema de envío: pérdida o devolución (HU-039: FUN-7.1.5)",
    description=(
        "Identifica el pedido por número de guía, registra el problema ('pérdida' o 'devolución') "
        "con descripción de máximo 500 caracteres, operador y fecha/hora, cambia el envío a "
        "'con incidencia' e informa a Ventas mediante la API Estados Orden."
    ),
    responses={
        201: {
            "description": "Problema de envío registrado e incidencia notificada a Ventas",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Problema de envío registrado exitosamente.",
                        "data": {
                            "problema": {
                                "id_problema": "INC-A1B2C3D4",
                                "id_orden": "ORD-A1B2C3D4",
                                "numero_guia": "SRV-1234567890",
                                "tipo_problema": "pérdida",
                                "descripcion": "Paquete extraviado en tránsito.",
                                "operador": "OP-LOG-01",
                                "fecha_hora": "2026-11-24T00:35:00+00:00",
                            },
                            "estado_envio": "con incidencia",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Tipo de problema inválido o descripción fuera de rango (> 500 caracteres)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Tipo de problema inválido: debe ser 'pérdida' o 'devolución'.",
                        "data": ["tipo_problema"],
                    }
                }
            },
        },
        404: {
            "description": "Número de guía inexistente",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No existe ningún envío registrado con el número de guía 'SRV-NOEXISTE'.",
                        "data": ["numero_guia"],
                    }
                }
            },
        },
    },
)
def crear_problema_envio(datos: RegistrarProblemaEnvioRequest):
    resultado = registrar_problema_envio(datos)
    return {
        "success": True,
        "message": "Problema de envío registrado exitosamente.",
        "data": resultado,
    }


@router.get(
    "/problemas",
    status_code=status.HTTP_200_OK,
    summary="Consultar problemas de envío registrados (HU-039)",
)
def obtener_problemas_envio(numero_guia: str | None = None):
    return {
        "success": True,
        "message": "Problemas de envío consultados exitosamente.",
        "data": envio_repository.listar_problemas_envio(numero_guia),
    }

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


@router.patch(
    "/estado",
    status_code=status.HTTP_200_OK,
    summary="Actualizar estado del envío desde la transportadora (HU-021: FUN-7.1.3)",
    description=(
        "Identifica el pedido asociado al número de guía, actualiza el estado del envío "
        "('despachado', 'en tránsito', 'entregado') con fecha y hora, y sincroniza el estado "
        "de la orden vía HU-011 cuando corresponde ('despachado' o 'entregado')."
    ),
    responses={
        200: {
            "description": "Estado del envío actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Estado del envío actualizado exitosamente.",
                        "data": {
                            "id_orden": "ORD-A1B2C3D4",
                            "numero_guia": "SRV-1234567890",
                            "estado_envio": "despachado",
                            "fecha_hora": "2026-11-24T00:15:00+00:00",
                            "orden_actualizada": True,
                            "estado_orden": "enviada",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Estado de envío no permitido (rechazo registrado)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Estado de envío no permitido: 'perdido'. Valores válidos: despachado, en tránsito, entregado.",
                        "data": {"numero_guia": "SRV-1234567890", "estado": "perdido"},
                    }
                }
            },
        },
        404: {
            "description": "Número de guía inexistente (rechazo registrado)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No existe ningún envío registrado con el número de guía 'SRV-NOEXISTE'.",
                        "data": ["numero_guia"],
                    }
                }
            },
        },
    },
)
def procesar_actualizacion_envio(datos: ActualizarEstadoEnvioRequest):
    resultado = actualizar_estado_envio(datos)
    return {
        "success": True,
        "message": "Estado del envío actualizado exitosamente.",
        "data": resultado,
    }


@router.get(
    "/actualizaciones-rechazadas",
    status_code=status.HTTP_200_OK,
    summary="Consultar actualizaciones de envío rechazadas (HU-021: CA4)",
)
def obtener_actualizaciones_rechazadas(numero_guia: str | None = None):
    return {
        "success": True,
        "message": "Actualizaciones de envío rechazadas consultadas exitosamente.",
        "data": envio_repository.listar_actualizaciones_envio_rechazadas(numero_guia),
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
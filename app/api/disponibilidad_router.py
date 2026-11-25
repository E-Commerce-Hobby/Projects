from fastapi import APIRouter, status
from app.domain.disponibilidad_schema import (
    ValidarCarritoRequest,
    VerificarVentaRequest,
)
from app.services.disponibilidad_service import (
    consultar_disponibilidad_total,
    validar_disponibilidad_carrito,
    verificar_disponibilidad_venta,
)

router = APIRouter(prefix="/api/v1/disponibilidad", tags=["Disponibilidad"])


@router.get(
    "/{id_producto}",
    status_code=status.HTTP_200_OK,
    summary="Consultar disponibilidad total de un producto (HU-005: FUN-2.1.5)",
    description=(
        "Retorna la suma de unidades disponibles en todas las ubicaciones (sin incluir reservadas) "
        "y el detalle por ubicación. Si el producto existe sin inventario, retorna total 0."
    ),
    responses={
        200: {
            "description": "Disponibilidad consultada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Disponibilidad consultada exitosamente.",
                        "data": {
                            "id_producto": "PROD-001",
                            "total_disponible": 10,
                            "ubicaciones": [
                                {"ubicacion": "Tienda Física", "disponible": 4},
                                {"ubicacion": "Bodega Virtual", "disponible": 6},
                            ],
                        },
                    }
                }
            },
        },
        404: {
            "description": "Producto inexistente en el catálogo",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto 'PROD-999' no existe en el catálogo.",
                        "data": ["id_producto"],
                    }
                }
            },
        },
    },
)
def obtener_disponibilidad_producto(id_producto: str):
    resultado = consultar_disponibilidad_total(id_producto)
    return {
        "success": True,
        "message": "Disponibilidad consultada exitosamente.",
        "data": resultado,
    }


@router.post(
    "/verificar-venta",
    status_code=status.HTTP_200_OK,
    summary="Verificar disponibilidad antes de cobrar una venta (HU-005: FUN-2.2.3)",
    description=(
        "Verifica si hay stock disponible suficiente para todos los productos de una solicitud "
        "de venta (e-commerce o POS) antes de iniciar el cobro (RN-01)."
    ),
    responses={
        200: {
            "description": "Operación confirmada; el cobro puede continuar",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Disponibilidad confirmada. Puede continuar con el cobro.",
                        "data": {
                            "canal": "ecommerce",
                            "resultado": "confirmada",
                            "puede_continuar_cobro": True,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Datos faltantes o cantidades inválidas",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Valor inválido en el campo 'cantidad'.",
                        "data": None,
                    }
                }
            },
        },
        404: {
            "description": "Algún producto no existe en el catálogo",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto 'PROD-999' no existe en el catálogo.",
                        "data": ["id_producto"],
                    }
                }
            },
        },
        409: {
            "description": "Stock insuficiente en al menos un producto (RN-01)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Stock insuficiente para completar la venta (RN-01).",
                        "data": {
                            "resultado": "rechazada",
                            "puede_continuar_cobro": False,
                            "productos_sin_disponibilidad": [
                                {
                                    "id_producto": "PROD-002",
                                    "cantidad_solicitada": 5,
                                    "cantidad_disponible": 2,
                                }
                            ],
                        },
                    }
                }
            },
        },
    },
)
def verificar_venta(datos: VerificarVentaRequest):
    resultado = verificar_disponibilidad_venta(datos)
    return {
        "success": True,
        "message": "Disponibilidad confirmada. Puede continuar con el cobro.",
        "data": resultado,
    }


@router.post(
    "/validar-carrito",
    status_code=status.HTTP_200_OK,
    summary="Validar disponibilidad del carrito (HU-005: FUN-4.1.2)",
    description=(
        "Valida que todos los productos del carrito cuenten con disponibilidad suficiente "
        "para autorizar la creación de la orden (RN-01). Rechaza si está vacío o si Inventario "
        "supera el tiempo límite de 5 segundos."
    ),
    responses={
        200: {
            "description": "Carrito validado; autorizado para crear la orden",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Carrito validado. Autorizado para crear la orden.",
                        "data": {
                            "autorizado": True,
                            "puede_crear_orden": True,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Carrito vacío o datos inválidos",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El carrito está vacío. Debe incluir al menos un producto para confirmar.",
                        "data": ["productos"],
                    }
                }
            },
        },
        409: {
            "description": "Al menos un producto supera la disponibilidad total (RN-01)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No hay disponibilidad suficiente para confirmar el carrito (RN-01).",
                        "data": {
                            "autorizado": False,
                            "productos_sin_disponibilidad": [
                                {
                                    "id_producto": "PROD-002",
                                    "cantidad_solicitada": 4,
                                    "cantidad_disponible": 2,
                                }
                            ],
                        },
                    }
                }
            },
        },
        503: {
            "description": "Servicio de inventario no disponible (timeout de 5 segundos)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Servicio de inventario no disponible. Tiempo de espera agotado (5 s).",
                        "data": {"autorizado": False},
                    }
                }
            },
        },
    },
)
def validar_carrito(datos: ValidarCarritoRequest):
    resultado = validar_disponibilidad_carrito(datos)
    return {
        "success": True,
        "message": "Carrito validado. Autorizado para crear la orden.",
        "data": resultado,
    }
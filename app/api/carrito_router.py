from fastapi import APIRouter, status
from app.domain.carrito_schema import CarritoAgregarRequest, CarritoModificarRequest
from app.services.carrito_service import (
    agregar_producto_carrito,
    modificar_cantidad_carrito,
    eliminar_producto_carrito,
    obtener_carrito_actual,
)

router = APIRouter(prefix="/api/v1/carrito", tags=["Carrito"])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Consultar contenido actual del carrito",
    description="Retorna las líneas actuales del carrito y su valor total.",
)
def consultar_carrito():
    carrito = obtener_carrito_actual()
    return {
        "success": True,
        "message": "Carrito consultado exitosamente.",
        "data": carrito,
    }


@router.post(
    "/productos",
    status_code=status.HTTP_200_OK,
    summary="Agregar producto al carrito (HU-009: CA1-CA4)",
    description=(
        "Agrega un producto al carrito o suma su cantidad si ya existe. "
        "Recalcula el valor total y retorna el carrito completo."
    ),
    responses={
        200: {
            "description": "Producto agregado y carrito actualizado",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Producto agregado al carrito exitosamente.",
                        "data": {
                            "lineas": [
                                {
                                    "id_producto": "PROD-001",
                                    "nombre": "Set Miniaturas Dark Angels",
                                    "precio_unitario": 150000.0,
                                    "cantidad": 2,
                                    "subtotal": 300000.0,
                                }
                            ],
                            "valor_total": 300000.0,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Cantidad inválida (menor o igual a 0 o no entera)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Cantidad inválida: debe ser un número entero mayor o igual a 1.",
                        "data": ["cantidad"],
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
                        "message": "El producto solicitado no existe en el catálogo.",
                        "data": ["id_producto"],
                    }
                }
            },
        },
    },
)
def agregar_producto(datos: CarritoAgregarRequest):
    carrito = agregar_producto_carrito(datos.id_producto, datos.cantidad)
    return {
        "success": True,
        "message": "Producto agregado al carrito exitosamente.",
        "data": carrito,
    }


@router.patch(
    "/productos/{id_producto}",
    status_code=status.HTTP_200_OK,
    summary="Modificar cantidad de un producto en el carrito (HU-009: CA5-CA7)",
    description=(
        "Reemplaza la cantidad de un producto existente en el carrito, "
        "recalcula el valor total y retorna el carrito completo."
    ),
    responses={
        200: {
            "description": "Cantidad modificada y carrito actualizado",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Cantidad actualizada exitosamente.",
                        "data": {
                            "lineas": [
                                {
                                    "id_producto": "PROD-001",
                                    "nombre": "Set Miniaturas Dark Angels",
                                    "precio_unitario": 150000.0,
                                    "cantidad": 3,
                                    "subtotal": 450000.0,
                                }
                            ],
                            "valor_total": 450000.0,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Nueva cantidad inválida (<= 0 o no entera)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Cantidad inválida. Para quitar el producto del carrito debe usar la eliminación.",
                        "data": ["nueva_cantidad"],
                    }
                }
            },
        },
        404: {
            "description": "Producto no encontrado en el carrito",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto no se encuentra en el carrito.",
                        "data": ["id_producto"],
                    }
                }
            },
        },
    },
)
def modificar_producto(id_producto: str, datos: CarritoModificarRequest):
    carrito = modificar_cantidad_carrito(id_producto, datos.nueva_cantidad)
    return {
        "success": True,
        "message": "Cantidad actualizada exitosamente.",
        "data": carrito,
    }


@router.delete(
    "/productos/{id_producto}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar producto del carrito (HU-009: CA8-CA10)",
    description=(
        "Elimina la línea completa del producto en el carrito, recalcula el valor total "
        "y retorna el carrito completo (con 0 líneas y valor_total 0 si era el único)."
    ),
    responses={
        200: {
            "description": "Producto eliminado y carrito actualizado",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Producto eliminado del carrito exitosamente.",
                        "data": {
                            "lineas": [],
                            "valor_total": 0.0,
                        },
                    }
                }
            },
        },
        404: {
            "description": "Producto no encontrado en el carrito",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El producto no se encuentra en el carrito.",
                        "data": ["id_producto"],
                    }
                }
            },
        },
    },
)
def eliminar_producto(id_producto: str):
    carrito = eliminar_producto_carrito(id_producto)
    return {
        "success": True,
        "message": "Producto eliminado del carrito exitosamente.",
        "data": carrito,
    }
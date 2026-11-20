from fastapi import APIRouter, Depends, status
from app.core.security import obtener_usuario_actual
from app.domain.cliente_schema import ClienteRegistro, PerfilActualizacion
from app.services.cliente_service import (
    registrar_nuevo_cliente,
    consultar_perfil_cliente,
    actualizar_perfil_usuario,
)

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo cliente"
)
def registrar_cliente(datos: ClienteRegistro):
    cliente_creado = registrar_nuevo_cliente(datos)

    # Copia sin el hash de la contraseña: nunca se expone un dato sensible.
    datos_publicos = {
        clave: valor
        for clave, valor in cliente_creado.items()
        if clave != "contrasena"
    }

    return {
        "success": True,
        "message": "Cliente registrado exitosamente",
        "data": datos_publicos
    }


# ── HU-028: Gestión de perfil ─────────────────────────────────────────────────

@router.get(
    "/{id_usuario}/perfil",
    status_code=status.HTTP_200_OK,
    summary="Consultar perfil del cliente (HU-028)",
    description=(
        "Retorna el nombre, correo, direcciones y preferencias del cliente autenticado "
        "sin exponer la contraseña. Solo permite consultar el perfil propio."
    ),
    responses={
        200: {
            "description": "Perfil consultado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Perfil consultado exitosamente.",
                        "data": {
                            "id": 2,
                            "nombre": "Ana Gómez",
                            "correo": "ana@hobbyvault.com",
                            "direcciones": ["Calle 45 # 12-30, Bucaramanga"],
                            "preferencias": {
                                "notificaciones_correo": True,
                                "categorias_favoritas": ["Warhammer", "Rol"],
                                "idioma": "es"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "No autenticado (token ausente, inválido o vencido)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Petición no autenticada, falta el token",
                        "data": []
                    }
                }
            }
        },
        403: {
            "description": "Sin permiso para consultar el perfil de otro usuario",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No tienes permiso para consultar el perfil de otro usuario.",
                        "data": ["id_usuario"]
                    }
                }
            }
        },
        404: {
            "description": "Cliente no encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El cliente solicitado no existe.",
                        "data": ["id_usuario"]
                    }
                }
            }
        }
    }
)
def obtener_perfil(
    id_usuario: int,
    usuario_actual: dict = Depends(obtener_usuario_actual)
):
    id_autenticado = int(usuario_actual["usuario_id"])
    perfil = consultar_perfil_cliente(id_usuario, id_autenticado)

    return {
        "success": True,
        "message": "Perfil consultado exitosamente.",
        "data": perfil
    }


@router.patch(
    "/{id_usuario}/perfil",
    status_code=status.HTTP_200_OK,
    summary="Actualizar perfil del cliente (HU-028)",
    description=(
        "Modifica únicamente los campos enviados (nombre, correo, direcciones y/o preferencias) "
        "del perfil propio del cliente autenticado. Valida unicidad de correo (RN-05)."
    ),
    responses={
        200: {
            "description": "Perfil actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Perfil actualizado exitosamente.",
                        "data": {
                            "id": 2,
                            "nombre": "Ana María Gómez",
                            "correo": "ana.nueva@hobbyvault.com",
                            "direcciones": ["Carrera 27 # 34-10, Bucaramanga"],
                            "preferencias": {
                                "notificaciones_correo": False,
                                "categorias_favoritas": ["Miniaturas"],
                                "idioma": "es"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Datos faltantes o con formato inválido",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Debe enviar al menos un campo válido para actualizar el perfil.",
                        "data": []
                    }
                }
            }
        },
        401: {
            "description": "No autenticado (token ausente, inválido o vencido)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Petición no autenticada, falta el token",
                        "data": []
                    }
                }
            }
        },
        403: {
            "description": "Sin permiso para modificar el perfil de otro usuario",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No tienes permiso para modificar el perfil de otro usuario.",
                        "data": ["id_usuario"]
                    }
                }
            }
        },
        409: {
            "description": "Conflicto de negocio: correo ya registrado (RN-05)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "El correo ingresado ya está registrado en otra cuenta (RN-05).",
                        "data": ["correo"]
                    }
                }
            }
        }
    }
)
def actualizar_perfil(
    id_usuario: int,
    datos: PerfilActualizacion,
    usuario_actual: dict = Depends(obtener_usuario_actual)
):
    id_autenticado = int(usuario_actual["usuario_id"])
    perfil_actualizado = actualizar_perfil_usuario(id_usuario, id_autenticado, datos)

    return {
        "success": True,
        "message": "Perfil actualizado exitosamente.",
        "data": perfil_actualizado
    }
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api import productos
from app.api.auth_router import router as auth_router
from app.api.cliente_router import router as cliente_router
from app.api.event import router as event_router
from app.api.product_router import router as product_router
from app.core.errors import (
    ReglaNegocioError,
    custom_exception_handler,
    validation_exception_handler,
)


app = FastAPI(
    title="HobbyVault API",
    description=(
        "API B2C Omnicanal para Gestión de "
        "Productos, Servicios y Eventos"
    ),
    version="1.0.0",
)


# Manejadores globales de errores
app.add_exception_handler(
    ReglaNegocioError,
    custom_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)


# Routers de las historias de usuario (cada router se registra UNA sola vez)
app.include_router(productos.router, prefix="/api/v1")       # HU-001
app.include_router(cliente_router)                           # HU-007
app.include_router(auth_router)                              # HU-008 / HU-029 / HU-030
app.include_router(event_router)                             # HU-017
app.include_router(product_router, prefix="/api/v1")         # HU-002


@app.get("/")
def read_root():
    return {
        "message": "Servidor activo y funcionando"
    }

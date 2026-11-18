from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.errors import (
    ReglaNegocioError,
    regla_negocio_exception_handler,
    validation_exception_handler
)
from app.api.event import router as event_router

app = FastAPI(
    title="HobbyVault API",
    description="API B2C Omnicanal para Gestión de Productos, Servicios y Eventos",
    version="1.0.0"
)

# Registro de manejadores de errores personalizados (Garantiza HTTP 400 y formato JSON estándar)
app.add_exception_handler(ReglaNegocioError, regla_negocio_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Registro de routers por Historia de Usuario
app.include_router(event_router)
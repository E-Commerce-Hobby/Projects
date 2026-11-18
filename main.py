<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api import productos
from app.api.auth_router import router as auth_router
from app.api.cliente_router import router as cliente_router
from app.api.event import router as event_router
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
=======
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import productos
from app.api import productos
from app.api.cliente_router import router as cliente_router
from app.api.product_router import router as product_router
from app.api.product_router import router as product_router
from app.core.errors import custom_exception_handler, ReglaNegocioError

app = FastAPI(
    title="Mi Web Service",
    description="Servicio web con FastAPI y arquitectura limpia",
    version="1.0.0"
)

# RN-05 (HTTP 409)
app.add_exception_handler(ReglaNegocioError, custom_exception_handler)

app.include_router(productos.router, prefix="/api/v1")
app.include_router(cliente_router)
app.include_router(product_router, prefix="/api/v1")

CAMPOS_PRODUCTO = ["codigo", "categoria", "caracteristicas", "estado"]
>>>>>>> feature/HU-002


# Manejadores globales de errores
app.add_exception_handler(
    ReglaNegocioError,
    custom_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)


<<<<<<< HEAD
# Routers de las historias de usuario
app.include_router(
    productos.router,
    prefix="/api/v1",
)

app.include_router(cliente_router)
app.include_router(auth_router)
app.include_router(event_router)


@app.get("/")
def read_root():
    return {
        "message": "Servidor activo y funcionando"
    }
=======
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    if error["type"] == "value_error":
        message = str(error["msg"]).removeprefix("Value error, ")
    else:
        field = str(error["loc"][-1])
        message = f"El filtro '{field}' tiene un formato inválido."
    return JSONResponse(status_code=400, content={"detail": message[:200]})
>>>>>>> feature/HU-002

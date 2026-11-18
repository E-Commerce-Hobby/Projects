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


def _vacio(valor) -> bool:
    return (
        valor is None
        or (isinstance(valor, str) and not valor.strip())
        or (isinstance(valor, (dict, list)) and len(valor) == 0)
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    if error["type"] == "value_error":
        message = str(error["msg"]).removeprefix("Value error, ")
    else:
        field = str(error["loc"][-1])
        message = f"El filtro '{field}' tiene un formato inválido."
    return JSONResponse(status_code=400, content={"detail": message[:200]})
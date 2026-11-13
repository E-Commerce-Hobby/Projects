from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import productos
from app.core.errors import registrar_manejadores

app = FastAPI(
    title="Mi Web Service",
    description="Servicio web con FastAPI y arquitectura limpia",
    version="1.0.0"
)

registrar_manejadores(app)

app.include_router(productos.router, prefix="/api/v1")

CAMPOS_PRODUCTO = ["codigo", "categoria", "caracteristicas", "estado"]


def _vacio(valor) -> bool:
    return (
        valor is None
        or (isinstance(valor, str) and not valor.strip())
        or (isinstance(valor, (dict, list)) and len(valor) == 0)
    )


@app.exception_handler(RequestValidationError)
async def validacion_handler(request: Request, exc: RequestValidationError):
    """Convierte los errores de Pydantic en HTTP 400 con mensaje en español.

    Faltante/vacío -> CA3. Formato inválido -> CA4.
    """
    faltantes: list[str] = []
    invalidos: list[str] = []

    for err in exc.errors():
        loc = err.get("loc", ())

        if tuple(loc) == ("body",) and err["type"] == "missing":
            faltantes = list(CAMPOS_PRODUCTO)
            break

        if len(loc) < 2 or loc[0] != "body":
            continue

        campo = str(loc[1])
        destino = faltantes if (err["type"] == "missing" or _vacio(err.get("input"))) else invalidos
        if campo not in destino:
            destino.append(campo)

    invalidos = [c for c in invalidos if c not in faltantes]

    partes = []
    if faltantes:
        partes.append(f"Campos faltantes: {', '.join(faltantes)}.")
    if invalidos:
        partes.append(f"Campos con formato inválido: {', '.join(invalidos)}.")
    mensaje = " ".join(partes) or "El cuerpo de la solicitud no tiene un formato válido."

    return JSONResponse(
        status_code=400,
        content={
            "mensaje": mensaje[:200],
            "campos_faltantes": faltantes,
            "campos_invalidos": invalidos,
        },
    )


@app.get("/")
def read_root():
    return {"message": "Servidor activo y funcionando"}
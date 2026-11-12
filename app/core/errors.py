from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ReglaNegocioError(Exception):
    """Conflicto con una regla de negocio (HTTP 409)."""
    def __init__(self, mensaje: str, campos: list[str] | None = None):
        self.mensaje = mensaje
        self.campos = campos or []


class ServicioNoDisponibleError(Exception):
    """Servicio interno o externo no disponible (HTTP 503)."""
    def __init__(self, mensaje: str):
        self.mensaje = mensaje


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validacion(request: Request, exc: RequestValidationError):
        campos = []
        for e in exc.errors():
            campo = str(e["loc"][-1])
            if campo not in campos:
                campos.append(campo)
        mensaje = "Datos faltantes o inválidos: " + ", ".join(campos)
        return JSONResponse(status_code=400,
                            content={"mensaje": mensaje[:200], "campos": campos})

    @app.exception_handler(ReglaNegocioError)
    async def regla(request: Request, exc: ReglaNegocioError):
        return JSONResponse(status_code=409,
                            content={"mensaje": exc.mensaje[:200], "campos": exc.campos})

    @app.exception_handler(ServicioNoDisponibleError)
    async def no_disponible(request: Request, exc: ServicioNoDisponibleError):
        return JSONResponse(status_code=503,
                            content={"mensaje": exc.mensaje[:200], "campos": []})
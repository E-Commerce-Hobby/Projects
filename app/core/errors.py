from fastapi import Request
from fastapi.responses import JSONResponse

class ReglaNegocioError(Exception):
    def __init__(self, mensaje: str, campos: list = None):
        self.mensaje = mensaje
        self.campos = campos or []

async def custom_exception_handler(request: Request, exc: ReglaNegocioError):
    return JSONResponse(
        status_code=409,
        content={"mensaje": exc.mensaje, "campos": exc.campos}
    )
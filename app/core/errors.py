from fastapi import Request
from fastapi.responses import JSONResponse

class ReglaNegocioError(Exception):
    def __init__(self, message: str, data: list = None):
        self.message = message
        self.data = data or []

async def custom_exception_handler(request: Request, exc: ReglaNegocioError):
    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "message": exc.message,
            "data": exc.data
        }
    )

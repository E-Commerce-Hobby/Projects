from fastapi import Request
from fastapi.responses import JSONResponse

class ReglaNegocioError(Exception):
    def __init__(self, message: str, data: list = None, status_code: int = 409):
        self.message = message
        self.data = data or []
        self.status_code = status_code

async def custom_exception_handler(request: Request, exc: ReglaNegocioError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": exc.data
        }
    )
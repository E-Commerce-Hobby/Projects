from fastapi import FastAPI
from app.core.errors import custom_exception_handler, ReglaNegocioError
from app.api.cliente_router import router as cliente_router

app = FastAPI(
    title="Mi Web Service",
    description="Servicio web con FastAPI y arquitectura limpia",
    version="1.0.0"
)

# Conectamos el manejador de errores para cumplir la RN-05 (HTTP 409)
app.add_exception_handler(ReglaNegocioError, custom_exception_handler)

# Conectamos tu Historia de Usuario (HU-007)
app.include_router(cliente_router)

@app.get("/")
def read_root():
    return {"message": "Servidor activo y funcionando"}
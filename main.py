from fastapi import FastAPI
from app.core.errors import custom_exception_handler, ReglaNegocioError

# 1. Quitamos "Projects." y aseguramos el nombre "cliente_router"
from app.api.cliente_router import router as cliente_router

# 2. Importamos el router de autenticación
from app.api.auth_router import router as auth_router

app = FastAPI(
    title="Mi Web Service",
    description="Servicio web con FastAPI y arquitectura limpia",
    version="1.0.0"
)

# Conectamos el manejador de errores
app.add_exception_handler(ReglaNegocioError, custom_exception_handler)

# Conectamos las Historias de Usuario
app.include_router(cliente_router)
app.include_router(auth_router) 

@app.get("/")
def read_root():
    return {"message": "Servidor activo y funcionando"}
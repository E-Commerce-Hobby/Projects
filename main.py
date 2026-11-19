from fastapi import FastAPI
from app.core.errors import registrar_manejadores

app = FastAPI(
    title="Mi Web Service",
    description="Servicio web con FastAPI y arquitectura limpia",
    version="1.0.0"
)

registrar_manejadores(app)

@app.get("/")
def read_root():
    return {"message": "Servidor activo y funcionando"}
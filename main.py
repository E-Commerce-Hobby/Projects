from fastapi import FastAPI

app = FastAPI(
    title="Mi Web Service",
    description="Servicio web con FastAPI y arquitectura limpia",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Servidor activo y funcionando"}
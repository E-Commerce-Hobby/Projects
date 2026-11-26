from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.api.orden_router import router as orden_router
from app.api.envio_router import router as envio_router

from app.api import productos
from app.api.auth_router import router as auth_router
from app.api.carrito_router import router as carrito_router
from app.api.cliente_router import router as cliente_router
from app.api.disponibilidad_router import router as disponibilidad_router
from app.api.enrollment import router as enrollment_router
from app.api.event import router as event_router
from app.api.reminder import router as reminder_router
from app.api.shipping import router as shipping_router
from app.api.invoice import router as invoice_router
from app.api.inventory_retry import router as inventory_retry_router
from app.api.rejected_payment import router as rejected_payment_router
from app.api.refund import router as refund_router
from app.api.inventory import router as inventory_router
from app.api.pos import router as pos_router
from app.api.product_router import router as product_router
from app.api.receipt import router as receipt_router
from app.api.reserva_router import router as reserva_router
from app.api.sincronizacion_inventario_router import (
    router as sincronizacion_inventario_router,
)
from app.api.pago_router import router as pago_router
from app.core.errors import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
    ServicioNoDisponibleError,
    custom_exception_handler,
    not_found_exception_handler,
    service_unavailable_exception_handler,
    validation_exception_handler,
)


app = FastAPI(
    title="HobbyVault API",
    description=(
        "API B2C Omnicanal para Gestión de "
        "Productos, Servicios y Eventos"
    ),
    version="1.0.0",
)


# Manejadores globales de errores
app.add_exception_handler(
    ReglaNegocioError,
    custom_exception_handler,
)
app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)
app.add_exception_handler(
    RecursoNoEncontradoError,
    not_found_exception_handler,
)
app.add_exception_handler(
    ServicioNoDisponibleError,
    service_unavailable_exception_handler,
)


# Routers de las historias de usuario (cada router se registra UNA sola vez)
app.include_router(productos.router, prefix="/api/v1")       # HU-001
app.include_router(product_router, prefix="/api/v1")         # HU-002
app.include_router(inventory_router, prefix="/api/v1")       # HU-003
app.include_router(reserva_router)                           # HU-004
app.include_router(disponibilidad_router)                    # HU-005
app.include_router(sincronizacion_inventario_router)         # HU-006
app.include_router(cliente_router)                           # HU-007
app.include_router(auth_router)                              # HU-008 / HU-029 / HU-030
app.include_router(carrito_router)                           # HU-009
app.include_router(orden_router)                             # HU-010
app.include_router(pago_router)                              # HU-014
app.include_router(invoice_router)                           # HU-016
app.include_router(shipping_router)                          # HU-019
app.include_router(envio_router)                             # HU-020
app.include_router(inventory_retry_router)                   # HU-027
app.include_router(event_router)                             # HU-017
app.include_router(rejected_payment_router)                  # HU-033
app.include_router(refund_router)                            # HU-034
app.include_router(enrollment_router)                        # HU-037 / Inscripciones
app.include_router(reminder_router)                          # HU-038
app.include_router(pos_router, prefix="/api/v1")             # POS
app.include_router(receipt_router, prefix="/api/v1")         # Comprobante POS


@app.get("/")
def read_root():
    return {
        "message": "Servidor activo y funcionando"
    }
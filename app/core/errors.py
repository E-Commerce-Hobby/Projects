# app/core/errors.py

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ReglaNegocioError(Exception):
    def __init__(
        self,
        message: str,
        data: list | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        # El mensaje no debe superar los 200 caracteres según el DoD.
        self.message = message[:200]
        self.data = data or []
        self.status_code = status_code

        super().__init__(self.message)


async def custom_exception_handler(
    request: Request,
    exc: ReglaNegocioError,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": exc.data,
        },
    )


# Alias temporal para mantener compatibilidad con el código de HU-017.
regla_negocio_exception_handler = custom_exception_handler


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = exc.errors()
    missing_fields = []
    custom_messages = []

    for err in errors:
        field = err["loc"][-1] if err.get("loc") else "desconocido"
        err_type = err.get("type", "")
        msg = err.get("msg", "")

        if err_type == "missing":
            missing_fields.append(str(field))

        elif "Value error," in msg:
            custom_messages.append(
                msg.replace("Value error, ", "")
            )

        elif "int_parsing" in err_type or "int_from_float" in err_type:
            if field == "max_capacity":
                custom_messages.append(
                    "La capacidad es inválida (RN-04): "
                    "debe ser un número entero mayor o igual a 1."
                )
            else:
                custom_messages.append(
                    f"El campo '{field}' debe ser un número entero válido."
                )

        elif "datetime" in err_type:
            custom_messages.append(
                "La fecha es inválida: formato de fecha y hora incorrecto."
            )

        elif "string_too_short" in err_type and field == "name":
            custom_messages.append(
                "El nombre del evento debe tener entre 1 y 100 caracteres."
            )

        elif "string_too_long" in err_type and field == "name":
            custom_messages.append(
                "El nombre del evento no puede superar los 100 caracteres."
            )

        else:
            custom_messages.append(
                f"Valor inválido en el campo '{field}'."
            )

    if missing_fields:
        fields_str = ", ".join(missing_fields)
        final_message = f"Faltan campos obligatorios: {fields_str}."

    elif custom_messages:
        final_message = custom_messages[0]

    else:
        final_message = "Datos de entrada inválidos."

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "message": final_message[:200],
        },
    )

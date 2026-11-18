from app.domain.auth_schema import LoginPeticion, TokenRespuesta
# Fíjate que aquí importamos tu función exacta
from app.repositories.cliente_repository import obtener_cliente_por_correo 
from app.core.security import verificar_contrasena, crear_token_acceso
from app.core.errors import ReglaNegocioError

class AuthService:
    def autenticar_usuario(self, credenciales: LoginPeticion) -> TokenRespuesta:
        # Llamamos a tu función para buscar el correo
        cliente = obtener_cliente_por_correo(credenciales.correo)
        
        # CA2: Si falla el correo o la clave, lanzamos el error estricto (401)
        if not cliente or not verificar_contrasena(credenciales.contrasena, cliente["contrasena"]):
            raise ReglaNegocioError(message="Credenciales inválidas", status_code=401)
        
        # Asumimos el rol por defecto si no lo tiene guardado
        rol_usuario = cliente.get("rol", "Cliente")
        
        token, fecha_expiracion = crear_token_acceso(
            data={"sub": str(cliente["id"]), "rol": rol_usuario}
        )

        return TokenRespuesta(
            token_acceso=token,
            rol=rol_usuario,
            fecha_vencimiento=fecha_expiracion
        )
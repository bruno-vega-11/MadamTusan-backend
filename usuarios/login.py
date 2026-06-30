import sys
sys.path.insert(0, "/opt/python")

from helpers import (
    parsear_body, ok, bad_request, no_autorizado, error_interno,
    hashear_password, crear_token, tabla_usuarios
)


def lambda_handler(event, context):
    try:
        body = parsear_body(event)
        email     = body.get("email", "").strip().lower()
        password  = body.get("password", "")
        tenant_id = body.get("tenant_id", "").strip()

        if not email or not password or not tenant_id:
            return bad_request("email, password y tenant_id son requeridos")

        usuario = tabla_usuarios.get_item(
            Key={"tenant_id": tenant_id, "email": email}
        ).get("Item")

        if not usuario:
            return no_autorizado("Credenciales inválidas")

        if not usuario.get("activo", True):
            return no_autorizado("Cuenta desactivada")

        hash_calculado, _ = hashear_password(password, usuario["salt"])
        if hash_calculado != usuario["password_hash"]:
            return no_autorizado("Credenciales inválidas")

        token = crear_token(
            email=email,
            nombre=usuario.get("nombre", ""),
            tenant_id=tenant_id,
        )

        return ok({
            "mensaje": "Login exitoso",
            "token": token,
            "email": email,
            "nombre": usuario.get("nombre", ""),
            "tenant_id": tenant_id,
        })

    except Exception as e:
        print(f"Error en login: {e}")
        return error_interno()

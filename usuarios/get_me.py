import sys
sys.path.insert(0, "/opt/python")

from helpers import ok, no_autorizado, error_interno, tabla_usuarios

CAMPOS_OCULTOS = {"password_hash", "salt"}


def lambda_handler(event, context):
    try:
        auth = event.get("requestContext", {}).get("authorizer", {})
        email     = auth.get("email")
        tenant_id = auth.get("tenant_id")

        if not email or not tenant_id:
            return no_autorizado()

        usuario = tabla_usuarios.get_item(
            Key={"tenant_id": tenant_id, "email": email}
        ).get("Item")

        if not usuario:
            return no_autorizado("Usuario no encontrado")

        perfil = {k: v for k, v in usuario.items() if k not in CAMPOS_OCULTOS}
        return ok({"usuario": perfil})

    except Exception as e:
        print(f"Error en get-me: {e}")
        return error_interno()

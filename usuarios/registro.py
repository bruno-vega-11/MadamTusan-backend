import sys
sys.path.insert(0, "/opt/python")

from helpers import (
    parsear_body, creado, bad_request, conflicto, error_interno,
    hashear_password, email_valido, tabla_usuarios
)


def lambda_handler(event, context):
    try:
        body      = parsear_body(event)
        email     = body.get("email", "").strip().lower()
        password  = body.get("password", "")
        nombre    = body.get("nombre", "").strip()
        tenant_id = body.get("tenant_id", "").strip()

        if not email or not password or not nombre or not tenant_id:
            return bad_request("email, password, nombre y tenant_id son requeridos")

        if not email_valido(email):
            return bad_request("Email inválido")

        if len(password) < 8:
            return bad_request("La contraseña debe tener al menos 8 caracteres")

        # Verificar que el email no esté registrado en este tenant
        existente = tabla_usuarios.get_item(
            Key={"tenant_id": tenant_id, "email": email}
        ).get("Item")

        if existente:
            return conflicto("Ya existe un usuario con ese email")

        password_hash, salt = hashear_password(password)

        tabla_usuarios.put_item(Item={
            "tenant_id":     tenant_id,
            "email":         email,
            "nombre":        nombre,
            "password_hash": password_hash,
            "salt":          salt,
            "activo":        True,
        })

        return creado({
            "mensaje": "Usuario registrado correctamente",
            "email":   email,
            "nombre":  nombre,
        })

    except Exception as e:
        print(f"Error en registro: {e}")
        return error_interno()

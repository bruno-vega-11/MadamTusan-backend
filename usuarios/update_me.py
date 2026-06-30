import sys
sys.path.insert(0, "/opt/python")

from helpers import (
    parsear_body, ok, bad_request, no_autorizado, error_interno,
    tabla_usuarios, tabla_sesiones
)

CAMPOS_PERMITIDOS = {"nombre", "telefono", "direccion"}


def lambda_handler(event, context):
    try:
        auth      = event.get("requestContext", {}).get("authorizer", {})
        email     = auth.get("email")
        tenant_id = auth.get("tenant_id")
        token     = (event.get("headers", {}) or {}).get("authorization", "").replace("Bearer ", "").strip()

        if not email or not tenant_id:
            return no_autorizado()

        body = parsear_body(event)
        updates = {k: v for k, v in body.items() if k in CAMPOS_PERMITIDOS}

        if not updates:
            return bad_request(f"Sin campos válidos. Permitidos: {CAMPOS_PERMITIDOS}")

        update_expr  = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        expr_names   = {f"#{k}": k for k in updates}
        expr_values  = {f":{k}": v for k, v in updates.items()}

        tabla_usuarios.update_item(
            Key={"tenant_id": tenant_id, "email": email},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        # Si cambió el nombre, actualizar también la sesión activa
        if "nombre" in updates and token:
            tabla_sesiones.update_item(
                Key={"token": token},
                UpdateExpression="SET #n = :n",
                ExpressionAttributeNames={"#n": "nombre"},
                ExpressionAttributeValues={":n": updates["nombre"]},
            )

        return ok({"mensaje": "Perfil actualizado correctamente"})

    except Exception as e:
        print(f"Error en update-me: {e}")
        return error_interno()

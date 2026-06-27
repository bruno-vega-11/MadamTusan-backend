import sys
sys.path.insert(0, "/opt/python")

from helpers import (
    ok, no_autorizado, error_interno,
    sesion_de_token, tabla_sesiones
)


def lambda_handler(event, context):
    try:
        sesion = sesion_de_token(event)
        if not sesion:
            return no_autorizado()

        tabla_sesiones.delete_item(Key={"token": sesion["token"]})

        return ok({"mensaje": "Sesión cerrada correctamente"})

    except Exception as e:
        print(f"Error en logout: {e}")
        return error_interno()

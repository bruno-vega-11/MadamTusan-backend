import os
import json
import uuid
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
tabla_trabajadores = dynamodb.Table(os.environ["dev-t-trabajadores"])

ROLES_VALIDOS = {"COCINERO", "DESPACHADOR", "REPARTIDOR"}


def lambda_handle(event, context):
    """
    POST /trabajadores
    Crea un trabajador con rol y estado inicial LIBRE.

    Body esperado:
        {
          "tenant_id": "madamtusan",
          "nombre": "Juan Pérez",
          "rol": "COCINERO" | "DESPACHADOR" | "REPARTIDOR"
        }
    """
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    nombre = body.get("nombre")
    rol = body.get("rol")

    if not tenant_id or not nombre or rol not in ROLES_VALIDOS:
        return _response(
            400,
            {
                "mensaje": "tenant_id, nombre y rol (COCINERO|DESPACHADOR|REPARTIDOR) son obligatorios"
            },
        )

    trabajador_id = str(uuid.uuid4())
    item = {
        "tenant_id": tenant_id,
        "trabajador_id": trabajador_id,
        "nombre": nombre,
        "rol": rol,
        "estado": "LIBRE",
        "activo": True,
        "creado_en": datetime.now(timezone.utc).isoformat(),
    }

    tabla_trabajadores.put_item(Item=item)

    return _response(201, item)


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body_dict),
    }
import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
tabla_trabajadores = dynamodb.Table(os.environ.get("TABLE_TRABAJADORES", "dev-t-trabajadores"))


def lambda_handle(event, context):
    """
    GET /trabajadores?tenant_id=madamtusan&rol=COCINERO

    Lista los trabajadores de un tenant. El filtro por rol es opcional;
    útil para que la app de trabajadores muestre, por ejemplo, solo los
    repartidores y su estado actual (LIBRE/OCUPADO).
    """
    params = event.get("queryStringParameters") or {}
    tenant_id = params.get("tenant_id")
    rol = params.get("rol")

    if not tenant_id:
        return _response(400, {"mensaje": "tenant_id es obligatorio"})

    if rol:
        respuesta = tabla_trabajadores.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id),
            FilterExpression=Attr("rol").eq(rol),
        )
    else:
        respuesta = tabla_trabajadores.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id)
        )

    return _response(200, {"trabajadores": respuesta.get("Items", [])})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body_dict),
    }

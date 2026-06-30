import os
import json
import boto3

dynamodb = boto3.resource("dynamodb")
tabla_trabajadores = dynamodb.Table(os.environ["dev-t-trabajadores"])


def lambda_handle(event, context):
    """
    PUT /trabajadores/{trabajador_id}/eliminar

    Soft delete: marca activo=False y estado=INACTIVO en vez de borrar
    el registro, para conservar el historial de qué trabajador atendió
    qué pedido (campo trabajador_cocinero / trabajador_despachador /
    trabajador_repartidor en la tabla de pedidos).

    Body esperado:
        { "tenant_id": "madamtusan" }
    """
    trabajador_id = event["pathParameters"]["trabajador_id"]
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")

    if not tenant_id:
        return _response(400, {"mensaje": "tenant_id es obligatorio"})

    try:
        tabla_trabajadores.update_item(
            Key={"tenant_id": tenant_id, "trabajador_id": trabajador_id},
            UpdateExpression="SET activo = :inactivo, estado = :estado_inactivo",
            ExpressionAttributeValues={
                ":inactivo": False,
                ":estado_inactivo": "INACTIVO",
            },
            ConditionExpression="attribute_exists(trabajador_id)",
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {"mensaje": "Trabajador no encontrado"})

    return _response(200, {"mensaje": "Trabajador dado de baja"})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body_dict),
    }
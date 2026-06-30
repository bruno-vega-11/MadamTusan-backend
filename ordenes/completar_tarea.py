import os
import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
tabla_pedidos = os.environ.get('TABLE_PEDIDOS', 'dev-t-pedidos')
sfn = boto3.client("stepfunctions")
eventbridge = boto3.client("events")


def lambda_handle(event, context):
    """
    PUT /pedidos/{pedido_id}/tareas/completar

    Llamada desde la app web de trabajadores cuando el cocinero,
    despachador, repartidor o cliente confirma que terminó su paso.
    Recupera el task_token guardado por asignar_tarea.py y hace
    SendTaskSuccess para que Step Functions continúe.
    """
    pedido_id = event["pathParameters"]["pedido_id"]
    body = json.loads(event.get("body") or "{}")
    tenant_id = body["tenant_id"]
    paso = body["paso"]

    item = tabla_pedidos.get_item(
        Key={"tenant_id": tenant_id, "pedido_id": pedido_id}
    ).get("Item")

    if not item:
        return _response(404, {"mensaje": "Pedido no encontrado"})

    if item.get("paso_actual") != paso or not item.get("task_token_actual"):
        return _response(
            409,
            {"mensaje": f"El pedido no está esperando el paso {paso}"},
        )

    task_token = item["task_token_actual"]
    ahora = datetime.now(timezone.utc).isoformat()

    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps(
            {
                "tenant_id": tenant_id,
                "pedido_id": pedido_id,
                "origen": item.get("origen", "WEB"),
                "rappi_order_id": item.get("rappi_order_id"),
            }
        ),
    )

    # Libera al trabajador para que vuelva a estar disponible
    trabajador_id = item.get(f"trabajador_{paso.lower()}")
    if trabajador_id:
        tabla_trabajadores = dynamodb.Table(os.environ["TABLE_TRABAJADORES"])
        tabla_trabajadores.update_item(
            Key={"tenant_id": tenant_id, "trabajador_id": trabajador_id},
            UpdateExpression="SET estado = :libre",
            ExpressionAttributeValues={":libre": "LIBRE"},
        )

    tabla_pedidos.update_item(
        Key={"tenant_id": tenant_id, "pedido_id": pedido_id},
        UpdateExpression=f"SET fin_{paso.lower()} = :ts",
        ExpressionAttributeValues={":ts": ahora},
    )

    # Evento para notificar al cliente en tiempo real (websocket/push) y
    # alimentar el dashboard, desacoplado de la State Machine.
    eventbridge.put_events(
        Entries=[
            {
                "Source": "custom.madamtusan.pedidos",
                "DetailType": "PasoCompletado",
                "Detail": json.dumps(
                    {
                        "tenant_id": tenant_id,
                        "pedido_id": pedido_id,
                        "paso": paso,
                        "completado_en": ahora,
                    }
                ),
            }
        ]
    )

    return _response(200, {"mensaje": "Tarea completada", "paso": paso})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body_dict),
    }

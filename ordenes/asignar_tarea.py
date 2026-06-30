import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
tabla_pedidos = dynamodb.Table(os.environ["dev-t-pedidos"])


def lambda_handle(event, context):
    """
    Invocada por Step Functions con el patrón waitForTaskToken en cada
    paso humano (COCINERO, DESPACHADOR, REPARTIDOR, RECEPCION_CLIENTE).

    No completa la tarea: solo guarda el task_token en DynamoDB y marca
    el pedido como "ESPERANDO_<PASO>" para que la app web de trabajadores
    pueda mostrarlo en su bandeja. La ejecución de Step Functions queda
    pausada (sin costo de cómputo) hasta que completar_tarea.py llame a
    SendTaskSuccess con este mismo token.

    Input esperado:
        {
          "task_token": "...",
          "paso": "COCINERO" | "DESPACHADOR" | "REPARTIDOR" | "RECEPCION_CLIENTE",
          "trabajador_id": "..."  (opcional, no aplica en RECEPCION_CLIENTE),
          "pedido_data": { "tenant_id": "...", "pedido_id": "...", ... }
        }
    """
    task_token = event["task_token"]
    paso = event["paso"]
    trabajador_id = event.get("trabajador_id")
    pedido_data = event["pedido_data"]

    tenant_id = pedido_data["tenant_id"]
    pedido_id = pedido_data["pedido_id"]
    ahora = datetime.now(timezone.utc).isoformat()

    update_expr = (
        "SET estado = :estado, "
        "task_token_actual = :token, "
        "paso_actual = :paso, "
        f"inicio_{paso.lower()} = :ts"
    )
    expr_values = {
        ":estado": f"ESPERANDO_{paso}",
        ":token": task_token,
        ":paso": paso,
        ":ts": ahora,
    }

    if trabajador_id:
        update_expr += f", trabajador_{paso.lower()} = :trabajador_id"
        expr_values[":trabajador_id"] = trabajador_id

    tabla_pedidos.update_item(
        Key={"tenant_id": tenant_id, "pedido_id": pedido_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
    )

    # No se retorna nada relevante: la ejecución queda pausada hasta el callback.
    return {"ok": True}
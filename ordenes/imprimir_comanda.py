import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
tabla_pedidos = dynamodb.Table(os.environ["dev-t-pedidos"])


def lambda_handle(event, context):
    """
    Rama paralela de EtapaCocina. No bloquea ni depende del cocinero:
    simplemente deja registro de que la comanda fue impresa, junto con
    el detalle de platos para que el front de cocina pueda mostrarla.

    En un escenario real, aquí se podría invocar una impresora térmica
    conectada vía IoT Core, o simplemente generar un PDF/ticket en S3.
    Para la demo, se deja la evidencia en DynamoDB.
    """
    pedido_data = event.get("pedido_data") or event
    tenant_id = pedido_data.get("tenant_id")
    pedido_id = pedido_data.get("pedido_id")

    tabla_pedidos.update_item(
        Key={"tenant_id": tenant_id, "pedido_id": pedido_id},
        UpdateExpression="SET comanda_impresa_en = :ts",
        ExpressionAttributeValues={":ts": datetime.now(timezone.utc).isoformat()},
    )

    return {"comanda_impresa": True}
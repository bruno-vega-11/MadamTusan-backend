import json
import os
import decimal
import boto3

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PEDIDOS', 'dev-t-pedidos')
table = dynamodb.Table(table_name)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


def lambda_handle(event, context):
    """
    obtener_pedido — GET /pedidos/{pedido_id}?tenant_id=...
    Detalle completo de un pedido: estado actual, historial de pasos,
    tiempos de inicio/fin y trabajadores que lo atendieron.
    """
    try:
        params    = event.get('queryStringParameters') or {}
        tenant_id = params.get('tenant_id')
        pedido_id = (event.get('pathParameters') or {}).get('pedido_id')

        if not tenant_id or not pedido_id:
            return _res(400, {"error": "Se requieren 'tenant_id' (query) y 'pedido_id' (ruta)."})

        result = table.get_item(Key={'tenant_id': tenant_id, 'pedido_id': pedido_id})
        pedido = result.get('Item')

        if not pedido:
            return _res(404, {"error": f"Pedido '{pedido_id}' no encontrado."})

        # Ocultar taskToken por seguridad
        if 'tarea_actual' in pedido and 'task_token' in pedido['tarea_actual']:
            pedido['tarea_actual'] = {k: v for k, v in pedido['tarea_actual'].items() if k != 'task_token'}

        return _res(200, pedido)

    except Exception as e:
        print(f"ERROR en obtener_pedido: {str(e)}")
        return _res(500, {"error": str(e)})


def _res(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }

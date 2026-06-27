import json
import os
import decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr

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
    obtener_pedidos — GET /pedidos?tenant_id=...&estado=...
    Dashboard para trabajadores: lista los pedidos del restaurante.
    El parámetro 'estado' es opcional para filtrar por estado actual.
    """
    try:
        params    = event.get('queryStringParameters') or {}
        tenant_id = params.get('tenant_id')
        filtro    = params.get('estado')

        if not tenant_id:
            return _res(400, {"error": "Se requiere el parámetro 'tenant_id'."})

        kwargs = {'KeyConditionExpression': Key('tenant_id').eq(tenant_id)}
        if filtro:
            kwargs['FilterExpression'] = Attr('estado').eq(filtro)

        result  = table.query(**kwargs)
        pedidos = result.get('Items', [])

        # Ocultar taskTokens por seguridad
        for p in pedidos:
            if 'tarea_actual' in p and 'task_token' in p['tarea_actual']:
                p['tarea_actual'] = {k: v for k, v in p['tarea_actual'].items() if k != 'task_token'}

        pedidos.sort(key=lambda x: x.get('fecha_creacion', ''), reverse=True)

        return _res(200, {"pedidos": pedidos, "total": len(pedidos)})

    except Exception as e:
        print(f"ERROR en obtener_pedidos: {str(e)}")
        return _res(500, {"error": str(e)})


def _res(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }

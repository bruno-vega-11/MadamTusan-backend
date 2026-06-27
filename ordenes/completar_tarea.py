import json
import os
import decimal
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sfn      = boto3.client('stepfunctions')
table_name = os.environ.get('TABLE_PEDIDOS', 'dev-t-pedidos')
table = dynamodb.Table(table_name)

# Qué estado queda visible en la app después de que cada rol completa su paso
ESTADO_SIGUIENTE = {
    'COCINERO':          'EN_PREPARACION',
    'DESPACHADOR':       'EN_EMPAQUE',
    'REPARTIDOR':        'EN_CAMINO',
    'RECEPCION_CLIENTE': 'ENTREGADO',
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


def lambda_handle(event, context):
    """
    completar_tarea — PUT /pedidos/{pedido_id}/tareas/completar
    El trabajador llama a este endpoint cuando termina su parte del flujo.
    Actualiza DynamoDB y llama SendTaskSuccess para reanudar la Step Function.

    Body esperado: { "tenant_id": "...", "trabajador": { "nombre": "...", "rol": "..." } }
    """
    try:
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        pedido_id = (event.get('pathParameters') or {}).get('pedido_id')
        tenant_id = body.get('tenant_id')
        trabajador = body.get('trabajador', {})   # { nombre, rol }

        if not pedido_id or not tenant_id:
            return _res(400, {"error": "Faltan 'pedido_id' en la ruta o 'tenant_id' en el body."})

        # 1. Leer el pedido actual de DynamoDB para obtener el taskToken
        result = table.get_item(Key={'tenant_id': tenant_id, 'pedido_id': pedido_id})
        pedido = result.get('Item')

        if not pedido:
            return _res(404, {"error": f"Pedido '{pedido_id}' no encontrado."})

        tarea_actual = pedido.get('tarea_actual')
        if not tarea_actual or not tarea_actual.get('task_token'):
            return _res(409, {"error": "El pedido no tiene ninguna tarea activa pendiente."})

        task_token    = tarea_actual['task_token']
        paso          = tarea_actual['paso']
        estado_sig    = ESTADO_SIGUIENTE.get(paso)
        ahora         = datetime.utcnow().isoformat()

        if not estado_sig:
            return _res(400, {"error": f"Paso desconocido en tarea_actual: {paso}"})

        # 2. Completar la entrada del historial que corresponde a este paso
        historial = pedido.get('historial', [])
        for i in range(len(historial) - 1, -1, -1):
            if historial[i].get('paso') == paso and historial[i].get('fin') is None:
                historial[i]['fin']        = ahora
                historial[i]['trabajador'] = trabajador
                break

        # 3. Actualizar DynamoDB: nuevo estado + historial + limpiar tarea_actual
        table.update_item(
            Key={'tenant_id': tenant_id, 'pedido_id': pedido_id},
            UpdateExpression=(
                'SET #estado = :estado, '
                'ultima_actualizacion = :ts, '
                '#historial = :historial '
                'REMOVE tarea_actual'
            ),
            ExpressionAttributeNames={
                '#estado':    'estado',
                '#historial': 'historial',
            },
            ExpressionAttributeValues={
                ':estado':    estado_sig,
                ':ts':        ahora,
                ':historial': historial,
            }
        )

        # 4. Construir el output que recibirá el siguiente estado de la Step Function
        output = {k: v for k, v in pedido.items() if k != 'tarea_actual'}
        output['historial']        = historial
        output['estado']           = estado_sig
        output['ultima_actualizacion'] = ahora

        # 5. Reanudar la Step Function
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps(output, cls=DecimalEncoder)
        )

        print(f"INFO - Paso '{paso}' completado en pedido {pedido_id}. Nuevo estado: {estado_sig}")

        return _res(200, {
            "mensaje":      f"Paso '{paso}' completado.",
            "pedido_id":    pedido_id,
            "nuevo_estado": estado_sig,
        })

    except sfn.exceptions.TaskTimedOut:
        return _res(410, {"error": "La tarea ya expiró en el flujo de trabajo."})
    except sfn.exceptions.InvalidToken:
        return _res(400, {"error": "El token de tarea no es válido."})
    except Exception as e:
        print(f"ERROR en completar_tarea: {str(e)}")
        return _res(500, {"error": str(e)})


def _res(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }

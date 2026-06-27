import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PEDIDOS', 'dev-t-pedidos')
table = dynamodb.Table(table_name)

# Estado que se muestra en la app mientras se espera a cada rol
ESTADO_ESPERA = {
    'COCINERO':          'ESPERANDO_COCINERO',
    'DESPACHADOR':       'ESPERANDO_DESPACHADOR',
    'REPARTIDOR':        'ESPERANDO_REPARTIDOR',
    'RECEPCION_CLIENTE': 'ESPERANDO_ENTREGA',
}

def lambda_handle(event, context):
    """
    asignar_tarea — invocada por Step Functions con waitForTaskToken.
    Guarda el taskToken en DynamoDB y pone el pedido en estado ESPERANDO_X.
    La Step Function se queda pausada hasta que 'completar_tarea' llame SendTaskSuccess.
    """
    task_token  = event.get('task_token')
    paso        = event.get('paso')
    pedido_data = event.get('pedido_data', {})

    tenant_id = pedido_data.get('tenant_id')
    pedido_id = pedido_data.get('pedido_id')

    if not task_token or not paso or not tenant_id or not pedido_id:
        raise Exception("Faltan parámetros obligatorios: task_token, paso, tenant_id, pedido_id")

    nuevo_estado = ESTADO_ESPERA.get(paso)
    if not nuevo_estado:
        raise Exception(f"Paso desconocido: {paso}")

    ahora = datetime.utcnow().isoformat()

    entrada_historial = {
        'paso':       paso,
        'estado':     nuevo_estado,
        'inicio':     ahora,
        'fin':        None,
        'trabajador': None,
    }

    table.update_item(
        Key={'tenant_id': tenant_id, 'pedido_id': pedido_id},
        UpdateExpression=(
            'SET #estado = :estado, '
            'ultima_actualizacion = :ts, '
            'tarea_actual = :tarea, '
            '#historial = list_append(if_not_exists(#historial, :lista_vacia), :entrada)'
        ),
        ExpressionAttributeNames={
            '#estado':   'estado',
            '#historial': 'historial',
        },
        ExpressionAttributeValues={
            ':estado':      nuevo_estado,
            ':ts':          ahora,
            ':tarea':       {'task_token': task_token, 'paso': paso, 'asignado_en': ahora},
            ':entrada':     [entrada_historial],
            ':lista_vacia': [],
        }
    )

    print(f"INFO - Pedido {pedido_id} → {nuevo_estado}. Esperando acción del {paso}.")
    # La Step Function queda pausada aquí; el return de esta Lambda se ignora.

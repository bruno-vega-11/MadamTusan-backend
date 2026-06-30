import os
import boto3
from datetime import datetime
from helpers import a_decimal

# Inicializamos el recurso de DynamoDB fuera del handler
dynamodb = boto3.resource('dynamodb')
# Recuperamos el nombre de la tabla de pedidos desde las variables de entorno
table_name = os.environ.get('TABLE_PEDIDOS', 'dev-t-pedidos')
table = dynamodb.Table(table_name)


def lambda_handle(event, context):
    """
    cambiar_estado_pedido (Task de Step Functions)
    Recibe el nuevo estado y los datos consolidados del pedido.
    Inserta o actualiza el registro en la tabla de DynamoDB 'dev-t-pedidos'.
    """
    try:
        print(f"DEBUG - Payload recibido en cambiar_estado_pedido: {event}")

        # 1. Extraer los parámetros configurados desde la Step Function
        nuevo_estado = event.get('nuevo_estado')
        pedido_data = event.get('pedido_data', {})

        # Extraer las llaves primarias y datos de negocio esenciales
        tenant_id = pedido_data.get('tenant_id')
        pedido_id = pedido_data.get('pedido_id')

        if not tenant_id or not pedido_id:
            raise Exception("No se encontró 'tenant_id' o 'pedido_id' dentro de 'pedido_data'.")

        fecha_actualizacion = datetime.utcnow().isoformat()

        # 2. Construir la estructura completa del registro para la base de datos
        registro_pedido = {
            'tenant_id': tenant_id,
            'pedido_id': pedido_id,
            'estado': nuevo_estado,
            'origen': pedido_data.get('origen', 'WEB'),
            'cliente': pedido_data.get('cliente', {}),
            'items': pedido_data.get('items', []),
            'monto_total': pedido_data.get('monto_total', 0.0),
            'fecha_creacion': pedido_data.get('fecha_creacion'),
            'ultima_actualizacion': fecha_actualizacion,
            'historial': [],   # se irá llenando con cada paso del flujo
        }
        # Si el pedido fue rechazado por stock, arrastramos el motivo para que el cliente sepa por qué
        if 'motivo_rechazo' in pedido_data:
            registro_pedido['motivo_rechazo'] = pedido_data['motivo_rechazo']

        print(f"INFO - Guardando pedido {pedido_id} con estado '{nuevo_estado}' para el tenant '{tenant_id}'")

        # 3. Guardar de forma persistente en DynamoDB
        # DynamoDB no acepta float (items[].precio, monto_total llegan como
        # float desde el JSON del evento): hay que convertir a Decimal antes
        # de put_item, o explota con
        # "Float types are not supported. Use Decimal types instead."
        table.put_item(Item=a_decimal(registro_pedido))

        # 4. Devolver la respuesta a la Step Function
        # Retornamos un resumen claro. Este return se convertirá en el Output del paso actual de la Step Function
        return {
            "status": "SUCCESS",
            "pedido_id": pedido_id,
            "tenant_id": tenant_id,
            "estado_actualizado": nuevo_estado,
            "fecha": fecha_actualizacion
        }

    except Exception as e:
        print(f"Error crítico al cambiar el estado del pedido: {str(e)}")
        # Lanzamos la excepción para que la Step Function se entere del fallo si la base de datos se cae
        raise Exception(f"Fallo en persistencia de datos DynamoDB: {str(e)}")

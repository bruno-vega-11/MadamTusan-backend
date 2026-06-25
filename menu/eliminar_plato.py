import json
import os
import boto3

# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')
# Se recupera el nombre de la tabla de las variable de entrono definidas en serverless.yml
table_name = os.environ.get('TABLE_NAME', 'dev-t-menu')
table = dynamodb.Table(table_name)

def lambda_handle(event, context):
    """
    eliminar_plato (DELETE /menu/admin/platos/{platoId})
    Realiza un borrado lógico del plato agregando un flag 'eliminado: true' y 
    apagando su disponibilidad para no romper el historial de órdenes pasadas.
    """
    try:
        # Recuperar el platoId desde los Path Parameters de la URL
        path_params = event.get('pathParameters') or {}
        plato_id = path_params.get('platoId')

        # Recuperar el tenant_id del body (requerido por la Partition Key)
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
            
        tenant_id = body.get('tenant_id')

        # Validación de campos obligatorios
        if not tenant_id or not plato_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El 'platoId' en la ruta y 'tenant_id' en el body son obligatorios."})
            }

        # Ejecutar actualización para el borrado lógico
        # Marcamos disponible=False y eliminado=True
        table.update_item(
            Key={
                'tenant_id': tenant_id,
                'uuid': plato_id
            },
            UpdateExpression="SET disponible = :disp, eliminado = :elim",
            ExpressionAttributeValues={
                ':disp': False,
                ':elim': True
            }
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "mensaje": f"El plato '{plato_id}' de '{tenant_id}' ha sido eliminado lógicamente del catálogo.",
                "uuid": plato_id,
                "eliminado": True
            })
        }

    except Exception as e:
        print(f"Error detectado en eliminar_plato: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error interno del servidor al eliminar el plato: {str(e)}"})
        }
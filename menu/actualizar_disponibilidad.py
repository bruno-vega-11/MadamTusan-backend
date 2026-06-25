import json
import os
import boto3

# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')
# Se recupera el nombre de la tabla de las variable de entrono definidas en serverless.yml
table_name = os.environ.get('TABLE_MENU', 'dev-t-menu')
table = dynamodb.Table(table_name)

def lambda_handle(event, context):
    """
    actualizar_disponibilidad (PATCH /menu/admin/platos/{platoId}/stock)
    Cambia el campo booleano disponible (true/false) en tiempo real si se agota un insumo.
    """
    try:
        # Recuperar el platoId desde los Path Parameters de la URL
        path_params = event.get('pathParameters') or {}
        plato_id = path_params.get('platoId')

        # Recuperar el estado de disponibilidad del body
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        tenant_id = body.get('tenant_id')
        disponible = body.get('disponible')

        # Validación estricta del tipo de dato booleano
        if tenant_id is None or plato_id is None or not isinstance(disponible, bool):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Los parámetros 'platoId', 'tenant_id' y un booleano 'disponible' son obligatorios."})
            }

        #Ejecutar la actualización rápida del atributo específico
        table.update_item(
            Key={
                'tenant_id': tenant_id,
                'uuid': plato_id
            },
            UpdateExpression="SET disponible = :disp",
            ExpressionAttributeValues={
                ':disp': disponible
            }
        )

        estado_texto = "disponible" if disponible else "AGOTADO"
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "mensaje": f"El plato '{plato_id}' de '{tenant_id}' ha sido marcado como {estado_texto}.",
                "uuid": plato_id,
                "disponible": disponible
            })
        }

    except Exception as e:
        print(f"Error detectado en actualizar_disponibilidad: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error interno del servidor al modificar el stock: {str(e)}"})
        }
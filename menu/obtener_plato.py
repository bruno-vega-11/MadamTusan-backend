import json
import os
import boto3
from decimal import Decimal

# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')
# Se recupera el nombre de la tabla de las variable de entrono definidas en serverless.yml
table_name = os.environ.get('TABLE_MENU', 'dev-t-menu')
table = dynamodb.Table(table_name)


def lambda_handle(event, context):
    """
    obtener_plato (GET /menu/{platoId})
    Recibe el ID de un plato específico (por ejemplo, wok-01 que pertenece al Pollo Chi Jau Kay) 
    y devuelve su información detallada.

    Se usa cuando el cliente le da clic a la foto de un plato para ver la descripción completa,
    elegir porciones o añadirlo al carrito de compras.
    """
    try:
        # Extraer el platoId (uuid) de los Path Parameters (/menu/{platoId})
        path_params = event.get('pathParameters') or {}
        plato_id = path_params.get('platoId')
        
        # Extraer el tenant_id de los Query String Parameters (?tenant_id=madam-tusan)
        query_params = event.get('queryStringParameters') or {}
        tenant_id = query_params.get('tenant_id')
        
        # Validaciones de entrada
        if not plato_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El parámetro 'platoId' en la ruta es obligatorio."})
            }
            
        if not tenant_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El query parameter 'tenant_id' es obligatorio para validar el restaurante."})
            }
            
        # 3Obtener el ítem directamente usando el tenant_id y el platoId
        response = table.get_item(
            Key={
                'tenant_id': tenant_id,
                'uuid': plato_id
            }
        )
        
        plato = response.get('Item')
        
        # Si el plato no existe en ese restaurante, devolvemos un 404 Not Found
        if not plato:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": True
                },
                "body": json.dumps({"error": f"Plato con ID '{plato_id}' no fue encontrado en el catálogo de '{tenant_id}'."})
            }
            
        # Retornar la información detallada del plato de Madam Tusan
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            # Usamos una clase helpe: DecimalEncoder para que el precio no rompa el json.dumps
            "body": json.dumps({"plato": plato}, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error detectado en obtener_plato: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno al procesar la solicitud del plato."})
        }

# Helper para convertir campos Decimal de DynamoDB a tipos nativos de Python
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

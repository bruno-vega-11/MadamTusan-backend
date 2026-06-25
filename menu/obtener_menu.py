import json
import os
import boto3
from boto3.dynamodb.conditions import Key

# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')
# Se recupera el nombre de la tabla de las variable de entrono definidas en serverless.yml
table_name = os.environ.get('TABLE_NAME', 'dev-t-menu')
table = dynamodb.Table(table_name)

def lambda_handle(event, context):
    """
    obtener_menu (GET /menu)
    Devuelve toda la carta del chifa estructurada por categorías (Dim Sum, Especialidades del Wok, Banquetes, Bebidas).

    Consumida por el frontend en AWS Amplify para 
    mostrar en la página de inicio con los precios. 
    """
    try:
        # Extraer el tenant_id de los Query String Parameters (?tenant_id=madam-tusan)
        query_params = event.get('queryStringParameters') or {}
        tenant_id = query_params.get('tenant_id')
        
        # Validación para verificar que se envie el tenant
        if not tenant_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El parámetro 'tenant_id' es obligatorio."})
            }
            
        # Hacer la query a DynamoDB usando partion key
        response = table.query(
            KeyConditionExpression=Key('tenant_id').eq(tenant_id)
        )
        
        platos = response.get('Items', [])
        
        # Agrupar los platos por categorías para que el Frontend lo renderice 
        menu_estructurado = {}
        for plato in platos:
            categoria = plato.get('categoria', 'Otros')
            if categoria not in menu_estructurado:
                menu_estructurado[categoria] = []
                
            menu_estructurado[categoria].append({
                "id": plato.get('uuid'),
                "nombre": plato.get('nombre'),
                "descripcion": plato.get('descripcion'),
                "precio": float(plato.get('precio', 0)),
                "imagen_url": plato.get('imagen_url'),
                "disponible": plato.get('disponible', True)
            })

        # Retornar la respuesta con formato exitoso
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": menu_structured_response(menu_estructurado)
        }

    except Exception as e:
        print(f"Error detectado: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno del servidor al obtener el menú."})
        }

def menu_structured_response(menu_dict):
    # Funcion auxiliar que formatea la respuesta en una lista de categorías
    resultado = []
    for cat_nombre, lista_platos in menu_dict.items():
        resultado.append({
            "categoria": cat_nombre,
            "platos": lista_platos
        })
    return json.dumps({"menu": resultado})
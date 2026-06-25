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
    actualizar_plato (PUT /menu/admin/platos/{platoId})
    Permite modificar los datos de un plato existente (precio, descripción, nombre, categoría).
    """
    try:
        # Recuperar el platoId desde los Path Parameters
        path_params = event.get('pathParameters') or {}
        plato_id = path_params.get('platoId')

        # Recuperar y parsear el body enviado por el frontend
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        tenant_id = body.get('tenant_id')
        nombre = body.get('nombre')
        descripcion = body.get('descripcion')
        precio = body.get('precio')
        categoria = body.get('categoria')

        if not tenant_id or not plato_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El 'platoId' en la ruta y 'tenant_id' en el body son obligatorios."})
            }

        # Construir dinámicamente la expresión de actualización
        # Esto evita actualizar campos que el administrador no envió en el formulario
        update_parts = []
        expression_values = {}
        expression_names = {}

        if nombre:
            update_parts.append("#n = :nombre")
            expression_values[":nombre"] = nombre
            expression_names["#n"] = "nombre"
        if descripcion is not None: # Permitir vacío string
            update_parts.append("descripcion = :desc")
            expression_values[":desc"] = descripcion
        if precio is not None:
            expression_values[":precio"] = int(precio) if float(precio).is_integer() else float(precio)
            update_parts.append("precio = :precio")
        if categoria:
            update_parts.append("categoria = :cat")
            expression_values[":cat"] = categoria

        if not update_parts:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "No se enviaron campos válidos para actualizar."})
            }

        # Unimos las partes: "SET #n = :nombre, precio = :precio, ..."
        update_expression = "SET " + ", ".join(update_parts)

        #Ejecutar la actualización en DynamoDB
        response = table.update_item(
            Key={
                'tenant_id': tenant_id,
                'uuid': plato_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
            ReturnValues="UPDATED_NEW" # Nos devuelve solo lo que cambió
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "mensaje": f"Plato {plato_id} de {tenant_id} actualizado correctamente.",
                "atributos_actualizados": json.loads(json.dumps(response.get('Attributes'), default=float))
            })
        }

    except Exception as e:
        print(f"Error detectado en actualizar_plato: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error interno al actualizar el plato: {str(e)}"})
        }

import json
import os
import boto3
from decimal import Decimal

# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')
# Se recupera el nombre de la tabla de las variables de entorno definidas en serverless.yml
table_name = os.environ.get('TABLE_MENU', 'dev-t-menu')
table = dynamodb.Table(table_name)

def lambda_handle(event, context):
    """
    actualizar_plato (PUT /menu/admin/platos/{platoId})
    Permite modificar de forma dinámica y segura los datos de un plato existente.
    Si un campo no se envía en el body, se conserva intacto en la base de datos.
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
        imagen_url = body.get('imagen_url')
        disponible = body.get('disponible')

        # Validación estricta de llaves primarias
        if not tenant_id or not plato_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "El 'platoId' en la ruta y 'tenant_id' en el body son obligatorios."})
            }

        # Construir dinámicamente la expresión de actualización para proteger los datos antiguos
        update_parts = []
        expression_values = {}
        expression_names = {}

        # 1. Validar Nombre
        if nombre is not None and str(nombre).strip() != "":
            update_parts.append("#n = :nombre")
            expression_values[":nombre"] = str(nombre).strip()
            expression_names["#n"] = "nombre"

        # 2. Validar Descripción (Permite modificar si viene un texto válido o vacío explícito, pero no borra si se omite)
        if descripcion is not None:
            update_parts.append("descripcion = :desc")
            expression_values[":desc"] = str(descripcion).strip()

        # 3. Validar Precio (Protección estricta contra strings vacíos o letras y conversión a tipo numérico)
        if precio is not None and str(precio).strip() != "":
            try:
                precio_num = float(precio)
                # Almacenamos en DynamoDB usando su propio tipo numérico seguro (Decimal)
                expression_values[":precio"] = Decimal(str(precio_num))
                update_parts.append("precio = :precio")
            except (ValueError, TypeError):
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({"error": "El campo 'precio' debe ser un número válido."})
                }

        # 4. Validar Categoría
        if categoria is not None and str(categoria).strip() != "":
            update_parts.append("categoria = :cat")
            expression_values[":cat"] = str(categoria).strip()

        # 5. Validar Imagen URL (Por si el administrador decide actualizar la foto del plato en S3)
        if imagen_url is not None and str(imagen_url).strip() != "":
            update_parts.append("imagen_url = :img")
            expression_values[":img"] = str(imagen_url).strip()

        # 6. Validar Disponibilidad (Evalúa explícitamente booleanos para evitar confusiones de tipo)
        if disponible is not None:
            if isinstance(disponible, bool):
                update_parts.append("disponible = :disp")
                expression_values[":disp"] = disponible
            elif str(disponible).lower() in ['true', 'false']:
                update_parts.append("disponible = :disp")
                expression_values[":disp"] = str(disponible).lower() == 'true'

        # Si el payload venía vacío o solo con el tenant_id, no hacemos nada
        if not update_parts:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"message": "No se enviaron campos nuevos o válidos para actualizar."})
            }

        # Unimos las expresiones dinámicas generadas
        update_expression = "SET " + ", ".join(update_parts)

        # Ejecutar la actualización controlada en DynamoDB
        response = table.update_item(
            Key={
                'tenant_id': tenant_id,
                'uuid': plato_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
            ReturnValues="UPDATED_NEW"  # Devuelve exclusivamente el mapa de datos que mutaron
        )

        # Retornamos la respuesta codificada de forma segura con el DecimalEncoder
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "mensaje": f"Plato {plato_id} de {tenant_id} actualizado correctamente.",
                "atributos_actualizados": response.get('Attributes', {})
            }, cls=DecimalEncoder) # Usa el codificador para evitar errores con los números
        }

    except Exception as e:
        print(f"Error detectado en actualizar_plato: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": f"Error interno al actualizar el plato: {str(e)}"})
        }

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
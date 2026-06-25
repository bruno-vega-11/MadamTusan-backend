import json
import os
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal


# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')

# Se recupera el nombre de la tabla de las variables de entorno definidas en serverless.yml
table_name = os.environ.get('TABLE_MENU', 'dev-t-menu')
table = dynamodb.Table(table_name)

# Se obtiene el nombre del bucket de imágenes de las variables de entorno definidas en serverless.yml
bucket_name = os.environ.get('BUCKET_MENU_IMAGE', 'dev-b-menu-images')

# Inicializamos el cliente de S3 para generar la Presigned URL
s3_client = boto3.client('s3')

def lambda_handle(event, context):
    """
    crear_plato (POST /menu/admin/platos)
    Permite al administrador del chifa agregar un nuevo plato a DynamoDB y 
    genera una Presigned URL de S3 para la subida directa de la imagen.
    """
    try:
        # Recuperar el body del evento enviado por el frontend
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
            
        # Extraer los campos requeridos para el plato
        tenant_id = body.get('tenant_id')
        uuid = body.get('uuid')                 
        nombre = body.get('nombre')
        descripcion = body.get('descripcion')
        precio = body.get('precio')
        categoria = body.get('categoria')
        nombre_archivo_imagen = body.get('nombre_imagen')
        
        # Validaciones de campos obligatorios
        if not all([tenant_id, uuid, nombre, precio, categoria]):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Faltan campos obligatorios (tenant_id, uuid, nombre, precio, categoria)."})
            }

        # Calcular la URL pública final que tendrá la imagen una vez subida a S3
        s3_key = f"{tenant_id}/{uuid}-{nombre_archivo_imagen}"
        imagen_url_final = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

        # Guardar el nuevo plato en la tabla de DynamoDB usando Decimal
        nuevo_plato = {
            'tenant_id': tenant_id,
            'uuid': uuid,
            'nombre': nombre,
            'descripcion': descripcion,
            'precio': Decimal(str(precio)), 
            'categoria': categoria,
            'imagen_url': imagen_url_final,
            'disponible': True 
        }
        
        table.put_item(Item=nuevo_plato)

        # Generar la Presigned URL de S3 para que el frontend suba la foto directamente
        url_firmada_s3 = ""
        if nombre_archivo_imagen:
            try:
                url_firmada_s3 = s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': s3_key,
                        'ContentType': 'image/jpeg' 
                    },
                    ExpiresIn=300 
                )
            except ClientError as e:
                print(f"Error al generar Presigned URL: {str(e)}")

        # Responder de forma exitosa. 
        # NOTA: Usamos cls=DecimalEncoder para mapear el objeto 'nuevo_plato' de forma segura
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "mensaje": "Plato de Madam Tusan registrado con éxito.",
                "plato": nuevo_plato,
                "upload_url_s3": url_firmada_s3 
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error detectado en crear_plato: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error interno del servidor al crear el plato: {str(e)}"})
        }

# Helper para convertir campos Decimal de DynamoDB a tipos nativos de Python en el JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
import json
import os
import boto3
from botocore.exceptions import ClientError

# Se inicializa el cliente de DynamoDB fuera del handler para reutilizar la conexión
dynamodb = boto3.resource('dynamodb')
# Se recupera el nombre de la tabla de las variable de entrono definidas en serverless.yml
table_name = os.environ.get('TABLE_NAME', 'dev-t-menu')
table = dynamodb.Table(table_name)
# Se obtiene el nombre del bucket de imágenes  de las variables de entorno definidas en serverless.yml
bucket_name = os.environ.get('BUCKET_NAME','dev-b-menu-images')
s3_client = boto3.client('s3')

def lambda_handle(event, context):
    """
    crear_plato (POST /menu/admin/platos)

    Permite al administrador del chifa agregar un nuevo plato a la base de datos de DynamoDB.

    Esta Lambda debe recibir los datos del plato y opcionalmente interactuar con Amazon S3 para registrar
    la URL de la imagen que se acaba de subir al bucket.
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
        # Estructura limpia dentro del bucket por inquilino: "tenant_id/uuid_nombre.jpg"
        s3_key = f"{tenant_id}/{uuid}-{nombre_archivo_imagen}"
        imagen_url_final = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

        # Guardar el nuevo plato en la tabla de DynamoDB
        nuevo_plato = {
            'tenant_id': tenant_id,
            'uuid': uuid,
            'nombre': nombre,
            'descripcion': descripcion,
            'precio': int(precio) if float(precio).is_integer() else float(precio), # Evita problemas con Decimal
            'categoria': categoria,
            'imagen_url': imagen_url_final,
            'disponible': True # Por defecto todo plato nuevo está disponible
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
                        'ContentType': 'image/jpeg' # Tipo de archivo esperado
                    },
                    ExpiresIn=300 # El frontend tiene 5 minutos de tolerancia para subir la foto
                )
            except ClientError as e:
                print(f"Error al generar Presigned URL: {str(e)}")
                # No detenemos el flujo, permitimos que se cree el plato aunque falle la firma temporal

        # Responder de forma exitosa regresando la URL de S3 para el frontend
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
                "upload_url_s3": url_firmada_s3 # El front toma este link para hacer su PUT de la imagen
            })
        }

    except Exception as e:
        print(f"Error detectado en crear_plato: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Error interno del servidor al crear el plato: {str(e)}"})
        }
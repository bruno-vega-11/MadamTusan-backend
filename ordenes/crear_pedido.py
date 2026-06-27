import json
import os
import uuid
from datetime import datetime
import boto3

events_client = boto3.client('events')

def lambda_handle(event, context):
    """
    crear_pedido (POST /pedidos)
    Punto de entrada síncrono que asume el rol de productor de eventos.
    Recibe la orden y la delega a EventBridge inmediatamente.
    """
    try:
        # Recuperar el body del evento enviado por el frontend (Carrito)
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
            
        # Extraer campos clave para la trazabilidad básica
        tenant_id = body.get('tenant_id')
        cliente   = body.get('cliente', {})
        items     = body.get('items', [])   # [{uuid, cantidad}, ...]
        # 'WEB' = app propia del restaurante | 'RAPPI' = API externa en otra nube
        origen    = body.get('origen', 'WEB')
        
        # Validaciones de negocio mínimas en la puerta de entrada
        if not tenant_id or not items:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Faltan campos obligatorios ('tenant_id' o 'items')."})
            }
            
        # Enriquecer la orden con identificadores únicos de control
        pedido_id = f"ord-{str(uuid.uuid4())[:8]}" # ID corto y amigable de 8 caracteres
        fecha_creacion = datetime.utcnow().isoformat()
        
        payload_evento = {
            "tenant_id":     tenant_id,
            "pedido_id":     pedido_id,
            "fecha_creacion": fecha_creacion,
            "origen":        origen,
            "cliente":       cliente,
            "items":         items,
            "monto_total":   body.get('monto_total', 0.0),
        }
        
        # Publicar de forma asíncrona en Amazon EventBridge
        # El Source y el DetailType deben coincidir EXACTAMENTE con los del serverless.yml
        response = events_client.put_events(
            Entries=[
                {
                    'Source': 'custom.madamtusan.pedidos',
                    'DetailType': 'PedidoCreado',
                    'Detail': json.dumps(payload_evento),
                    'EventBusName': 'default' # Bus nativo de la cuenta de AWS
                }
            ]
        )

        print("EVENTBRIDGE RESPONSE:")
        print(json.dumps(response, default=str))
        
        # Verificamos si EventBridge rechazó la inserción del evento
        if response.get('FailedEntryCount', 0) > 0:
            print(response["Entries"])
            raise Exception("EventBridge rechazó la publicación del evento de pedido.")
            
        # Responder inmediatamente al frontend (HTTP 202 Accepted)
        return {
            "statusCode": 202,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps({
                "mensaje": "Pedido recibido de forma segura y encolado para su procesamiento.",
                "pedido_id": pedido_id,
                "tenant_id": tenant_id
            })
        }
        
    except Exception as e:
        print(f"Error detectado en crear_pedido: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": f"Error interno al encolar la orden: {str(e)}"})
        }
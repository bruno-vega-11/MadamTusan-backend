"""
Responsabilidad: Está completamente fuera del flujo de la cocina. 
Se dispara en paralelo gracias a EventBridge apenas el pedido es recibido para enviarle un correo
 automático al cliente confirmando su orden.
"""

def lambda_handle(event, context):

    return 
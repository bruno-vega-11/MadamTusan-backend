"""
Responsabilidad: Recibe el carrito desde la web del cliente, 
valida la estructura inicial y publica el evento "PedidoCreado" en el Bus de EventBridge. 
Responde de inmediato al cliente con un 202 Accepted.
"""
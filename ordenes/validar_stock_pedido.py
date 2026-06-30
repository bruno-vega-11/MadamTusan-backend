import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

table_name = os.environ.get('TABLE_MENU', 'dev-t-menu')
table = dynamodb.Table(table_name)

def lambda_handle(event, context):
    """
    validar_stock_pedido (Task de Step Functions)
    Recibe el payload del evento 'PedidoCreado' directamente en el parámetro 'event'.
    Verifica en DynamoDB que todos los platos solicitados estén disponibles.
    """
    try:
        print(f"DEBUG - Iniciando validación de stock para el evento: {event}")
        
        # Extraer los datos del pedido mapeados directamente por la Step Function
        tenant_id = event.get('tenant_id')
        items_pedido = event.get('items', [])
        pedido_id = event.get('pedido_id', 'unknown')

        if not tenant_id or not items_pedido:
            print("CRITICAL - Faltan campos esenciales ('tenant_id' o 'items') en el input.")
            event['stock_ok'] = False
            event['motivo_rechazo'] = "Datos de orden malformados o vacíos."
            return event

        # Flag para controlar si todo el pedido cuenta con disponibilidad
        todo_disponible = True
        platos_agotados = []

        # 2. Validar cada plato del carrito en la base de datos de menú
        for item in items_pedido:
            plato_uuid = item.get('uuid') or item.get('id') or item.get('plato_id')
            nombre_plato = item.get('nombre', plato_uuid)
            
            try:
                # Buscamos el plato usando su llave compuesta obligatoria (HASH y RANGE)
                response = table.get_item(
                    Key={
                        'tenant_id': tenant_id,
                        'uuid': plato_uuid
                    }
                )
                
                item_db = response.get('Item')
                
                # Evaluación de reglas de negocio:
                # A. Si el plato no existe en la carta de la base de datos
                if not item_db:
                    print(f"Alerta - El plato {nombre_plato} ({plato_uuid}) no existe en DynamoDB.")
                    todo_disponible = False
                    platos_agotados.append(f"{nombre_plato} (No registrado)")
                    continue
                
                # B. Si el plato existe pero está marcado como no disponible (Agotado)
                # Evaluamos que explícitamente sea True. Si es False o no tiene la propiedad, se rechaza.
                esta_disponible = item_db.get('disponible', False)
                if not esta_disponible:
                    print(f"Alerta - El plato {nombre_plato} se encuentra AGOTADO en cocina.")
                    todo_disponible = False
                    platos_agotados.append(nombre_plato)
                    
            except ClientError as e:
                print(f"Error al consultar la tabla de menú para el plato {plato_uuid}: {e.response['Error']['Message']}")
                todo_disponible = False
                platos_agotados.append(f"{nombre_plato} (Error de lectura de BD)")

        # 3. Adjuntar el veredicto del stock al payload original
        # Es OBLIGATORY retornar el evento original modificado para mantener el estado en la Step Function
        if todo_disponible:
            print(f"Éxito - Stock verificado por completo para el pedido: {pedido_id}. Procediendo a registrar.")
            event['stock_ok'] = True
        else:
            print(f"Rechazo - El pedido {pedido_id} fue denegado por falta de insumos: {platos_agotados}")
            event['stock_ok'] = False
            event['motivo_rechazo'] = f"Los siguientes platos no tienen stock disponible: {', '.join(platos_agotados)}"

        # Retornamos el objeto completo enriquecido. La Step Function leerá la llave '$.stock_ok'
        return event

    except Exception as e:
        print(f"Error crítico en la Lambda de validación de stock: {str(e)}")
        # En caso de caída del código por un imprevisto, respondemos con rechazo seguro para no procesar órdenes fantasmas
        event['stock_ok'] = False
        event['motivo_rechazo'] = f"Excepción interna en la validación de stock: {str(e)}"
        return event

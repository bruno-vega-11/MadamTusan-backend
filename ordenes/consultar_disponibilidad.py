import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
tabla_trabajadores = dynamodb.Table(os.environ.get("TABLE_TRABAJADORES", "dev-t-trabajadores"))


def lambda_handle(event, context):
    """
    Invocada por Step Functions dentro de cada Parallel (cocina/empaque/reparto).
    Consulta si existe un trabajador del rol indicado en estado LIBRE.

    El rol se inyecta vía variable de entorno porque el mismo handler se
    reutiliza para las 3 funciones (consultar_cocinero_disponible,
    consultar_despachador_disponible, consultar_repartidor_disponible),
    evitando triplicar código.

    Input esperado (viene del estado anterior dentro del Parallel):
        { "tenant_id": "...", "pedido_id": "...", "origen": "WEB|RAPPI", ... }

    Output:
        { ...input original..., "disponible": true/false, "trabajador_id": "..." }
    """
    rol = os.environ["ROL"]
    tenant_id = event.get("tenant_id") or event.get("pedido_data", {}).get("tenant_id")

    respuesta = tabla_trabajadores.query(
        KeyConditionExpression=Key("tenant_id").eq(tenant_id),
        FilterExpression=Attr("rol").eq(rol) & Attr("estado").eq("LIBRE"),
    )

    items = respuesta.get("Items", [])

    resultado = dict(event)
    if items:
        trabajador = items[0]
        resultado["disponible"] = True
        resultado["trabajador_id"] = trabajador["trabajador_id"]

        # Marca al trabajador como OCUPADO de inmediato para que dos
        # ejecuciones concurrentes no le asignen el mismo pedido.
        tabla_trabajadores.update_item(
            Key={"tenant_id": tenant_id, "trabajador_id": trabajador["trabajador_id"]},
            UpdateExpression="SET estado = :ocupado",
            ExpressionAttributeValues={":ocupado": "OCUPADO"},
        )
    else:
        resultado["disponible"] = False

    return resultado

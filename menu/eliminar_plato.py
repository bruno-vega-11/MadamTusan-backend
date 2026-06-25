import json
import os
import boto3
from decimal import Decimal

def lambda_handle(event, context):
    """
    Elimina un plato de la tabla de DynamoDB (o hace un borrado lógico cambiando el estado a eliminado: true)
    """
    return



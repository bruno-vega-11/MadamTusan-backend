import json
import os
import boto3
from decimal import Decimal


def lambda_handle(event, context):
    """
    Cambia un campo booleano en DynamoDB (ej. disponible: true/false).

    : En un chifa pasa mucho que se acaba el pato asado 
    o un Dim Sum específico a mitad de la jornada. El administrador del restaurante necesita apagar 
    el plato desde su web para que los clientes ya no puedan pedirlo en tiempo real.
    """
    return
import os
import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
tabla_sesiones = dynamodb.Table(os.environ.get("TABLE_SESIONES", "dev-sesiones"))


def lambda_handler(event, context):
    headers = event.get("headers", {}) or {}
    auth = headers.get("authorization") or headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()

    method_arn = event.get("methodArn", "*")

    if not token:
        return politica("anonymous", "Deny", method_arn, {})

    sesion = tabla_sesiones.get_item(Key={"token": token}).get("Item")

    if not sesion:
        return politica("anonymous", "Deny", method_arn, {})

    return politica(
        sesion["email"],
        "Allow",
        method_arn,
        {
            "email":     sesion["email"],
            "nombre":    sesion.get("nombre", ""),
            "tenant_id": sesion.get("tenant_id", ""),
        },
    )


def politica(principal, effect, method_arn, context):
    return {
        "principalId": principal,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": method_arn,
            }],
        },
        "context": context, 
    }

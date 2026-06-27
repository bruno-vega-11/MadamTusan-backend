import hashlib
import json
import os
import re
import uuid
import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
tabla_usuarios = dynamodb.Table(os.environ.get("TABLE_USUARIOS", "dev-usuarios"))
tabla_sesiones = dynamodb.Table(os.environ.get("TABLE_SESIONES", "dev-sesiones"))


# ── Password ──────────────────────────────────────────────────────────────────

def hashear_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    hash_resultado = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()
    return hash_resultado, salt


# ── Token / sesión ────────────────────────────────────────────────────────────

def crear_token(email, nombre, tenant_id): 
    token = str(uuid.uuid4())
    tabla_sesiones.put_item(Item={
        "token": token,
        "email": email,
        "nombre": nombre,
        "tenant_id": tenant_id, 
    })
    return token


def sesion_de_token(event):
    """Devuelve el Item de sesión o None si el token es inválido."""
    headers = event.get("headers", {}) or {}
    auth = headers.get("authorization") or headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    if not token:
        return None
    return tabla_sesiones.get_item(Key={"token": token}).get("Item")


# ── Validaciones ──────────────────────────────────────────────────────────────

def email_valido(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


# ── Respuestas HTTP ───────────────────────────────────────────────────────────

def respuesta(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, default=str),
    }


def ok(body):          return respuesta(200, body)
def creado(body):      return respuesta(201, body)
def bad_request(msg):  return respuesta(400, {"error": msg})
def no_autorizado(msg="Sesión inválida"): return respuesta(401, {"error": msg})
def prohibido(msg="No tienes permisos"):  return respuesta(403, {"error": msg})
def no_encontrado(msg="No encontrado"):   return respuesta(404, {"error": msg})
def conflicto(msg):    return respuesta(409, {"error": msg})
def error_interno():   return respuesta(500, {"error": "Error interno del servidor"})


# ── Body parser ───────────────────────────────────────────────────────────────

def parsear_body(event):
    body = event.get("body", "{}")
    if isinstance(body, str):
        return json.loads(body or "{}")
    return body or {}

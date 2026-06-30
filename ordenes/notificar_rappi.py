import os
import json
import urllib.request
import urllib.error

RAPPI_API_URL = os.environ["RAPPI_API_URL"]
RAPPI_API_KEY = os.environ["RAPPI_API_KEY"]


def lambda_handle(event, context):
    """
    Llamada solo cuando el pedido se originó en Rappi (filtrado por el
    Choice EvaluarOrigenRappi* en cada etapa del Step Functions).

    Hace POST al 2do API REST alojado en otra nube (OCI/GCP/Azure) para
    reflejar el cambio de estado del lado de Rappi.

    Input esperado:
        {
          "estado": "EN_PREPARACION" | "EMPACADO" | "EN_CAMINO" | "ENTREGADO",
          "pedido_data": { "pedido_id": "...", "rappi_order_id": "...", ... }
        }
    """
    estado = event["estado"]
    pedido_data = event.get("pedido_data") or {}

    payload = {
        "rappi_order_id": pedido_data.get("rappi_order_id") or pedido_data.get("pedido_id"),
        "pedido_id": pedido_data.get("pedido_id"),
        "estado": estado,
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{RAPPI_API_URL.rstrip('/')}/estado",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": RAPPI_API_KEY,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            respuesta_body = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        # No se quiere tumbar la State Machine completa por un timeout
        # del lado de Rappi: se deja registro y se continúa el flujo.
        return {
            "notificado": False,
            "error": str(exc),
            "estado_intentado": estado,
        }

    return {
        "notificado": True,
        "status_code": status_code,
        "respuesta": respuesta_body,
        "estado": estado,
    }
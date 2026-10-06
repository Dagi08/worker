"""Obtiene la llave privada RSA desde la API de PAM (senhasegura) con OAuth2 client_credentials."""
import requests

from config import PAM_BASE_URL, PAM_CLIENT_ID, PAM_CLIENT_SECRET, PAM_KEY_ID

PAM_TIMEOUT = 15


def _obtener_token() -> str:
    respuesta = requests.post(
        f"{PAM_BASE_URL}/api/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": PAM_CLIENT_ID,
            "client_secret": PAM_CLIENT_SECRET,
        },
        timeout=PAM_TIMEOUT,
    )
    respuesta.raise_for_status()
    return respuesta.json()["access_token"]


def obtener_llave_privada_pam() -> str:
    """Devuelve la llave privada (DER en base64) guardada en PAM bajo PAM_KEY_ID.
    No se escribe a disco ni se loguea su contenido."""
    token = _obtener_token()
    respuesta = requests.get(
        f"{PAM_BASE_URL}/api/pam/key/{PAM_KEY_ID}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=PAM_TIMEOUT,
    )
    respuesta.raise_for_status()
    return respuesta.json()["key"]["private_key"]

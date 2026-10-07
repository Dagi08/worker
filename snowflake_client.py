"""Conexion a Snowflake: autenticacion por llave RSA (key-pair auth) con respaldo
opcional a usuario/contrasena si la conexion por RSA falla."""
import base64

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from config import (
    SF_ACCOUNT,
    SF_DATABASE,
    SF_FALLBACK_PASSWORD,
    SF_FALLBACK_USER,
    SF_PRIVATE_KEY_PASSPHRASE,
    SF_ROLE,
    SF_SCHEMA,
    SF_USER,
    SF_WAREHOUSE,
    log,
)
from pam_client import obtener_llave_privada_pam


def _cargar_llave_privada_snowflake() -> bytes:
    """Obtiene la llave desde PAM (DER en base64) y la devuelve en formato DER/PKCS8 sin cifrar,
    como lo requiere snowflake-connector-python."""
    clave = serialization.load_der_private_key(
        base64.b64decode(obtener_llave_privada_pam()),
        password=SF_PRIVATE_KEY_PASSPHRASE.encode() if SF_PRIVATE_KEY_PASSPHRASE else None,
        backend=default_backend(),
    )
    return clave.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def conectar_snowflake():
    """Abre una conexion a Snowflake. Intenta primero con la llave privada RSA (key-pair auth);
    si esa conexion falla, reintenta con el usuario/contrasena de respaldo
    (SNOWFLAKE_FALLBACK_USER/SNOWFLAKE_FALLBACK_PASSWORD)."""
    try:
        conn = snowflake.connector.connect(
            account=SF_ACCOUNT,
            user=SF_USER,
            private_key=_cargar_llave_privada_snowflake(),
            warehouse=SF_WAREHOUSE,
            database=SF_DATABASE,
            schema=SF_SCHEMA,
            role=SF_ROLE,
        )
    except Exception:
        log.exception("Fallo la autenticacion RSA en Snowflake (PAM o conexion), se reintentara con usuario/contrasena de respaldo")
        if not SF_FALLBACK_PASSWORD:
            raise
        conn = snowflake.connector.connect(
            account=SF_ACCOUNT,
            user=SF_FALLBACK_USER,
            password=SF_FALLBACK_PASSWORD,
            warehouse=SF_WAREHOUSE,
            database=SF_DATABASE,
            schema=SF_SCHEMA,
            role=SF_ROLE,
        )
        log.info("Conectado a Snowflake con usuario de respaldo")
        return conn
    log.info("Conectado a Snowflake con llave RSA")
    return conn

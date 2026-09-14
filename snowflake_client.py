"""Conexion a Snowflake: autenticacion por llave RSA (key-pair auth) con respaldo
opcional a usuario/contrasena si la conexion por RSA falla."""
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from config import (
    SF_ACCOUNT,
    SF_DATABASE,
    SF_FALLBACK_PASSWORD,
    SF_FALLBACK_USER,
    SF_PRIVATE_KEY_PASSPHRASE,
    SF_PRIVATE_KEY_PATH,
    SF_ROLE,
    SF_SCHEMA,
    SF_USER,
    SF_WAREHOUSE,
    log,
)


def _cargar_llave_privada_snowflake() -> bytes:
    """Lee el .p8 configurado en SNOWFLAKE_PRIVATE_KEY_PATH y lo devuelve en formato
    DER/PKCS8 sin cifrar, como lo requiere snowflake-connector-python."""
    with open(SF_PRIVATE_KEY_PATH, "rb") as f:
        clave = serialization.load_pem_private_key(
            f.read(),
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
        return snowflake.connector.connect(
            account=SF_ACCOUNT,
            user=SF_USER,
            private_key=_cargar_llave_privada_snowflake(),
            warehouse=SF_WAREHOUSE,
            database=SF_DATABASE,
            schema=SF_SCHEMA,
            role=SF_ROLE,
        )
    except Exception:
        log.exception("Fallo la conexion a Snowflake via RSA, se reintentara con usuario/contrasena de respaldo")
        if not SF_FALLBACK_PASSWORD:
            raise
        return snowflake.connector.connect(
            account=SF_ACCOUNT,
            user=SF_FALLBACK_USER,
            password=SF_FALLBACK_PASSWORD,
            warehouse=SF_WAREHOUSE,
            database=SF_DATABASE,
            schema=SF_SCHEMA,
            role=SF_ROLE,
        )

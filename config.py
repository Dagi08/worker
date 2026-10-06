"""Carga .env y expone la configuracion (rutas, cadena SQL Server, credenciales Snowflake)
y el logger compartido por el resto de modulos."""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

load_dotenv(SCRIPT_DIR / ".env")

# Validacion preventiva para que no se caiga con un KeyError feo
if "PWC_INTERCEPT_BASE_DIR" not in os.environ:
    print(f"Error crítico: No se encontró el archivo '.env' o falta la variable PWC_INTERCEPT_BASE_DIR en la ruta: {SCRIPT_DIR}")
    sys.exit(1)

BASE_DIR = Path(os.environ["PWC_INTERCEPT_BASE_DIR"])
STATE_FILE = Path(os.environ.get("PWC_STATE_FILE", str(SCRIPT_DIR / "worker_pwc_state.json")))
POLL_SECONDS = int(os.environ.get("PWC_POLL_SECONDS", "5"))
CONN_STR = os.environ["PWC_DB_CONN_STR"]
RESULTADOS_DIR = Path(os.environ.get("PWC_RESULTADOS_DIR", str(SCRIPT_DIR / "resultados")))
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

# API de PAM (senhasegura) de donde se obtiene la llave privada RSA de Snowflake
PAM_BASE_URL = os.environ["PAM_BASE_URL"].rstrip("/")
PAM_CLIENT_ID = os.environ["PAM_CLIENT_ID"]
PAM_CLIENT_SECRET = os.environ["PAM_CLIENT_SECRET"]
PAM_KEY_ID = os.environ["PAM_KEY_ID"]

# Conexion a Snowflake (autenticacion por llave RSA / key-pair auth)
SF_ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
SF_USER = os.environ["SNOWFLAKE_USER"]
SF_PRIVATE_KEY_PASSPHRASE = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None
SF_WAREHOUSE = os.environ["SNOWFLAKE_WAREHOUSE"]
SF_DATABASE = os.environ["SNOWFLAKE_DATABASE"]
SF_SCHEMA = os.environ["SNOWFLAKE_SCHEMA"]
SF_ROLE = os.environ.get("SNOWFLAKE_ROLE") or None

# Respaldo: si la conexion via RSA falla, se reintenta con usuario/contrasena personal
SF_FALLBACK_USER = os.environ.get("SNOWFLAKE_FALLBACK_USER") or SF_USER
SF_FALLBACK_PASSWORD = os.environ.get("SNOWFLAKE_FALLBACK_PASSWORD") or None

FORMATO_LOG = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=FORMATO_LOG,
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_DIR / "worker_pwc.log", encoding="utf-8")],
)

_handler_errores = logging.FileHandler(LOG_DIR / "errores.log", encoding="utf-8")
_handler_errores.setLevel(logging.ERROR)
_handler_errores.setFormatter(logging.Formatter(FORMATO_LOG))
logging.getLogger().addHandler(_handler_errores)

log = logging.getLogger("worker_pwc")

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

# Conexion a Snowflake (autenticacion por llave RSA / key-pair auth)
SF_ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
SF_USER = os.environ["SNOWFLAKE_USER"]
SF_PRIVATE_KEY_PATH = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"])
SF_PRIVATE_KEY_PASSPHRASE = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None
SF_WAREHOUSE = os.environ["SNOWFLAKE_WAREHOUSE"]
SF_DATABASE = os.environ["SNOWFLAKE_DATABASE"]
SF_SCHEMA = os.environ["SNOWFLAKE_SCHEMA"]
SF_ROLE = os.environ.get("SNOWFLAKE_ROLE") or None

# Respaldo: si la conexion via RSA falla, se reintenta con usuario/contrasena personal
SF_FALLBACK_USER = os.environ.get("SNOWFLAKE_FALLBACK_USER") or SF_USER
SF_FALLBACK_PASSWORD = os.environ.get("SNOWFLAKE_FALLBACK_PASSWORD") or None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(SCRIPT_DIR / "worker_pwc.log", encoding="utf-8")],
)
log = logging.getLogger("worker_pwc")

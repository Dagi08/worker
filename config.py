"""Carga .env y expone la configuracion (rutas, cadena SQL Server, credenciales Snowflake)
y el logger compartido por el resto de modulos."""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import certifi
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

# snowflake-connector-python busca el CA bundle en rutas fijas dentro de _MEIPASS cuando el
# worker corre como .exe (PyInstaller), y esas rutas no coinciden con donde certifi lo deja
# ("No cabundle file is found in _MEIPASS"). Fijar REQUESTS_CA_BUNDLE evita esa busqueda:
# es la primera variable que revisa, antes de caer en la logica de _MEIPASS.
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

load_dotenv(SCRIPT_DIR / ".env")

# Validacion preventiva para que no se caiga con un KeyError feo
if "PWC_INTERCEPT_BASE_DIR" not in os.environ:
    print(f"Error crítico: No se encontró el archivo '.env' o falta la variable PWC_INTERCEPT_BASE_DIR en la ruta: {SCRIPT_DIR}")
    sys.exit(1)

BASE_DIR = Path(os.environ["PWC_INTERCEPT_BASE_DIR"])
STATE_FILE = Path(os.environ.get("PWC_STATE_FILE", str(SCRIPT_DIR / "worker_pwc_state.json")))
POLL_SECONDS = int(os.environ.get("PWC_POLL_SECONDS", "5"))
MAX_REINTENTOS = int(os.environ.get("PWC_MAX_REINTENTOS", "5"))
CONN_STR = os.environ["PWC_DB_CONN_STR"]

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



class _ArchivoPorDia(logging.FileHandler):
    """Escribe en logs\\{yyyyMMdd}\\<nombre>. Al cambiar el dia (el servicio corre sin reiniciarse)
    cierra el archivo y sigue en la carpeta del dia nuevo."""

    _nombres: list[str] = []  # todos los logs por dia, para crearlos juntos al cambiar el dia

    def __init__(self, nombre: str):
        self._nombre = nombre
        self._nombres.append(nombre)
        self._dia = datetime.now().strftime("%Y%m%d")
        super().__init__(self._ruta(), encoding="utf-8")

    def _ruta(self) -> Path:
        carpeta = LOG_DIR / self._dia
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta / self._nombre

    def emit(self, record: logging.LogRecord) -> None:
        dia = datetime.fromtimestamp(record.created).strftime("%Y%m%d")
        if dia != self._dia:
            self._dia = dia
            self.close()  # FileHandler reabre el stream en el siguiente emit
            self.baseFilename = str(self._ruta())
            # Los demas logs solo cambian de carpeta cuando escriben: se crean ya vacios para
            # que la carpeta del dia tenga los 4 archivos desde el inicio.
            for nombre in self._nombres:
                (LOG_DIR / dia / nombre).touch(exist_ok=True)
        super().emit(record)


_handlers: list[logging.Handler] = [_ArchivoPorDia("worker_pwc.log")]
if sys.stderr is not None:  # como servicio de Windows no hay consola donde escribir
    _handlers.append(logging.StreamHandler())
logging.basicConfig(level=logging.INFO, format=FORMATO_LOG, handlers=_handlers)

_handler_errores = _ArchivoPorDia("errores.log")
_handler_errores.setLevel(logging.ERROR)
_handler_errores.setFormatter(logging.Formatter(FORMATO_LOG))
logging.getLogger().addHandler(_handler_errores)

log = logging.getLogger("worker_pwc")

_handler_exitos = _ArchivoPorDia("exitos_snowflake.log")
_handler_exitos.setFormatter(logging.Formatter(FORMATO_LOG))
log_exitos = logging.getLogger("worker_pwc.exitos")
log_exitos.addHandler(_handler_exitos)

_handler_fallidas = _ArchivoPorDia("solicitudes_fallidas.log")
_handler_fallidas.setFormatter(logging.Formatter(FORMATO_LOG))
log_fallidas = logging.getLogger("worker_pwc.fallidas")
log_fallidas.addHandler(_handler_fallidas)

"""Worker que consume LogPwc\\{yyyyMMdd}\\InterceptPwc26201\\InterceptPwc26201.log (NDJSON)
generado por ws_PowerCurve y, por cada IdSolicitudCredito nuevo interceptado, ejecuta las
queries de sqlserver_client y carga el resultado normalizado en Snowflake (snowflake_loader).
El archivo rota por dia, igual que el resto de logs del proyecto."""
import json
import time
from datetime import datetime, timedelta
from typing import Callable

from config import BASE_DIR, POLL_SECONDS, log
from log_reader import cargar_estado, guardar_estado, leer_desde, ruta_del_dia
from snowflake_client import conectar_snowflake
from snowflake_loader import cargar_solicitud
from sqlserver_client import obtener_datos_vehiculo

_conexion_sf = None


def _conexion_snowflake():
    global _conexion_sf
    if _conexion_sf is None:
        _conexion_sf = conectar_snowflake()
    return _conexion_sf


def _descartar_conexion_snowflake() -> None:
    global _conexion_sf
    if _conexion_sf is not None:
        try:
            _conexion_sf.close()
        except Exception:
            pass
    _conexion_sf = None


def procesar_linea(linea: str) -> None:
    registro = {k.lower(): v for k, v in json.loads(linea).items()}
    id_solicitud_credito = registro.get("idsolicitudcredito")
    if id_solicitud_credito is None:
        log.error("Linea sin idSolicitudCredito, se descarta: %s", linea)
        return
    log.info(
        "Procesando IdSolicitudCredito=%s idOpcion=%s I815categorialaboral=%s",
        id_solicitud_credito, registro.get("idopcion"), registro.get("i815categorialaboral"),
    )
    result_sets = obtener_datos_vehiculo(id_solicitud_credito)
    try:
        cargar_solicitud(_conexion_snowflake(), id_solicitud_credito, result_sets)
    except Exception:
        _descartar_conexion_snowflake()
        raise


def _guardador(fecha: str) -> Callable[[int], None]:
    return lambda offset: guardar_estado({"fecha": fecha, "offset": offset})


def ciclo() -> None:
    estado = cargar_estado()
    hoy = datetime.now().strftime("%Y%m%d")
    while estado["fecha"] != hoy:
        ruta = ruta_del_dia(estado["fecha"])
        estado["offset"] = leer_desde(ruta, estado["offset"], procesar_linea, _guardador(estado["fecha"]))
        if ruta.exists() and estado["offset"] < ruta.stat().st_size:
            return
        siguiente = (datetime.strptime(estado["fecha"], "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        estado = {"fecha": siguiente, "offset": 0}
        guardar_estado(estado)
    leer_desde(ruta_del_dia(hoy), estado["offset"], procesar_linea, _guardador(hoy))


def verificar_snowflake() -> None:
    try:
        conectar_snowflake().close()
    except Exception:
        log.error("No se pudo establecer la conexion a Snowflake al iniciar el worker")


def main() -> None:
    log.info("Worker PWC iniciado. Base=%s cada %ss", BASE_DIR, POLL_SECONDS)
    verificar_snowflake()
    while True:
        try:
            ciclo()
        except Exception:
            log.exception("Error inesperado en el ciclo del worker")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

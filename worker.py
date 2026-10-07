"""Worker que consume LogPwc\\{yyyyMMdd}\\InterceptPwc26201\\InterceptPwc26201.log (NDJSON)
generado por ws_PowerCurve y, por cada IdSolicitudCredito nuevo interceptado, ejecuta las
queries equivalentes a usp_ObtenerDatosVehiculoSolicitud (sqlserver_client) y guarda el
resultado como JSON. El archivo rota por dia, igual que el resto de logs del proyecto."""
import json
import time
from datetime import datetime, timedelta
from typing import Callable

from config import BASE_DIR, POLL_SECONDS, RESULTADOS_DIR, log
from log_reader import cargar_estado, guardar_estado, leer_desde, ruta_del_dia
from snowflake_client import conectar_snowflake
from sqlserver_client import obtener_datos_vehiculo


def guardar_resultado(id_solicitud_credito: int, result_sets: list) -> None:
    ruta = RESULTADOS_DIR / f"{id_solicitud_credito}.json"
    ruta.write_text(json.dumps(result_sets, ensure_ascii=False, indent=2), encoding="utf-8")


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
    guardar_resultado(id_solicitud_credito, result_sets)
    log.info(
        "Datos obtenidos OK para IdSolicitudCredito=%s, resultado guardado en %s",
        id_solicitud_credito, RESULTADOS_DIR / f"{id_solicitud_credito}.json",
    )


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

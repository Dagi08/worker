"""Worker que consume LogPwc\\{yyyyMMdd}\\InterceptPwc26201\\InterceptPwc26201.log (NDJSON)
generado por ws_PowerCurve y, por cada IdSolicitudCredito nuevo interceptado, ejecuta las
queries equivalentes a usp_ObtenerDatosVehiculoSolicitud (sqlserver_client) y guarda el
resultado como JSON. El archivo rota por dia, igual que el resto de logs del proyecto."""
import json
import time
from datetime import datetime, timedelta

from config import BASE_DIR, POLL_SECONDS, RESULTADOS_DIR, log
from log_reader import cargar_estado, guardar_estado, leer_desde, ruta_del_dia
from sqlserver_client import obtener_datos_vehiculo


def guardar_resultado(id_solicitud_credito: int, result_sets: list) -> None:
    ruta = RESULTADOS_DIR / f"{id_solicitud_credito}.json"
    ruta.write_text(json.dumps(result_sets, ensure_ascii=False, indent=2), encoding="utf-8")


def procesar_linea(linea: str) -> None:
    registro = json.loads(linea)
    id_solicitud_credito = registro.get("IdSolicitudCredito")
    log.info(
        "Procesando IdSolicitudCredito=%s idOpcion=%s I815categorialaboral=%s",
        id_solicitud_credito, registro.get("idOpcion"), registro.get("I815categorialaboral"),
    )
    result_sets = obtener_datos_vehiculo(id_solicitud_credito)
    guardar_resultado(id_solicitud_credito, result_sets)
    log.info(
        "Datos obtenidos OK para IdSolicitudCredito=%s, resultado guardado en %s",
        id_solicitud_credito, RESULTADOS_DIR / f"{id_solicitud_credito}.json",
    )


def ciclo() -> None:
    estado = cargar_estado()
    hoy = datetime.now().strftime("%Y%m%d")
    while estado["fecha"] != hoy:
        estado["offset"] = leer_desde(ruta_del_dia(estado["fecha"]), estado["offset"], procesar_linea)
        guardar_estado(estado)
        siguiente = (datetime.strptime(estado["fecha"], "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        estado = {"fecha": siguiente, "offset": 0}
        guardar_estado(estado)
    nuevo_offset = leer_desde(ruta_del_dia(hoy), estado["offset"], procesar_linea)
    if nuevo_offset != estado["offset"]:
        guardar_estado({"fecha": hoy, "offset": nuevo_offset})


def main() -> None:
    log.info("Worker PWC iniciado. Base=%s cada %ss", BASE_DIR, POLL_SECONDS)
    while True:
        try:
            ciclo()
        except Exception:
            log.exception("Error inesperado en el ciclo del worker")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

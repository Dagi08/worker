"""Worker que consume LogPwc\\{yyyyMMdd}\\InterceptPwc26201\\InterceptPwc26201.log (NDJSON)
generado por ws_PowerCurve y, por cada IdSolicitudCredito nuevo interceptado, ejecuta las
queries de sqlserver_client y carga el resultado normalizado en Snowflake (snowflake_loader).
El archivo rota por dia, igual que el resto de logs del proyecto."""
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Callable

from config import BASE_DIR, MAX_REINTENTOS, POLL_SECONDS, SF_DATABASE, SF_SCHEMA, log, log_fallidas
from log_reader import EsperandoReintento, cargar_estado, guardar_estado, leer_desde, ruta_del_dia
from snowflake_client import conectar_snowflake
from snowflake_loader import cargar_solicitud
from sqlserver_client import obtener_datos_vehiculo

_conexion_sf = None
# SP de Snowflake que ejecuta el proceso SAGI completo de una instancia:
# modelo, web scraping, compliance y dictamen.
SP_PROCESAR_SAGI = f"{SF_DATABASE}.{SF_SCHEMA}.SP_SAGI_PROCESAR_INSTANCIA"
_intentos: dict[str, tuple[int, float]] = {}
# Lo activa el servicio de Windows (servicio.py) al recibir "Detener": el worker termina la
# linea en curso, deja de leer y sale del bucle principal.
detener = threading.Event()


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


def _ejecutar_procesamiento_sagi(id_solicitud_credito) -> None:
    """Ejecuta SP_SAGI_PROCESAR_INSTANCIA y espera su resultado (modelo, web scraping,
    compliance y dictamen; puede tardar varios minutos). Usa su propia conexion para no
    bloquear ni compartir la sesion del hilo principal, y deja el log del SP en worker_pwc.log."""
    conn = None
    try:
        conn = conectar_snowflake()
        cur = conn.cursor()
        try:
            log.info("SAGI: procesamiento iniciado IdSolicitudCredito=%s", id_solicitud_credito)
            cur.execute(f"CALL {SP_PROCESAR_SAGI}(%s)", (int(id_solicitud_credito),))
            fila = cur.fetchone()
            resultado = fila[0] if fila else ""
            log.info("SAGI: procesamiento terminado IdSolicitudCredito=%s query_id=%s\n%s",
                     id_solicitud_credito, cur.sfqid, resultado)
            if str(resultado).startswith("ERROR"):
                log_fallidas.error("SAGI: %s", resultado)
        finally:
            cur.close()
    except Exception:
        # No se relanza: la carga de Bantotal ya quedo confirmada y no debe repetirse.
        log_fallidas.exception("SAGI: fallo el procesamiento IdSolicitudCredito=%s", id_solicitud_credito)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def lanzar_procesamiento_sagi(id_solicitud_credito) -> None:
    """Lanza el proceso SAGI de la instancia en un hilo aparte: el worker sigue leyendo el log
    mientras el SP corre en Snowflake y espera su resultado para dejarlo en el log."""
    threading.Thread(
        target=_ejecutar_procesamiento_sagi,
        args=(id_solicitud_credito,),
        name=f"sagi-{id_solicitud_credito}",
        daemon=True,
    ).start()


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
    lanzar_procesamiento_sagi(id_solicitud_credito)


def _procesar_con_reintentos(linea: str) -> None:
    if detener.is_set():
        # Corta la lectura sin avanzar el offset: la linea se procesa al volver a iniciar.
        raise EsperandoReintento()
    ahora = time.monotonic()
    intentos, proximo_intento = _intentos.get(linea, (0, 0.0))
    if ahora < proximo_intento:
        raise EsperandoReintento()
    try:
        procesar_linea(linea)
    except Exception:
        intentos += 1
        if intentos >= MAX_REINTENTOS:
            _intentos.pop(linea, None)
            log_fallidas.error("Descartada tras %s intentos: %s", intentos, linea)
            log.error("Linea descartada tras %s intentos, se continua con la siguiente: %s", intentos, linea)
            return
        _intentos[linea] = (intentos, ahora + POLL_SECONDS * 2 ** intentos)
        raise
    _intentos.pop(linea, None)


def _guardador(fecha: str) -> Callable[[int], None]:
    return lambda offset: guardar_estado({"fecha": fecha, "offset": offset})


def ciclo() -> None:
    estado = cargar_estado()
    hoy = datetime.now().strftime("%Y%m%d")
    while estado["fecha"] != hoy:
        ruta = ruta_del_dia(estado["fecha"])
        estado["offset"] = leer_desde(ruta, estado["offset"], _procesar_con_reintentos, _guardador(estado["fecha"]))
        if ruta.exists() and estado["offset"] < ruta.stat().st_size:
            return
        siguiente = (datetime.strptime(estado["fecha"], "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        estado = {"fecha": siguiente, "offset": 0}
        guardar_estado(estado)
    leer_desde(ruta_del_dia(hoy), estado["offset"], _procesar_con_reintentos, _guardador(hoy))


def verificar_snowflake() -> None:
    try:
        conectar_snowflake().close()
    except Exception:
        log.error("No se pudo establecer la conexion a Snowflake al iniciar el worker")


def main() -> None:
    log.info("Worker PWC iniciado. Base=%s cada %ss", BASE_DIR, POLL_SECONDS)
    verificar_snowflake()
    while not detener.is_set():
        try:
            ciclo()
        except Exception:
            log.exception("Error inesperado en el ciclo del worker")
        detener.wait(POLL_SECONDS)
    _descartar_conexion_snowflake()
    log.info("Worker PWC detenido")


if __name__ == "__main__":
    main()

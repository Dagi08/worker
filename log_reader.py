"""Lectura incremental del log NDJSON de PWC y persistencia del estado (fecha + offset)."""
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from config import BASE_DIR, STATE_FILE, log


def ruta_del_dia(fecha: str) -> Path:
    return BASE_DIR / fecha / "InterceptPwc26201" / "InterceptPwc26201.log"


def cargar_estado() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (ValueError, OSError):
            pass
    return {"fecha": datetime.now().strftime("%Y%m%d"), "offset": 0}


def guardar_estado(estado: dict) -> None:
    STATE_FILE.write_text(json.dumps(estado))


def leer_desde(ruta: Path, offset: int, procesar: Callable[[str], None]) -> int:
    """Lee lineas completas de `ruta` a partir de `offset`, invocando `procesar` por cada una.
    Devuelve el offset hasta donde se proceso con exito (se detiene ante linea incompleta, EOF o error)."""
    if not ruta.exists():
        return offset
    with ruta.open("r", encoding="utf-8-sig") as f:
        f.seek(offset)
        while True:
            pos_antes = f.tell()
            linea = f.readline()
            if not linea.endswith("\n"):
                return pos_antes
            linea = linea.strip()
            if linea:
                try:
                    procesar(linea)
                except Exception:
                    log.exception("Fallo procesando linea, se reintentara en el proximo ciclo: %s", linea)
                    return pos_antes

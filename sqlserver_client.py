"""Ejecucion de las queries de sqlserver_queries.py contra SQL Server (pyodbc)."""
from datetime import date, datetime
from decimal import Decimal

import pyodbc

from config import CONN_STR
from sqlserver_queries import (
    SQL_CANTIDAD_SOLICITUDES,
    SQL_CUOTA_MAF_USD,
    SQL_DEUDA_FIANCIERA,
    SQL_DOMICILIOS,
    SQL_GASTO_OPERATIVO_USD,
    SQL_INGRESO_USD,
    SQL_INGRESOS,
    SQL_MOROSIDAD_CUENTA,
    SQL_MOROSIDAD_DNI,
    SQL_NET_USD,
    SQL_NUMERO_DOCUMENTO,
    SQL_NUMERO_INGRESO,
    SQL_PERIODOS_INGRESO,
    SQL_PERSONA,
    SQL_RCI_USD,
    SQL_REGIMEN_SUNAT,
    SQL_SALDO_USD,
    SQL_UTILIDAD_OPERATIVA_USD,
    SQL_VEHICULO,
)


def _valor_json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _ejecutar(cursor, sql: str, *params) -> list:
    cursor.execute(sql, params)
    columnas = [c[0] for c in cursor.description] if cursor.description else []
    return [dict(zip(columnas, (_valor_json(v) for v in fila))) for fila in cursor.fetchall()]


def obtener_datos_vehiculo(id_solicitud_credito: int) -> list:
    """Ejecuta las queries equivalentes al SP y devuelve sus result sets,
    cada uno como lista de dicts columna->valor."""
    with pyodbc.connect(CONN_STR, timeout=10) as conn:
        cursor = conn.cursor()
        filas_doc = _ejecutar(cursor, SQL_NUMERO_DOCUMENTO, id_solicitud_credito)
        numero_documento = filas_doc[0]["NumeroDocumento"] if filas_doc else None
        return [
            _ejecutar(cursor, SQL_VEHICULO, id_solicitud_credito),
            _ejecutar(cursor, SQL_PERSONA, id_solicitud_credito),
            _ejecutar(cursor, SQL_DOMICILIOS, numero_documento),
            _ejecutar(cursor, SQL_CANTIDAD_SOLICITUDES, numero_documento),
            _ejecutar(cursor, SQL_MOROSIDAD_DNI, numero_documento),
            _ejecutar(cursor, SQL_MOROSIDAD_CUENTA, numero_documento),
            _ejecutar(cursor, SQL_NUMERO_INGRESO, id_solicitud_credito),
            _ejecutar(cursor, SQL_REGIMEN_SUNAT, id_solicitud_credito),
            _ejecutar(cursor, SQL_PERIODOS_INGRESO, id_solicitud_credito),
            _ejecutar(cursor, SQL_INGRESOS, id_solicitud_credito),
            _ejecutar(cursor, SQL_DEUDA_FIANCIERA, id_solicitud_credito),
            _ejecutar(cursor, SQL_INGRESO_USD, id_solicitud_credito),
            _ejecutar(cursor, SQL_GASTO_OPERATIVO_USD, id_solicitud_credito),
            _ejecutar(cursor, SQL_UTILIDAD_OPERATIVA_USD, id_solicitud_credito),
            _ejecutar(cursor, SQL_NET_USD, id_solicitud_credito),
            _ejecutar(cursor, SQL_CUOTA_MAF_USD, id_solicitud_credito),
            _ejecutar(cursor, SQL_SALDO_USD, id_solicitud_credito),
            _ejecutar(cursor, SQL_RCI_USD, id_solicitud_credito),
        ]

"""Carga en Snowflake el resultado de las queries de SQL Server en el modelo normalizado AGT_SAGI_BT_*.

sqlserver_client.obtener_datos_vehiculo devuelve una lista de 19 result sets (cada uno lista de dicts
columna -> valor), en este orden:
   0 SQL_VEHICULO              -> solicitud (montos, score, puntaje, cuotas), persona (tipo y numero de documento)
   1 SQL_PERSONA               -> persona (nombre, fecha de nacimiento), empleo
   2 SQL_DOMICILIOS            -> domicilio
   3 SQL_CANTIDAD_SOLICITUDES  -> solicitud.cantidad_solicitudes_previas
   4 SQL_MOROSIDAD_DNI         -> morosidad_operacion, persona_cuenta
   5 SQL_MOROSIDAD_CUENTA      -> morosidad_operacion
   6 SQL_NUMERO_INGRESO        -> solicitud.valor_bd, nro_ingresos_mensuales
   7 SQL_REGIMEN_SUNAT         -> solicitud.codigo_regimen, regimen_sunat
   8 SQL_PERIODOS_INGRESO      -> solicitud.fecha_solicitud, periodo_3..1
   9 SQL_INGRESOS              -> ingreso_detalle (una fila por categoria)
  10 SQL_DEUDA_FIANCIERA       -> deuda_financiera
  11-16 indicadores en USD     -> indicador_financiero
  17 SQL_RCI_USD               -> rci
  18 SQL_MODELO_VEHICULO       -> vehiculo

Cada solicitud se carga en una sola transaccion: si algo falla, no queda nada a medias.
Las tablas se reemplazan por llave (borrar y volver a insertar), asi reprocesar no duplica filas."""
import re
from typing import Any

from config import SF_DATABASE, SF_SCHEMA, log, log_exitos

CATEGORIAS_INGRESO = ("5° Categoría", "4° Categoría", "3° Categoría", "1° Categoría")
INDICES_INDICADORES = range(11, 17)

PERSONA_COLS = ("numero_documento", "tipo_documento", "nombre", "apellido_paterno", "apellido_materno", "fecha_nacimiento")
SOLICITUD_COLS = (
    "instancia", "fecha_solicitud", "numero_documento", "monto_soles", "monto_dolares", "score", "puntaje",
    "cuotas", "cantidad_solicitudes_previas", "valor_bd", "nro_ingresos_mensuales", "codigo_regimen",
    "regimen_sunat", "periodo_3", "periodo_2", "periodo_1",
)
EMPLEO_COLS = (
    "instancia", "tipo_ocupacion", "nombre_ocupacion", "ruc_empleador", "cod_tipo_empresa", "tipo_empresa",
    "cod_tipo_ingreso", "tipo_ingreso", "fecha_ingreso_empresa",
)
DOMICILIO_COLS = ("numero_documento", "codigo", "tipo_domicilio", "direccion", "cod_habilitado", "habilitado")
PERSONA_CUENTA_COLS = ("numero_documento", "cuenta")
MOROSIDAD_COLS = ("operacion", "cuenta", "moneda", "monto_capital", "estado")
INGRESO_COLS = ("instancia", "variable_periodo", "categoria", "monto")
DEUDA_COLS = (
    "instancia", "nro_registro", "entidad", "tipo_credito", "modalidad", "moneda", "f_creacion", "f_modif",
    "cuota_titular", "cuota_conyuge",
)
INDICADOR_COLS = ("instancia", "concepto", "valor_mensual", "total_acumulado")
RCI_COLS = ("instancia", "valor_obtenido", "resultados")
VEHICULO_COLS = ("instancia", "proveedor", "marca", "modelo", "anio", "tipo_uso")


def _numero(valor: Any) -> float | None:
    """Convierte texto como 'S/. 4,500.00' o '-' a numero; None si no hay valor."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = valor.replace("S/.", "").replace(",", "").strip()
    if texto in ("", "-"):
        return None
    return float(texto)


def _entero(valor: Any) -> int | None:
    numero = _numero(valor)
    return None if numero is None else int(numero)


def _fecha(valor: Any) -> str | None:
    return valor[:10] if valor else None


def _texto(valor: Any) -> str | None:
    return None if valor is None else str(valor)


def _especificaciones(instancia: int, rs: list) -> list:
    """Devuelve, por tabla, (sufijo, columnas, columnas para borrar, llaves a borrar, filas a insertar)."""
    veh = rs[0][0] if rs[0] else {}
    per = rs[1][0] if rs[1] else {}
    cantidad = rs[3][0] if rs[3] else {}
    ingreso = rs[6][0] if rs[6] else {}
    regimen = rs[7][0] if rs[7] else {}
    periodos = rs[8][0] if rs[8] else {}

    numero_documento = veh.get("Numero de Documento") or (rs[3][0]["DNI"] if rs[3] else None)
    if numero_documento is None:
        raise ValueError(f"IdSolicitudCredito={instancia} sin numero de documento")

    persona = [(numero_documento, veh.get("Tipo Documento"), per.get("Nombre"), per.get("Apellido Paterno"),
                per.get("Apellido Materno"), _fecha(per.get("Fecha de Nacimiento")))]
    solicitud = [(
        instancia, _fecha(periodos.get("Fecha Solicitud")), numero_documento,
        _numero(veh.get("Monto en soles")), _numero(veh.get("Monto en dólares")),
        _numero(veh.get("Score")), _numero(veh.get("Puntaje")), _numero(veh.get("Cuotas")),
        _entero(cantidad.get("Cantidad de Solicitudes")),
        _numero(ingreso.get("Valor BD")), _entero(ingreso.get("Nro. Ingresos Mensuales")),
        _texto(regimen.get("Codigo_Regimen")), regimen.get("Regimen_Sunat"),
        periodos.get("Periodo 3"), periodos.get("Periodo 2"), periodos.get("Periodo 1"),
    )]
    empleo = [(
        instancia, per.get("Tipo de ocupación"), per.get("Nombre de ocupación"), per.get("RUC Empleador"),
        per.get("Cod. Tipo de empresa"), per.get("Tipo de empresa"), per.get("Cod. Tipo de ingreso"),
        per.get("Tipo de ingreso"), per.get("Fecha Ingreso Empresa"),
    )] if rs[1] else []
    domicilio = [(numero_documento, _entero(d["Código"]), d["Tipo Dom."], d["Dirección"],
                  _texto(d["Cod. Habilitado"]), d["Habilitado"]) for d in rs[2]]

    morosidad = {}
    for fila in rs[5] + rs[4]:
        clave = (_entero(fila["Operacion"]), _entero(fila["Cuenta"]))
        morosidad.setdefault(clave, (clave[0], clave[1], fila["Moneda"], _numero(fila["Monto de capital"]), fila["Estado"]))
    persona_cuenta = sorted({(numero_documento, _entero(f["Cuenta"])) for f in rs[4]})

    ingresos = [(instancia, f["Variable Periodo"], categoria, _numero(f[categoria]))
                for f in rs[9] for categoria in CATEGORIAS_INGRESO]
    deuda = [(instancia, _entero(f["Nro. Registro"]), f["Entidad"], f["Tipo de Crédito"], f["Modalidad"],
              f["Moneda"], f["F. Creación"], f["F. Modif"], _numero(f["Cuota Titular"]), _numero(f["Cuota Cónyuge"]))
             for f in rs[10]]
    indicadores = [(instancia, f["Concepto"], _numero(f.get("Valor Mensual")), _numero(f.get("Total Acumulado")))
                   for i in INDICES_INDICADORES for f in rs[i]]
    rci = [(instancia, f["Valor Obtenido"], f["Resultados"]) for f in rs[17]]
    vehiculo = [(instancia, f["Proveedor"], f["Marca"], f["Modelo"], _entero(f["Año"]), f["Tipo de Uso"])
                for f in rs[18]]

    llave_instancia = [(instancia,)]
    return [
        ("PERSONA", PERSONA_COLS, ["numero_documento"], [(numero_documento,)], persona),
        ("SOLICITUD", SOLICITUD_COLS, ["instancia"], llave_instancia, solicitud),
        ("EMPLEO", EMPLEO_COLS, ["instancia"], llave_instancia, empleo),
        ("DOMICILIO", DOMICILIO_COLS, ["numero_documento"], [(numero_documento,)], domicilio),
        ("PERSONA_CUENTA", PERSONA_CUENTA_COLS, ["numero_documento"], [(numero_documento,)], persona_cuenta),
        ("MOROSIDAD_OPERACION", MOROSIDAD_COLS, ["operacion", "cuenta"],
         [(op, cuenta) for op, cuenta, *_ in morosidad.values()], list(morosidad.values())),
        ("INGRESO_DETALLE", INGRESO_COLS, ["instancia"], llave_instancia, ingresos),
        ("DEUDA_FINANCIERA", DEUDA_COLS, ["instancia"], llave_instancia, deuda),
        ("INDICADOR_FINANCIERO", INDICADOR_COLS, ["instancia"], llave_instancia, indicadores),
        ("RCI", RCI_COLS, ["instancia"], llave_instancia, rci),
        ("VEHICULO", VEHICULO_COLS, ["instancia"], llave_instancia, vehiculo),
    ]


def _reemplazar(cur, tabla: str, columnas: tuple, borrar_por: list, llaves: list, filas: list) -> None:
    if llaves:
        condicion = " AND ".join(f"{c} = %s" for c in borrar_por)
        cur.executemany(f"DELETE FROM {tabla} WHERE {condicion}", llaves)
    if filas:
        marcadores = ", ".join("%s" for _ in columnas)
        cur.executemany(f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({marcadores})", filas)


def cargar_solicitud(conn, instancia: int, result_sets: list) -> None:
    cur = conn.cursor()
    cur.execute("BEGIN")
    conteos = {}
    try:
        for sufijo, columnas, borrar_por, llaves, filas in _especificaciones(instancia, result_sets):
            _reemplazar(cur, f"{SF_DATABASE}.{SF_SCHEMA}.AGT_SAGI_BT_{sufijo}", columnas, borrar_por, llaves, filas)
            conteos[sufijo] = len(filas)
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        log.error("Fallo la carga en Snowflake de IdSolicitudCredito=%s, se hizo ROLLBACK", instancia)
        raise
    log_exitos.info("IdSolicitudCredito=%s cargado en Snowflake: %s", instancia, conteos)

# worker

Worker que monitorea el log NDJSON generado por ws_PowerCurve
(`LogPwc\{yyyyMMdd}\InterceptPwc26201\InterceptPwc26201.log`), y por cada
`IdSolicitudCredito` nuevo interceptado ejecuta contra SQL Server las queries
equivalentes a `usp_ObtenerDatosVehiculoSolicitud` y guarda el resultado como
un `.json` por solicitud en `resultados/`.

## Estructura

- `worker.py` — entrypoint: lee el log, orquesta el procesamiento y el ciclo principal.
- `config.py` — carga `.env` y expone la configuración (rutas, conexión SQL Server, credenciales Snowflake).
- `log_reader.py` — lectura incremental del log y persistencia del estado (fecha + offset).
- `sqlserver_queries.py` — las queries SQL usadas.
- `sqlserver_client.py` — ejecución de esas queries contra SQL Server (pyodbc).
- `snowflake_client.py` — conexión a Snowflake por llave RSA (con respaldo a usuario/contraseña).

## Instalación

```
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en esta carpeta con las siguientes variables:

```
# Carpeta base de logs (arma la ruta del dia como {PWC_INTERCEPT_BASE_DIR}\{yyyyMMdd}\InterceptPwc26201\InterceptPwc26201.log)
PWC_INTERCEPT_BASE_DIR=C:\ruta\real\del\sitio\LogPwc

# Cadena de conexion ODBC a SQL Server
PWC_DB_CONN_STR=DRIVER={ODBC Driver 17 for SQL Server};SERVER=...;DATABASE=...;Trusted_Connection=yes

# Conexion a Snowflake (autenticacion por llave RSA)
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PRIVATE_KEY_PATH=C:\ruta\real\a\tu\llave_privada.p8
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_SCHEMA=...

# Opcionales
# PWC_STATE_FILE=C:\ruta\real\del\sitio\worker_pwc_state.json
# PWC_POLL_SECONDS=5
# PWC_RESULTADOS_DIR=C:\ruta\real\del\sitio\resultados
# SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=
# SNOWFLAKE_ROLE=...
# SNOWFLAKE_FALLBACK_USER=...
# SNOWFLAKE_FALLBACK_PASSWORD=...
```

## Uso

```
py worker.py
```

El worker corre en loop, revisando el log cada `PWC_POLL_SECONDS` segundos
(default 5) y guardando el estado procesado en `worker_pwc_state.json`.

# worker

Worker que monitorea el log NDJSON generado por ws_PowerCurve
(`LogPwc\{yyyyMMdd}\InterceptPwc26201\InterceptPwc26201.log`), y por cada
`IdSolicitudCredito` nuevo interceptado ejecuta contra SQL Server las queries
equivalentes a `usp_ObtenerDatosVehiculoSolicitud` y carga el resultado normalizado
en tablas `AGT_SAGI_BT_*` de Snowflake (una transacción por solicitud).

## Estructura

- `worker.py` — entrypoint: lee el log, orquesta el procesamiento y el ciclo principal.
- `config.py` — carga `.env` y expone la configuración (rutas, conexión SQL Server, credenciales Snowflake).
- `log_reader.py` — lectura incremental del log y persistencia del estado (fecha + offset).
- `sqlserver_queries.py` — las queries SQL usadas.
- `sqlserver_client.py` — ejecución de esas queries contra SQL Server (pyodbc).
- `pam_client.py` — obtiene el token OAuth2 y la llave privada RSA desde la API de PAM.
- `snowflake_client.py` — conexión a Snowflake por llave RSA (con respaldo a usuario/contraseña).
- `snowflake_loader.py` — transforma los 19 result sets al modelo normalizado y los carga en Snowflake.
- `ddl_snowflake.sql` — creación de las tablas `AGT_SAGI_BT_*` en `DB_DEV.SC_SLV_RIESGOS`.

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

# API de PAM (senhasegura) de donde se obtiene la llave privada RSA (OAuth2 client_credentials)
PAM_BASE_URL=https://...senhasegura.app
PAM_CLIENT_ID=...
PAM_CLIENT_SECRET=...
PAM_KEY_ID=...

# Conexion a Snowflake (autenticacion por llave RSA obtenida de PAM)
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
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

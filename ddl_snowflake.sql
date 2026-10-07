-- Modelo normalizado de las queries de SQL Server. Destino: DB_DEV.SC_SLV_RIESGOS
-- Tipos inferidos de las queries; ajustar si la carga reporta conversiones fallidas.

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_PERSONA (
    numero_documento    VARCHAR(20)   NOT NULL,
    tipo_documento      VARCHAR(100),
    nombre              VARCHAR(200),
    apellido_paterno    VARCHAR(100),
    apellido_materno    VARCHAR(100),
    fecha_nacimiento    DATE,
    CONSTRAINT PK_AGT_SAGI_BT_PERSONA PRIMARY KEY (numero_documento)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (
    instancia                   NUMBER(38,0)  NOT NULL,
    fecha_solicitud             DATE,
    numero_documento            VARCHAR(20),
    monto_soles                 NUMBER(18,2),
    monto_dolares               NUMBER(18,2),
    score                       NUMBER(18,2),
    puntaje                     NUMBER(18,2),
    cuotas                      NUMBER(18,2),
    cantidad_solicitudes_previas NUMBER(38,0),
    valor_bd                    NUMBER(18,2),
    nro_ingresos_mensuales      NUMBER(38,0),
    codigo_regimen              VARCHAR(20),
    regimen_sunat               VARCHAR(200),
    periodo_3                   VARCHAR(6),
    periodo_2                   VARCHAR(6),
    periodo_1                   VARCHAR(6),
    CONSTRAINT PK_AGT_SAGI_BT_SOLICITUD PRIMARY KEY (instancia),
    CONSTRAINT FK_AGT_SAGI_BT_SOLICITUD_PERSONA FOREIGN KEY (numero_documento)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_PERSONA (numero_documento)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_EMPLEO (
    instancia               NUMBER(38,0) NOT NULL,
    tipo_ocupacion          VARCHAR(20),
    nombre_ocupacion        VARCHAR(200),
    ruc_empleador           VARCHAR(20),
    cod_tipo_empresa        NUMBER(38,0),
    tipo_empresa            VARCHAR(50),
    cod_tipo_ingreso        NUMBER(38,0),
    tipo_ingreso            VARCHAR(50),
    fecha_ingreso_empresa   VARCHAR(30),
    CONSTRAINT PK_AGT_SAGI_BT_EMPLEO PRIMARY KEY (instancia),
    CONSTRAINT FK_AGT_SAGI_BT_EMPLEO_SOLICITUD FOREIGN KEY (instancia)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (instancia)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_DOMICILIO (
    numero_documento    VARCHAR(20)  NOT NULL,
    codigo              NUMBER(38,0) NOT NULL,
    tipo_domicilio      VARCHAR(100),
    direccion           VARCHAR(500),
    cod_habilitado      VARCHAR(5),
    habilitado          VARCHAR(5),
    CONSTRAINT PK_AGT_SAGI_BT_DOMICILIO PRIMARY KEY (numero_documento, codigo),
    CONSTRAINT FK_AGT_SAGI_BT_DOMICILIO_PERSONA FOREIGN KEY (numero_documento)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_PERSONA (numero_documento)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_MOROSIDAD_OPERACION (
    operacion       NUMBER(38,0) NOT NULL,
    cuenta          NUMBER(38,0) NOT NULL,
    moneda          VARCHAR(20),
    monto_capital   NUMBER(18,2),
    estado          VARCHAR(100),
    CONSTRAINT PK_AGT_SAGI_BT_MOROSIDAD_OPERACION PRIMARY KEY (operacion, cuenta)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_PERSONA_CUENTA (
    numero_documento    VARCHAR(20)  NOT NULL,
    cuenta              NUMBER(38,0) NOT NULL,
    CONSTRAINT PK_AGT_SAGI_BT_PERSONA_CUENTA PRIMARY KEY (numero_documento, cuenta),
    CONSTRAINT FK_AGT_SAGI_BT_PERSONA_CUENTA_PERSONA FOREIGN KEY (numero_documento)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_PERSONA (numero_documento)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_INGRESO_DETALLE (
    instancia           NUMBER(38,0) NOT NULL,
    variable_periodo    VARCHAR(50)  NOT NULL,
    categoria           VARCHAR(50)  NOT NULL,
    monto               NUMBER(18,2),
    CONSTRAINT PK_AGT_SAGI_BT_INGRESO_DETALLE PRIMARY KEY (instancia, variable_periodo, categoria),
    CONSTRAINT FK_AGT_SAGI_BT_INGRESO_DETALLE_SOLICITUD FOREIGN KEY (instancia)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (instancia)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_DEUDA_FINANCIERA (
    instancia       NUMBER(38,0) NOT NULL,
    nro_registro    NUMBER(38,0) NOT NULL,
    entidad         VARCHAR(200),
    tipo_credito    VARCHAR(100),
    modalidad       VARCHAR(100),
    moneda          VARCHAR(100),
    f_creacion      VARCHAR(50),
    f_modif         VARCHAR(50),
    cuota_titular   NUMBER(18,2),
    cuota_conyuge   NUMBER(18,2),
    CONSTRAINT PK_AGT_SAGI_BT_DEUDA_FINANCIERA PRIMARY KEY (instancia, nro_registro),
    CONSTRAINT FK_AGT_SAGI_BT_DEUDA_FINANCIERA_SOLICITUD FOREIGN KEY (instancia)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (instancia)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_INDICADOR_FINANCIERO (
    instancia           NUMBER(38,0) NOT NULL,
    concepto            VARCHAR(50)  NOT NULL,
    valor_mensual       NUMBER(18,2),
    total_acumulado     NUMBER(18,2),
    CONSTRAINT PK_AGT_SAGI_BT_INDICADOR_FINANCIERO PRIMARY KEY (instancia, concepto),
    CONSTRAINT FK_AGT_SAGI_BT_INDICADOR_FINANCIERO_SOLICITUD FOREIGN KEY (instancia)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (instancia)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_RCI (
    instancia           NUMBER(38,0) NOT NULL,
    valor_obtenido      VARCHAR(100),
    resultados          VARCHAR(200),
    CONSTRAINT PK_AGT_SAGI_BT_RCI PRIMARY KEY (instancia),
    CONSTRAINT FK_AGT_SAGI_BT_RCI_SOLICITUD FOREIGN KEY (instancia)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (instancia)
);

CREATE TABLE IF NOT EXISTS DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_VEHICULO (
    instancia       NUMBER(38,0) NOT NULL,
    proveedor       VARCHAR(200),
    marca           VARCHAR(200),
    modelo          VARCHAR(200),
    anio            NUMBER(38,0),
    tipo_uso        VARCHAR(100),
    CONSTRAINT FK_AGT_SAGI_BT_VEHICULO_SOLICITUD FOREIGN KEY (instancia)
        REFERENCES DB_DEV.SC_SLV_RIESGOS.AGT_SAGI_BT_SOLICITUD (instancia)
);

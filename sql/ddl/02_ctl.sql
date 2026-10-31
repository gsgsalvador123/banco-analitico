-- Control de lotes: toda carga deja rastro de qué llegó, qué entró y qué se apartó.
IF OBJECT_ID('ctl.lote') IS NULL
CREATE TABLE ctl.lote (
    lote_id          INT IDENTITY(1, 1) CONSTRAINT pk_lote PRIMARY KEY,
    fecha_negocio    DATE          NOT NULL,
    tipo             VARCHAR(20)   NOT NULL,
    estado           VARCHAR(20)   NOT NULL,
    inicio           DATETIME2(0)  NOT NULL CONSTRAINT df_lote_inicio DEFAULT SYSUTCDATETIME(),
    fin              DATETIME2(0)  NULL,
    filas_recibidas  INT           NULL,
    filas_cargadas   INT           NULL,
    filas_cuarentena INT           NULL,
    mensaje          NVARCHAR(4000) NULL,
    CONSTRAINT ck_lote_estado CHECK (estado IN ('EN_PROCESO', 'OK', 'ERROR'))
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ux_lote_ok')
CREATE UNIQUE INDEX ux_lote_ok ON ctl.lote (fecha_negocio, tipo) WHERE estado = 'OK';
GO

IF OBJECT_ID('ctl.regla_calidad') IS NULL
CREATE TABLE ctl.regla_calidad (
    regla        VARCHAR(30)   NOT NULL CONSTRAINT pk_regla_calidad PRIMARY KEY,
    archivo      VARCHAR(30)   NOT NULL,
    descripcion  NVARCHAR(200) NOT NULL
);
GO

IF OBJECT_ID('ctl.cuarentena') IS NULL
CREATE TABLE ctl.cuarentena (
    cuarentena_id BIGINT IDENTITY(1, 1) CONSTRAINT pk_cuarentena PRIMARY KEY,
    lote_id       INT           NOT NULL CONSTRAINT fk_cuarentena_lote REFERENCES ctl.lote (lote_id),
    archivo       VARCHAR(30)   NOT NULL,
    clave_origen  NVARCHAR(50)  NULL,
    regla         VARCHAR(30)   NOT NULL CONSTRAINT fk_cuarentena_regla REFERENCES ctl.regla_calidad (regla),
    fila          NVARCHAR(MAX) NOT NULL,
    registrado    DATETIME2(0)  NOT NULL CONSTRAINT df_cuarentena_registrado DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ctl.conciliacion') IS NULL
CREATE TABLE ctl.conciliacion (
    lote_id       INT            NOT NULL CONSTRAINT fk_conciliacion_lote REFERENCES ctl.lote (lote_id),
    archivo       VARCHAR(30)    NOT NULL,
    filas_control INT            NOT NULL,
    filas_stg     INT            NOT NULL,
    suma_control  DECIMAL(18, 2) NULL,
    suma_stg      DECIMAL(18, 2) NULL,
    CONSTRAINT pk_conciliacion PRIMARY KEY (lote_id, archivo)
);
GO

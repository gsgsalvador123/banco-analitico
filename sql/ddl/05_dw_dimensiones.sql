-- Dimensiones con clave sustituta. La fila -1 representa un valor desconocido.
IF OBJECT_ID('dw.dim_fecha') IS NULL
CREATE TABLE dw.dim_fecha (
    fecha_key    INT          NOT NULL CONSTRAINT pk_dim_fecha PRIMARY KEY,
    fecha        DATE         NOT NULL,
    anio         SMALLINT     NOT NULL,
    trimestre    TINYINT      NOT NULL,
    mes          TINYINT      NOT NULL,
    nombre_mes   VARCHAR(12)  NOT NULL,
    anio_mes     CHAR(7)      NOT NULL,
    dia          TINYINT      NOT NULL,
    dia_semana   TINYINT      NOT NULL,
    nombre_dia   VARCHAR(10)  NOT NULL,
    es_dia_habil BIT          NOT NULL,
    es_fin_mes   BIT          NOT NULL
);
GO

IF OBJECT_ID('dw.dim_distrito') IS NULL
BEGIN
    CREATE TABLE dw.dim_distrito (
        distrito_key         INT IDENTITY(1, 1) CONSTRAINT pk_dim_distrito PRIMARY KEY,
        distrito_id          INT            NOT NULL CONSTRAINT uq_dim_distrito UNIQUE,
        nombre               NVARCHAR(100)  NOT NULL,
        region               NVARCHAR(100)  NOT NULL,
        habitantes           INT            NULL,
        poblacion_urbana_pct DECIMAL(5, 1)  NULL,
        salario_promedio     INT            NULL,
        desempleo_95         DECIMAL(5, 2)  NULL,
        desempleo_96         DECIMAL(5, 2)  NULL,
        delitos_95           INT            NULL,
        delitos_96           INT            NULL
    );
    SET IDENTITY_INSERT dw.dim_distrito ON;
    INSERT dw.dim_distrito (distrito_key, distrito_id, nombre, region) VALUES (-1, -1, N'Desconocido', N'Desconocida');
    SET IDENTITY_INSERT dw.dim_distrito OFF;
END
GO

-- Historial SCD tipo 2: cada cambio crea una versión con sus fechas de vigencia.
IF OBJECT_ID('dw.dim_cliente') IS NULL
BEGIN
    CREATE TABLE dw.dim_cliente (
        cliente_key      INT IDENTITY(1, 1) CONSTRAINT pk_dim_cliente PRIMARY KEY,
        cliente_id       INT          NOT NULL,
        sexo             VARCHAR(12)  NOT NULL,
        fecha_nacimiento DATE         NULL,
        distrito_key     INT          NOT NULL CONSTRAINT fk_cliente_distrito REFERENCES dw.dim_distrito (distrito_key),
        vigente_desde    DATE         NOT NULL,
        vigente_hasta    DATE         NOT NULL,
        es_actual        BIT          NOT NULL
    );
    SET IDENTITY_INSERT dw.dim_cliente ON;
    INSERT dw.dim_cliente (cliente_key, cliente_id, sexo, distrito_key, vigente_desde, vigente_hasta, es_actual)
    VALUES (-1, -1, 'Desconocido', -1, '19000101', '99991231', 1);
    SET IDENTITY_INSERT dw.dim_cliente OFF;
    CREATE UNIQUE INDEX ux_dim_cliente_actual ON dw.dim_cliente (cliente_id) WHERE es_actual = 1;
    CREATE INDEX ix_dim_cliente_vigencia ON dw.dim_cliente (cliente_id, vigente_desde, vigente_hasta);
END
GO

IF OBJECT_ID('dw.dim_cuenta') IS NULL
BEGIN
    CREATE TABLE dw.dim_cuenta (
        cuenta_key         INT IDENTITY(1, 1) CONSTRAINT pk_dim_cuenta PRIMARY KEY,
        cuenta_id          INT           NOT NULL,
        distrito_key       INT           NOT NULL CONSTRAINT fk_cuenta_distrito REFERENCES dw.dim_distrito (distrito_key),
        cliente_titular_id INT           NOT NULL,
        frecuencia         NVARCHAR(50)  NOT NULL,
        fecha_apertura     DATE          NULL,
        vigente_desde      DATE          NOT NULL,
        vigente_hasta      DATE          NOT NULL,
        es_actual          BIT           NOT NULL
    );
    SET IDENTITY_INSERT dw.dim_cuenta ON;
    INSERT dw.dim_cuenta (cuenta_key, cuenta_id, distrito_key, cliente_titular_id, frecuencia, vigente_desde, vigente_hasta, es_actual)
    VALUES (-1, -1, -1, -1, N'Desconocida', '19000101', '99991231', 1);
    SET IDENTITY_INSERT dw.dim_cuenta OFF;
    CREATE UNIQUE INDEX ux_dim_cuenta_actual ON dw.dim_cuenta (cuenta_id) WHERE es_actual = 1;
    CREATE INDEX ix_dim_cuenta_vigencia ON dw.dim_cuenta (cuenta_id, vigente_desde, vigente_hasta);
END
GO

IF OBJECT_ID('dw.dim_movimiento') IS NULL
CREATE TABLE dw.dim_movimiento (
    movimiento_key   INT IDENTITY(1, 1) CONSTRAINT pk_dim_movimiento PRIMARY KEY,
    tipo_codigo      NVARCHAR(20)  NOT NULL,
    operacion_codigo NVARCHAR(50)  NOT NULL,
    categoria_codigo NVARCHAR(50)  NOT NULL,
    tipo             NVARCHAR(50)  NOT NULL,
    operacion        NVARCHAR(100) NOT NULL,
    categoria        NVARCHAR(100) NOT NULL,
    CONSTRAINT uq_dim_movimiento UNIQUE (tipo_codigo, operacion_codigo, categoria_codigo)
);
GO

IF OBJECT_ID('dw.dim_estado_prestamo') IS NULL
CREATE TABLE dw.dim_estado_prestamo (
    estado_key      INT          NOT NULL CONSTRAINT pk_dim_estado_prestamo PRIMARY KEY,
    codigo          CHAR(1)      NOT NULL CONSTRAINT uq_dim_estado_prestamo UNIQUE,
    descripcion     NVARCHAR(60) NOT NULL,
    es_problematico BIT          NOT NULL
);
GO

IF OBJECT_ID('dw.dim_prestamo') IS NULL
CREATE TABLE dw.dim_prestamo (
    prestamo_key     INT IDENTITY(1, 1) CONSTRAINT pk_dim_prestamo PRIMARY KEY,
    prestamo_id      INT            NOT NULL CONSTRAINT uq_dim_prestamo UNIQUE,
    cuenta_id        INT            NOT NULL,
    estado_key       INT            NOT NULL CONSTRAINT fk_prestamo_estado REFERENCES dw.dim_estado_prestamo (estado_key),
    fecha_concesion  DATE           NOT NULL,
    monto            DECIMAL(18, 2) NOT NULL,
    plazo_meses      INT            NOT NULL,
    cuota            DECIMAL(18, 2) NOT NULL
);
GO

-- Vínculo entre disposición y cuenta: las tarjetas nuevas llegan solo con su disposición.
IF OBJECT_ID('dw.disposicion') IS NULL
CREATE TABLE dw.disposicion (
    disp_id   INT NOT NULL CONSTRAINT pk_disposicion PRIMARY KEY,
    cuenta_id INT NOT NULL
);
GO

IF OBJECT_ID('dw.dim_tarjeta') IS NULL
BEGIN
    CREATE TABLE dw.dim_tarjeta (
        tarjeta_key   INT IDENTITY(1, 1) CONSTRAINT pk_dim_tarjeta PRIMARY KEY,
        tarjeta_id    INT          NOT NULL CONSTRAINT uq_dim_tarjeta UNIQUE,
        cuenta_id     INT          NOT NULL,
        tipo          VARCHAR(20)  NOT NULL,
        fecha_emision DATE         NULL
    );
    SET IDENTITY_INSERT dw.dim_tarjeta ON;
    INSERT dw.dim_tarjeta (tarjeta_key, tarjeta_id, cuenta_id, tipo) VALUES (-1, -1, -1, 'Sin tarjeta');
    SET IDENTITY_INSERT dw.dim_tarjeta OFF;
END
GO

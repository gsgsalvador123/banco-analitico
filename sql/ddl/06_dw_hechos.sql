-- Grano: un movimiento. cuenta_id se conserva para reconstruir saldos sin pasar por el historial.
IF OBJECT_ID('dw.fact_transaccion') IS NULL
BEGIN
    CREATE TABLE dw.fact_transaccion (
        trans_id          BIGINT         NOT NULL,
        fecha_key         INT            NOT NULL CONSTRAINT fk_trans_fecha REFERENCES dw.dim_fecha (fecha_key),
        cuenta_key        INT            NOT NULL CONSTRAINT fk_trans_cuenta REFERENCES dw.dim_cuenta (cuenta_key),
        cliente_key       INT            NOT NULL CONSTRAINT fk_trans_cliente REFERENCES dw.dim_cliente (cliente_key),
        distrito_key      INT            NOT NULL CONSTRAINT fk_trans_distrito REFERENCES dw.dim_distrito (distrito_key),
        movimiento_key    INT            NOT NULL CONSTRAINT fk_trans_movimiento REFERENCES dw.dim_movimiento (movimiento_key),
        cuenta_id         INT            NOT NULL,
        monto             DECIMAL(18, 2) NOT NULL,
        saldo_posterior   DECIMAL(18, 2) NULL,
        banco_contraparte NVARCHAR(20)   NULL,
        lote_id           INT            NOT NULL CONSTRAINT fk_trans_lote REFERENCES ctl.lote (lote_id),
        CONSTRAINT pk_fact_transaccion PRIMARY KEY NONCLUSTERED (trans_id)
    );
    CREATE CLUSTERED INDEX cx_fact_transaccion ON dw.fact_transaccion (fecha_key, trans_id);
    CREATE INDEX ix_fact_transaccion_cuenta ON dw.fact_transaccion (cuenta_id, fecha_key) INCLUDE (saldo_posterior, movimiento_key, monto);
END
GO

-- Grano: una cuenta por mes. mes_key es el último día del mes.
IF OBJECT_ID('dw.fact_saldo_mensual') IS NULL
CREATE TABLE dw.fact_saldo_mensual (
    mes_key           INT            NOT NULL CONSTRAINT fk_saldo_fecha REFERENCES dw.dim_fecha (fecha_key),
    cuenta_key        INT            NOT NULL CONSTRAINT fk_saldo_cuenta REFERENCES dw.dim_cuenta (cuenta_key),
    cliente_key       INT            NOT NULL CONSTRAINT fk_saldo_cliente REFERENCES dw.dim_cliente (cliente_key),
    distrito_key      INT            NOT NULL CONSTRAINT fk_saldo_distrito REFERENCES dw.dim_distrito (distrito_key),
    tarjeta_key       INT            NOT NULL CONSTRAINT fk_saldo_tarjeta REFERENCES dw.dim_tarjeta (tarjeta_key),
    saldo_cierre      DECIMAL(18, 2) NOT NULL,
    saldo_promedio    DECIMAL(18, 2) NOT NULL,
    abonos            DECIMAL(18, 2) NOT NULL,
    cargos            DECIMAL(18, 2) NOT NULL,
    num_movimientos   INT            NOT NULL,
    intereses_pagados DECIMAL(18, 2) NOT NULL,
    comisiones        DECIMAL(18, 2) NOT NULL,
    sanciones         DECIMAL(18, 2) NOT NULL,
    CONSTRAINT pk_fact_saldo_mensual PRIMARY KEY (mes_key, cuenta_key)
);
GO

-- Grano: un préstamo por mes. El atraso sale de contar los pagos UVER contra las cuotas esperadas.
IF OBJECT_ID('dw.fact_prestamo_mensual') IS NULL
CREATE TABLE dw.fact_prestamo_mensual (
    mes_key           INT            NOT NULL CONSTRAINT fk_prestamo_fecha REFERENCES dw.dim_fecha (fecha_key),
    prestamo_key      INT            NOT NULL CONSTRAINT fk_prestamo_prestamo REFERENCES dw.dim_prestamo (prestamo_key),
    cuenta_key        INT            NOT NULL CONSTRAINT fk_prestamo_cuenta REFERENCES dw.dim_cuenta (cuenta_key),
    cliente_key       INT            NOT NULL CONSTRAINT fk_prestamo_cliente REFERENCES dw.dim_cliente (cliente_key),
    distrito_key      INT            NOT NULL CONSTRAINT fk_prestamo_distrito REFERENCES dw.dim_distrito (distrito_key),
    estado_key        INT            NOT NULL CONSTRAINT fk_prestamo_mes_estado REFERENCES dw.dim_estado_prestamo (estado_key),
    cuotas_esperadas  INT            NOT NULL,
    cuotas_pagadas    INT            NOT NULL,
    cuotas_atrasadas  INT            NOT NULL,
    capital_pendiente DECIMAL(18, 2) NOT NULL,
    interes_estimado  DECIMAL(18, 2) NOT NULL,
    en_mora           BIT            NOT NULL,
    tramo_atraso      VARCHAR(12)    NOT NULL,
    CONSTRAINT pk_fact_prestamo_mensual PRIMARY KEY (mes_key, prestamo_key)
);
GO

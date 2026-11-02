-- Grano: una gestión de cobranza registrada en la app. fecha_key es la fecha real de la gestión.
IF OBJECT_ID('dw.fact_gestion_cobranza') IS NULL
CREATE TABLE dw.fact_gestion_cobranza (
    gestion_id       INT            NOT NULL CONSTRAINT pk_fact_gestion_cobranza PRIMARY KEY,
    fecha_key        INT            NOT NULL CONSTRAINT fk_gestion_fecha REFERENCES dw.dim_fecha (fecha_key),
    prestamo_key     INT            NOT NULL CONSTRAINT fk_gestion_prestamo REFERENCES dw.dim_prestamo (prestamo_key),
    cuenta_key       INT            NOT NULL CONSTRAINT fk_gestion_cuenta REFERENCES dw.dim_cuenta (cuenta_key),
    cliente_key      INT            NOT NULL CONSTRAINT fk_gestion_cliente REFERENCES dw.dim_cliente (cliente_key),
    distrito_key     INT            NOT NULL CONSTRAINT fk_gestion_distrito REFERENCES dw.dim_distrito (distrito_key),
    analista         NVARCHAR(100)  NOT NULL,
    resultado        NVARCHAR(40)   NOT NULL,
    monto_prometido  DECIMAL(18, 2) NULL,
    fecha_compromiso DATE           NULL
);
GO

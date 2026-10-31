-- Gestiones que registra la app de cobranzas. Solo la app escribe aquí.
IF OBJECT_ID('ops.gestion_cobranza') IS NULL
CREATE TABLE ops.gestion_cobranza (
    gestion_id       INT IDENTITY(1, 1) CONSTRAINT pk_gestion_cobranza PRIMARY KEY,
    prestamo_id      INT            NOT NULL,
    fecha_gestion    DATETIME2(0)   NOT NULL CONSTRAINT df_gestion_fecha DEFAULT SYSUTCDATETIME(),
    analista         NVARCHAR(100)  NOT NULL,
    resultado        NVARCHAR(40)   NOT NULL,
    monto_prometido  DECIMAL(18, 2) NULL,
    fecha_compromiso DATE           NULL,
    comentario       NVARCHAR(500)  NULL
);
GO

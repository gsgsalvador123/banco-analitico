-- Traduce los códigos en checo y guarda los supuestos del negocio.
IF OBJECT_ID('ref.codigo') IS NULL
CREATE TABLE ref.codigo (
    dominio     VARCHAR(30)   NOT NULL,
    codigo      NVARCHAR(50)  NOT NULL,
    descripcion NVARCHAR(100) NOT NULL,
    CONSTRAINT pk_codigo PRIMARY KEY (dominio, codigo)
);
GO

-- Berka no incluye intereses de préstamos: esta tasa es un supuesto y no un dato real.
IF OBJECT_ID('ref.supuesto_tasa') IS NULL
CREATE TABLE ref.supuesto_tasa (
    vigente_desde DATE          NOT NULL CONSTRAINT pk_supuesto_tasa PRIMARY KEY,
    vigente_hasta DATE          NOT NULL,
    tasa_anual    DECIMAL(6, 4) NOT NULL,
    descripcion   NVARCHAR(200) NOT NULL
);
GO

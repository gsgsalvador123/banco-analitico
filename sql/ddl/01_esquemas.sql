-- Una capa por esquema: stg recibe, dw guarda, mart publica, ctl audita, ref documenta y ops opera.
IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');
GO
IF SCHEMA_ID('dw') IS NULL EXEC('CREATE SCHEMA dw');
GO
IF SCHEMA_ID('mart') IS NULL EXEC('CREATE SCHEMA mart');
GO
IF SCHEMA_ID('ctl') IS NULL EXEC('CREATE SCHEMA ctl');
GO
IF SCHEMA_ID('ref') IS NULL EXEC('CREATE SCHEMA ref');
GO
IF SCHEMA_ID('ops') IS NULL EXEC('CREATE SCHEMA ops');
GO

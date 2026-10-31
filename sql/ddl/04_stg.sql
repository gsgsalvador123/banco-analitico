-- Copia de los archivos: todo es texto para que ningún error de tipo detenga la recepción.
IF OBJECT_ID('stg.distrito') IS NULL
CREATE TABLE stg.distrito (
    distrito_id NVARCHAR(20), nombre NVARCHAR(100), region NVARCHAR(100), habitantes NVARCHAR(20),
    poblacion_urbana_pct NVARCHAR(20), salario_promedio NVARCHAR(20), desempleo_95 NVARCHAR(20),
    desempleo_96 NVARCHAR(20), delitos_95 NVARCHAR(20), delitos_96 NVARCHAR(20)
);
GO
IF OBJECT_ID('stg.cliente') IS NULL
CREATE TABLE stg.cliente (
    cliente_id NVARCHAR(20), fecha_nacimiento NVARCHAR(20), sexo NVARCHAR(5), distrito_id NVARCHAR(20)
);
GO
IF OBJECT_ID('stg.cuenta') IS NULL
CREATE TABLE stg.cuenta (
    cuenta_id NVARCHAR(20), distrito_id NVARCHAR(20), frecuencia NVARCHAR(50), fecha_apertura NVARCHAR(20)
);
GO
IF OBJECT_ID('stg.disp') IS NULL
CREATE TABLE stg.disp (
    disp_id NVARCHAR(20), cliente_id NVARCHAR(20), cuenta_id NVARCHAR(20), tipo NVARCHAR(20)
);
GO
IF OBJECT_ID('stg.trans') IS NULL
CREATE TABLE stg.trans (
    trans_id NVARCHAR(20), cuenta_id NVARCHAR(20), fecha NVARCHAR(20), tipo NVARCHAR(20),
    operacion NVARCHAR(50), monto NVARCHAR(30), saldo NVARCHAR(30), categoria NVARCHAR(50),
    banco_contraparte NVARCHAR(20), cuenta_contraparte NVARCHAR(30),
    motivo_rechazo VARCHAR(30) NULL
);
GO
IF OBJECT_ID('stg.prestamo') IS NULL
CREATE TABLE stg.prestamo (
    prestamo_id NVARCHAR(20), cuenta_id NVARCHAR(20), fecha NVARCHAR(20), monto NVARCHAR(30),
    plazo_meses NVARCHAR(10), cuota NVARCHAR(30), estado NVARCHAR(5),
    motivo_rechazo VARCHAR(30) NULL
);
GO
IF OBJECT_ID('stg.tarjeta') IS NULL
CREATE TABLE stg.tarjeta (
    tarjeta_id NVARCHAR(20), disp_id NVARCHAR(20), tipo NVARCHAR(20), fecha_emision NVARCHAR(20)
);
GO
IF OBJECT_ID('stg.cambio_cliente') IS NULL
CREATE TABLE stg.cambio_cliente (cliente_id NVARCHAR(20), distrito_id NVARCHAR(20));
GO
IF OBJECT_ID('stg.cambio_cuenta') IS NULL
CREATE TABLE stg.cambio_cuenta (cuenta_id NVARCHAR(20), frecuencia NVARCHAR(50));
GO

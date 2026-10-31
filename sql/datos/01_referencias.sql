-- Datos de referencia. Se pueden volver a ejecutar sin duplicar filas.
MERGE ref.codigo AS d
USING (VALUES
    ('tipo', N'PRIJEM', N'Abono'),
    ('tipo', N'VYDAJ', N'Cargo'),
    ('tipo', N'VYBER', N'Cargo'),
    ('operacion', N'', N'Sin operación'),
    ('operacion', N'VYBER KARTOU', N'Retiro con tarjeta'),
    ('operacion', N'VKLAD', N'Depósito en efectivo'),
    ('operacion', N'PREVOD Z UCTU', N'Cobro desde otro banco'),
    ('operacion', N'VYBER', N'Retiro en efectivo'),
    ('operacion', N'PREVOD NA UCET', N'Envío a otro banco'),
    ('categoria', N'', N'Sin categoría'),
    ('categoria', N'POJISTNE', N'Pago de seguro'),
    ('categoria', N'SLUZBY', N'Pago por extracto'),
    ('categoria', N'UROK', N'Interés abonado'),
    ('categoria', N'SANKC. UROK', N'Interés de sanción'),
    ('categoria', N'SIPO', N'Pagos del hogar'),
    ('categoria', N'DUCHOD', N'Pensión'),
    ('categoria', N'UVER', N'Pago de préstamo'),
    ('frecuencia', N'POPLATEK MESICNE', N'Mensual'),
    ('frecuencia', N'POPLATEK TYDNE', N'Semanal'),
    ('frecuencia', N'POPLATEK PO OBRATU', N'Después de cada transacción')
) AS o (dominio, codigo, descripcion)
ON d.dominio = o.dominio AND d.codigo = o.codigo
WHEN MATCHED THEN UPDATE SET descripcion = o.descripcion
WHEN NOT MATCHED THEN INSERT (dominio, codigo, descripcion) VALUES (o.dominio, o.codigo, o.descripcion);
GO

MERGE ctl.regla_calidad AS d
USING (VALUES
    ('TRX_DUPLICADO', 'trans', N'El identificador se repite dentro del archivo'),
    ('TRX_MONTO_NULO', 'trans', N'El monto está vacío o no es numérico'),
    ('TRX_FECHA_INVALIDA', 'trans', N'La fecha no existe en el calendario'),
    ('TRX_CUENTA_DESCONOCIDA', 'trans', N'La cuenta no existe en el almacén'),
    ('TRX_YA_CARGADA', 'trans', N'El movimiento ya se cargó en un lote anterior'),
    ('PRE_CUENTA_DESCONOCIDA', 'prestamo', N'La cuenta del préstamo no existe en el almacén')
) AS o (regla, archivo, descripcion)
ON d.regla = o.regla
WHEN MATCHED THEN UPDATE SET archivo = o.archivo, descripcion = o.descripcion
WHEN NOT MATCHED THEN INSERT (regla, archivo, descripcion) VALUES (o.regla, o.archivo, o.descripcion);
GO

IF NOT EXISTS (SELECT 1 FROM ref.supuesto_tasa)
INSERT ref.supuesto_tasa (vigente_desde, vigente_hasta, tasa_anual, descripcion)
VALUES ('19000101', '99991231', 0.1200, N'Supuesto del proyecto: Berka no trae intereses de préstamos');
GO

MERGE dw.dim_estado_prestamo AS d
USING (VALUES
    (1, 'A', N'Terminado sin problemas', 0),
    (2, 'B', N'Terminado sin pagar', 1),
    (3, 'C', N'Vigente al día', 0),
    (4, 'D', N'Vigente con deuda', 1)
) AS o (estado_key, codigo, descripcion, es_problematico)
ON d.estado_key = o.estado_key
WHEN MATCHED THEN UPDATE SET codigo = o.codigo, descripcion = o.descripcion, es_problematico = o.es_problematico
WHEN NOT MATCHED THEN INSERT (estado_key, codigo, descripcion, es_problematico)
    VALUES (o.estado_key, o.codigo, o.descripcion, o.es_problematico);
GO

-- Calendario de 2021 a 2027, sin depender del idioma del servidor.
IF NOT EXISTS (SELECT 1 FROM dw.dim_fecha)
BEGIN
    DECLARE @dias INT = DATEDIFF(DAY, '20210101', '20271231') + 1;
    WITH numeros AS (
        SELECT TOP (@dias) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
        FROM sys.all_objects a CROSS JOIN sys.all_objects b
    ), dias AS (
        SELECT DATEADD(DAY, n, CAST('20210101' AS DATE)) AS fecha FROM numeros
    ), calendario AS (
        SELECT fecha,
               (DATEDIFF(DAY, '19000101', fecha) % 7) + 1 AS dia_semana
        FROM dias
    )
    INSERT dw.dim_fecha (fecha_key, fecha, anio, trimestre, mes, nombre_mes, anio_mes, dia, dia_semana, nombre_dia, es_dia_habil, es_fin_mes)
    SELECT YEAR(fecha) * 10000 + MONTH(fecha) * 100 + DAY(fecha),
           fecha,
           YEAR(fecha),
           (MONTH(fecha) + 2) / 3,
           MONTH(fecha),
           CHOOSE(MONTH(fecha), 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'),
           CONVERT(CHAR(7), fecha, 120),
           DAY(fecha),
           dia_semana,
           CHOOSE(dia_semana, 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'),
           IIF(dia_semana <= 5, 1, 0),
           IIF(fecha = EOMONTH(fecha), 1, 0)
    FROM calendario;
END
GO

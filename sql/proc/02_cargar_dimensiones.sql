-- Los maestros van antes de validar: las reglas consultan las cuentas que existen.
CREATE OR ALTER PROCEDURE dw.usp_cargar_maestros
AS
BEGIN
    SET NOCOUNT ON;

    INSERT dw.dim_distrito (distrito_id, nombre, region, habitantes, poblacion_urbana_pct, salario_promedio,
                            desempleo_95, desempleo_96, delitos_95, delitos_96)
    SELECT TRY_CONVERT(INT, s.distrito_id), s.nombre, s.region, TRY_CONVERT(INT, s.habitantes),
           TRY_CONVERT(DECIMAL(5, 1), s.poblacion_urbana_pct), TRY_CONVERT(INT, s.salario_promedio),
           TRY_CONVERT(DECIMAL(5, 2), s.desempleo_95), TRY_CONVERT(DECIMAL(5, 2), s.desempleo_96),
           TRY_CONVERT(INT, s.delitos_95), TRY_CONVERT(INT, s.delitos_96)
    FROM stg.distrito s
    WHERE NOT EXISTS (SELECT 1 FROM dw.dim_distrito d WHERE d.distrito_id = TRY_CONVERT(INT, s.distrito_id));

    INSERT dw.dim_cliente (cliente_id, sexo, fecha_nacimiento, distrito_key, vigente_desde, vigente_hasta, es_actual)
    SELECT TRY_CONVERT(INT, s.cliente_id),
           IIF(s.sexo = N'M', 'Mujer', 'Hombre'),
           TRY_CONVERT(DATE, s.fecha_nacimiento, 112),
           ISNULL(d.distrito_key, -1),
           '19000101', '99991231', 1
    FROM stg.cliente s
    LEFT JOIN dw.dim_distrito d ON d.distrito_id = TRY_CONVERT(INT, s.distrito_id)
    WHERE NOT EXISTS (SELECT 1 FROM dw.dim_cliente c WHERE c.cliente_id = TRY_CONVERT(INT, s.cliente_id));

    INSERT dw.dim_cuenta (cuenta_id, distrito_key, cliente_titular_id, frecuencia, fecha_apertura,
                          vigente_desde, vigente_hasta, es_actual)
    SELECT TRY_CONVERT(INT, s.cuenta_id),
           ISNULL(d.distrito_key, -1),
           ISNULL(TRY_CONVERT(INT, t.cliente_id), -1),
           ISNULL(r.descripcion, N'Desconocida'),
           TRY_CONVERT(DATE, s.fecha_apertura, 112),
           '19000101', '99991231', 1
    FROM stg.cuenta s
    LEFT JOIN dw.dim_distrito d ON d.distrito_id = TRY_CONVERT(INT, s.distrito_id)
    LEFT JOIN stg.disp t ON t.cuenta_id = s.cuenta_id AND t.tipo = N'OWNER'
    LEFT JOIN ref.codigo r ON r.dominio = 'frecuencia' AND r.codigo = s.frecuencia
    WHERE NOT EXISTS (SELECT 1 FROM dw.dim_cuenta c WHERE c.cuenta_id = TRY_CONVERT(INT, s.cuenta_id));

END
GO

CREATE OR ALTER PROCEDURE dw.usp_cargar_dimensiones
    @fecha_negocio DATE
AS
BEGIN
    SET NOCOUNT ON;

    INSERT dw.dim_prestamo (prestamo_id, cuenta_id, estado_key, fecha_concesion, monto, plazo_meses, cuota)
    SELECT TRY_CONVERT(INT, s.prestamo_id), TRY_CONVERT(INT, s.cuenta_id), e.estado_key,
           TRY_CONVERT(DATE, s.fecha, 112), TRY_CONVERT(DECIMAL(18, 2), s.monto),
           TRY_CONVERT(INT, s.plazo_meses), TRY_CONVERT(DECIMAL(18, 2), s.cuota)
    FROM stg.prestamo s
    JOIN dw.dim_estado_prestamo e ON e.codigo = s.estado
    WHERE s.motivo_rechazo IS NULL
      AND NOT EXISTS (SELECT 1 FROM dw.dim_prestamo p WHERE p.prestamo_id = TRY_CONVERT(INT, s.prestamo_id));

    INSERT dw.disposicion (disp_id, cuenta_id)
    SELECT TRY_CONVERT(INT, s.disp_id), TRY_CONVERT(INT, s.cuenta_id)
    FROM stg.disp s
    WHERE NOT EXISTS (SELECT 1 FROM dw.disposicion d WHERE d.disp_id = TRY_CONVERT(INT, s.disp_id));

    INSERT dw.dim_tarjeta (tarjeta_id, cuenta_id, tipo, fecha_emision)
    SELECT TRY_CONVERT(INT, s.tarjeta_id), d.cuenta_id, s.tipo, TRY_CONVERT(DATE, s.fecha_emision, 112)
    FROM stg.tarjeta s
    JOIN dw.disposicion d ON d.disp_id = TRY_CONVERT(INT, s.disp_id)
    WHERE NOT EXISTS (SELECT 1 FROM dw.dim_tarjeta t WHERE t.tarjeta_id = TRY_CONVERT(INT, s.tarjeta_id));

    -- SCD tipo 2: se cierra la versión actual y se abre otra desde la fecha de negocio.
    DECLARE @cierre DATE = DATEADD(DAY, -1, @fecha_negocio);

    SELECT c.cliente_key, c.cliente_id, c.sexo, c.fecha_nacimiento, d.distrito_key
    INTO #clientes_cambiados
    FROM stg.cambio_cliente s
    JOIN dw.dim_cliente c ON c.cliente_id = TRY_CONVERT(INT, s.cliente_id) AND c.es_actual = 1
    JOIN dw.dim_distrito d ON d.distrito_id = TRY_CONVERT(INT, s.distrito_id)
    WHERE c.distrito_key <> d.distrito_key;

    UPDATE c SET vigente_hasta = @cierre, es_actual = 0
    FROM dw.dim_cliente c
    JOIN #clientes_cambiados n ON n.cliente_key = c.cliente_key;

    INSERT dw.dim_cliente (cliente_id, sexo, fecha_nacimiento, distrito_key, vigente_desde, vigente_hasta, es_actual)
    SELECT cliente_id, sexo, fecha_nacimiento, distrito_key, @fecha_negocio, '99991231', 1
    FROM #clientes_cambiados;

    SELECT c.cuenta_key, c.cuenta_id, c.distrito_key, c.cliente_titular_id, r.descripcion AS frecuencia, c.fecha_apertura
    INTO #cuentas_cambiadas
    FROM stg.cambio_cuenta s
    JOIN dw.dim_cuenta c ON c.cuenta_id = TRY_CONVERT(INT, s.cuenta_id) AND c.es_actual = 1
    JOIN ref.codigo r ON r.dominio = 'frecuencia' AND r.codigo = s.frecuencia
    WHERE c.frecuencia <> r.descripcion;

    UPDATE c SET vigente_hasta = @cierre, es_actual = 0
    FROM dw.dim_cuenta c
    JOIN #cuentas_cambiadas n ON n.cuenta_key = c.cuenta_key;

    INSERT dw.dim_cuenta (cuenta_id, distrito_key, cliente_titular_id, frecuencia, fecha_apertura,
                          vigente_desde, vigente_hasta, es_actual)
    SELECT cuenta_id, distrito_key, cliente_titular_id, frecuencia, fecha_apertura, @fecha_negocio, '99991231', 1
    FROM #cuentas_cambiadas;
END
GO

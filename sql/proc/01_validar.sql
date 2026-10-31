-- Marca cada fila mala con la primera regla que incumple y la copia a cuarentena con su motivo.
CREATE OR ALTER PROCEDURE ctl.usp_validar_lote
    @lote_id INT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE stg.trans SET motivo_rechazo = NULL;
    UPDATE stg.prestamo SET motivo_rechazo = NULL;

    UPDATE t SET motivo_rechazo = 'TRX_MONTO_NULO'
    FROM stg.trans t
    WHERE TRY_CONVERT(DECIMAL(18, 2), NULLIF(t.monto, N'')) IS NULL;

    UPDATE t SET motivo_rechazo = 'TRX_FECHA_INVALIDA'
    FROM stg.trans t
    WHERE t.motivo_rechazo IS NULL
      AND NOT EXISTS (SELECT 1 FROM dw.dim_fecha f WHERE f.fecha = TRY_CONVERT(DATE, t.fecha, 112));

    UPDATE t SET motivo_rechazo = 'TRX_CUENTA_DESCONOCIDA'
    FROM stg.trans t
    WHERE t.motivo_rechazo IS NULL
      AND NOT EXISTS (SELECT 1 FROM dw.dim_cuenta c WHERE c.cuenta_id = TRY_CONVERT(INT, t.cuenta_id) AND c.cuenta_key <> -1);

    -- De las copias válidas de un mismo movimiento se conserva una.
    WITH copias AS (
        SELECT motivo_rechazo,
               ROW_NUMBER() OVER (PARTITION BY trans_id ORDER BY (SELECT NULL)) AS orden
        FROM stg.trans
        WHERE motivo_rechazo IS NULL
    )
    UPDATE copias SET motivo_rechazo = 'TRX_DUPLICADO' WHERE orden > 1;

    UPDATE t SET motivo_rechazo = 'TRX_YA_CARGADA'
    FROM stg.trans t
    WHERE t.motivo_rechazo IS NULL
      AND EXISTS (SELECT 1 FROM dw.fact_transaccion f WHERE f.trans_id = TRY_CONVERT(BIGINT, t.trans_id));

    UPDATE p SET motivo_rechazo = 'PRE_CUENTA_DESCONOCIDA'
    FROM stg.prestamo p
    WHERE NOT EXISTS (SELECT 1 FROM dw.dim_cuenta c WHERE c.cuenta_id = TRY_CONVERT(INT, p.cuenta_id) AND c.cuenta_key <> -1);

    INSERT ctl.cuarentena (lote_id, archivo, clave_origen, regla, fila)
    SELECT @lote_id, 'trans', t.trans_id, t.motivo_rechazo,
           (SELECT t.trans_id, t.cuenta_id, t.fecha, t.tipo, t.operacion, t.monto, t.saldo, t.categoria
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM stg.trans t
    WHERE t.motivo_rechazo IS NOT NULL;

    INSERT ctl.cuarentena (lote_id, archivo, clave_origen, regla, fila)
    SELECT @lote_id, 'prestamo', p.prestamo_id, p.motivo_rechazo,
           (SELECT p.prestamo_id, p.cuenta_id, p.fecha, p.monto, p.plazo_meses, p.cuota, p.estado
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM stg.prestamo p
    WHERE p.motivo_rechazo IS NOT NULL;
END
GO

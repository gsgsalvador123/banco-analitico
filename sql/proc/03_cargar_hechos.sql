CREATE OR ALTER PROCEDURE dw.usp_cargar_hechos
    @lote_id INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Una combinación nueva de códigos crea su fila sin necesidad de cambiar código.
    INSERT dw.dim_movimiento (tipo_codigo, operacion_codigo, categoria_codigo, tipo, operacion, categoria)
    SELECT DISTINCT s.tipo, s.operacion, s.categoria,
           ISNULL(rt.descripcion, s.tipo),
           ISNULL(ro.descripcion, s.operacion),
           ISNULL(rc.descripcion, s.categoria)
    FROM stg.trans s
    LEFT JOIN ref.codigo rt ON rt.dominio = 'tipo' AND rt.codigo = s.tipo
    LEFT JOIN ref.codigo ro ON ro.dominio = 'operacion' AND ro.codigo = s.operacion
    LEFT JOIN ref.codigo rc ON rc.dominio = 'categoria' AND rc.codigo = s.categoria
    WHERE s.motivo_rechazo IS NULL
      AND NOT EXISTS (
          SELECT 1 FROM dw.dim_movimiento m
          WHERE m.tipo_codigo = s.tipo AND m.operacion_codigo = s.operacion AND m.categoria_codigo = s.categoria
      );

    -- Cada movimiento apunta a la versión de la cuenta y del cliente vigente en su fecha.
    INSERT dw.fact_transaccion (trans_id, fecha_key, cuenta_key, cliente_key, distrito_key, movimiento_key,
                                cuenta_id, monto, saldo_posterior, banco_contraparte, lote_id)
    SELECT TRY_CONVERT(BIGINT, s.trans_id), f.fecha_key, c.cuenta_key, ISNULL(cl.cliente_key, -1),
           c.distrito_key, m.movimiento_key, c.cuenta_id, TRY_CONVERT(DECIMAL(18, 2), s.monto),
           TRY_CONVERT(DECIMAL(18, 2), NULLIF(s.saldo, N'')), NULLIF(s.banco_contraparte, N''), @lote_id
    FROM stg.trans s
    JOIN dw.dim_fecha f ON f.fecha = TRY_CONVERT(DATE, s.fecha, 112)
    JOIN dw.dim_cuenta c ON c.cuenta_id = TRY_CONVERT(INT, s.cuenta_id)
                        AND f.fecha BETWEEN c.vigente_desde AND c.vigente_hasta
    JOIN dw.dim_movimiento m ON m.tipo_codigo = s.tipo AND m.operacion_codigo = s.operacion
                            AND m.categoria_codigo = s.categoria
    LEFT JOIN dw.dim_cliente cl ON cl.cliente_id = c.cliente_titular_id
                               AND f.fecha BETWEEN cl.vigente_desde AND cl.vigente_hasta
    WHERE s.motivo_rechazo IS NULL;
END
GO

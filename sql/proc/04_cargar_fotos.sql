-- Reconstruye las fotos del mes que contiene @corte con los datos disponibles hasta esa fecha.
-- Se puede repetir: primero borra el mes y luego lo calcula de nuevo.
CREATE OR ALTER PROCEDURE dw.usp_cargar_fotos
    @corte DATE
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @inicio DATE = DATEFROMPARTS(YEAR(@corte), MONTH(@corte), 1);
    DECLARE @fin_mes DATE = EOMONTH(@corte);
    DECLARE @mes_key INT = CONVERT(INT, CONVERT(CHAR(8), @fin_mes, 112));
    DECLARE @inicio_key INT = CONVERT(INT, CONVERT(CHAR(8), @inicio, 112));
    DECLARE @corte_key INT = CONVERT(INT, CONVERT(CHAR(8), @corte, 112));
    DECLARE @tasa DECIMAL(6, 4) = (SELECT tasa_anual FROM ref.supuesto_tasa WHERE @corte BETWEEN vigente_desde AND vigente_hasta);
    DECLARE @parte_mes DECIMAL(9, 6) = DAY(@corte) * 1.0 / DAY(@fin_mes);
    -- En un mes sin cerrar, su cuota aún no vence: solo cuentan los meses completos.
    DECLARE @mes_cerrado DATE = IIF(@corte = @fin_mes, @corte, EOMONTH(@corte, -1));

    DELETE dw.fact_saldo_mensual WHERE mes_key = @mes_key;
    DELETE dw.fact_prestamo_mensual WHERE mes_key = @mes_key;

    -- El saldo se acumula desde los montos: trans_id no sigue el orden real dentro de un día.
    SELECT t.cuenta_id, SUM(IIF(m.tipo = N'Abono', t.monto, -t.monto)) AS saldo
    INTO #apertura
    FROM dw.fact_transaccion t
    JOIN dw.dim_movimiento m ON m.movimiento_key = t.movimiento_key
    WHERE t.fecha_key < @inicio_key
    GROUP BY t.cuenta_id;

    SELECT x.cuenta_id, x.fecha,
           ISNULL(a.saldo, 0) + SUM(x.neto) OVER (PARTITION BY x.cuenta_id ORDER BY x.fecha) AS saldo
    INTO #cierres
    FROM (
        SELECT t.cuenta_id, f.fecha, SUM(IIF(m.tipo = N'Abono', t.monto, -t.monto)) AS neto
        FROM dw.fact_transaccion t
        JOIN dw.dim_movimiento m ON m.movimiento_key = t.movimiento_key
        JOIN dw.dim_fecha f ON f.fecha_key = t.fecha_key
        WHERE t.fecha_key BETWEEN @inicio_key AND @corte_key
        GROUP BY t.cuenta_id, f.fecha
    ) x
    LEFT JOIN #apertura a ON a.cuenta_id = x.cuenta_id;

    -- Cada saldo pesa según los días que estuvo vigente.
    WITH tramos AS (
        SELECT cuenta_id, @inicio AS fecha, 0 AS orden, saldo FROM #apertura
        UNION ALL
        SELECT cuenta_id, fecha, 1, saldo FROM #cierres
    ), pesos AS (
        SELECT cuenta_id, fecha, saldo,
               DATEDIFF(DAY, fecha, LEAD(fecha, 1, DATEADD(DAY, 1, @corte)) OVER (PARTITION BY cuenta_id ORDER BY fecha, orden)) AS dias,
               ROW_NUMBER() OVER (PARTITION BY cuenta_id ORDER BY fecha DESC, orden DESC) AS desde_el_final
        FROM tramos
    )
    SELECT cuenta_id,
           SUM(saldo * dias) / NULLIF(SUM(dias), 0) AS saldo_promedio,
           MAX(IIF(desde_el_final = 1, saldo, NULL)) AS saldo_cierre
    INTO #saldos
    FROM pesos
    GROUP BY cuenta_id;

    SELECT t.cuenta_id,
           SUM(IIF(m.tipo = N'Abono', t.monto, 0)) AS abonos,
           SUM(IIF(m.tipo = N'Cargo', t.monto, 0)) AS cargos,
           COUNT(*) AS num_movimientos,
           SUM(IIF(m.categoria_codigo = N'UROK', t.monto, 0)) AS intereses_pagados,
           SUM(IIF(m.categoria_codigo = N'SLUZBY', t.monto, 0)) AS comisiones,
           SUM(IIF(m.categoria_codigo = N'SANKC. UROK', t.monto, 0)) AS sanciones
    INTO #flujos
    FROM dw.fact_transaccion t
    JOIN dw.dim_movimiento m ON m.movimiento_key = t.movimiento_key
    WHERE t.fecha_key BETWEEN @inicio_key AND @corte_key
    GROUP BY t.cuenta_id;

    INSERT dw.fact_saldo_mensual (mes_key, cuenta_key, cliente_key, distrito_key, tarjeta_key, saldo_cierre, saldo_promedio,
                                  abonos, cargos, num_movimientos, intereses_pagados, comisiones, sanciones)
    SELECT @mes_key, c.cuenta_key, ISNULL(cl.cliente_key, -1), c.distrito_key, ISNULL(tj.tarjeta_key, -1),
           ISNULL(s.saldo_cierre, 0), ISNULL(s.saldo_promedio, 0),
           ISNULL(g.abonos, 0), ISNULL(g.cargos, 0), ISNULL(g.num_movimientos, 0),
           ISNULL(g.intereses_pagados, 0), ISNULL(g.comisiones, 0), ISNULL(g.sanciones, 0)
    FROM dw.dim_cuenta c
    LEFT JOIN dw.dim_cliente cl ON cl.cliente_id = c.cliente_titular_id AND @corte BETWEEN cl.vigente_desde AND cl.vigente_hasta
    LEFT JOIN #saldos s ON s.cuenta_id = c.cuenta_id
    LEFT JOIN #flujos g ON g.cuenta_id = c.cuenta_id
    OUTER APPLY (
        SELECT TOP (1) t.tarjeta_key FROM dw.dim_tarjeta t
        WHERE t.cuenta_id = c.cuenta_id AND t.fecha_emision <= @corte
        ORDER BY t.fecha_emision
    ) tj
    WHERE c.cuenta_key <> -1
      AND @corte BETWEEN c.vigente_desde AND c.vigente_hasta
      AND c.fecha_apertura <= @corte;

    -- Se cuentan pagos: cada UVER corresponde a una cuota, con diferencias solo de redondeo.
    SELECT t.cuenta_id, COUNT(*) AS cuotas_pagadas
    INTO #pagos
    FROM dw.fact_transaccion t
    JOIN dw.dim_movimiento m ON m.movimiento_key = t.movimiento_key
    WHERE m.categoria_codigo = N'UVER' AND t.fecha_key <= @corte_key
    GROUP BY t.cuenta_id;

    WITH base AS (
        SELECT p.prestamo_key, p.cuenta_id, p.estado_key, p.monto, p.plazo_meses, p.cuota,
               CASE WHEN p.fecha_concesion > @mes_cerrado THEN 0
                    WHEN DATEDIFF(MONTH, p.fecha_concesion, @mes_cerrado) < p.plazo_meses
                        THEN DATEDIFF(MONTH, p.fecha_concesion, @mes_cerrado)
                    ELSE p.plazo_meses END AS cuotas_esperadas,
               ISNULL(g.cuotas_pagadas, 0) AS cuotas_pagadas
        FROM dw.dim_prestamo p
        LEFT JOIN #pagos g ON g.cuenta_id = p.cuenta_id
        WHERE p.fecha_concesion <= @corte
    ), calculo AS (
        SELECT b.*,
               IIF(b.cuotas_esperadas > b.cuotas_pagadas, b.cuotas_esperadas - b.cuotas_pagadas, 0) AS cuotas_atrasadas,
               IIF(b.monto > b.cuotas_pagadas * b.cuota, b.monto - b.cuotas_pagadas * b.cuota, 0) AS capital_pendiente
        FROM base b
    )
    INSERT dw.fact_prestamo_mensual (mes_key, prestamo_key, cuenta_key, cliente_key, distrito_key, estado_key,
                                     cuotas_esperadas, cuotas_pagadas, cuotas_atrasadas, capital_pendiente,
                                     interes_estimado, en_mora, tramo_atraso)
    SELECT @mes_key, k.prestamo_key, c.cuenta_key, ISNULL(cl.cliente_key, -1), c.distrito_key, k.estado_key,
           k.cuotas_esperadas, k.cuotas_pagadas, k.cuotas_atrasadas, k.capital_pendiente,
           ROUND(k.capital_pendiente * @tasa / 12 * @parte_mes, 2),
           IIF(k.cuotas_atrasadas > 1, 1, 0),
           CASE WHEN k.cuotas_atrasadas <= 1 THEN 'Al día'
                WHEN k.cuotas_atrasadas = 2 THEN '31 a 60 días'
                WHEN k.cuotas_atrasadas = 3 THEN '61 a 90 días'
                ELSE 'Más de 90' END
    FROM calculo k
    JOIN dw.dim_cuenta c ON c.cuenta_id = k.cuenta_id AND @corte BETWEEN c.vigente_desde AND c.vigente_hasta
    LEFT JOIN dw.dim_cliente cl ON cl.cliente_id = c.cliente_titular_id AND @corte BETWEEN cl.vigente_desde AND cl.vigente_hasta
    WHERE k.capital_pendiente > 0;
END
GO

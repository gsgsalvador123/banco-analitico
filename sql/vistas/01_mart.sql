-- Los reportes leen solo este esquema.
CREATE OR ALTER VIEW mart.vw_kpi_mensual
AS
WITH saldos AS (
    SELECT mes_key,
           SUM(saldo_cierre) AS depositos,
           SUM(saldo_promedio) AS depositos_promedio,
           COUNT(*) AS cuentas,
           SUM(intereses_pagados) AS intereses_pagados,
           SUM(comisiones) AS comisiones,
           SUM(sanciones) AS sanciones
    FROM dw.fact_saldo_mensual
    GROUP BY mes_key
), prestamos AS (
    SELECT mes_key,
           COUNT(*) AS prestamos_vigentes,
           SUM(capital_pendiente) AS cartera,
           SUM(IIF(en_mora = 1, capital_pendiente, 0)) AS cartera_en_mora,
           SUM(IIF(en_mora = 1, 1, 0)) AS prestamos_en_mora,
           SUM(interes_estimado) AS intereses_estimados
    FROM dw.fact_prestamo_mensual
    GROUP BY mes_key
)
SELECT f.fecha AS mes,
       f.anio_mes,
       s.depositos,
       s.depositos_promedio,
       s.cuentas,
       ISNULL(p.prestamos_vigentes, 0) AS prestamos_vigentes,
       ISNULL(p.prestamos_en_mora, 0) AS prestamos_en_mora,
       ISNULL(p.cartera, 0) AS cartera,
       ISNULL(p.cartera_en_mora, 0) AS cartera_en_mora,
       ISNULL(p.intereses_estimados, 0) AS intereses_estimados,
       s.comisiones,
       s.sanciones,
       s.intereses_pagados,
       ISNULL(p.intereses_estimados, 0) + s.comisiones + s.sanciones - s.intereses_pagados AS margen_estimado
FROM saldos s
JOIN dw.dim_fecha f ON f.fecha_key = s.mes_key
LEFT JOIN prestamos p ON p.mes_key = s.mes_key;
GO

-- Préstamos en mora de la última foto, con su gestión más reciente.
CREATE OR ALTER VIEW mart.vw_bandeja_cobranza
AS
SELECT p.prestamo_id,
       c.cuenta_id,
       cl.cliente_id,
       d.nombre AS distrito,
       d.region,
       p.monto,
       p.cuota,
       h.cuotas_atrasadas,
       h.capital_pendiente,
       h.tramo_atraso,
       g.fecha_gestion AS ultima_gestion,
       g.resultado AS ultimo_resultado,
       g.fecha_compromiso
FROM dw.fact_prestamo_mensual h
JOIN dw.dim_prestamo p ON p.prestamo_key = h.prestamo_key
JOIN dw.dim_cuenta c ON c.cuenta_key = h.cuenta_key
JOIN dw.dim_cliente cl ON cl.cliente_key = h.cliente_key
JOIN dw.dim_distrito d ON d.distrito_key = h.distrito_key
OUTER APPLY (
    SELECT TOP (1) o.fecha_gestion, o.resultado, o.fecha_compromiso
    FROM ops.gestion_cobranza o
    WHERE o.prestamo_id = p.prestamo_id
    ORDER BY o.fecha_gestion DESC
) g
WHERE h.en_mora = 1
  AND h.mes_key = (SELECT MAX(mes_key) FROM dw.fact_prestamo_mensual);
GO

CREATE OR ALTER VIEW mart.vw_calidad_lotes
AS
SELECT l.lote_id,
       l.fecha_negocio,
       l.tipo,
       l.estado,
       l.inicio,
       l.fin,
       l.filas_recibidas,
       l.filas_cargadas,
       l.filas_cuarentena,
       IIF(l.filas_recibidas > 0, l.filas_cuarentena * 1.0 / l.filas_recibidas, 0) AS tasa_cuarentena
FROM ctl.lote l;
GO

CREATE OR ALTER VIEW mart.vw_cuarentena_por_regla
AS
SELECT q.lote_id, l.fecha_negocio, q.regla, r.descripcion, COUNT(*) AS filas
FROM ctl.cuarentena q
JOIN ctl.lote l ON l.lote_id = q.lote_id
JOIN ctl.regla_calidad r ON r.regla = q.regla
GROUP BY q.lote_id, l.fecha_negocio, q.regla, r.descripcion;
GO

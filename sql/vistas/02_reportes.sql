-- Modelo estrella para Power BI y Excel. Un mes está cerrado cuando el último lote llegó a su último día.
CREATE OR ALTER VIEW mart.vw_dim_fecha
AS
SELECT f.fecha_key,
       f.fecha,
       f.anio,
       f.trimestre,
       f.mes,
       f.nombre_mes,
       f.anio_mes,
       f.es_fin_mes,
       EOMONTH(f.fecha) AS fin_mes,
       IIF(EOMONTH(f.fecha) <= k.ultimo_lote, 1, 0) AS mes_cerrado,
       IIF(EOMONTH(f.fecha) <= k.ultimo_lote
           AND EOMONTH(f.fecha) > EOMONTH(k.ultimo_lote, IIF(k.ultimo_lote = EOMONTH(k.ultimo_lote), -13, -14)), 1, 0) AS en_ultimos_13
FROM dw.dim_fecha f
CROSS JOIN (SELECT MAX(l.fecha_negocio) AS ultimo_lote FROM ctl.lote l WHERE l.estado = 'OK') k;
GO

CREATE OR ALTER VIEW mart.vw_dim_distrito
AS
SELECT distrito_key, distrito_id, nombre AS distrito, region, habitantes, poblacion_urbana_pct,
       salario_promedio, desempleo_96
FROM dw.dim_distrito;
GO

CREATE OR ALTER VIEW mart.vw_dim_cuenta
AS
SELECT cuenta_key, cuenta_id, frecuencia, fecha_apertura, es_actual
FROM dw.dim_cuenta;
GO

CREATE OR ALTER VIEW mart.vw_dim_cliente
AS
WITH corte AS (SELECT MAX(fecha_negocio) AS fecha FROM ctl.lote WHERE estado = 'OK')
SELECT c.cliente_key,
       c.cliente_id,
       c.sexo,
       c.es_actual,
       CASE WHEN c.fecha_nacimiento IS NULL THEN 'Desconocido'
            WHEN DATEDIFF(YEAR, c.fecha_nacimiento, k.fecha) < 25 THEN 'Menos de 25'
            WHEN DATEDIFF(YEAR, c.fecha_nacimiento, k.fecha) < 40 THEN '25 a 39'
            WHEN DATEDIFF(YEAR, c.fecha_nacimiento, k.fecha) < 60 THEN '40 a 59'
            ELSE '60 o más' END AS rango_edad
FROM dw.dim_cliente c
CROSS JOIN corte k;
GO

CREATE OR ALTER VIEW mart.vw_dim_tarjeta
AS
SELECT tarjeta_key, tarjeta_id, tipo AS tipo_tarjeta
FROM dw.dim_tarjeta;
GO

CREATE OR ALTER VIEW mart.vw_dim_prestamo
AS
SELECT p.prestamo_key,
       p.prestamo_id,
       p.cuenta_id,
       e.descripcion AS estado,
       e.es_problematico,
       p.fecha_concesion,
       p.monto,
       p.plazo_meses,
       CONCAT(p.plazo_meses, ' meses') AS plazo,
       p.cuota
FROM dw.dim_prestamo p
JOIN dw.dim_estado_prestamo e ON e.estado_key = p.estado_key;
GO

CREATE OR ALTER VIEW mart.vw_fact_saldo_mensual
AS
SELECT mes_key, cuenta_key, cliente_key, distrito_key, tarjeta_key, saldo_cierre, saldo_promedio,
       abonos, cargos, num_movimientos, intereses_pagados, comisiones, sanciones
FROM dw.fact_saldo_mensual;
GO

CREATE OR ALTER VIEW mart.vw_fact_prestamo_mensual
AS
SELECT mes_key, prestamo_key, cuenta_key, cliente_key, distrito_key, cuotas_esperadas, cuotas_pagadas,
       cuotas_atrasadas, capital_pendiente, interes_estimado, en_mora, tramo_atraso
FROM dw.fact_prestamo_mensual;
GO

-- No incluye al analista: el reporte puede publicarse y su nombre no hace falta para leerlo.
CREATE OR ALTER VIEW mart.vw_fact_gestion_cobranza
AS
SELECT gestion_id, fecha_key, prestamo_key, cuenta_key, cliente_key, distrito_key, resultado,
       monto_prometido, fecha_compromiso,
       CASE WHEN resultado <> N'Promesa de pago' THEN 'Sin compromiso'
            WHEN fecha_compromiso < CONVERT(DATE, SYSUTCDATETIME()) THEN 'Vencido'
            ELSE 'Por vencer' END AS estado_compromiso
FROM dw.fact_gestion_cobranza;
GO

-- Cada componente del margen estimado, con el signo con el que suma.
CREATE OR ALTER VIEW mart.vw_margen_componente
AS
SELECT mes_key, distrito_key, N'Préstamos' AS producto, N'Intereses de préstamos (estimado)' AS componente,
       1 AS orden, SUM(interes_estimado) AS monto
FROM dw.fact_prestamo_mensual
GROUP BY mes_key, distrito_key
UNION ALL
SELECT mes_key, distrito_key, N'Cuentas', N'Comisiones', 2, SUM(comisiones)
FROM dw.fact_saldo_mensual
GROUP BY mes_key, distrito_key
UNION ALL
SELECT mes_key, distrito_key, N'Cuentas', N'Sanciones', 3, SUM(sanciones)
FROM dw.fact_saldo_mensual
GROUP BY mes_key, distrito_key
UNION ALL
SELECT mes_key, distrito_key, N'Cuentas', N'Intereses pagados', 4, -SUM(intereses_pagados)
FROM dw.fact_saldo_mensual
GROUP BY mes_key, distrito_key;
GO

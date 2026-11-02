-- Lleva al almacén las gestiones nuevas de la app. Se puede repetir: solo inserta las que faltan.
CREATE OR ALTER PROCEDURE dw.usp_cargar_gestiones
AS
BEGIN
    SET NOCOUNT ON;

    INSERT dw.fact_gestion_cobranza (gestion_id, fecha_key, prestamo_key, cuenta_key, cliente_key, distrito_key,
                                     analista, resultado, monto_prometido, fecha_compromiso)
    SELECT g.gestion_id, f.fecha_key, p.prestamo_key, c.cuenta_key, ISNULL(cl.cliente_key, -1), c.distrito_key,
           g.analista, g.resultado, g.monto_prometido, g.fecha_compromiso
    FROM ops.gestion_cobranza g
    JOIN dw.dim_fecha f ON f.fecha = CONVERT(DATE, g.fecha_gestion)
    JOIN dw.dim_prestamo p ON p.prestamo_id = g.prestamo_id
    JOIN dw.dim_cuenta c ON c.cuenta_id = p.cuenta_id AND c.es_actual = 1
    LEFT JOIN dw.dim_cliente cl ON cl.cliente_id = c.cliente_titular_id AND cl.es_actual = 1
    WHERE NOT EXISTS (SELECT 1 FROM dw.fact_gestion_cobranza x WHERE x.gestion_id = g.gestion_id);
END
GO

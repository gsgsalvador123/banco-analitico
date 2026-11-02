"""Pruebas de punta a punta contra una base local exclusiva para pruebas."""

from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from banco import db, etl, simulador
from banco.config import conexion_sql

pytestmark = pytest.mark.sql

BASE_PRUEBA = "BancoAnaliticoPruebas"
DIA_1, DIA_2, DIA_3 = date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)


@pytest.fixture(scope="module")
def cx(tmp_path_factory):
    config = replace(conexion_sql(), base=BASE_PRUEBA)
    with db.conectar(config, "master") as maestro:
        maestro.execute(
            f"IF DB_ID('{BASE_PRUEBA}') IS NOT NULL BEGIN "
            f"ALTER DATABASE [{BASE_PRUEBA}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
            f"DROP DATABASE [{BASE_PRUEBA}]; END"
        )
    db.crear_base(config)
    conexion = db.conectar(config)
    db.aplicar_scripts(conexion)
    destino = tmp_path_factory.mktemp("landing")
    etl.cargar_historico(conexion, destino)
    yield conexion, destino
    conexion.close()


def _valor(conexion, consulta, *parametros):
    return conexion.execute(consulta, *parametros).fetchval()


def test_historico_carga_todo(cx):
    conexion, _ = cx
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.fact_transaccion") == 905_083
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.dim_cuenta WHERE cuenta_key <> -1") == 4_500
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.dim_cliente WHERE cliente_key <> -1") == 5_369
    assert _valor(conexion, "SELECT COUNT(*) FROM ctl.cuarentena") == 0
    tarjetas = "SELECT COUNT(*) FROM dw.dim_tarjeta WHERE tarjeta_key <> -1"
    assert _valor(conexion, tarjetas) > 0


def test_scripts_se_pueden_repetir(cx):
    conexion, _ = cx
    db.aplicar_scripts(conexion)
    assert _valor(conexion, "SELECT COUNT(*) FROM ref.codigo") == 20


def test_historico_repetido_no_duplica(cx):
    conexion, destino = cx
    resultado = etl.cargar_historico(conexion, destino)
    assert resultado["omitido"] is True
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.fact_transaccion") == 905_083


def test_dia_concilia_y_aparta_errores(cx):
    conexion, destino = cx
    resultado = etl.cargar_dia(conexion, DIA_1, destino)
    assert resultado["recibidas"] == resultado["cargadas"] + resultado["cuarentena"]
    assert resultado["cuarentena"] > 0


def test_dia_repetido_no_duplica(cx):
    conexion, destino = cx
    antes = _valor(conexion, "SELECT COUNT(*) FROM dw.fact_transaccion")
    resultado = etl.cargar_dia(conexion, DIA_1, destino)
    assert resultado["omitido"] is True
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.fact_transaccion") == antes


def test_scd2_conserva_una_sola_version_actual(cx):
    conexion, destino = cx
    etl.cargar_dia(conexion, DIA_2, destino)
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.dim_cliente WHERE es_actual = 0") > 0
    repetidos = _valor(
        conexion,
        "SELECT COUNT(*) FROM (SELECT cliente_id FROM dw.dim_cliente WHERE es_actual = 1 "
        "GROUP BY cliente_id HAVING COUNT(*) > 1) x",
    )
    assert repetidos == 0


def test_cada_hecho_apunta_a_una_version_vigente(cx):
    conexion, _ = cx
    fuera = _valor(
        conexion,
        "SELECT COUNT(*) FROM dw.fact_transaccion t "
        "JOIN dw.dim_fecha f ON f.fecha_key = t.fecha_key "
        "JOIN dw.dim_cuenta c ON c.cuenta_key = t.cuenta_key "
        "WHERE f.fecha NOT BETWEEN c.vigente_desde AND c.vigente_hasta",
    )
    assert fuera == 0


def test_fila_danada_se_recupera_al_dia_siguiente(cx):
    conexion, _ = cx
    pendientes = _valor(
        conexion,
        "SELECT COUNT(*) FROM ctl.cuarentena q JOIN ctl.lote l ON l.lote_id = q.lote_id "
        "WHERE l.fecha_negocio = ? AND q.regla IN "
        "('TRX_MONTO_NULO', 'TRX_FECHA_INVALIDA', 'TRX_CUENTA_DESCONOCIDA') "
        "AND NOT EXISTS (SELECT 1 FROM dw.fact_transaccion t "
        "WHERE t.trans_id = TRY_CONVERT(BIGINT, q.clave_origen))",
        DIA_1,
    )
    assert pendientes == 0


def test_rechazo_masivo_detiene_el_lote(cx):
    conexion, destino = cx
    carpeta = simulador.generar_dia(DIA_3, destino)
    archivo = carpeta / "trans.csv"
    tabla = pd.read_csv(archivo, sep=";", dtype=str, keep_default_na=False)
    tabla["cuenta_id"] = simulador.CUENTA_INEXISTENTE
    tabla.to_csv(archivo, sep=";", index=False)
    antes = _valor(conexion, "SELECT COUNT(*) FROM dw.fact_transaccion")
    with pytest.raises(etl.ErrorConciliacion):
        etl._ejecutar(conexion, carpeta, etl.ARCHIVOS_DIARIO, "DIARIO")
    assert _valor(conexion, "SELECT COUNT(*) FROM dw.fact_transaccion") == antes
    assert _valor(conexion, "SELECT estado FROM ctl.lote WHERE fecha_negocio = ?", DIA_3) == "ERROR"


def test_fila_mala_queda_con_motivo(cx):
    conexion, _ = cx
    assert _valor(conexion, "SELECT COUNT(*) FROM ctl.cuarentena WHERE fila IS NULL") == 0
    assert _valor(conexion, "SELECT COUNT(DISTINCT regla) FROM ctl.cuarentena") >= 2


def test_saldo_de_foto_coincide_con_movimientos(cx):
    """Donde el último día tuvo un solo movimiento, su saldo es el cierre real."""
    conexion, _ = cx
    diferencias = _valor(
        conexion,
        """
        WITH dias AS (
            SELECT cuenta_id, fecha_key, COUNT(*) AS movimientos, MAX(saldo_posterior) AS saldo,
                   ROW_NUMBER() OVER (PARTITION BY cuenta_id ORDER BY fecha_key DESC) AS orden
            FROM dw.fact_transaccion WHERE fecha_key <= 20260531
            GROUP BY cuenta_id, fecha_key
        )
        SELECT COUNT(*)
        FROM dw.fact_saldo_mensual s
        JOIN dw.dim_cuenta c ON c.cuenta_key = s.cuenta_key
        JOIN dias d ON d.cuenta_id = c.cuenta_id AND d.orden = 1 AND d.movimientos = 1
        WHERE s.mes_key = 20260531 AND ABS(s.saldo_cierre - d.saldo) > 3
        """,
    )
    assert diferencias == 0


def test_mes_sin_cerrar_no_infla_la_mora(cx):
    conexion, _ = cx
    consulta = "SELECT prestamos_en_mora FROM mart.vw_kpi_mensual WHERE anio_mes = ?"
    assert _valor(conexion, consulta, "2026-07") <= _valor(conexion, consulta, "2026-06")


def test_gestion_llega_al_almacen_sin_duplicarse(cx):
    conexion, _ = cx
    prestamo = _valor(conexion, "SELECT TOP 1 prestamo_id FROM mart.vw_bandeja_cobranza")
    conexion.execute(
        "INSERT ops.gestion_cobranza (prestamo_id, analista, resultado, monto_prometido, fecha_compromiso) "
        "VALUES (?, 'Prueba', 'Promesa de pago', 1000, '20200101')",
        prestamo,
    )
    conexion.execute("EXEC dw.usp_cargar_gestiones")
    conexion.execute("EXEC dw.usp_cargar_gestiones")
    assert _valor(conexion, "SELECT COUNT(*) FROM mart.vw_fact_gestion_cobranza") == 1
    assert _valor(conexion, "SELECT estado_compromiso FROM mart.vw_fact_gestion_cobranza") == "Vencido"


def test_margen_por_componentes_coincide_con_kpi(cx):
    conexion, _ = cx
    diferencia = _valor(
        conexion,
        "SELECT ABS(SUM(c.monto) - MAX(k.margen_estimado)) FROM mart.vw_margen_componente c "
        "JOIN mart.vw_dim_fecha f ON f.fecha_key = c.mes_key "
        "JOIN mart.vw_kpi_mensual k ON k.mes = f.fecha WHERE k.anio_mes = '2026-06'",
    )
    assert diferencia < 0.01


def test_solo_se_cierran_meses_completos(cx):
    conexion, _ = cx
    consulta = "SELECT mes_cerrado FROM mart.vw_kpi_mensual WHERE anio_mes = ?"
    assert _valor(conexion, consulta, "2026-06") == 1
    assert _valor(conexion, consulta, "2026-07") == 0


def test_kpi_mensual_no_tiene_huecos(cx):
    conexion, _ = cx
    meses = _valor(conexion, "SELECT COUNT(*) FROM mart.vw_kpi_mensual")
    assert meses == 67
    assert _valor(conexion, "SELECT COUNT(*) FROM mart.vw_bandeja_cobranza") > 0

from datetime import date

import pandas as pd
import pytest

from banco import berka, simulador
from banco.config import FECHA_CORTE


def test_desplazamiento_conserva_calendario():
    assert berka.fecha_negocio("980701") == date(2026, 7, 1)
    assert berka.fecha_negocio("960229") == date(2024, 2, 29)
    assert berka.fecha_berka("980701").weekday() == date(2026, 7, 1).weekday()


def test_decodifica_sexo_y_nacimiento():
    assert berka.decodificar_nacimiento("706213") == (date(1970, 12, 13), "M")
    assert berka.decodificar_nacimiento("450204") == (date(1945, 2, 4), "H")


def test_dias_habiles_saltan_el_fin_de_semana():
    viernes, lunes = date(2026, 7, 3), date(2026, 7, 6)
    assert simulador.dia_habil_siguiente(viernes) == lunes
    assert simulador.dia_habil_anterior(lunes) == viernes


def test_rechaza_fechas_fuera_de_la_simulacion():
    with pytest.raises(ValueError):
        simulador.generar_dia(date(2026, 7, 4))
    with pytest.raises(ValueError):
        simulador.generar_dia(FECHA_CORTE)


def test_generar_dia_es_reproducible(tmp_path):
    fecha = date(2026, 7, 7)
    uno = simulador.generar_dia(fecha, tmp_path / "a") / "trans.csv"
    dos = simulador.generar_dia(fecha, tmp_path / "b") / "trans.csv"
    assert uno.read_bytes() == dos.read_bytes()


def test_ningun_movimiento_se_pierde_ni_se_entrega_dos_veces(tmp_path):
    """Sin contar errores inyectados, cada movimiento llega en un solo día."""
    trans = simulador._preparar_trans(berka.leer("trans"))
    fechas = pd.bdate_range("2026-07-01", "2026-07-31")
    entregados = pd.concat(
        [simulador._movimientos_del_dia(trans, f.date()) for f in fechas], ignore_index=True
    )
    assert entregados["trans_id"].is_unique
    atrasados_de_salida = trans[
        (trans["fecha"] > "20260730")
        & (trans["fecha"] <= "20260731")
        & trans["trans_id"].map(simulador.se_atrasa)
    ]
    esperados = trans[(trans["fecha"] > "20260630") & (trans["fecha"] <= "20260731")]
    assert len(entregados) == len(esperados) - len(atrasados_de_salida)

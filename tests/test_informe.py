"""El informe mensual se genera sin Excel: basta comprobar lo que queda dentro del archivo."""

import datetime as dt
import decimal
import re
import zipfile

import pytest

from banco import informe


def _datos(filas_morosos):
    """Datos con la misma forma que las consultas, tomando las columnas de la plantilla."""
    with zipfile.ZipFile(informe.PLANTILLA) as libro:
        tablas = {}
        for nombre in libro.namelist():
            if re.fullmatch(r"xl/tables/table\d+\.xml", nombre):
                xml = libro.read(nombre).decode("utf-8")
                tabla = re.search(r'<table [^>]*?\bname="([^"]+)"', xml).group(1)
                tablas[tabla] = re.findall(r'<tableColumn [^>]*?\bname="([^"]+)"', xml)
    datos = {t: (c, [[1] * len(c)]) for t, c in tablas.items()}
    columnas = tablas["tMorosos"]
    filas = []
    for n in range(filas_morosos):
        fila = [None] * len(columnas)
        fila[0] = 1000 + n
        fila[1] = "Hl.m. Praha & <Sur>"
        fila[6] = decimal.Decimal("1234.50")
        fila[8] = dt.date(2026, 7, 1)
        filas.append(fila)
    datos["tMorosos"] = (columnas, filas)
    return datos


def _leer(archivo, parte_tabla):
    with zipfile.ZipFile(archivo) as libro:
        for nombre in libro.namelist():
            if re.fullmatch(r"xl/tables/table\d+\.xml", nombre):
                xml = libro.read(nombre).decode("utf-8")
                if f'name="{parte_tabla}"' in xml:
                    return (
                        xml,
                        libro.read("xl/workbook.xml").decode("utf-8"),
                        libro.namelist(),
                        libro,
                    )
    raise AssertionError(parte_tabla)


@pytest.mark.parametrize("filas", [3, 200])
def test_la_tabla_crece_o_se_encoge_con_los_datos(tmp_path, filas):
    salida = tmp_path / "informe.xlsx"
    informe.rellenar(informe.PLANTILLA, salida, _datos(filas))

    tabla, libro, _, _ = _leer(salida, "tMorosos")
    # La tabla empieza en la fila 9 de la hoja Morosos, debajo del selector.
    assert re.search(r'\bref="A9:K(\d+)"', tabla).group(1) == str(9 + filas)
    assert "fullCalcOnLoad" in libro


def test_conserva_dinamicas_y_segmentaciones(tmp_path):
    salida = tmp_path / "informe.xlsx"
    informe.rellenar(informe.PLANTILLA, salida, _datos(3))

    with zipfile.ZipFile(informe.PLANTILLA) as original, zipfile.ZipFile(salida) as nuevo:
        assert set(original.namelist()) == set(nuevo.namelist())
        caches = [n for n in nuevo.namelist() if "pivotCacheDefinition" in n and n.endswith(".xml")]
        assert caches
        for nombre in caches:
            assert 'refreshOnLoad="1"' in nuevo.read(nombre).decode("utf-8")
        assert any("slicers/" in n for n in nuevo.namelist())


def test_escapa_el_texto_y_conserva_el_encabezado(tmp_path):
    salida = tmp_path / "informe.xlsx"
    informe.rellenar(informe.PLANTILLA, salida, _datos(3))

    with zipfile.ZipFile(salida) as libro:
        hojas = [
            libro.read(n).decode("utf-8")
            for n in libro.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)
        ]
    morosos = next(h for h in hojas if "Hl.m. Praha" in h)
    assert "Hl.m. Praha &amp; &lt;Sur&gt;" in morosos
    assert '<row r="9"' in morosos
    # 2026-07-01 como número de serie de Excel.
    assert "<v>46204</v>" in morosos


def test_rechaza_una_consulta_que_no_coincide_con_la_plantilla(tmp_path):
    datos = _datos(3)
    columnas, filas = datos["tKpi"]
    datos["tKpi"] = (["otra", *columnas[1:]], filas)
    with pytest.raises(ValueError, match="tKpi"):
        informe.rellenar(informe.PLANTILLA, tmp_path / "informe.xlsx", datos)

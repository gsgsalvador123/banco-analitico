"""Genera el informe mensual en Excel: pone los datos de mart en una copia de la plantilla.

El runner de GitHub no tiene Excel, así que se editan las hojas de datos dentro del archivo.
Las tablas dinámicas, sus gráficos y segmentaciones no se tocan y se actualizan al abrirlo.

Uso:
    python -m banco.informe generar [carpeta]   escribe Informe_AAAA-MM.xlsx
    python -m banco.informe semilla [carpeta]   escribe los CSV con los que se crea la plantilla
"""

import csv
import datetime as dt
import decimal
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from banco import db

PLANTILLA = Path(__file__).resolve().parents[2] / "excel" / "plantilla_informe.xlsx"

REGIONES = {
    "Prague": "Praga",
    "central Bohemia": "Bohemia Central",
    "south Bohemia": "Bohemia del Sur",
    "west Bohemia": "Bohemia del Oeste",
    "north Bohemia": "Bohemia del Norte",
    "east Bohemia": "Bohemia del Este",
    "south Moravia": "Moravia del Sur",
    "north Moravia": "Moravia del Norte",
}

ULTIMO_DIA_CERRADO = "(SELECT MAX(fecha_key) FROM mart.vw_dim_fecha WHERE mes_cerrado = 1)"

# Una tabla de Excel por consulta. Los nombres de columna son los encabezados de la plantilla.
CONSULTAS = {
    "tKpi": """
        SELECT anio_mes, depositos, cartera, cartera_en_mora, prestamos_en_mora, prestamos_vigentes,
               cuentas, margen_estimado
        FROM (SELECT TOP 13 * FROM mart.vw_kpi_mensual WHERE mes_cerrado = 1 ORDER BY mes DESC) k
        ORDER BY mes""",
    "tMargen": """
        SELECT f.anio_mes, d.region, m.producto, m.componente, SUM(m.monto) AS monto
        FROM mart.vw_margen_componente m
        JOIN mart.vw_dim_fecha f ON f.fecha_key = m.mes_key
        JOIN mart.vw_dim_distrito d ON d.distrito_key = m.distrito_key
        WHERE f.en_ultimos_13 = 1
        GROUP BY f.anio_mes, d.region, m.producto, m.componente
        ORDER BY f.anio_mes, d.region, m.producto, m.componente""",
    "tCartera": f"""
        SELECT p.prestamo_id, d.distrito, d.region, p.plazo, c.tramo_atraso,
               IIF(c.en_mora = 1, 'En mora', N'Al día') AS situacion, c.capital_pendiente, c.cuotas_atrasadas
        FROM mart.vw_fact_prestamo_mensual c
        JOIN mart.vw_dim_prestamo p ON p.prestamo_key = c.prestamo_key
        JOIN mart.vw_dim_distrito d ON d.distrito_key = c.distrito_key
        WHERE c.mes_key = {ULTIMO_DIA_CERRADO}
        ORDER BY p.prestamo_id""",
    "tMorosos": """
        SELECT prestamo_id AS [Préstamo], distrito AS Distrito, region AS [Región], monto AS Monto,
               cuota AS Cuota, cuotas_atrasadas AS [Cuotas atrasadas],
               capital_pendiente AS [Capital pendiente], tramo_atraso AS [Tiempo de atraso],
               ultima_gestion AS [Última gestión], ultimo_resultado AS [Último resultado],
               fecha_compromiso AS Compromiso
        FROM mart.vw_bandeja_cobranza
        ORDER BY [Capital pendiente] DESC""",
}


def extraer(conexion):
    """Devuelve {tabla: (columnas, filas)} con las regiones en español."""
    datos = {}
    for tabla, sql in CONSULTAS.items():
        cursor = conexion.cursor()
        cursor.execute(sql)
        columnas = [d[0] for d in cursor.description]
        filas = [list(fila) for fila in cursor.fetchall()]
        cursor.close()
        for rotulo in ("region", "Región"):
            if rotulo in columnas:
                i = columnas.index(rotulo)
                for fila in filas:
                    fila[i] = REGIONES.get(fila[i], fila[i])
        datos[tabla] = (columnas, filas)
    return datos


def _letra(numero):
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _numero_columna(letras):
    numero = 0
    for letra in letras:
        numero = numero * 26 + ord(letra) - 64
    return numero


def _celda(referencia, valor, estilo):
    atributo = f' s="{estilo}"' if estilo else ""
    if valor is None:
        return f'<c r="{referencia}"{atributo}/>'
    if isinstance(valor, dt.datetime):
        valor = valor.date()
    if isinstance(valor, dt.date):
        valor = (valor - dt.date(1899, 12, 30)).days
    if isinstance(valor, bool):
        valor = int(valor)
    if isinstance(valor, int | float | decimal.Decimal):
        return f'<c r="{referencia}"{atributo}><v>{valor}</v></c>'
    texto = escape(str(valor))
    return f'<c r="{referencia}"{atributo} t="inlineStr"><is><t>{texto}</t></is></c>'


def _reemplazar_filas(hoja, encabezado, primera_columna, columnas, filas):
    """Cambia las filas de datos de la tabla y conserva los formatos de la primera fila."""
    contenido = re.search(r"<sheetData>(.*)</sheetData>", hoja, flags=re.DOTALL).group(1)
    previas, estilos = [], {}
    # Una fila puede cerrarse sola o traer celdas que se cierran solas: hay que distinguirlas.
    for fila in re.finditer(
        r'<row r="(\d+)"[^>]*?(?:/>|[^/]>.*?</row>)', contenido, flags=re.DOTALL
    ):
        numero = int(fila.group(1))
        if numero <= encabezado:
            previas.append(fila.group(0))
        elif numero == encabezado + 1:
            for letras, estilo in re.findall(r'<c r="([A-Z]+)\d+"(?: s="(\d+)")?', fila.group(0)):
                estilos[_numero_columna(letras)] = estilo
    nuevas = []
    for desplazamiento, valores in enumerate(filas, start=1):
        numero = encabezado + desplazamiento
        celdas = "".join(
            _celda(
                f"{_letra(primera_columna + i)}{numero}",
                valor,
                estilos.get(primera_columna + i, ""),
            )
            for i, valor in enumerate(valores)
        )
        nuevas.append(f'<row r="{numero}">{celdas}</row>')
    ultima_fila = encabezado + len(filas)
    ultima_columna = _letra(primera_columna + len(columnas) - 1)
    hoja = re.sub(
        r"<sheetData>.*</sheetData>",
        lambda _: "<sheetData>" + "".join(previas + nuevas) + "</sheetData>",
        hoja,
        count=1,
        flags=re.DOTALL,
    )
    return re.sub(
        r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:{ultima_columna}{ultima_fila}"/>', hoja
    )


def _ruta_relativa(base, destino):
    if destino.startswith("/"):
        return destino.lstrip("/")
    partes = Path(base).parent.joinpath(destino).as_posix().split("/")
    salida = []
    for parte in partes:
        if parte == "..":
            salida.pop()
        else:
            salida.append(parte)
    return "/".join(salida)


def rellenar(plantilla, salida, datos):
    """Copia la plantilla a salida con los datos nuevos en cada tabla."""
    with zipfile.ZipFile(plantilla) as origen:
        archivos = {nombre: origen.read(nombre) for nombre in origen.namelist()}

    hojas_por_tabla = {}
    for nombre, contenido in archivos.items():
        coincide = re.fullmatch(r"xl/worksheets/_rels/(sheet\d+\.xml)\.rels", nombre)
        if not coincide:
            continue
        hoja = f"xl/worksheets/{coincide.group(1)}"
        relaciones = contenido.decode("utf-8")
        for destino in re.findall(r'Target="([^"]*tables/table\d+\.xml)"', relaciones):
            hojas_por_tabla[_ruta_relativa(hoja, destino)] = hoja

    pendientes = set(datos)
    for ruta_tabla, ruta_hoja in hojas_por_tabla.items():
        tabla = archivos[ruta_tabla].decode("utf-8")
        nombre = re.search(r'<table [^>]*?\bname="([^"]+)"', tabla).group(1)
        if nombre not in datos:
            continue
        pendientes.discard(nombre)
        columnas, filas = datos[nombre]
        if not filas:
            raise ValueError(f"La consulta de {nombre} no devolvió filas")
        esperadas = re.findall(r'<tableColumn [^>]*?\bname="([^"]+)"', tabla)
        if esperadas != columnas:
            raise ValueError(
                f"{nombre}: la plantilla espera {esperadas} y la consulta da {columnas}"
            )
        inicio_col, encabezado, fin_col = re.fullmatch(
            r"([A-Z]+)(\d+):([A-Z]+)\d+", re.search(r'\bref="([^"]+)"', tabla).group(1)
        ).groups()
        encabezado = int(encabezado)
        rango = f"{inicio_col}{encabezado}:{fin_col}{encabezado + len(filas)}"
        archivos[ruta_tabla] = re.sub(r'\bref="[^"]+"', f'ref="{rango}"', tabla).encode("utf-8")
        archivos[ruta_hoja] = _reemplazar_filas(
            archivos[ruta_hoja].decode("utf-8"),
            encabezado,
            _numero_columna(inicio_col),
            columnas,
            filas,
        ).encode("utf-8")
    if pendientes:
        raise ValueError(f"La plantilla no tiene las tablas {sorted(pendientes)}")

    # Las fórmulas guardan valores de la plantilla: se recalculan al abrir el archivo.
    libro = archivos["xl/workbook.xml"].decode("utf-8")
    if "fullCalcOnLoad" not in libro:
        libro = re.sub(r"<calcPr\b", '<calcPr fullCalcOnLoad="1"', libro, count=1)
    archivos["xl/workbook.xml"] = libro.encode("utf-8")

    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as destino:
        for nombre, contenido in archivos.items():
            destino.writestr(nombre, contenido)


def _publicar_resultado(archivo, mes):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as salida:
            salida.write(f"archivo={archivo}\nmes={mes}\n")


def generar(carpeta):
    conexion = db.conectar()
    try:
        datos = extraer(conexion)
    finally:
        conexion.close()
    columnas, filas = datos["tKpi"]
    mes = filas[-1][columnas.index("anio_mes")]
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"Informe_{mes}.xlsx"
    rellenar(PLANTILLA, archivo, datos)
    _publicar_resultado(archivo, mes)
    print(f"Informe de {mes}: {archivo}")


def semilla(carpeta):
    conexion = db.conectar()
    try:
        datos = extraer(conexion)
    finally:
        conexion.close()
    carpeta.mkdir(parents=True, exist_ok=True)
    for tabla, (columnas, filas) in datos.items():
        with open(carpeta / f"{tabla}.csv", "w", newline="", encoding="utf-8") as salida:
            escritor = csv.writer(salida)
            escritor.writerow(columnas)
            escritor.writerows(filas)
    print("Semilla escrita en", carpeta)


def main():
    accion = sys.argv[1] if len(sys.argv) > 1 else "generar"
    carpeta = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("salida")
    {"generar": generar, "semilla": semilla}[accion](carpeta)


if __name__ == "__main__":
    main()

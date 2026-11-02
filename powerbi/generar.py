"""Escribe el proyecto de Power BI: modelo en TMDL, tema y páginas en PBIR.

Uso: python powerbi/generar.py
Power BI Desktop abre el resultado desde powerbi/BancoAnalitico.pbip.
"""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
NOMBRE = "BancoAnalitico"
SERVIDOR = "ba-sql-gdhi0s.database.windows.net"
BASE = "BancoAnalitico"

ESQUEMAS = "https://developer.microsoft.com/json-schemas/fabric"
ESQUEMA_REPORTE = f"{ESQUEMAS}/item/report/definition"

# Marino solo para texto y cabecera. Azul y turquesa son las series; rojo se reserva para la mora.
MARINO, GRIS, FONDO, BORDE = "#12284B", "#5B6776", "#F3F5F8", "#E2E6EC"
AZUL, TURQUESA, ROJO = "#2F6FD0", "#00A5A0", "#D6453D"

ENTERO = "#,0"
CZK = '#,0" CZK"'
PORCENTAJE = "0.0%"
MILLON, MIL = 1000000, 1000
DECIMALES = {MILLON: 1, MIL: 0}


# ---------------------------------------------------------------- modelo


def k(nombre):
    return (nombre, "int64", True, "0")


TABLAS = {
    "Fecha": (
        "vw_dim_fecha",
        [
            k("fecha_key"),
            ("fecha", "dateTime", False, "dd/mm/yyyy"),
            ("anio", "int64", False, "0"),
            ("trimestre", "int64", False, "0"),
            ("mes", "int64", False, "0"),
            ("nombre_mes", "string", False, None),
            ("anio_mes", "string", True, None),
            ("es_fin_mes", "boolean", True, None),
            ("fin_mes", "dateTime", True, "dd/mm/yyyy"),
            ("mes_cerrado", "int64", True, "0"),
            ("en_ultimos_13", "int64", True, "0"),
        ],
    ),
    "Distrito": (
        "vw_dim_distrito",
        [
            k("distrito_key"),
            ("distrito_id", "int64", True, "0"),
            ("distrito", "string", False, None),
            ("region", "string", True, None),
            ("habitantes", "int64", False, ENTERO),
            ("poblacion_urbana_pct", "double", False, "0.0"),
            ("salario_promedio", "int64", False, ENTERO),
            ("desempleo_96", "double", False, "0.00"),
        ],
    ),
    "Cuenta": (
        "vw_dim_cuenta",
        [
            k("cuenta_key"),
            ("cuenta_id", "int64", False, "0"),
            ("frecuencia", "string", False, None),
            ("fecha_apertura", "dateTime", False, "dd/mm/yyyy"),
            ("es_actual", "boolean", True, None),
        ],
    ),
    "Cliente": (
        "vw_dim_cliente",
        [
            k("cliente_key"),
            ("cliente_id", "int64", False, "0"),
            ("sexo", "string", False, None),
            ("es_actual", "boolean", True, None),
            ("rango_edad", "string", True, None),
        ],
    ),
    "Tarjeta": (
        "vw_dim_tarjeta",
        [
            k("tarjeta_key"),
            ("tarjeta_id", "int64", True, "0"),
            ("tipo_tarjeta", "string", True, None),
        ],
    ),
    "Prestamo": (
        "vw_dim_prestamo",
        [
            k("prestamo_key"),
            ("prestamo_id", "int64", False, "0"),
            ("cuenta_id", "int64", True, "0"),
            ("estado", "string", False, None),
            ("es_problematico", "boolean", True, None),
            ("fecha_concesion", "dateTime", False, "dd/mm/yyyy"),
            ("monto", "decimal", False, ENTERO),
            ("plazo_meses", "int64", True, "0"),
            ("plazo", "string", False, None),
            ("cuota", "decimal", False, ENTERO),
        ],
    ),
    "Saldos": (
        "vw_fact_saldo_mensual",
        [
            k("mes_key"),
            k("cuenta_key"),
            k("cliente_key"),
            k("distrito_key"),
            k("tarjeta_key"),
            ("saldo_cierre", "decimal", True, ENTERO),
            ("saldo_promedio", "decimal", True, ENTERO),
            ("abonos", "decimal", True, ENTERO),
            ("cargos", "decimal", True, ENTERO),
            ("num_movimientos", "int64", True, ENTERO),
            ("intereses_pagados", "decimal", True, ENTERO),
            ("comisiones", "decimal", True, ENTERO),
            ("sanciones", "decimal", True, ENTERO),
        ],
    ),
    "Cartera": (
        "vw_fact_prestamo_mensual",
        [
            k("mes_key"),
            k("prestamo_key"),
            k("cuenta_key"),
            k("cliente_key"),
            k("distrito_key"),
            ("cuotas_esperadas", "int64", True, "0"),
            ("cuotas_pagadas", "int64", True, "0"),
            ("cuotas_atrasadas", "int64", True, "0"),
            ("capital_pendiente", "decimal", True, ENTERO),
            ("interes_estimado", "decimal", True, ENTERO),
            ("en_mora", "boolean", True, None),
            ("tramo_atraso", "string", False, None),
        ],
    ),
    "Gestiones": (
        "vw_fact_gestion_cobranza",
        [
            ("gestion_id", "int64", True, "0"),
            k("fecha_key"),
            k("prestamo_key"),
            k("cuenta_key"),
            k("cliente_key"),
            k("distrito_key"),
            ("resultado", "string", False, None),
            ("monto_prometido", "decimal", True, ENTERO),
            ("fecha_compromiso", "dateTime", False, "dd/mm/yyyy"),
            ("estado_compromiso", "string", False, None),
        ],
    ),
    "Margen": (
        "vw_margen_componente",
        [
            k("mes_key"),
            k("distrito_key"),
            ("producto", "string", False, None),
            ("componente", "string", False, None),
            ("orden", "int64", True, "0"),
            ("monto", "decimal", True, ENTERO),
        ],
    ),
    "Lotes": (
        "vw_calidad_lotes",
        [
            ("lote_id", "int64", False, "0"),
            ("fecha_negocio", "dateTime", True, "dd/mm/yyyy"),
            ("tipo", "string", False, None),
            ("estado", "string", False, None),
            ("inicio", "dateTime", True, "dd/mm/yyyy hh:nn"),
            ("fin", "dateTime", True, "dd/mm/yyyy hh:nn"),
            ("filas_recibidas", "int64", False, ENTERO),
            ("filas_cargadas", "int64", False, ENTERO),
            ("filas_cuarentena", "int64", False, ENTERO),
            ("tasa_cuarentena", "double", False, "0.00%"),
        ],
    ),
    "Cuarentena": (
        "vw_cuarentena_por_regla",
        [
            ("lote_id", "int64", True, "0"),
            ("fecha_negocio", "dateTime", True, "dd/mm/yyyy"),
            ("regla", "string", True, None),
            ("descripcion", "string", False, None),
            ("filas", "int64", True, ENTERO),
        ],
    ),
}

ORDENAR_POR = {
    ("Prestamo", "plazo"): "plazo_meses",
    ("Margen", "componente"): "orden",
    ("Fecha", "mes_corto"): "anio_mes",
    ("Cliente", "edad"): "orden_edad",
    ("Lotes", "fecha_carga"): "fecha_negocio",
}

# Columnas calculadas: nombre, expresión, tipo y si se ocultan.
CALCULADAS = {
    "Lotes": [("fecha_carga", 'FORMAT(Lotes[fecha_negocio], "dd/mm/yyyy")', "string", False)],
    "Fecha": [
        (
            "mes_corto",
            (
                'MID("enefebmarabrmayjunjulagosepoctnovdic", (Fecha[mes] - 1) * 3 + 1, 3)'
                ' & " " & RIGHT(Fecha[anio], 2)'
            ),
            "string",
            False,
        ),
    ],
    "Distrito": [
        (
            "region_es",
            (
                'SWITCH(Distrito[region], "Prague", "Praga", "central Bohemia", "Bohemia Central",'
                ' "south Bohemia", "Bohemia del Sur", "west Bohemia", "Bohemia del Oeste",'
                ' "north Bohemia", "Bohemia del Norte", "east Bohemia", "Bohemia del Este",'
                ' "south Moravia", "Moravia del Sur", "north Moravia", "Moravia del Norte",'
                " Distrito[region])"
            ),
            "string",
            False,
        ),
    ],
    # La columna ordenada no puede ser de la que depende su orden: de ahí "edad" aparte de rango_edad.
    "Cliente": [
        ("edad", "Cliente[rango_edad]", "string", False),
        (
            "orden_edad",
            (
                'SWITCH(Cliente[rango_edad], "Menos de 25", 1, "25 a 39", 2, "40 a 59", 3,'
                ' "60 o más", 4, 5)'
            ),
            "int64",
            True,
        ),
    ],
    "Tarjeta": [
        (
            "tarjeta",
            "UPPER(LEFT(Tarjeta[tipo_tarjeta], 1)) & MID(Tarjeta[tipo_tarjeta], 2, 50)",
            "string",
            False,
        ),
    ],
}

RELACIONES = [
    ("Saldos.mes_key", "Fecha.fecha_key"),
    ("Saldos.cuenta_key", "Cuenta.cuenta_key"),
    ("Saldos.cliente_key", "Cliente.cliente_key"),
    ("Saldos.distrito_key", "Distrito.distrito_key"),
    ("Saldos.tarjeta_key", "Tarjeta.tarjeta_key"),
    ("Cartera.mes_key", "Fecha.fecha_key"),
    ("Cartera.prestamo_key", "Prestamo.prestamo_key"),
    ("Cartera.cuenta_key", "Cuenta.cuenta_key"),
    ("Cartera.cliente_key", "Cliente.cliente_key"),
    ("Cartera.distrito_key", "Distrito.distrito_key"),
    ("Gestiones.fecha_key", "Fecha.fecha_key"),
    ("Gestiones.prestamo_key", "Prestamo.prestamo_key"),
    ("Gestiones.cuenta_key", "Cuenta.cuenta_key"),
    ("Gestiones.cliente_key", "Cliente.cliente_key"),
    ("Gestiones.distrito_key", "Distrito.distrito_key"),
    ("Margen.mes_key", "Fecha.fecha_key"),
    ("Margen.distrito_key", "Distrito.distrito_key"),
    ("Lotes.fecha_negocio", "Fecha.fecha"),
    ("Cuarentena.lote_id", "Lotes.lote_id"),
]


def foto(expresion):
    """Medida de foto mensual: toma el último mes cerrado del contexto y no suma entre meses."""
    return f"""VAR corte = [Mes de corte]
RETURN IF(NOT ISBLANK(corte), CALCULATE({expresion}, KEEPFILTERS(Fecha[fin_mes] = corte)))"""


DIARIO = 'Lotes[tipo] = "DIARIO"'
SALDO = "SUM(Saldos[saldo_cierre])"
CAPITAL = "SUM(Cartera[capital_pendiente])"
MORA = f"CALCULATE({CAPITAL}, Cartera[en_mora] = TRUE())"
MORA_N = "CALCULATE(COUNTROWS(Cartera), Cartera[en_mora] = TRUE())"
MARGEN = "SUM(Margen[monto])"
INGRESOS = f"CALCULATE({MARGEN}, Margen[orden] <> 4)"
PAGADOS = f"-CALCULATE({MARGEN}, Margen[orden] = 4)"
SALDO_MEDIO = f"DIVIDE({SALDO}, DISTINCTCOUNT(Saldos[cliente_key]))"

CONTRA_MES = ' & " vs. " & LOWER(FORMAT(EOMONTH(corte, -1), "mmmm"))'


def _anterior(expresion):
    return f"CALCULATE({expresion}, REMOVEFILTERS(Fecha), Fecha[fin_mes] = EOMONTH(corte, -1))"


def _flecha(cambio):
    return f'IF({cambio} > 0, "▲ ", IF({cambio} < 0, "▼ ", "= "))'


def variacion_pct(medida, base):
    """Texto con el cambio porcentual frente al mes cerrado anterior."""
    return f"""VAR corte = [Mes de corte]
VAR anterior = {_anterior(base)}
VAR cambio = DIVIDE([{medida}] - anterior, ABS(anterior))
RETURN IF(NOT ISBLANK(cambio),
    {_flecha("cambio")} & FORMAT(cambio, "+0.0%;-0.0%;0.0%"){CONTRA_MES})"""


def variacion_abs(medida, base, formato, unidad, escala=1):
    """Texto con la diferencia frente al mes cerrado anterior, en la unidad de la medida."""
    return f"""VAR corte = [Mes de corte]
VAR anterior = {_anterior(base)}
VAR cambio = ([{medida}] - anterior) * {escala}
RETURN IF(NOT ISBLANK(anterior),
    {_flecha("cambio")} & FORMAT(cambio, "{formato}") & "{unidad}"{CONTRA_MES})"""


MEDIDAS = [
    (
        "Mes de corte",
        "CALCULATE(MAX(Fecha[fin_mes]), Fecha[mes_cerrado] = 1)",
        "dd/mm/yyyy",
        "Base",
    ),
    ("Depósitos", foto(SALDO), CZK, "Negocio"),
    ("Cuentas", foto("COUNTROWS(Saldos)"), ENTERO, "Negocio"),
    ("Cartera", foto(CAPITAL), CZK, "Riesgo"),
    ("Préstamos vigentes", foto("COUNTROWS(Cartera)"), ENTERO, "Riesgo"),
    ("Cartera en mora", foto(MORA), CZK, "Riesgo"),
    (
        "Cartera en mora top 10",
        """VAR valor = [Cartera en mora]
RETURN IF(NOT ISBLANK(valor) && RANKX(ALLSELECTED(Distrito[distrito]), [Cartera en mora]) <= 10, valor)""",
        CZK,
        "Riesgo",
    ),
    ("Préstamos en mora", foto(MORA_N), ENTERO, "Riesgo"),
    ("Capital en mora", foto(MORA), CZK, "Riesgo"),
    (
        "Cuotas atrasadas",
        foto("CALCULATE(SUM(Cartera[cuotas_atrasadas]), Cartera[en_mora] = TRUE())"),
        ENTERO,
        "Riesgo",
    ),
    ("Ratio de mora", "DIVIDE([Cartera en mora], [Cartera])", PORCENTAJE, "Riesgo"),
    ("Cartera sobre depósitos", "DIVIDE([Cartera], [Depósitos])", PORCENTAJE, "Riesgo"),
    ("Margen estimado", foto(MARGEN), CZK, "Rentabilidad"),
    ("Ingresos estimados", foto(INGRESOS), CZK, "Rentabilidad"),
    ("Intereses pagados", foto(PAGADOS), CZK, "Rentabilidad"),
    (
        "Margen estimado 12 meses",
        f"""VAR corte = [Mes de corte]
RETURN IF(NOT ISBLANK(corte),
    CALCULATE({MARGEN}, REMOVEFILTERS(Fecha), Fecha[fin_mes] > EOMONTH(corte, -12), Fecha[fin_mes] <= corte))""",
        CZK,
        "Rentabilidad",
    ),
    (
        "Margen del mes en curso (parcial)",
        f"CALCULATE({MARGEN}, REMOVEFILTERS(Fecha), Fecha[mes_cerrado] = 0)",
        CZK,
        "Rentabilidad",
    ),
    ("Clientes", foto("DISTINCTCOUNT(Saldos[cliente_key])"), ENTERO, "Negocio"),
    ("Distritos con clientes", foto("DISTINCTCOUNT(Saldos[distrito_key])"), ENTERO, "Negocio"),
    ("Saldo por cliente", "DIVIDE([Depósitos], [Clientes])", CZK, "Negocio"),
    (
        "Cuentas con tarjeta",
        'DIVIDE(CALCULATE([Cuentas], Tarjeta[tipo_tarjeta] <> "Sin tarjeta"), [Cuentas])',
        PORCENTAJE,
        "Negocio",
    ),
    ("Gestiones realizadas", "COUNTROWS(Gestiones) + 0", ENTERO, "Cobranzas"),
    ("Gestiones por préstamo", "COUNTROWS(Gestiones)", ENTERO, "Cobranzas"),
    ("Préstamos gestionados", "DISTINCTCOUNT(Gestiones[prestamo_key]) + 0", ENTERO, "Cobranzas"),
    ("Monto prometido", "SUM(Gestiones[monto_prometido]) + 0", CZK, "Cobranzas"),
    (
        "Compromisos vencidos",
        'CALCULATE(COUNTROWS(Gestiones), Gestiones[estado_compromiso] = "Vencido") + 0',
        ENTERO,
        "Cobranzas",
    ),
    (
        "Cobertura de gestión",
        "DIVIDE([Préstamos gestionados], [Préstamos en mora], 0)",
        PORCENTAJE,
        "Cobranzas",
    ),
    (
        "Último lote",
        f'CALCULATE(MAX(Lotes[fecha_negocio]), {DIARIO}, Lotes[estado] = "OK")',
        "dd/mm/yyyy",
        "Calidad",
    ),
    ("Filas recibidas", f"CALCULATE(SUM(Lotes[filas_recibidas]), {DIARIO}) + 0", ENTERO, "Calidad"),
    ("Filas cargadas", f"CALCULATE(SUM(Lotes[filas_cargadas]), {DIARIO}) + 0", ENTERO, "Calidad"),
    (
        "Filas en cuarentena",
        f"CALCULATE(SUM(Lotes[filas_cuarentena]), {DIARIO}) + 0",
        ENTERO,
        "Calidad",
    ),
    (
        "Tasa de cuarentena",
        "DIVIDE([Filas en cuarentena], [Filas recibidas], 0)",
        "0.00%",
        "Calidad",
    ),
    ("Filas apartadas", "SUM(Cuarentena[filas]) + 0", ENTERO, "Calidad"),
    # Textos: se calculan con los datos para que nunca digan algo que dejó de ser cierto.
    ("Nombre del corte", 'LOWER(FORMAT([Mes de corte], "mmmm yyyy"))', None, "Textos"),
    ("Cierre de datos", '"Cierre: " & [Nombre del corte]', None, "Textos"),
    (
        "Hallazgo resumen",
        """"Margen estimado de " & [Nombre del corte] & ": " & FORMAT([Margen estimado], "#,0")
    & " CZK. La cartera equivale al " & FORMAT([Cartera sobre depósitos], "0%") & " de los depósitos.\"""",
        None,
        "Textos",
    ),
    (
        "Hallazgo rentabilidad",
        """VAR pagados = [Intereses pagados]
VAR ingresos = [Ingresos estimados]
RETURN "Los intereses pagados (" & FORMAT(pagados, "#,0") & " CZK) "
    & IF(pagados > ingresos, "superan", "no superan") & " a los ingresos (" & FORMAT(ingresos, "#,0")
    & " CZK). El interés de préstamos usa una tasa supuesta del 12 %.\"""",
        None,
        "Textos",
    ),
    (
        "Hallazgo cartera",
        """VAR mora = [Cartera en mora]
RETURN [Préstamos en mora] & " préstamos en mora, " & FORMAT([Ratio de mora], "0.0%")
    & " de la cartera. Más de 90 días pesa " & FORMAT(DIVIDE(CALCULATE([Cartera en mora], Cartera[tramo_atraso] = "Más de 90"), mora), "0%")
    & " de la mora. Se tolera una cuota de atraso.\"""",
        None,
        "Textos",
    ),
    (
        "Hallazgo clientes",
        """VAR region = MAXX(TOPN(1, ALLSELECTED(Distrito[region_es]), [Depósitos]), Distrito[region_es])
VAR parte = DIVIDE(CALCULATE([Depósitos], Distrito[region_es] = region), CALCULATE([Depósitos], ALLSELECTED(Distrito)))
RETURN region & " concentra el " & FORMAT(parte, "0%") & " de los depósitos. El saldo medio es de "
    & FORMAT([Saldo por cliente], "#,0") & " CZK por cliente.\"""",
        None,
        "Textos",
    ),
    (
        "Hallazgo cobranzas",
        """[Préstamos gestionados] & " de " & [Préstamos en mora]
    & " préstamos en mora con gestión registrada. Lo de la app entra al almacén en la carga siguiente.\"""",
        None,
        "Textos",
    ),
    (
        "Hallazgo calidad",
        """[Filas en cuarentena] & " de " & FORMAT([Filas recibidas], "#,0")
    & " filas recibidas quedaron apartadas con su motivo. Solo se cuentan las cargas diarias.\"""",
        None,
        "Textos",
    ),
    ("Nota depósitos", variacion_pct("Depósitos", SALDO), None, "Textos"),
    ("Nota cartera", variacion_pct("Cartera", CAPITAL), None, "Textos"),
    ("Nota cartera en mora", variacion_pct("Cartera en mora", MORA), None, "Textos"),
    (
        "Nota préstamos en mora",
        variacion_abs("Préstamos en mora", MORA_N, "+0;-0;0", ""),
        None,
        "Textos",
    ),
    (
        "Nota ratio",
        variacion_abs("Ratio de mora", f"DIVIDE({MORA}, {CAPITAL})", "+0.0;-0.0;0.0", " pp", 100),
        None,
        "Textos",
    ),
    (
        "Nota margen",
        variacion_abs("Margen estimado", MARGEN, "+#,0;-#,0;0", " CZK"),
        None,
        "Textos",
    ),
    ("Nota ingresos", variacion_pct("Ingresos estimados", INGRESOS), None, "Textos"),
    ("Nota pagados", variacion_pct("Intereses pagados", PAGADOS), None, "Textos"),
    (
        "Nota 12 meses",
        """VAR corte = [Mes de corte]
RETURN LOWER(FORMAT(EOMONTH(corte, -11), "mmm yyyy")) & " a " & LOWER(FORMAT(corte, "mmm yyyy"))""",
        None,
        "Textos",
    ),
    ("Nota en curso", '"Datos hasta " & FORMAT([Último lote], "dd/mm/yyyy")', None, "Textos"),
    ("Nota clientes", '"En " & [Distritos con clientes] & " distritos"', None, "Textos"),
    ("Nota saldo", variacion_pct("Saldo por cliente", SALDO_MEDIO), None, "Textos"),
    (
        "Nota tarjeta",
        """FORMAT(CALCULATE([Cuentas], Tarjeta[tipo_tarjeta] <> "Sin tarjeta"), "#,0") & " de "
    & FORMAT([Cuentas], "#,0") & " cuentas\"""",
        None,
        "Textos",
    ),
    (
        "Nota gestiones",
        '[Préstamos gestionados] & IF([Préstamos gestionados] = 1, " préstamo gestionado", " préstamos gestionados")',
        None,
        "Textos",
    ),
    ("Nota cobertura", '"De " & [Préstamos en mora] & " préstamos en mora"', None, "Textos"),
    (
        "Nota prometido",
        'VAR n = CALCULATE(COUNTROWS(Gestiones), Gestiones[resultado] = "Promesa de pago") + 0 RETURN n & IF(n = 1, " promesa de pago", " promesas de pago")',
        None,
        "Textos",
    ),
    (
        "Nota vencidos",
        'CALCULATE(COUNTROWS(Gestiones), Gestiones[estado_compromiso] = "Por vencer") + 0 & " por vencer"',
        None,
        "Textos",
    ),
    (
        "Nota lote",
        f'CALCULATE(COUNTROWS(Lotes), {DIARIO}, Lotes[estado] = "OK") + 0 & " cargas diarias correctas"',
        None,
        "Textos",
    ),
    ("Nota recibidas", 'FORMAT([Filas cargadas], "#,0") & " cargadas"', None, "Textos"),
    (
        "Nota cuarentena",
        'DISTINCTCOUNT(Cuarentena[descripcion]) + 0 & " motivos distintos"',
        None,
        "Textos",
    ),
    ("Nota tasa", '"Sobre las filas de cargas diarias"', None, "Textos"),
]


def _id(texto):
    return hashlib.md5(texto.encode()).hexdigest()[:20]


def _guid(texto):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"banco-analitico/{texto}"))


def _indentar(texto, tabs):
    return "\n".join("\t" * tabs + linea for linea in texto.splitlines())


def _tabla_tmdl(nombre, vista, columnas):
    lineas = [f"table {nombre}"]
    if nombre == "Fecha":
        lineas.append("\tdataCategory: Time")
    lineas.append(f"\tlineageTag: {_guid(nombre)}")
    lineas.append("")
    for columna, tipo, oculta, formato in columnas:
        lineas.append(f"\tcolumn {columna}")
        lineas.append(f"\t\tdataType: {tipo}")
        if nombre == "Fecha" and columna == "fecha":
            lineas.append("\t\tisKey")
        if oculta:
            lineas.append("\t\tisHidden")
        if formato:
            lineas.append(f"\t\tformatString: {formato}")
        lineas.append(f"\t\tlineageTag: {_guid(nombre + columna)}")
        lineas.append("\t\tsummarizeBy: none")
        lineas.append(f"\t\tsourceColumn: {columna}")
        if (nombre, columna) in ORDENAR_POR:
            lineas.append(f"\t\tsortByColumn: {ORDENAR_POR[(nombre, columna)]}")
        lineas.append("")
    for columna, expresion, tipo, oculta in CALCULADAS.get(nombre, []):
        lineas.append(f"\tcolumn {columna} = {expresion}")
        lineas.append(f"\t\tdataType: {tipo}")
        if oculta:
            lineas.append("\t\tisHidden")
        lineas.append(f"\t\tlineageTag: {_guid(nombre + columna)}")
        lineas.append("\t\tsummarizeBy: none")
        if (nombre, columna) in ORDENAR_POR:
            lineas.append(f"\t\tsortByColumn: {ORDENAR_POR[(nombre, columna)]}")
        lineas.append("")
    lineas += [
        f"\tpartition {nombre} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Origen = Sql.Database(Servidor, BaseDatos),",
        f'\t\t\t\t    Vista = Origen{{[Schema = "mart", Item = "{vista}"]}}[Data]',
        "\t\t\t\tin",
        "\t\t\t\t    Vista",
        "",
    ]
    return "\n".join(lineas)


def _medidas_tmdl():
    lineas = ["table Medidas", f"\tlineageTag: {_guid('Medidas')}", ""]
    for nombre, expresion, formato, carpeta in MEDIDAS:
        lineas.append(f"\tmeasure '{nombre}' =")
        lineas.append(_indentar(expresion, 3))
        if formato:
            lineas.append(f"\t\tformatString: {formato}")
        lineas.append(f"\t\tdisplayFolder: {carpeta}")
        lineas.append(f"\t\tlineageTag: {_guid('m' + nombre)}")
        lineas.append("")
    lineas += [
        "\tcolumn Oculta",
        "\t\tdataType: int64",
        "\t\tisHidden",
        "\t\tsummarizeBy: none",
        f"\t\tlineageTag: {_guid('Medidas.Oculta')}",
        "\t\tsourceColumn: Oculta",
        "",
        "\tpartition Medidas = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Tabla = #table(type table [Oculta = Int64.Type], {})",
        "\t\t\t\tin",
        "\t\t\t\t    Tabla",
        "",
    ]
    return "\n".join(lineas)


def _escribir(ruta: Path, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(contenido, str):
        contenido = json.dumps(contenido, ensure_ascii=False, indent=2)
    ruta.write_text(contenido, encoding="utf-8", newline="\n")


def _modelo(carpeta: Path):
    _escribir(
        carpeta / ".platform",
        {
            "$schema": f"{ESQUEMAS}/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": NOMBRE},
            "config": {"version": "2.0", "logicalId": _guid("modelo")},
        },
    )
    _escribir(
        carpeta / "definition.pbism",
        {
            "$schema": f"{ESQUEMAS}/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {},
        },
    )
    d = carpeta / "definition"
    _escribir(d / "database.tmdl", "database\n\tcompatibilityLevel: 1567\n")
    referencias = "\n".join(f"ref table {t}" for t in [*TABLAS, "Medidas"])
    _escribir(
        d / "model.tmdl",
        f"""model Model
\tculture: es-PE
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: es-PE
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

{referencias}
""",
    )
    _escribir(
        d / "expressions.tmdl",
        f"""expression Servidor = "{SERVIDOR}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
\tlineageTag: {_guid("Servidor")}

expression BaseDatos = "{BASE}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
\tlineageTag: {_guid("BaseDatos")}
""",
    )
    for nombre, (vista, columnas) in TABLAS.items():
        _escribir(d / "tables" / f"{nombre}.tmdl", _tabla_tmdl(nombre, vista, columnas))
    _escribir(d / "tables" / "Medidas.tmdl", _medidas_tmdl())
    relaciones = []
    for origen, destino in RELACIONES:
        relaciones.append(
            f"relationship {_guid(origen + destino)}\n\tfromColumn: {origen}\n\ttoColumn: {destino}\n"
        )
    _escribir(d / "relationships.tmdl", "\n".join(relaciones))
    _escribir(
        d / "roles" / "Analista Moravia del Sur.tmdl",
        """role 'Analista Moravia del Sur'
\tmodelPermission: read

\ttablePermission Distrito = [region] = "south Moravia"
""",
    )


# ---------------------------------------------------------------- reporte


def lit(valor):
    return {"expr": {"Literal": {"Value": valor}}}


def texto(valor):
    return lit("'" + valor.replace("'", "''") + "'")


def color(valor):
    return {"solid": {"color": texto(valor)}}


def col(tabla, columna):
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": columna}}


def med(nombre):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": nombre}}


def _ref(campo):
    if "Measure" in campo:
        p = campo["Measure"]
        return f"Medidas.{p['Property']}", p["Property"]
    p = campo["Column"]
    return f"{p['Expression']['SourceRef']['Entity']}.{p['Property']}", p["Property"]


# Cómo se leen las columnas y medidas en encabezados, leyendas y descripciones emergentes.
ROTULOS = {
    "mes_corto": "Mes",
    "region_es": "Región",
    "distrito": "Distrito",
    "componente": "Componente",
    "producto": "Producto",
    "plazo": "Plazo",
    "tramo_atraso": "Tiempo de atraso",
    "edad": "Edad",
    "tarjeta": "Tarjeta",
    "prestamo_id": "Préstamo",
    "fecha_carga": "Fecha",
    "Saldo por cliente": "Saldo medio",
    "estado": "Estado",
    "filas_recibidas": "Recibidas",
    "filas_cargadas": "Cargadas",
    "filas_cuarentena": "En cuarentena",
    "tasa_cuarentena": "Tasa",
    "resultado": "Resultado",
    "estado_compromiso": "Estado",
    "descripcion": "Motivo",
    "Cartera en mora top 10": "Cartera en mora",
    "Gestiones por préstamo": "Gestiones",
}


def _proyeccion(campo, nombre=None):
    ref, propiedad = _ref(campo)
    salida = {"field": campo, "queryRef": ref, "nativeQueryRef": propiedad}
    rotulo = nombre or ROTULOS.get(propiedad)
    if rotulo:
        salida["displayName"] = rotulo
    return salida


def filtro_igual(tabla, columna, valor, nombre):
    return {
        "name": _id(nombre + tabla + columna),
        "field": col(tabla, columna),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "t", "Entity": tabla, "Type": 0}],
            "Where": [
                {
                    "Condition": {
                        "In": {
                            "Expressions": [
                                {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Source": "t"}},
                                        "Property": columna,
                                    }
                                }
                            ],
                            "Values": [[{"Literal": {"Value": valor}}]],
                        }
                    }
                }
            ],
        },
    }


def filtro_excluye(tabla, columna, valor, nombre):
    salida = filtro_igual(tabla, columna, valor, nombre)
    condicion = salida["filter"]["Where"][0]["Condition"]
    salida["filter"]["Where"][0]["Condition"] = {"Not": {"Expression": condicion}}
    return salida


def contenedor(titulo=None):
    objetos = {
        "background": [
            {
                "properties": {
                    "show": lit("true"),
                    "color": color("#FFFFFF"),
                    "transparency": lit("0D"),
                }
            }
        ],
        "border": [
            {"properties": {"show": lit("true"), "color": color(BORDE), "radius": lit("8D")}}
        ],
    }
    if titulo:
        objetos["title"] = [
            {
                "properties": {
                    "show": lit("true"),
                    "text": texto(titulo),
                    "fontSize": lit("12D"),
                    "bold": lit("true"),
                    "fontColor": color(MARINO),
                    "alignment": texto("left"),
                }
            }
        ]
    else:
        objetos["title"] = [{"properties": {"show": lit("false")}}]
    return objetos


def transparente(sin_borde=True):
    objetos = {
        "background": [{"properties": {"show": lit("false")}}],
        "title": [{"properties": {"show": lit("false")}}],
    }
    if sin_borde:
        objetos["border"] = [{"properties": {"show": lit("false")}}]
    return objetos


def parrafos(*lineas):
    return [
        {
            "properties": {
                "paragraphs": [
                    {"textRuns": [{"value": valor, "textStyle": estilo}]}
                    for valor, estilo in lineas
                ]
            }
        }
    ]


class Pagina:
    """Cabecera marina con hallazgo y filtro, navegación debajo, tarjetas y luego gráficos."""

    def __init__(self, nombre, titulo, hallazgo, orden):
        self.id = _id(nombre)
        self.nombre, self.titulo, self.hallazgo, self.orden = nombre, titulo, hallazgo, orden
        self.visuales = []
        self.z = 1000
        self._cabecera()

    def _agregar(self, x, y, ancho, alto, visual, filtros=None):
        self.z += 100
        contenido = {
            "$schema": f"{ESQUEMA_REPORTE}/visualContainer/2.2.0/schema.json",
            "name": _id(f"{self.nombre}{self.z}"),
            "position": {
                "x": x,
                "y": y,
                "z": self.z,
                "height": alto,
                "width": ancho,
                "tabOrder": self.z,
            },
            "visual": visual,
        }
        if filtros:
            contenido["filterConfig"] = {"filters": filtros}
        self.visuales.append(contenido)

    def _cabecera(self):
        self._agregar(
            0,
            0,
            1280,
            64,
            {
                "visualType": "textbox",
                "objects": {
                    "general": parrafos(
                        (
                            self.titulo,
                            {"fontSize": "17pt", "fontWeight": "bold", "color": "#FFFFFF"},
                        )
                    )
                },
                "visualContainerObjects": {
                    "background": [
                        {
                            "properties": {
                                "show": lit("true"),
                                "color": color(MARINO),
                                "transparency": lit("0D"),
                            }
                        }
                    ],
                    "title": [{"properties": {"show": lit("false")}}],
                    "border": [{"properties": {"show": lit("false")}}],
                },
            },
        )
        self._agregar(
            8,
            32,
            800,
            30,
            {
                "visualType": "multiRowCard",
                "query": {
                    "queryState": {"Values": {"projections": [_proyeccion(med(self.hallazgo))]}}
                },
                "objects": {
                    # Un único texto se dibuja como título de la tarjeta, no como dato.
                    "cardTitle": [
                        {
                            "properties": {
                                "color": color("#D5DDEA"),
                                "fontSize": lit("10D"),
                                "fontFamily": texto("Segoe UI"),
                            }
                        }
                    ],
                    "dataLabels": [
                        {"properties": {"color": color("#D5DDEA"), "fontSize": lit("10D")}}
                    ],
                    "categoryLabels": [{"properties": {"show": lit("false")}}],
                    "card": [{"properties": {"barShow": lit("false"), "outlineStyle": lit("0D")}}],
                },
                "visualContainerObjects": transparente(),
            },
        )
        self._nota_cabecera()
        self._agregar(
            24,
            70,
            1232,
            28,
            {
                "visualType": "pageNavigator",
                "visualContainerObjects": transparente(),
            },
        )

    def _nota_cabecera(self):
        self._agregar(
            824,
            16,
            196,
            32,
            {
                "visualType": "card",
                "query": {
                    "queryState": {"Values": {"projections": [_proyeccion(med("Cierre de datos"))]}}
                },
                "objects": {
                    "labels": [
                        {
                            "properties": {
                                "fontSize": lit("10D"),
                                "color": color("#FFFFFF"),
                            }
                        }
                    ],
                    "categoryLabels": [{"properties": {"show": lit("false")}}],
                },
                "visualContainerObjects": transparente(),
            },
        )

    def _caja(self, x, y, ancho, alto):
        self._agregar(
            x,
            y,
            ancho,
            alto,
            {
                "visualType": "textbox",
                "objects": {"general": parrafos((" ", {"fontSize": "8pt"}))},
                "visualContainerObjects": contenedor(),
            },
        )

    def tarjeta(self, x, ancho, medida, nota, nombre=None, unidades=1):
        """Valor grande con su rótulo y, debajo, la nota con el contexto del número."""
        y, alto = 104, 88
        self._caja(x, y, ancho, alto)
        valor = {
            "fontSize": lit("18D"),
            "color": color(MARINO),
            "bold": lit("true"),
            "labelDisplayUnits": lit(f"{unidades}D"),
        }
        if unidades in DECIMALES:
            valor["labelPrecision"] = lit(f"{DECIMALES[unidades]}L")
        self._agregar(
            x,
            y,
            ancho,
            66,
            {
                "visualType": "card",
                "query": {
                    "queryState": {
                        "Values": {"projections": [_proyeccion(med(medida), nombre or medida)]}
                    }
                },
                "objects": {
                    "labels": [{"properties": valor}],
                    "categoryLabels": [
                        {
                            "properties": {
                                "show": lit("true"),
                                "fontSize": lit("9D"),
                                "color": color(GRIS),
                            }
                        }
                    ],
                },
                "visualContainerObjects": transparente(),
            },
        )
        self._agregar(
            x,
            y + 64,
            ancho,
            24,
            {
                "visualType": "card",
                "query": {"queryState": {"Values": {"projections": [_proyeccion(med(nota))]}}},
                "objects": {
                    "labels": [{"properties": {"fontSize": lit("9D"), "color": color(GRIS)}}],
                    "categoryLabels": [{"properties": {"show": lit("false")}}],
                },
                "visualContainerObjects": transparente(),
            },
        )

    def grafico(
        self,
        tipo,
        x,
        y,
        ancho,
        alto,
        titulo,
        categoria,
        valores,
        orden=None,
        filtros=None,
        colores=None,
        etiquetas=False,
        unidades=1,
    ):
        consulta = {
            "queryState": {
                "Category": {"projections": [{**_proyeccion(categoria), "active": True}]},
                "Y": {"projections": [_proyeccion(v) for v in valores]},
            }
        }
        if orden:
            campo, direccion = orden
            consulta["sortDefinition"] = {
                "sort": [{"field": campo, "direction": direccion}],
                "isDefaultSort": False,
            }
        # Con etiquetas el eje de valores sobra: cada barra ya dice su número.
        eje_valores = {
            "showAxisTitle": lit("false"),
            "labelColor": color(GRIS),
            "fontSize": lit("9D"),
            "labelDisplayUnits": lit(f"{unidades}D"),
        }
        if unidades in DECIMALES:
            eje_valores["labelPrecision"] = lit("0L")
        if etiquetas:
            eje_valores |= {"show": lit("false"), "gridlineShow": lit("false")}
        else:
            eje_valores |= {"gridlineShow": lit("true"), "gridlineColor": color("#E9ECF1")}
        eje_categorias = {
            "showAxisTitle": lit("false"),
            "labelColor": color(GRIS),
            "fontSize": lit("9D"),
        }
        if tipo in ("clusteredBarChart", "clusteredColumnChart"):
            eje_categorias["innerPadding"] = lit("35L")
        if tipo == "clusteredBarChart":
            eje_categorias["maxMarginFactor"] = lit("45L")
        hay_leyenda = len(valores) > 1 or tipo == "waterfallChart"
        leyenda = {"show": lit("true" if hay_leyenda else "false")}
        if hay_leyenda:
            leyenda |= {
                "position": texto("Top"),
                "labelColor": color(GRIS),
                "fontSize": lit("9D"),
            }
        objetos = {
            "valueAxis": [{"properties": eje_valores}],
            "categoryAxis": [{"properties": eje_categorias}],
            "legend": [{"properties": leyenda}],
        }
        if tipo == "lineChart":
            objetos["lineStyles"] = [
                {
                    "properties": {
                        "strokeWidth": lit("2D"),
                        "showMarker": lit("true"),
                        "markerSize": lit("5D"),
                    }
                }
            ]
        if etiquetas:
            rotulo = {
                "show": lit("true"),
                "fontSize": lit("9D"),
                "color": color(MARINO),
                "labelDisplayUnits": lit(f"{unidades}D"),
            }
            if unidades in DECIMALES:
                rotulo["labelPrecision"] = lit(f"{DECIMALES[unidades]}L")
            if tipo in ("clusteredBarChart", "clusteredColumnChart"):
                rotulo["labelPosition"] = texto("OutsideEnd")
            objetos["labels"] = [{"properties": rotulo}]
        if colores:
            relleno = {"properties": {"fill": color(colores)}}
            # En una línea el color se asigna a la serie, no a cada punto.
            if tipo == "lineChart":
                relleno["selector"] = {"metadata": _ref(valores[0])[0]}
            objetos["dataPoint"] = [relleno]
        self._agregar(
            x,
            y,
            ancho,
            alto,
            {
                "visualType": tipo,
                "query": consulta,
                "objects": objetos,
                "visualContainerObjects": contenedor(titulo),
            },
            filtros,
        )

    def tabla(self, x, y, ancho, alto, titulo, campos, anchos, orden=None, filtros=None):
        consulta = {"queryState": {"Values": {"projections": [_proyeccion(c) for c in campos]}}}
        if orden:
            consulta["sortDefinition"] = {
                "sort": [{"field": orden[0], "direction": orden[1]}],
                "isDefaultSort": False,
            }
        self._agregar(
            x,
            y,
            ancho,
            alto,
            {
                "visualType": "tableEx",
                "query": consulta,
                "objects": {
                    "columnHeaders": [
                        {
                            "properties": {
                                "fontColor": color(MARINO),
                                "backColor": color("#EEF1F6"),
                                "bold": lit("true"),
                                "fontSize": lit("9D"),
                            }
                        }
                    ],
                    "values": [
                        {
                            "properties": {
                                "fontColorPrimary": color(MARINO),
                                "backColorPrimary": color("#FFFFFF"),
                                "fontColorSecondary": color(MARINO),
                                "backColorSecondary": color("#FFFFFF"),
                                "fontSize": lit("9D"),
                            }
                        }
                    ],
                    "grid": [
                        {
                            "properties": {
                                "gridVertical": lit("false"),
                                "gridHorizontal": lit("true"),
                                "gridHorizontalColor": color(BORDE),
                                "rowPadding": lit("5D"),
                            }
                        }
                    ],
                    "columnWidth": [
                        {
                            "properties": {"value": lit(f"{a}D")},
                            "selector": {"metadata": _ref(c)[0]},
                        }
                        for c, a in zip(campos, anchos, strict=True)
                    ],
                },
                "visualContainerObjects": contenedor(titulo),
            },
            filtros,
        )

    def segmentador(self, campo, titulo):
        self._agregar(
            1036,
            2,
            220,
            60,
            {
                "visualType": "slicer",
                "query": {
                    "queryState": {
                        "Values": {"projections": [{**_proyeccion(campo), "active": True}]}
                    }
                },
                "objects": {
                    "data": [{"properties": {"mode": texto("Dropdown")}}],
                    "header": [
                        {
                            "properties": {
                                "show": lit("true"),
                                "text": texto(titulo),
                                "fontColor": color(GRIS),
                                "textSize": lit("9D"),
                            }
                        }
                    ],
                },
                "visualContainerObjects": {
                    "background": [
                        {
                            "properties": {
                                "show": lit("true"),
                                "color": color("#FFFFFF"),
                                "transparency": lit("0D"),
                            }
                        }
                    ],
                    "border": [
                        {
                            "properties": {
                                "show": lit("true"),
                                "color": color(BORDE),
                                "radius": lit("6D"),
                            }
                        }
                    ],
                    "title": [{"properties": {"show": lit("false")}}],
                },
            },
        )


MES_CORTO = col("Fecha", "mes_corto")
REGION = col("Distrito", "region_es")
ULTIMOS_13 = [filtro_igual("Fecha", "en_ultimos_13", "1L", "u13")]
SOLO_DIARIOS = [filtro_igual("Lotes", "tipo", "'DIARIO'", "dia")]
SIN_AL_DIA = [filtro_excluye("Cartera", "tramo_atraso", "'Al día'", "dia")]
MES = (MES_CORTO, "Ascending")

# Rejilla de 1280 x 720: márgenes de 24, gráficos desde y=200 en una fila de 504 o dos de 246.
Y, ALTO, MITAD, Y2 = 200, 504, 246, 458
TRES = [(24, 402), (438, 402), (852, 404)]
CUATRO = [(24, 299), (335, 299), (646, 299), (957, 299)]


def _paginas():
    p1 = Pagina("resumen", "Resumen ejecutivo", "Hallazgo resumen", 1)
    p1.tarjeta(24, 236, "Depósitos", "Nota depósitos", None, MILLON)
    p1.tarjeta(272, 236, "Cartera", "Nota cartera", None, MILLON)
    p1.tarjeta(520, 236, "Ratio de mora", "Nota ratio")
    p1.tarjeta(768, 236, "Margen estimado", "Nota margen", "Margen estimado del mes", MIL)
    p1.tarjeta(
        1016,
        240,
        "Margen del mes en curso (parcial)",
        "Nota en curso",
        "Mes en curso: parcial, no comparable",
        MIL,
    )
    p1.grafico(
        "lineChart",
        24,
        Y,
        720,
        ALTO,
        "Depósitos y cartera, últimos 13 meses cerrados",
        MES_CORTO,
        [med("Depósitos"), med("Cartera")],
        MES,
        ULTIMOS_13,
        unidades=MILLON,
    )
    p1.grafico(
        "clusteredColumnChart",
        756,
        Y,
        500,
        MITAD,
        "Margen estimado por mes",
        MES_CORTO,
        [med("Margen estimado")],
        MES,
        ULTIMOS_13,
        AZUL,
        unidades=MIL,
    )
    p1.grafico(
        "lineChart",
        756,
        Y2,
        500,
        MITAD,
        "Ratio de mora por mes",
        MES_CORTO,
        [med("Ratio de mora")],
        MES,
        ULTIMOS_13,
        ROJO,
    )

    p2 = Pagina("rentabilidad", "Rentabilidad", "Hallazgo rentabilidad", 2)
    p2.segmentador(REGION, "Región")
    p2.tarjeta(CUATRO[0][0], 299, "Margen estimado", "Nota margen", "Margen estimado del mes", MIL)
    p2.tarjeta(CUATRO[1][0], 299, "Margen estimado 12 meses", "Nota 12 meses", None, MIL)
    p2.tarjeta(
        CUATRO[2][0], 299, "Ingresos estimados", "Nota ingresos", "Ingresos estimados del mes", MIL
    )
    p2.tarjeta(
        CUATRO[3][0], 299, "Intereses pagados", "Nota pagados", "Intereses pagados del mes", MIL
    )
    p2.grafico(
        "waterfallChart",
        24,
        Y,
        520,
        ALTO,
        "De los ingresos al margen estimado, último mes cerrado",
        col("Margen", "componente"),
        [med("Margen estimado")],
        (col("Margen", "componente"), "Ascending"),
        None,
        None,
        True,
        MIL,
    )
    p2.grafico(
        "clusteredBarChart",
        556,
        Y,
        700,
        MITAD,
        "Aporte al margen por producto, último mes cerrado",
        col("Margen", "producto"),
        [med("Margen estimado")],
        None,
        None,
        AZUL,
        True,
        MIL,
    )
    p2.grafico(
        "lineChart",
        556,
        Y2,
        700,
        MITAD,
        "Ingresos e intereses pagados, últimos 13 meses cerrados",
        MES_CORTO,
        [med("Ingresos estimados"), med("Intereses pagados")],
        MES,
        ULTIMOS_13,
        unidades=MIL,
    )

    p3 = Pagina("cartera", "Cartera y mora", "Hallazgo cartera", 3)
    p3.segmentador(REGION, "Región")
    p3.tarjeta(TRES[0][0], TRES[0][1], "Cartera en mora", "Nota cartera en mora", None, MILLON)
    p3.tarjeta(TRES[1][0], TRES[1][1], "Préstamos en mora", "Nota préstamos en mora")
    p3.tarjeta(TRES[2][0], TRES[2][1], "Ratio de mora", "Nota ratio")
    p3.grafico(
        "lineChart",
        24,
        Y,
        816,
        MITAD,
        "Ratio de mora, últimos 13 meses cerrados",
        MES_CORTO,
        [med("Ratio de mora")],
        MES,
        ULTIMOS_13,
        ROJO,
    )
    p3.grafico(
        "clusteredBarChart",
        24,
        Y2,
        402,
        MITAD,
        "Cartera en mora por tiempo de atraso",
        col("Cartera", "tramo_atraso"),
        [med("Cartera en mora")],
        (col("Cartera", "tramo_atraso"), "Ascending"),
        SIN_AL_DIA,
        ROJO,
        True,
        MILLON,
    )
    p3.grafico(
        "clusteredColumnChart",
        438,
        Y2,
        402,
        MITAD,
        "Ratio de mora por plazo del préstamo",
        col("Prestamo", "plazo"),
        [med("Ratio de mora")],
        (col("Prestamo", "plazo"), "Ascending"),
        None,
        AZUL,
        True,
    )
    p3.grafico(
        "clusteredBarChart",
        852,
        Y,
        404,
        ALTO,
        "Los 10 distritos con más cartera en mora",
        col("Distrito", "distrito"),
        [med("Cartera en mora top 10")],
        (med("Cartera en mora top 10"), "Descending"),
        None,
        ROJO,
        True,
        MIL,
    )

    p4 = Pagina("clientes", "Clientes y distritos", "Hallazgo clientes", 4)
    p4.segmentador(REGION, "Región")
    p4.tarjeta(TRES[0][0], TRES[0][1], "Clientes", "Nota clientes")
    p4.tarjeta(TRES[1][0], TRES[1][1], "Saldo por cliente", "Nota saldo", "Saldo medio por cliente")
    p4.tarjeta(TRES[2][0], TRES[2][1], "Cuentas con tarjeta", "Nota tarjeta")
    p4.grafico(
        "clusteredBarChart",
        24,
        Y,
        402,
        ALTO,
        "Depósitos por región",
        REGION,
        [med("Depósitos")],
        (med("Depósitos"), "Descending"),
        None,
        AZUL,
        True,
        MILLON,
    )
    p4.grafico(
        "clusteredColumnChart",
        438,
        Y,
        402,
        MITAD,
        "Clientes por edad",
        col("Cliente", "edad"),
        [med("Clientes")],
        (col("Cliente", "edad"), "Ascending"),
        None,
        AZUL,
        True,
    )
    p4.grafico(
        "clusteredBarChart",
        438,
        Y2,
        402,
        MITAD,
        "Cuentas por tipo de tarjeta",
        col("Tarjeta", "tarjeta"),
        [med("Cuentas")],
        (med("Cuentas"), "Descending"),
        None,
        AZUL,
        True,
    )
    p4.tabla(
        852,
        Y,
        404,
        ALTO,
        "Detalle por distrito",
        [col("Distrito", "distrito"), med("Clientes"), med("Depósitos"), med("Saldo por cliente")],
        [108, 62, 112, 84],
        (med("Depósitos"), "Descending"),
    )

    p5 = Pagina("cobranzas", "Cobranzas", "Hallazgo cobranzas", 5)
    p5.tarjeta(CUATRO[0][0], 299, "Gestiones realizadas", "Nota gestiones")
    p5.tarjeta(
        CUATRO[1][0], 299, "Cobertura de gestión", "Nota cobertura", "Préstamos en mora gestionados"
    )
    p5.tarjeta(CUATRO[2][0], 299, "Monto prometido", "Nota prometido")
    p5.tarjeta(CUATRO[3][0], 299, "Compromisos vencidos", "Nota vencidos")
    p5.grafico(
        "clusteredBarChart",
        24,
        Y,
        402,
        MITAD,
        "Gestiones por resultado",
        col("Gestiones", "resultado"),
        [med("Gestiones realizadas")],
        (med("Gestiones realizadas"), "Descending"),
        None,
        AZUL,
        True,
    )
    p5.grafico(
        "clusteredBarChart",
        24,
        Y2,
        402,
        MITAD,
        "Gestiones por estado del compromiso",
        col("Gestiones", "estado_compromiso"),
        [med("Gestiones realizadas")],
        (med("Gestiones realizadas"), "Descending"),
        None,
        AZUL,
        True,
    )
    p5.tabla(
        438,
        Y,
        818,
        ALTO,
        "Préstamos en mora por gestionar, de mayor a menor capital",
        [
            col("Prestamo", "prestamo_id"),
            col("Distrito", "distrito"),
            med("Cuotas atrasadas"),
            med("Capital en mora"),
            med("Gestiones por préstamo"),
        ],
        [110, 270, 130, 170, 100],
        (med("Capital en mora"), "Descending"),
    )

    p6 = Pagina("calidad", "Calidad de datos", "Hallazgo calidad", 6)
    p6.tarjeta(CUATRO[0][0], 299, "Último lote", "Nota lote", "Último lote cargado")
    p6.tarjeta(CUATRO[1][0], 299, "Filas recibidas", "Nota recibidas")
    p6.tarjeta(CUATRO[2][0], 299, "Filas en cuarentena", "Nota cuarentena")
    p6.tarjeta(CUATRO[3][0], 299, "Tasa de cuarentena", "Nota tasa")
    p6.tabla(
        24,
        Y,
        740,
        ALTO,
        "Lotes diarios",
        [
            col("Lotes", "fecha_carga"),
            col("Lotes", "estado"),
            col("Lotes", "filas_recibidas"),
            col("Lotes", "filas_cargadas"),
            col("Lotes", "filas_cuarentena"),
            col("Lotes", "tasa_cuarentena"),
        ],
        [150, 90, 110, 110, 130, 100],
        (col("Lotes", "fecha_carga"), "Descending"),
        SOLO_DIARIOS,
    )
    p6.grafico(
        "clusteredBarChart",
        776,
        Y,
        480,
        MITAD,
        "Filas apartadas por motivo",
        col("Cuarentena", "descripcion"),
        [med("Filas apartadas")],
        (med("Filas apartadas"), "Descending"),
        None,
        AZUL,
        True,
    )
    p6.grafico(
        "clusteredColumnChart",
        776,
        Y2,
        480,
        MITAD,
        "Filas en cuarentena por carga diaria",
        col("Lotes", "fecha_carga"),
        [med("Filas en cuarentena")],
        (col("Lotes", "fecha_carga"), "Ascending"),
        SOLO_DIARIOS,
        AZUL,
        True,
    )
    return [p1, p2, p3, p4, p5, p6]


TEMA = {
    "name": NOMBRE,
    "dataColors": [AZUL, TURQUESA, "#7A8CA5", "#E0A030", ROJO, "#4F6D9A", "#9DB4C0", GRIS],
    "foreground": MARINO,
    "background": "#FFFFFF",
    "tableAccent": AZUL,
    "good": TURQUESA,
    "bad": ROJO,
    "textClasses": {
        "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": GRIS},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 24, "color": MARINO},
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": MARINO},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": MARINO},
    },
}

VERSION_TEMA = {"visual": "1.8.53", "report": "2.0.53", "page": "1.3.53"}


def _reporte(carpeta: Path):
    _escribir(
        carpeta / ".platform",
        {
            "$schema": f"{ESQUEMAS}/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": NOMBRE},
            "config": {"version": "2.0", "logicalId": _guid("reporte")},
        },
    )
    _escribir(
        carpeta / "definition.pbir",
        {
            "$schema": f"{ESQUEMAS}/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{NOMBRE}.SemanticModel"}},
        },
    )
    tema = f"{NOMBRE}.json"
    _escribir(carpeta / "StaticResources" / "RegisteredResources" / tema, TEMA)
    d = carpeta / "definition"
    _escribir(
        d / "version.json",
        {"$schema": f"{ESQUEMA_REPORTE}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"},
    )
    _escribir(
        d / "report.json",
        {
            "$schema": f"{ESQUEMA_REPORTE}/report/3.0.0/schema.json",
            "themeCollection": {
                "customTheme": {
                    "name": tema,
                    "reportVersionAtImport": VERSION_TEMA,
                    "type": "RegisteredResources",
                }
            },
            "objects": {"outspacePane": [{"properties": {"expanded": lit("false")}}]},
            "resourcePackages": [
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [{"name": tema, "path": tema, "type": "CustomTheme"}],
                }
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
            },
        },
    )
    paginas = _paginas()
    _escribir(
        d / "pages" / "pages.json",
        {
            "$schema": f"{ESQUEMA_REPORTE}/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [p.id for p in paginas],
            "activePageName": paginas[0].id,
        },
    )
    for p in paginas:
        _escribir(
            d / "pages" / p.id / "page.json",
            {
                "$schema": f"{ESQUEMA_REPORTE}/page/2.0.0/schema.json",
                "name": p.id,
                "displayName": p.titulo,
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
                "objects": {
                    "background": [
                        {"properties": {"color": color(FONDO), "transparency": lit("0D")}}
                    ]
                },
            },
        )
        for v in p.visuales:
            _escribir(d / "pages" / p.id / "visuals" / v["name"] / "visual.json", v)


def main():
    for carpeta in (RAIZ / f"{NOMBRE}.Report", RAIZ / f"{NOMBRE}.SemanticModel" / "definition"):
        if carpeta.exists():
            shutil.rmtree(carpeta)
    _modelo(RAIZ / f"{NOMBRE}.SemanticModel")
    _reporte(RAIZ / f"{NOMBRE}.Report")
    _escribir(
        RAIZ / f"{NOMBRE}.pbip",
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{NOMBRE}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    print("Proyecto escrito en", RAIZ)


if __name__ == "__main__":
    main()

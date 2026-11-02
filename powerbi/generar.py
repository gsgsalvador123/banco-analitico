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

MARINO, ACENTO, ROJO, GRIS, FONDO = "#12284B", "#1F8A8C", "#C8372D", "#5B6776", "#F3F5F8"

MILLONES = '#,0.0,," M CZK"'
ENTERO = "#,0"
CZK = '#,0" CZK"'
PORCENTAJE = "0.0%"


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
            ("anio_mes", "string", False, None),
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
            ("region", "string", False, None),
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
            ("rango_edad", "string", False, None),
        ],
    ),
    "Tarjeta": (
        "vw_dim_tarjeta",
        [
            k("tarjeta_key"),
            ("tarjeta_id", "int64", True, "0"),
            ("tipo_tarjeta", "string", False, None),
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
            ("fecha_negocio", "dateTime", False, "dd/mm/yyyy"),
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

ORDENAR_POR = {("Prestamo", "plazo"): "plazo_meses", ("Margen", "componente"): "orden"}

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

MEDIDAS = [
    (
        "Mes de corte",
        "CALCULATE(MAX(Fecha[fin_mes]), Fecha[mes_cerrado] = 1)",
        "dd/mm/yyyy",
        "Base",
    ),
    ("Depósitos", foto("SUM(Saldos[saldo_cierre])"), MILLONES, "Negocio"),
    ("Cuentas", foto("COUNTROWS(Saldos)"), ENTERO, "Negocio"),
    ("Cartera", foto("SUM(Cartera[capital_pendiente])"), MILLONES, "Riesgo"),
    ("Préstamos vigentes", foto("COUNTROWS(Cartera)"), ENTERO, "Riesgo"),
    (
        "Cartera en mora",
        foto("CALCULATE(SUM(Cartera[capital_pendiente]), Cartera[en_mora] = TRUE())"),
        MILLONES,
        "Riesgo",
    ),
    (
        "Préstamos en mora",
        foto("CALCULATE(COUNTROWS(Cartera), Cartera[en_mora] = TRUE())"),
        ENTERO,
        "Riesgo",
    ),
    (
        "Capital en mora",
        foto("CALCULATE(SUM(Cartera[capital_pendiente]), Cartera[en_mora] = TRUE())"),
        CZK,
        "Riesgo",
    ),
    (
        "Cuotas atrasadas",
        foto("CALCULATE(SUM(Cartera[cuotas_atrasadas]), Cartera[en_mora] = TRUE())"),
        ENTERO,
        "Riesgo",
    ),
    ("Ratio de mora", "DIVIDE([Cartera en mora], [Cartera])", PORCENTAJE, "Riesgo"),
    ("Cartera sobre depósitos", "DIVIDE([Cartera], [Depósitos])", PORCENTAJE, "Riesgo"),
    ("Margen estimado", foto("SUM(Margen[monto])"), CZK, "Rentabilidad"),
    ("Monto del componente", foto("SUM(Margen[monto])"), CZK, "Rentabilidad"),
    (
        "Margen estimado 12 meses",
        """VAR corte = [Mes de corte]
RETURN IF(NOT ISBLANK(corte),
    CALCULATE(SUM(Margen[monto]), REMOVEFILTERS(Fecha), Fecha[fin_mes] > EOMONTH(corte, -12), Fecha[fin_mes] <= corte))""",
        CZK,
        "Rentabilidad",
    ),
    (
        "Margen del mes anterior",
        """VAR corte = [Mes de corte]
RETURN IF(NOT ISBLANK(corte),
    CALCULATE(SUM(Margen[monto]), REMOVEFILTERS(Fecha), Fecha[fin_mes] = EOMONTH(corte, -1)))""",
        CZK,
        "Rentabilidad",
    ),
    (
        "Margen del mes en curso (parcial)",
        "CALCULATE(SUM(Margen[monto]), REMOVEFILTERS(Fecha), Fecha[mes_cerrado] = 0)",
        CZK,
        "Rentabilidad",
    ),
    ("Clientes", foto("DISTINCTCOUNT(Saldos[cliente_key])"), ENTERO, "Negocio"),
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
        if "#" in formato or '"' in formato:
            lineas.append(f"\t\tformatString: {formato}")
        else:
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
\tculture: es-ES
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: es-ES
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


def _proyeccion(campo, nombre=None):
    ref, propiedad = _ref(campo)
    salida = {"field": campo, "queryRef": ref, "nativeQueryRef": propiedad}
    if nombre:
        salida["displayName"] = nombre
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
            {"properties": {"show": lit("true"), "color": color("#E2E6EC"), "radius": lit("8D")}}
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


class Pagina:
    def __init__(self, nombre, titulo, hallazgo, orden):
        self.id = _id(nombre)
        self.nombre, self.titulo, self.hallazgo, self.orden = nombre, titulo, hallazgo, orden
        self.visuales = []
        self.z = 1000

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

    def tarjeta(self, x, y, ancho, alto, medida, nombre=None, tamano=24):
        self._agregar(
            x,
            y,
            ancho,
            alto,
            {
                "visualType": "card",
                "query": {
                    "queryState": {
                        "Values": {"projections": [_proyeccion(med(medida), nombre or medida)]}
                    }
                },
                "objects": {
                    "labels": [
                        {
                            "properties": {
                                "fontSize": lit(f"{tamano}D"),
                                "color": color(MARINO),
                                "bold": lit("true"),
                            }
                        }
                    ],
                    "categoryLabels": [
                        {
                            "properties": {
                                "show": lit("true"),
                                "fontSize": lit("10D"),
                                "color": color(GRIS),
                            }
                        }
                    ],
                },
                "visualContainerObjects": contenedor(),
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
        objetos = {
            "valueAxis": [{"properties": {"gridlineColor": color("#E9ECF1")}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit("false")}}],
        }
        if etiquetas:
            objetos["labels"] = [{"properties": {"show": lit("true"), "fontSize": lit("9D")}}]
        if colores:
            objetos["dataPoint"] = [{"properties": {"fill": color(colores)}}]
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

    def tabla(self, x, y, ancho, alto, titulo, campos, orden=None, filtros=None):
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
                                "fontColor": color("#FFFFFF"),
                                "backColor": color(MARINO),
                                "bold": lit("true"),
                            }
                        }
                    ],
                },
                "visualContainerObjects": contenedor(titulo),
            },
            filtros,
        )

    def segmentador(self, x, y, ancho, alto, campo, titulo):
        self._agregar(
            x,
            y,
            ancho,
            alto,
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
                    "background": [{"properties": {"show": lit("false")}}],
                    "title": [{"properties": {"show": lit("false")}}],
                },
            },
        )

    def encabezado(self):
        self._agregar(
            24,
            12,
            860,
            62,
            {
                "visualType": "textbox",
                "objects": {
                    "general": [
                        {
                            "properties": {
                                "paragraphs": [
                                    {
                                        "textRuns": [
                                            {
                                                "value": self.titulo,
                                                "textStyle": {
                                                    "fontSize": "18pt",
                                                    "fontWeight": "bold",
                                                    "color": MARINO,
                                                },
                                            }
                                        ]
                                    },
                                    {
                                        "textRuns": [
                                            {
                                                "value": self.hallazgo,
                                                "textStyle": {"fontSize": "11pt", "color": GRIS},
                                            }
                                        ]
                                    },
                                ]
                            }
                        }
                    ]
                },
                "visualContainerObjects": {"background": [{"properties": {"show": lit("false")}}]},
            },
        )

    def navegador(self):
        self._agregar(
            24,
            684,
            1232,
            28,
            {
                "visualType": "pageNavigator",
                "visualContainerObjects": {"background": [{"properties": {"show": lit("false")}}]},
            },
        )


ANIO_MES = col("Fecha", "anio_mes")
ULTIMOS_13 = [filtro_igual("Fecha", "en_ultimos_13", "1L", "u13")]
SOLO_DIARIOS = [filtro_igual("Lotes", "tipo", "'DIARIO'", "dia")]
SIN_AL_DIA = [filtro_excluye("Cartera", "tramo_atraso", "'Al día'", "dia")]
MES = (ANIO_MES, "Ascending")


def _paginas():
    # Rejilla: márgenes de 24, tarjetas en y=84, gráficos en y=184 y navegación abajo.
    p1 = Pagina(
        "resumen",
        "Resumen ejecutivo",
        "El margen estimado sigue negativo: el banco presta menos de un tercio de lo que capta.",
        1,
    )
    p1.tarjeta(24, 84, 232, 88, "Depósitos")
    p1.tarjeta(268, 84, 232, 88, "Cartera")
    p1.tarjeta(512, 84, 232, 88, "Ratio de mora")
    p1.tarjeta(756, 84, 232, 88, "Margen estimado", "Margen estimado del mes")
    p1.tarjeta(
        1000,
        84,
        256,
        88,
        "Margen del mes en curso (parcial)",
        "Mes en curso: parcial, no comparable",
        16,
    )
    p1.grafico(
        "lineChart",
        24,
        184,
        720,
        488,
        "Depósitos y cartera, últimos 13 meses cerrados",
        ANIO_MES,
        [med("Depósitos"), med("Cartera")],
        MES,
        ULTIMOS_13,
    )
    p1.grafico(
        "clusteredColumnChart",
        756,
        184,
        500,
        488,
        "Margen estimado por mes",
        ANIO_MES,
        [med("Margen estimado")],
        MES,
        ULTIMOS_13,
        ACENTO,
    )

    p2 = Pagina(
        "rentabilidad",
        "Rentabilidad",
        "Los intereses pagados pesan más que los ingresos. El interés de préstamos usa una tasa supuesta del 12 %.",
        2,
    )
    p2.segmentador(1016, 12, 240, 62, col("Distrito", "region"), "Región")
    p2.tarjeta(24, 84, 400, 88, "Margen estimado", "Margen estimado del mes")
    p2.tarjeta(440, 84, 400, 88, "Margen estimado 12 meses")
    p2.tarjeta(856, 84, 400, 88, "Margen del mes anterior")
    p2.grafico(
        "waterfallChart",
        24,
        184,
        620,
        488,
        "De los ingresos al margen estimado, último mes cerrado",
        col("Margen", "componente"),
        [med("Monto del componente")],
        (col("Margen", "componente"), "Ascending"),
    )
    p2.grafico(
        "clusteredBarChart",
        656,
        184,
        600,
        230,
        "Aporte por producto, último mes cerrado",
        col("Margen", "producto"),
        [med("Monto del componente")],
        None,
        None,
        ACENTO,
        True,
    )
    p2.grafico(
        "lineChart",
        656,
        426,
        600,
        246,
        "Margen estimado, últimos 13 meses cerrados",
        ANIO_MES,
        [med("Margen estimado")],
        MES,
        ULTIMOS_13,
    )

    p3 = Pagina(
        "cartera",
        "Cartera y mora",
        "La mora se mide contando cuotas pagadas contra esperadas, con tolerancia de una cuota.",
        3,
    )
    p3.segmentador(1016, 12, 240, 62, col("Distrito", "region"), "Región")
    p3.tarjeta(24, 84, 400, 88, "Cartera en mora")
    p3.tarjeta(440, 84, 400, 88, "Préstamos en mora")
    p3.tarjeta(856, 84, 400, 88, "Ratio de mora")
    p3.grafico(
        "clusteredBarChart",
        24,
        184,
        400,
        488,
        "Mora por tiempo de atraso",
        col("Cartera", "tramo_atraso"),
        [med("Cartera en mora")],
        None,
        SIN_AL_DIA,
        ROJO,
        True,
    )
    p3.grafico(
        "clusteredColumnChart",
        436,
        184,
        400,
        488,
        "Mora por plazo del préstamo",
        col("Prestamo", "plazo"),
        [med("Cartera en mora")],
        (col("Prestamo", "plazo"), "Ascending"),
        None,
        MARINO,
        True,
    )
    p3.grafico(
        "clusteredBarChart",
        848,
        184,
        408,
        488,
        "Distritos con más cartera en mora",
        col("Distrito", "distrito"),
        [med("Cartera en mora")],
        (med("Cartera en mora"), "Descending"),
        None,
        ROJO,
    )

    p4 = Pagina(
        "clientes",
        "Clientes y distritos",
        "Moravia concentra más cuentas, y Praga más saldo por cliente.",
        4,
    )
    p4.segmentador(1016, 12, 240, 62, col("Distrito", "region"), "Región")
    p4.tarjeta(24, 84, 400, 88, "Clientes")
    p4.tarjeta(440, 84, 400, 88, "Saldo por cliente")
    p4.tarjeta(856, 84, 400, 88, "Cuentas con tarjeta")
    p4.grafico(
        "clusteredBarChart",
        24,
        184,
        400,
        488,
        "Depósitos por región",
        col("Distrito", "region"),
        [med("Depósitos")],
        (med("Depósitos"), "Descending"),
        None,
        MARINO,
    )
    p4.grafico(
        "clusteredColumnChart",
        436,
        184,
        400,
        488,
        "Clientes por edad",
        col("Cliente", "rango_edad"),
        [med("Clientes")],
        None,
        None,
        ACENTO,
        True,
    )
    p4.tabla(
        848,
        184,
        408,
        488,
        "Detalle por distrito",
        [col("Distrito", "distrito"), med("Clientes"), med("Depósitos"), med("Saldo por cliente")],
        (med("Depósitos"), "Descending"),
    )

    p5 = Pagina(
        "cobranzas",
        "Cobranzas",
        "Lo que el equipo registró en la app. Los datos entran al almacén en la carga siguiente.",
        5,
    )
    p5.tarjeta(24, 84, 298, 88, "Gestiones realizadas")
    p5.tarjeta(334, 84, 298, 88, "Cobertura de gestión", "Préstamos en mora gestionados")
    p5.tarjeta(644, 84, 298, 88, "Monto prometido")
    p5.tarjeta(954, 84, 302, 88, "Compromisos vencidos")
    p5.grafico(
        "clusteredBarChart",
        24,
        184,
        400,
        488,
        "Gestiones por resultado",
        col("Gestiones", "resultado"),
        [med("Gestiones realizadas")],
        None,
        None,
        ACENTO,
        True,
    )
    p5.tabla(
        436,
        184,
        820,
        488,
        "Préstamos en mora por gestionar",
        [
            col("Prestamo", "prestamo_id"),
            col("Distrito", "distrito"),
            med("Cuotas atrasadas"),
            med("Capital en mora"),
            med("Gestiones por préstamo"),
        ],
        (med("Capital en mora"), "Descending"),
    )

    p6 = Pagina(
        "calidad",
        "Calidad de datos",
        "Cada fila recibida queda cargada o en cuarentena con su motivo. Solo se cuentan las cargas diarias.",
        6,
    )
    p6.tarjeta(24, 84, 298, 88, "Último lote", "Último lote cargado")
    p6.tarjeta(334, 84, 298, 88, "Filas recibidas")
    p6.tarjeta(644, 84, 298, 88, "Filas en cuarentena")
    p6.tarjeta(954, 84, 302, 88, "Tasa de cuarentena")
    p6.tabla(
        24,
        184,
        740,
        488,
        "Lotes diarios",
        [
            col("Lotes", "fecha_negocio"),
            col("Lotes", "estado"),
            col("Lotes", "filas_recibidas"),
            col("Lotes", "filas_cargadas"),
            col("Lotes", "filas_cuarentena"),
            col("Lotes", "tasa_cuarentena"),
        ],
        (col("Lotes", "fecha_negocio"), "Descending"),
        SOLO_DIARIOS,
    )
    p6.grafico(
        "clusteredBarChart",
        776,
        184,
        480,
        488,
        "Filas apartadas por motivo",
        col("Cuarentena", "descripcion"),
        [med("Filas apartadas")],
        (med("Filas apartadas"), "Descending"),
        None,
        ROJO,
        True,
    )
    return [p1, p2, p3, p4, p5, p6]


TEMA = {
    "name": NOMBRE,
    "dataColors": [MARINO, ACENTO, "#7A8CA5", "#E0A030", ROJO, "#4F6D9A", "#9DB4C0", GRIS],
    "foreground": MARINO,
    "background": "#FFFFFF",
    "tableAccent": MARINO,
    "good": ACENTO,
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
        p.encabezado()
        p.navegador()
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
    for carpeta in (RAIZ / f"{NOMBRE}.Report", RAIZ / f"{NOMBRE}.SemanticModel"):
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

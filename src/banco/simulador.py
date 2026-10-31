"""Publica los datos de Berka como si fueran archivos del core bancario.

El histórico llega de una vez. Después de la fecha de corte, cada día hábil genera una carpeta
con sus archivos y un control de totales. La generación es determinista: la misma fecha siempre
produce los mismos archivos, aunque se ejecute en otra máquina.
"""

import json
import random
import shutil
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from banco import berka
from banco.config import DIR_BERKA, DIR_LANDING, FECHA_CORTE, FECHA_FIN

PROB_DUPLICADO = 0.005
PROB_MONTO_NULO = 0.001
PROB_FECHA_INVALIDA = 0.001
PROB_CUENTA_INEXISTENTE = 0.001
PROB_ATRASADO = 0.005
CAMBIOS_CLIENTE_POR_DIA = 3
CAMBIOS_CUENTA_POR_DIA = 1
CUENTA_INEXISTENTE = "999999"
FECHA_INVALIDA = "20269999"


def es_dia_habil(fecha: date) -> bool:
    return fecha.weekday() < 5


def dia_habil_anterior(fecha: date) -> date:
    actual = fecha - timedelta(days=1)
    while not es_dia_habil(actual):
        actual -= timedelta(days=1)
    return actual


def dia_habil_siguiente(fecha: date) -> date:
    actual = fecha + timedelta(days=1)
    while not es_dia_habil(actual):
        actual += timedelta(days=1)
    return actual


def se_atrasa(trans_id: str) -> bool:
    """Decide si un movimiento llega un día hábil después de lo que le corresponde."""
    return random.Random(f"atraso:{trans_id}").random() < PROB_ATRASADO


def _fecha_iso(serie: pd.Series) -> pd.Series:
    return serie.map(lambda v: berka.fecha_negocio(v).strftime("%Y%m%d"))


def _preparar_trans(trans: pd.DataFrame) -> pd.DataFrame:
    salida = pd.DataFrame(
        {
            "trans_id": trans["trans_id"],
            "cuenta_id": trans["account_id"],
            "fecha": _fecha_iso(trans["date"]),
            "tipo": trans["type"],
            "operacion": trans["operation"].str.strip(),
            "monto": trans["amount"],
            "saldo": trans["balance"],
            "categoria": trans["k_symbol"].str.strip(),
            "banco_contraparte": trans["bank"].str.strip(),
            "cuenta_contraparte": trans["account"].str.strip(),
        }
    )
    return salida.sort_values(["fecha", "trans_id"], kind="stable").reset_index(drop=True)


def _preparar_prestamos(loan: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "prestamo_id": loan["loan_id"],
            "cuenta_id": loan["account_id"],
            "fecha": _fecha_iso(loan["date"]),
            "monto": loan["amount"],
            "plazo_meses": loan["duration"],
            "cuota": loan["payments"],
            "estado": loan["status"],
        }
    )


def _preparar_tarjetas(card: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "tarjeta_id": card["card_id"],
            "disp_id": card["disp_id"],
            "tipo": card["type"],
            "fecha_emision": _fecha_iso(card["issued"]),
        }
    )


def _preparar_cuentas(account: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cuenta_id": account["account_id"],
            "distrito_id": account["district_id"],
            "frecuencia": account["frequency"],
            "fecha_apertura": _fecha_iso(account["date"]),
        }
    )


def _preparar_clientes(client: pd.DataFrame) -> pd.DataFrame:
    nacimiento = client["birth_number"].map(berka.decodificar_nacimiento)
    return pd.DataFrame(
        {
            "cliente_id": client["client_id"],
            "fecha_nacimiento": nacimiento.map(
                lambda n: berka.desplazar(n[0]).strftime("%Y%m%d")
            ),
            "sexo": nacimiento.map(lambda n: n[1]),
            "distrito_id": client["district_id"],
        }
    )


def _preparar_disp(disp: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "disp_id": disp["disp_id"],
            "cliente_id": disp["client_id"],
            "cuenta_id": disp["account_id"],
            "tipo": disp["type"],
        }
    )


def _preparar_distritos(district: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "distrito_id": district["A1"],
            "nombre": district["A2"],
            "region": district["A3"],
            "habitantes": district["A4"],
            "poblacion_urbana_pct": district["A10"],
            "salario_promedio": district["A11"],
            "desempleo_95": district["A12"],
            "desempleo_96": district["A13"],
            "delitos_95": district["A15"],
            "delitos_96": district["A16"],
        }
    )


def _guardar(tabla: pd.DataFrame, carpeta: Path, nombre: str, control: dict) -> None:
    tabla.to_csv(carpeta / f"{nombre}.csv", sep=";", index=False, encoding="utf-8")
    entrada = {"filas": len(tabla)}
    columna = "monto" if "monto" in tabla.columns else None
    if columna:
        entrada["suma_monto"] = round(float(pd.to_numeric(tabla[columna], errors="coerce").sum()), 2)
    control[nombre] = entrada


def _guardar_control(carpeta: Path, tipo: str, fecha: date, archivos: dict) -> None:
    control = {"tipo": tipo, "fecha_negocio": fecha.isoformat(), "archivos": archivos}
    (carpeta / "control.json").write_text(json.dumps(control, indent=2), encoding="utf-8")


def generar_historico(
    destino: Path = DIR_LANDING, origen: Path = DIR_BERKA, corte: date = FECHA_CORTE
) -> Path:
    """Escribe los maestros y todo lo ocurrido hasta la fecha de corte."""
    carpeta = destino / "historico"
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    corte_txt = corte.strftime("%Y%m%d")
    control: dict = {}

    _guardar(_preparar_distritos(berka.leer("district", origen)), carpeta, "distrito", control)
    _guardar(_preparar_clientes(berka.leer("client", origen)), carpeta, "cliente", control)
    _guardar(_preparar_cuentas(berka.leer("account", origen)), carpeta, "cuenta", control)
    _guardar(_preparar_disp(berka.leer("disp", origen)), carpeta, "disp", control)

    trans = _preparar_trans(berka.leer("trans", origen))
    _guardar(trans[trans["fecha"] <= corte_txt], carpeta, "trans", control)
    prestamos = _preparar_prestamos(berka.leer("loan", origen))
    _guardar(prestamos[prestamos["fecha"] <= corte_txt], carpeta, "prestamo", control)
    tarjetas = _preparar_tarjetas(berka.leer("card", origen))
    _guardar(tarjetas[tarjetas["fecha_emision"] <= corte_txt], carpeta, "tarjeta", control)

    _guardar_control(carpeta, "HISTORICO", corte, control)
    return carpeta


def _ventana(fecha: date) -> tuple[str, str]:
    """Rango de fechas que cubre un día hábil: desde el día hábil anterior, sin incluirlo."""
    anterior = dia_habil_anterior(fecha)
    return anterior.strftime("%Y%m%d"), fecha.strftime("%Y%m%d")


def _movimientos_del_dia(trans: pd.DataFrame, fecha: date) -> pd.DataFrame:
    """Movimientos que llegan en el archivo de una fecha, incluidos los atrasados."""
    desde, hasta = _ventana(fecha)
    propios = trans[(trans["fecha"] > desde) & (trans["fecha"] <= hasta)]
    propios = propios[~propios["trans_id"].map(se_atrasa)]

    desde_previo, hasta_previo = _ventana(dia_habil_anterior(fecha))
    inicio_previo = max(desde_previo, FECHA_CORTE.strftime("%Y%m%d"))
    previos = trans[(trans["fecha"] > inicio_previo) & (trans["fecha"] <= hasta_previo)]
    atrasados = previos[previos["trans_id"].map(se_atrasa)]
    return pd.concat([propios, atrasados], ignore_index=True)


def _inyectar_errores(tabla: pd.DataFrame, fecha: date) -> pd.DataFrame:
    """Agrega problemas de calidad reproducibles para probar los controles."""
    azar = random.Random(f"errores:{fecha.isoformat()}")
    filas = tabla.to_dict("records")
    salida = []
    for fila in filas:
        sorteo = azar.random()
        if sorteo < PROB_MONTO_NULO:
            fila = {**fila, "monto": ""}
        elif sorteo < PROB_MONTO_NULO + PROB_FECHA_INVALIDA:
            fila = {**fila, "fecha": FECHA_INVALIDA}
        elif sorteo < PROB_MONTO_NULO + PROB_FECHA_INVALIDA + PROB_CUENTA_INEXISTENTE:
            fila = {**fila, "cuenta_id": CUENTA_INEXISTENTE}
        salida.append(fila)
        if azar.random() < PROB_DUPLICADO:
            salida.append(dict(fila))
    return pd.DataFrame(salida, columns=tabla.columns)


def _correcciones(trans: pd.DataFrame, fecha: date) -> pd.DataFrame:
    """Reenvía corregidas las filas que el día hábil anterior llegaron dañadas."""
    anterior = dia_habil_anterior(fecha)
    if anterior <= FECHA_CORTE:
        return trans.iloc[0:0]
    enviadas = _inyectar_errores(_movimientos_del_dia(trans, anterior), anterior)
    danadas = enviadas[
        (enviadas["monto"] == "")
        | (enviadas["fecha"] == FECHA_INVALIDA)
        | (enviadas["cuenta_id"] == CUENTA_INEXISTENTE)
    ]
    return trans[trans["trans_id"].isin(set(danadas["trans_id"]))]


def _cambios_maestros(clientes, cuentas, distritos, fecha: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    azar = random.Random(f"cambios:{fecha.isoformat()}")
    cambios_cliente = [
        {"cliente_id": cliente, "distrito_id": azar.choice(distritos)}
        for cliente in azar.sample(clientes, CAMBIOS_CLIENTE_POR_DIA)
    ]
    frecuencias = ["POPLATEK MESICNE", "POPLATEK TYDNE", "POPLATEK PO OBRATU"]
    cambios_cuenta = [
        {"cuenta_id": cuenta, "frecuencia": azar.choice(frecuencias)}
        for cuenta in azar.sample(cuentas, CAMBIOS_CUENTA_POR_DIA)
    ]
    return (
        pd.DataFrame(cambios_cliente, columns=["cliente_id", "distrito_id"]),
        pd.DataFrame(cambios_cuenta, columns=["cuenta_id", "frecuencia"]),
    )


def generar_dia(fecha: date, destino: Path = DIR_LANDING, origen: Path = DIR_BERKA) -> Path:
    """Escribe los archivos de un día hábil posterior al corte."""
    if not es_dia_habil(fecha):
        raise ValueError(f"{fecha} no es día hábil")
    if not FECHA_CORTE < fecha <= FECHA_FIN:
        raise ValueError(f"{fecha} está fuera del periodo simulado")

    carpeta = destino / fecha.strftime("%Y%m%d")
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    desde, hasta = _ventana(fecha)
    control: dict = {}

    trans = _preparar_trans(berka.leer("trans", origen))
    del_dia = _inyectar_errores(_movimientos_del_dia(trans, fecha), fecha)
    _guardar(pd.concat([del_dia, _correcciones(trans, fecha)]), carpeta, "trans", control)

    prestamos = _preparar_prestamos(berka.leer("loan", origen))
    del_dia = (prestamos["fecha"] > desde) & (prestamos["fecha"] <= hasta)
    _guardar(prestamos[del_dia], carpeta, "prestamo", control)

    tarjetas = _preparar_tarjetas(berka.leer("card", origen))
    del_dia = (tarjetas["fecha_emision"] > desde) & (tarjetas["fecha_emision"] <= hasta)
    _guardar(tarjetas[del_dia], carpeta, "tarjeta", control)

    cambios_cliente, cambios_cuenta = _cambios_maestros(
        sorted(berka.leer("client", origen)["client_id"]),
        sorted(berka.leer("account", origen)["account_id"]),
        sorted(berka.leer("district", origen)["A1"]),
        fecha,
    )
    _guardar(cambios_cliente, carpeta, "cambio_cliente", control)
    _guardar(cambios_cuenta, carpeta, "cambio_cuenta", control)

    _guardar_control(carpeta, "DIARIO", fecha, control)
    return carpeta

"""Carga un lote completo: archivos, validación, almacén, fotos y conciliación.

Uso:
    python -m banco.etl preparar
    python -m banco.etl historico
    python -m banco.etl siguiente
    python -m banco.etl dia --fecha 2026-07-01
"""

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyodbc

from banco import db, simulador
from banco.config import DIR_LANDING, FECHA_CORTE, FECHA_FIN

TAMANO_TANDA = 20_000
MAX_TASA_CUARENTENA = 0.05
ARCHIVOS_HISTORICO = ("distrito", "cliente", "cuenta", "disp", "trans", "prestamo", "tarjeta")
ARCHIVOS_DIARIO = ("trans", "prestamo", "tarjeta", "cambio_cliente", "cambio_cuenta")
TABLAS_STG = (
    "distrito", "cliente", "cuenta", "disp", "trans", "prestamo", "tarjeta",
    "cambio_cliente", "cambio_cuenta",
)


def _avance(mensaje: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {mensaje}", flush=True)


class ErrorConciliacion(Exception):
    """Los totales no cuadran o se rechazaron demasiadas filas."""


def _abrir_lote(cx: pyodbc.Connection, fecha: date, tipo: str) -> int:
    return cx.execute(
        "INSERT ctl.lote (fecha_negocio, tipo, estado) OUTPUT INSERTED.lote_id "
        "VALUES (?, ?, 'EN_PROCESO')",
        fecha,
        tipo,
    ).fetchval()


def _lote_terminado(cx: pyodbc.Connection, fecha: date, tipo: str) -> bool:
    fila = cx.execute(
        "SELECT 1 FROM ctl.lote WHERE fecha_negocio = ? AND tipo = ? AND estado = 'OK'", fecha, tipo
    ).fetchone()
    return fila is not None


def _vaciar_stg(cx: pyodbc.Connection) -> None:
    for tabla in TABLAS_STG:
        cx.execute(f"TRUNCATE TABLE stg.{tabla}")


def _cargar_archivo(cx: pyodbc.Connection, carpeta: Path, nombre: str) -> None:
    tabla = pd.read_csv(
        carpeta / f"{nombre}.csv", sep=";", dtype=str, keep_default_na=False, encoding="utf-8"
    )
    if tabla.empty:
        return
    columnas = ", ".join(tabla.columns)
    marcas = ", ".join("?" * len(tabla.columns))
    filas = list(tabla.itertuples(index=False, name=None))
    cursor = cx.cursor()
    cursor.fast_executemany = True
    # Confirmar por tandas evita escribir el registro de transacciones por cada fila.
    cx.autocommit = False
    try:
        for inicio in range(0, len(filas), TAMANO_TANDA):
            cursor.executemany(
                f"INSERT stg.{nombre} ({columnas}) VALUES ({marcas})",
                filas[inicio : inicio + TAMANO_TANDA],
            )
            cx.commit()
    finally:
        cx.autocommit = True
    _avance(f"stg.{nombre}: {len(filas)} filas")


def _conciliar_recepcion(cx: pyodbc.Connection, lote_id: int, control: dict) -> None:
    """Compara lo recibido en stg con el archivo de control."""
    for nombre, esperado in control["archivos"].items():
        suma_esperada = esperado.get("suma_monto")
        expresion = "SUM(TRY_CONVERT(DECIMAL(18, 2), monto))" if suma_esperada is not None else "NULL"
        filas, suma = cx.execute(f"SELECT COUNT(*), {expresion} FROM stg.{nombre}").fetchone()
        cx.execute(
            "INSERT ctl.conciliacion (lote_id, archivo, filas_control, filas_stg, suma_control, suma_stg) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            lote_id, nombre, esperado["filas"], filas, suma_esperada, suma,
        )
        if filas != esperado["filas"]:
            raise ErrorConciliacion(f"{nombre}: {filas} filas, el control dice {esperado['filas']}")
        if suma_esperada is not None and abs(float(suma or 0) - suma_esperada) > 0.01:
            raise ErrorConciliacion(f"{nombre}: suma {suma}, el control dice {suma_esperada}")


def _conciliar_carga(cx: pyodbc.Connection, lote_id: int) -> tuple[int, int, int]:
    """Toda fila recibida debe estar cargada o en cuarentena."""
    recibidas = cx.execute("SELECT COUNT(*) FROM stg.trans").fetchval()
    cargadas = cx.execute(
        "SELECT COUNT(*) FROM dw.fact_transaccion WHERE lote_id = ?", lote_id
    ).fetchval()
    apartadas = cx.execute(
        "SELECT COUNT(*) FROM ctl.cuarentena WHERE lote_id = ? AND archivo = 'trans'", lote_id
    ).fetchval()
    if recibidas != cargadas + apartadas:
        raise ErrorConciliacion(
            f"trans: recibidas {recibidas}, cargadas {cargadas}, en cuarentena {apartadas}"
        )
    if recibidas and apartadas / recibidas > MAX_TASA_CUARENTENA:
        raise ErrorConciliacion(f"trans: {apartadas} de {recibidas} filas fueron rechazadas")
    return recibidas, cargadas, apartadas


def _meses_del_historico(cx: pyodbc.Connection, corte: date) -> list[date]:
    primero = cx.execute("SELECT MIN(fecha_apertura) FROM dw.dim_cuenta").fetchval()
    meses = pd.date_range(primero.replace(day=1), corte, freq="ME")
    return [m.date() for m in meses]


def _cerrar_lote(cx, lote_id: int, recibidas: int, cargadas: int, apartadas: int) -> None:
    cx.execute(
        "UPDATE ctl.lote SET estado = 'OK', fin = SYSUTCDATETIME(), filas_recibidas = ?, "
        "filas_cargadas = ?, filas_cuarentena = ? WHERE lote_id = ?",
        recibidas, cargadas, apartadas, lote_id,
    )


def _marcar_error(cx, lote_id: int, error: Exception) -> None:
    try:
        cx.execute(
            "UPDATE ctl.lote SET estado = 'ERROR', fin = SYSUTCDATETIME(), mensaje = ? "
            "WHERE lote_id = ?",
            str(error)[:4000], lote_id,
        )
    except pyodbc.Error:
        _avance(f"No se pudo marcar el lote {lote_id}: se perdió la conexión")


def _ejecutar(cx: pyodbc.Connection, carpeta: Path, nombres: tuple[str, ...], tipo: str) -> dict:
    control = json.loads((carpeta / "control.json").read_text(encoding="utf-8"))
    fecha = date.fromisoformat(control["fecha_negocio"])
    if _lote_terminado(cx, fecha, tipo):
        return {"fecha": fecha, "omitido": True}

    lote_id = _abrir_lote(cx, fecha, tipo)
    try:
        _vaciar_stg(cx)
        for nombre in nombres:
            _cargar_archivo(cx, carpeta, nombre)
        _conciliar_recepcion(cx, lote_id, control)

        # El almacén cambia dentro de una sola transacción: o entra todo el lote, o nada.
        cx.autocommit = False
        try:
            cx.execute("EXEC dw.usp_cargar_maestros")
            _avance("Maestros cargados")
            cx.execute("EXEC ctl.usp_validar_lote @lote_id = ?", lote_id)
            _avance("Lote validado")
            cx.execute("EXEC dw.usp_cargar_dimensiones @fecha_negocio = ?", fecha)
            cx.execute("EXEC dw.usp_cargar_hechos @lote_id = ?", lote_id)
            _avance("Hechos cargados")
            recibidas, cargadas, apartadas = _conciliar_carga(cx, lote_id)
            cx.commit()
        except Exception:
            cx.rollback()
            raise
        finally:
            cx.autocommit = True

        if tipo == "HISTORICO":
            for mes in _meses_del_historico(cx, fecha):
                cx.execute("EXEC dw.usp_cargar_fotos @corte = ?", mes)
                _avance(f"Foto de {mes:%Y-%m}")
        else:
            # Un movimiento atrasado puede cambiar el cierre del mes anterior.
            if simulador.dia_habil_anterior(fecha).month != fecha.month:
                anterior = simulador.dia_habil_anterior(fecha)
                cierre = pd.Timestamp(anterior).to_period("M").end_time.date()
                cx.execute("EXEC dw.usp_cargar_fotos @corte = ?", cierre)
            cx.execute("EXEC dw.usp_cargar_fotos @corte = ?", fecha)

        _cerrar_lote(cx, lote_id, recibidas, cargadas, apartadas)
        return {
            "fecha": fecha, "lote_id": lote_id, "omitido": False,
            "recibidas": recibidas, "cargadas": cargadas, "cuarentena": apartadas,
        }
    except Exception as error:
        _marcar_error(cx, lote_id, error)
        raise


def preparar() -> None:
    db.crear_base()
    with db.conectar() as cx:
        db.aplicar_scripts(cx)


def cargar_historico(cx: pyodbc.Connection, destino: Path = DIR_LANDING) -> dict:
    return _ejecutar(cx, simulador.generar_historico(destino), ARCHIVOS_HISTORICO, "HISTORICO")


def cargar_dia(cx: pyodbc.Connection, fecha: date, destino: Path = DIR_LANDING) -> dict:
    return _ejecutar(cx, simulador.generar_dia(fecha, destino), ARCHIVOS_DIARIO, "DIARIO")


def siguiente_fecha(cx: pyodbc.Connection) -> date | None:
    """Próximo día hábil por procesar, o None si la simulación terminó."""
    ultima = cx.execute(
        "SELECT MAX(fecha_negocio) FROM ctl.lote WHERE estado = 'OK' AND tipo = 'DIARIO'"
    ).fetchval()
    siguiente = simulador.dia_habil_siguiente(ultima or FECHA_CORTE)
    return siguiente if siguiente <= FECHA_FIN else None


def _publicar_resultado(resultado: dict) -> None:
    """Deja el resultado disponible para el aviso del workflow."""
    salida = os.getenv("GITHUB_OUTPUT")
    if not salida:
        return
    with open(salida, "a", encoding="utf-8") as archivo:
        archivo.write(f"fecha_negocio={resultado['fecha']}\n")
        archivo.write(f"filas_cargadas={resultado.get('cargadas', 0)}\n")
        archivo.write(f"filas_cuarentena={resultado.get('cuarentena', 0)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=["preparar", "historico", "siguiente", "dia"])
    parser.add_argument("--fecha", type=date.fromisoformat)
    args = parser.parse_args()

    if args.accion == "preparar":
        preparar()
        print("Base y objetos listos")
        return

    with db.conectar() as cx:
        if args.accion == "historico":
            print(cargar_historico(cx))
        elif args.accion == "dia":
            print(cargar_dia(cx, args.fecha))
        else:
            fecha = siguiente_fecha(cx)
            if fecha is None:
                print("La simulación ya terminó")
                return
            resultado = cargar_dia(cx, fecha)
            _publicar_resultado(resultado)
            print(resultado)


if __name__ == "__main__":
    main()

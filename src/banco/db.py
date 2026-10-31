"""Conexión a SQL Server y despliegue de los scripts."""

import re
import time
from pathlib import Path

import pyodbc

from banco.config import DIR_SQL, ConexionSql, conexion_sql

CARPETAS_EN_ORDEN = ("ddl", "proc", "vistas", "datos")
SEPARADOR_GO = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)
INTENTOS_AZURE = 6
ESPERA_AZURE_SEGUNDOS = 20


def conectar(config: ConexionSql | None = None, base: str | None = None) -> pyodbc.Connection:
    """Conecta y, en Azure, espera a que la base salga de la pausa."""
    config = config or conexion_sql()
    intentos = INTENTOS_AZURE if config.autenticacion == "sql" else 1
    for intento in range(1, intentos + 1):
        try:
            return pyodbc.connect(config.cadena(base), autocommit=True, timeout=30)
        except pyodbc.Error:
            if intento == intentos:
                raise
            time.sleep(ESPERA_AZURE_SEGUNDOS)
    raise RuntimeError("Sin intentos de conexión")


def crear_base(config: ConexionSql | None = None) -> None:
    """Crea la base local si no existe. En Azure la base se crea aparte, con la oferta gratuita."""
    config = config or conexion_sql()
    if config.servidor.endswith(".database.windows.net"):
        return
    with conectar(config, "master") as cx:
        if cx.execute("SELECT DB_ID(?)", config.base).fetchval() is None:
            cx.execute(f"CREATE DATABASE [{config.base}]")


def bloques(script: str) -> list[str]:
    return [b.strip() for b in SEPARADOR_GO.split(script) if b.strip()]


def aplicar_scripts(cx: pyodbc.Connection, raiz: Path = DIR_SQL) -> None:
    """Ejecuta los scripts en orden. Todos se pueden repetir sin perder datos."""
    for carpeta in CARPETAS_EN_ORDEN:
        for archivo in sorted((raiz / carpeta).glob("*.sql")):
            for bloque in bloques(archivo.read_text(encoding="utf-8")):
                cx.execute(bloque)

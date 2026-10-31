"""Conexión a SQL Server y despliegue de los scripts."""

import re
from pathlib import Path

import pyodbc

from banco.config import DIR_SQL, ConexionSql, conexion_sql

CARPETAS_EN_ORDEN = ("ddl", "proc", "vistas", "datos")
SEPARADOR_GO = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)


def conectar(config: ConexionSql | None = None, base: str | None = None) -> pyodbc.Connection:
    config = config or conexion_sql()
    return pyodbc.connect(config.cadena(base), autocommit=True)


def crear_base(config: ConexionSql | None = None) -> None:
    """Crea la base local si no existe. En Azure la base se crea aparte, con la oferta gratuita."""
    config = config or conexion_sql()
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

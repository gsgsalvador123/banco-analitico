"""Lectura de los archivos originales de Berka."""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from banco.config import DESPLAZAMIENTO_DIAS, DIR_BERKA


def leer(nombre: str, directorio: Path = DIR_BERKA) -> pd.DataFrame:
    """Lee un archivo .asc como texto, sin interpretar ningún valor."""
    return pd.read_csv(
        directorio / f"{nombre}.asc",
        sep=";",
        dtype=str,
        keep_default_na=False,
        encoding="latin-1",
    )


def fecha_berka(valor: str) -> date:
    """Convierte AAMMDD, con o sin hora, en una fecha del siglo XX."""
    texto = valor.strip()[:6]
    return date(1900 + int(texto[:2]), int(texto[2:4]), int(texto[4:6]))


def desplazar(fecha: date) -> date:
    return fecha + timedelta(days=DESPLAZAMIENTO_DIAS)


def fecha_negocio(valor: str) -> date:
    """Convierte una fecha de Berka en la fecha que usa el banco simulado."""
    return desplazar(fecha_berka(valor))


def decodificar_nacimiento(birth_number: str) -> tuple[date, str]:
    """Separa fecha de nacimiento y sexo de birth_number."""
    texto = birth_number.strip()
    mes = int(texto[2:4])
    sexo = "M" if mes > 50 else "H"
    if mes > 50:
        mes -= 50
    return date(1900 + int(texto[:2]), mes, int(texto[4:6])), sexo

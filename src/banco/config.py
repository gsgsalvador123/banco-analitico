"""Rutas, fechas y conexión del proyecto."""

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
DIR_BERKA = RAIZ / "data" / "raw" / "berka"
DIR_LANDING = RAIZ / "data" / "landing"
DIR_SQL = RAIZ / "sql"

# 28 años exactos son 1461 semanas, así que se conservan el calendario y el día de la semana.
DESPLAZAMIENTO_DIAS = 10_227

# Fechas ya desplazadas: hasta el corte se carga de golpe y después llega un archivo diario.
FECHA_CORTE = date(2026, 6, 30)
FECHA_FIN = date(2026, 12, 31)

load_dotenv(RAIZ / ".env")


@dataclass(frozen=True)
class ConexionSql:
    servidor: str
    base: str
    driver: str
    autenticacion: str
    usuario: str
    clave: str
    confiar_certificado: bool = False

    def cadena(self, base: str | None = None) -> str:
        partes = [
            f"DRIVER={{{self.driver}}}",
            f"SERVER={self.servidor}",
            f"DATABASE={base or self.base}",
        ]
        if self.autenticacion == "sql":
            partes += [f"UID={self.usuario}", f"PWD={self.clave}", "Encrypt=yes"]
            if self.confiar_certificado:
                partes.append("TrustServerCertificate=yes")
        else:
            # LocalDB solo acepta conexiones locales y no admite cifrado.
            partes += ["Trusted_Connection=yes", "Encrypt=no"]
        return ";".join(partes)


def conexion_sql() -> ConexionSql:
    return ConexionSql(
        servidor=os.getenv("BA_SQL_SERVER", r"(localdb)\MSSQLLocalDB"),
        base=os.getenv("BA_SQL_DATABASE", "BancoAnalitico"),
        driver=os.getenv("BA_SQL_DRIVER", "ODBC Driver 17 for SQL Server"),
        autenticacion=os.getenv("BA_SQL_AUTH", "windows"),
        usuario=os.getenv("BA_SQL_USER", ""),
        clave=os.getenv("BA_SQL_PASSWORD", ""),
        # Solo para el contenedor de pruebas, que usa un certificado autofirmado.
        confiar_certificado=os.getenv("BA_SQL_CONFIAR_CERTIFICADO") == "si",
    )

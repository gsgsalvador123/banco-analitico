"""Crea en Azure SQL los usuarios del proyecto, cada uno con el mínimo permiso necesario.

Las claves se leen de BA_CLAVE_ETL, BA_CLAVE_BI y BA_CLAVE_APP.
"""

import os

from banco import db

PERMISOS = {
    "etl_user": (
        "BA_CLAVE_ETL",
        [
            "GRANT SELECT, INSERT, ALTER ON SCHEMA::stg TO etl_user",
            "GRANT SELECT ON SCHEMA::dw TO etl_user",
            "GRANT SELECT, INSERT, UPDATE ON SCHEMA::ctl TO etl_user",
            "GRANT EXECUTE ON SCHEMA::dw TO etl_user",
            "GRANT EXECUTE ON SCHEMA::ctl TO etl_user",
        ],
    ),
    "bi_reader": ("BA_CLAVE_BI", ["GRANT SELECT ON SCHEMA::mart TO bi_reader"]),
    "app_cobranzas": (
        "BA_CLAVE_APP",
        [
            "GRANT SELECT ON mart.vw_bandeja_cobranza TO app_cobranzas",
            "GRANT SELECT, INSERT ON ops.gestion_cobranza TO app_cobranzas",
        ],
    ),
}


def crear_usuarios() -> None:
    with db.conectar() as cx:
        for usuario, (variable, permisos) in PERMISOS.items():
            clave = os.environ[variable].replace("'", "''")
            if cx.execute("SELECT USER_ID(?)", usuario).fetchval() is None:
                cx.execute(f"CREATE USER [{usuario}] WITH PASSWORD = '{clave}'")
            for permiso in permisos:
                cx.execute(permiso)


if __name__ == "__main__":
    crear_usuarios()
    print("Usuarios listos")

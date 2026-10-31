"""Descarga Berka del Internet Archive y comprueba que sea el archivo original."""

import hashlib
import io
import time
import urllib.request
import zipfile
from pathlib import Path

from banco.config import DIR_BERKA

URL_BERKA = (
    "https://web.archive.org/web/20220616072552id_/"
    "https://sorry.vse.cz/~berka/challenge/pkdd1999/data_berka.zip"
)
SHA256_BERKA = "affa4477572e9d8f2de6beff8a525d37c056d5d8e4a9670dd8c7636208c002ce"
INTENTOS = 5
ESPERA_SEGUNDOS = 30


def _bajar() -> bytes:
    pedido = urllib.request.Request(URL_BERKA, headers={"User-Agent": "banco-analitico"})
    for intento in range(1, INTENTOS + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=180) as respuesta:
                return respuesta.read()
        except OSError:
            if intento == INTENTOS:
                raise
            time.sleep(ESPERA_SEGUNDOS)
    raise RuntimeError("Sin intentos de descarga")


def descargar(destino: Path = DIR_BERKA) -> None:
    if (destino / "trans.asc").exists():
        return
    contenido = _bajar()
    huella = hashlib.sha256(contenido).hexdigest()
    if huella != SHA256_BERKA:
        raise ValueError(f"El archivo descargado no es el original: {huella}")
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(contenido)) as comprimido:
        for miembro in comprimido.namelist():
            if miembro.endswith(".asc"):
                (destino / Path(miembro).name).write_bytes(comprimido.read(miembro))


if __name__ == "__main__":
    descargar()
    print("Berka listo")

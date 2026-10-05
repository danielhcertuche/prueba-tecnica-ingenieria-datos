"""Extracción: lee cada hoja tal cual y valida que el layout siga siendo el esperado.

La hoja tiene dos filas de encabezado: la primera con el título de cada bloque
(EVAPORACIÓN, EVAPOTRANSPIRACIÓN POTENCIAL...) y la segunda con ENE..DIC y ANUAL. Debajo de
los datos viene la leyenda de categorías, que no son estaciones.

La salida es la capa raw: una fila por fila de Excel, con todos los valores como
texto. No se tipa nada aquí; si un valor no se puede convertir, se ve en calidad.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from etl_clima.config import (
    ALIAS_ENCABEZADO,
    COLUMNAS_ESTACION,
    ENCABEZADOS_ANUAL,
    MESES,
    Hoja,
)

FILAS_ENCABEZADO = 2


class LayoutInesperado(Exception):
    """El archivo no tiene la estructura que el pipeline sabe leer."""


@dataclass
class HojaExtraida:
    hoja: Hoja
    datos: pd.DataFrame  # capa raw, todo como texto
    filas_descartadas: int  # leyenda y filas vacías debajo de los datos


def normalizar_texto(valor: object) -> str:
    """'E V A P O R A C I O N (mm)' -> 'EVAPORACION'."""
    texto = str(valor).split("(")[0]
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(texto.split()).upper()


def hash_archivo(ruta: Path) -> str:
    sha = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            sha.update(bloque)
    return sha.hexdigest()


def _ubicar_bloques(titulos: pd.Series, hoja: Hoja) -> dict[str, int]:
    """Devuelve la columna donde arranca cada variable configurada."""
    por_titulo = {v.titulo_fuente: v.codigo for v in hoja.variables}
    inicio = {}
    for col, titulo in titulos.items():
        if col < len(COLUMNAS_ESTACION) or pd.isna(titulo):
            continue
        clave = normalizar_texto(titulo)
        if clave in por_titulo:
            inicio[por_titulo[clave]] = col
    faltantes = set(por_titulo.values()) - set(inicio)
    if faltantes:
        raise LayoutInesperado(f"Hoja {hoja.nombre}: no se encontraron los bloques {sorted(faltantes)}")
    return inicio


def _validar_encabezados(fila: pd.Series, inicio: dict[str, int], hoja: Hoja) -> None:
    esperado_estacion = list(COLUMNAS_ESTACION)
    encontrado = [ALIAS_ENCABEZADO.get(normalizar_texto(v), normalizar_texto(v)) for v in fila.iloc[:8]]
    if encontrado != esperado_estacion:
        raise LayoutInesperado(f"Hoja {hoja.nombre}: columnas de estación {encontrado}")
    for variable, col in inicio.items():
        meses = [normalizar_texto(v) for v in fila.iloc[col : col + 12]]
        anual = str(fila.iloc[col + 12]).strip().upper()
        if meses != list(MESES) or anual not in ENCABEZADOS_ANUAL:
            raise LayoutInesperado(f"Hoja {hoja.nombre}, bloque {variable}: encabezados {meses + [anual]}")


def extraer_hoja(ruta: Path, hoja: Hoja) -> HojaExtraida:
    crudo = pd.read_excel(ruta, sheet_name=hoja.nombre, header=None, dtype=object, engine="openpyxl")
    inicio = _ubicar_bloques(crudo.iloc[0], hoja)
    _validar_encabezados(crudo.iloc[1], inicio, hoja)

    cuerpo = crudo.iloc[FILAS_ENCABEZADO:]
    # Una fila es estación si el código es numérico; la leyenda trae texto en esa columna.
    es_estacion = pd.to_numeric(cuerpo[0], errors="coerce").notna()

    columnas = {i: nombre for i, nombre in enumerate(COLUMNAS_ESTACION.values())}
    for variable, col in inicio.items():
        for j, mes in enumerate(MESES):
            columnas[col + j] = f"{variable}_{mes.lower()}"
        columnas[col + 12] = f"{variable}_anual"

    datos = cuerpo.loc[es_estacion, list(columnas)].rename(columns=columnas)
    datos = datos.apply(lambda s: s.map(lambda v: None if pd.isna(v) else str(v).strip()))
    datos.insert(0, "fila_excel", cuerpo.index[es_estacion] + 1)
    datos.insert(0, "hoja", hoja.nombre)
    return HojaExtraida(hoja=hoja, datos=datos.reset_index(drop=True), filas_descartadas=int((~es_estacion).sum()))

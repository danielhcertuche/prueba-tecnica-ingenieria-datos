"""Transformación de raw a silver.

- estacion: una fila por código de estación, con tipos y coordenadas en grados decimales.
- normal_mensual: formato largo (estación, variable, mes, valor). Es el grano que
  permite agregar cualquier variable sin tocar el modelo cuando se suma otra hoja.
- normal_anual: el anual que trae la fuente junto al recalculado desde los meses,
  para poder medir qué tanto se parecen.
"""

from __future__ import annotations

import re

import pandas as pd

from etl_clima.config import MESES
from etl_clima.extraer import HojaExtraida

_PATRON_COORDENADA = re.compile(r"^\s*(\d+)\s*°\s*(\d+)\s*'\s*([\d.,]+)\s*\"\s*([NSEW])\s*$")


def coordenada_a_decimal(texto: str | None) -> float | None:
    """'73°12'34.0"W' -> -73.2094. Acepta coma o punto como separador decimal."""
    if texto is None:
        return None
    m = _PATRON_COORDENADA.match(str(texto))
    if not m:
        return None
    grados, minutos, segundos, hemisferio = m.groups()
    valor = int(grados) + int(minutos) / 60 + float(segundos.replace(",", ".")) / 3600
    return round(-valor if hemisferio in "SW" else valor, 6)


def _a_numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce")


def estaciones_de_hoja(extraida: HojaExtraida) -> pd.DataFrame:
    d = extraida.datos
    return pd.DataFrame(
        {
            "codigo": _a_numero(d["codigo"]).astype("Int64").astype("string"),
            "categoria": d["categoria"].str.upper(),
            "nombre": d["nombre"],
            "municipio": d["municipio"],
            "departamento": d["departamento"],
            "elevacion_m": _a_numero(d["elevacion"]),
            "latitud": d["latitud"].map(coordenada_a_decimal),
            "longitud": d["longitud"].map(coordenada_a_decimal),
            "latitud_fuente": d["latitud"],
            "longitud_fuente": d["longitud"],
            "hoja": extraida.hoja.nombre,
        }
    )


def consolidar_estaciones(por_hoja: list[pd.DataFrame]) -> pd.DataFrame:
    """Una fila por estación. Si aparece en varias hojas, gana la primera según el orden de HOJAS;
    las diferencias entre hojas se reportan en calidad, no se resuelven en silencio."""
    todas = pd.concat(por_hoja, ignore_index=True)
    hojas = todas.groupby("codigo")["hoja"].agg(lambda s: ",".join(s)).rename("hojas")
    unicas = todas.drop_duplicates("codigo", keep="first").drop(columns=["hoja", "latitud_fuente", "longitud_fuente"])
    return unicas.merge(hojas, on="codigo").sort_values("codigo").reset_index(drop=True)


def normales_mensuales(extraida: HojaExtraida) -> pd.DataFrame:
    d = extraida.datos
    codigo = _a_numero(d["codigo"]).astype("Int64").astype("string")
    partes = []
    for variable in extraida.hoja.variables:
        for numero_mes, mes in enumerate(MESES, start=1):
            texto = d[f"{variable.codigo}_{mes.lower()}"]
            partes.append(
                pd.DataFrame(
                    {
                        "codigo_estacion": codigo,
                        "variable": variable.codigo,
                        "mes": numero_mes,
                        "valor_fuente": texto,
                        "valor": _a_numero(texto),
                    }
                )
            )
    return pd.concat(partes, ignore_index=True)


def normales_anuales(extraida: HojaExtraida, mensual: pd.DataFrame) -> pd.DataFrame:
    d = extraida.datos
    codigo = _a_numero(d["codigo"]).astype("Int64").astype("string")
    partes = []
    for variable in extraida.hoja.variables:
        meses = mensual[(mensual["variable"] == variable.codigo) & mensual["valor"].notna()]
        agg = "sum" if variable.agregacion_anual == "suma" else "mean"
        calculado = meses.groupby("codigo_estacion")["valor"].agg([agg, "count"])
        # Solo se recalcula cuando están los 12 meses; con huecos el anual no es comparable.
        calculado = calculado.loc[calculado["count"] == 12, agg].rename("valor_calculado")
        fuente = pd.DataFrame(
            {"codigo_estacion": codigo, "variable": variable.codigo, "valor_fuente": _a_numero(d[f"{variable.codigo}_anual"])}
        )
        partes.append(fuente.merge(calculado, left_on="codigo_estacion", right_index=True, how="left"))
    anual = pd.concat(partes, ignore_index=True)
    anual["diferencia_relativa"] = (anual["valor_fuente"] - anual["valor_calculado"]) / anual["valor_calculado"]
    return anual[anual["valor_fuente"].notna() | anual["valor_calculado"].notna()].reset_index(drop=True)


def transformar(extraidas: list[HojaExtraida]) -> dict[str, pd.DataFrame]:
    estaciones_hoja = [estaciones_de_hoja(e) for e in extraidas]
    mensual_hoja = [normales_mensuales(e) for e in extraidas]
    anual = pd.concat([normales_anuales(e, m) for e, m in zip(extraidas, mensual_hoja)], ignore_index=True)
    mensual = pd.concat(mensual_hoja, ignore_index=True)
    return {
        "estacion_por_hoja": pd.concat(estaciones_hoja, ignore_index=True),
        "estacion": consolidar_estaciones(estaciones_hoja),
        "normal_mensual_completa": mensual,  # incluye nulos y no numéricos, solo para calidad
        "normal_mensual": mensual[mensual["valor"].notna()].drop(columns="valor_fuente").reset_index(drop=True),
        "normal_anual": anual,
    }


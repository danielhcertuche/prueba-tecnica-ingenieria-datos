"""Reglas de calidad sobre silver.

Cada regla devuelve cuántas filas evaluó, cuántas fallaron y algunos ejemplos.
Severidad "error": se cancela la publicación (no se toca gold).
Severidad "advertencia": se publica y queda registrada para revisión.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd

from etl_clima.config import CATEGORIAS_ESTACION, HOJAS, LIMITES_COLOMBIA, RAZON_EVAPORACION_ETP

ERROR = "error"
ADVERTENCIA = "advertencia"
MAX_EJEMPLOS = 5


@dataclass
class ResultadoRegla:
    regla: str
    tabla: str
    severidad: str
    evaluadas: int
    fallidas: int
    descripcion: str
    ejemplos: list = field(default_factory=list)

    @property
    def estado(self) -> str:
        if self.fallidas == 0:
            return "ok"
        return "fallida" if self.severidad == ERROR else "advertencia"

    def como_fila(self) -> dict:
        return {
            "regla": self.regla,
            "tabla": self.tabla,
            "severidad": self.severidad,
            "estado": self.estado,
            "evaluadas": self.evaluadas,
            "fallidas": self.fallidas,
            "descripcion": self.descripcion,
            "ejemplos": json.dumps(self.ejemplos, ensure_ascii=False, default=str),
        }


def _resultado(regla, tabla, severidad, descripcion, base: pd.DataFrame, malas: pd.Series, columnas) -> ResultadoRegla:
    ejemplos = base.loc[malas, columnas].head(MAX_EJEMPLOS).to_dict("records")
    return ResultadoRegla(regla, tabla, severidad, len(base), int(malas.sum()), descripcion, ejemplos)


def reglas_estacion(por_hoja: pd.DataFrame) -> list[ResultadoRegla]:
    t = "silver.estacion"
    lim = LIMITES_COLOMBIA
    claves = ["hoja", "codigo", "nombre"]
    fuera = ~(
        por_hoja["latitud"].between(lim["lat_min"], lim["lat_max"])
        & por_hoja["longitud"].between(lim["lon_min"], lim["lon_max"])
    )
    return [
        _resultado("codigo_unico_por_hoja", t, ERROR, "Cada estación aparece una sola vez por hoja",
                   por_hoja, por_hoja.duplicated(["hoja", "codigo"], keep=False), claves),
        _resultado("identificacion_completa", t, ERROR, "Código, nombre, municipio y departamento presentes",
                   por_hoja, por_hoja[["codigo", "nombre", "municipio", "departamento"]].isna().any(axis=1), claves),
        _resultado("coordenadas_legibles", t, ERROR, "Latitud y longitud en formato grados-minutos-segundos",
                   por_hoja, por_hoja[["latitud", "longitud"]].isna().any(axis=1),
                   claves + ["latitud_fuente", "longitud_fuente"]),
        _resultado("coordenadas_en_colombia", t, ERROR, "La ubicación cae dentro del territorio nacional",
                   por_hoja, fuera & por_hoja["latitud"].notna(), claves + ["latitud", "longitud"]),
        _resultado("elevacion_valida", t, ERROR, "Elevación entre 0 y 6000 m",
                   por_hoja, ~por_hoja["elevacion_m"].between(0, 6000), claves + ["elevacion_m"]),
        _resultado("categoria_conocida", t, ADVERTENCIA, "Categoría de estación dentro del catálogo",
                   por_hoja, ~por_hoja["categoria"].isin(list(CATEGORIAS_ESTACION)), claves + ["categoria"]),
        _consistencia_entre_hojas(por_hoja),
    ]


def _consistencia_entre_hojas(por_hoja: pd.DataFrame) -> ResultadoRegla:
    """Una misma estación debería describirse igual en todas las hojas."""
    repetidas = por_hoja[por_hoja.duplicated("codigo", keep=False)]
    g = repetidas.groupby("codigo")
    difiere = (
        (g["nombre"].nunique() > 1)
        | (g["municipio"].nunique() > 1)
        | (g["elevacion_m"].nunique() > 1)
        | ((g["latitud"].max() - g["latitud"].min()) > 0.01)
        | ((g["longitud"].max() - g["longitud"].min()) > 0.01)
    )
    codigos = difiere[difiere].index
    ejemplos = (
        repetidas[repetidas["codigo"].isin(codigos[:MAX_EJEMPLOS])]
        [["codigo", "hoja", "nombre", "municipio", "elevacion_m", "latitud", "longitud"]]
        .to_dict("records")
    )
    return ResultadoRegla("estacion_consistente_entre_hojas", "silver.estacion", ADVERTENCIA, int(g.ngroups),
                          len(codigos), "Mismo nombre, municipio, elevación y ubicación (±0.01°) en todas las hojas",
                          ejemplos)


def reglas_normales(mensual: pd.DataFrame, anual: pd.DataFrame) -> list[ResultadoRegla]:
    t = "silver.normal_mensual"
    resultados = [
        _resultado("valores_numericos", t, ERROR, "Todo valor presente en la fuente es numérico",
                   mensual, mensual["valor_fuente"].notna() & mensual["valor"].isna(),
                   ["codigo_estacion", "variable", "mes", "valor_fuente"]),
    ]
    variables = {v.codigo: v for h in HOJAS for v in h.variables}
    for codigo, v in variables.items():
        filas = mensual[(mensual["variable"] == codigo) & mensual["valor"].notna()]
        if filas.empty:
            continue
        bajo, alto = v.rango_mensual
        resultados.append(_resultado(f"rango_fisico_{codigo}", t, ERROR, f"Valor mensual entre {bajo} y {alto} {v.unidad}",
                                     filas, ~filas["valor"].between(bajo, alto), ["codigo_estacion", "mes", "valor"]))

        presentes = mensual[mensual["variable"] == codigo].groupby("codigo_estacion")["valor"].count()
        estaciones = presentes.to_frame("meses").reset_index()
        resultados.append(_resultado(f"serie_completa_{codigo}", t, ADVERTENCIA,
                                     "La estación tiene los 12 meses o ninguno (no series a medias)",
                                     estaciones, estaciones["meses"].between(1, 11), ["codigo_estacion", "meses"]))

        a = anual[(anual["variable"] == codigo) & anual["valor_calculado"].notna() & anual["valor_fuente"].notna()]
        resultados.append(_resultado(f"anual_consistente_{codigo}", "silver.normal_anual", ADVERTENCIA,
                                     f"El anual de la fuente difiere menos de {v.tolerancia_anual:.0%} del recalculado ({v.agregacion_anual} de meses)",
                                     a, a["diferencia_relativa"].abs() > v.tolerancia_anual,
                                     ["codigo_estacion", "valor_fuente", "valor_calculado", "diferencia_relativa"]))

    resultados.append(_coherencia_evaporacion_etp(anual))
    return resultados


def _coherencia_evaporacion_etp(anual: pd.DataFrame) -> ResultadoRegla:
    """Donde hay ambas medidas, la evaporación de tanque y la ETP deberían ser del mismo orden."""
    bajo, alto = RAZON_EVAPORACION_ETP
    pares = anual.pivot_table(index="codigo_estacion", columns="variable", values="valor_calculado").dropna()
    if not {"evaporacion", "evapotranspiracion_potencial"} <= set(pares.columns):
        pares = pd.DataFrame(columns=["evaporacion", "evapotranspiracion_potencial"])
    pares = pares.reset_index()
    razon = pares["evaporacion"] / pares["evapotranspiracion_potencial"]
    pares["razon"] = razon
    return _resultado("coherencia_evaporacion_etp", "silver.normal_anual", ADVERTENCIA,
                      f"Evaporación / ETP entre {bajo} y {alto} en estaciones con ambas medidas",
                      pares, ~razon.between(bajo, alto),
                      ["codigo_estacion", "evaporacion", "evapotranspiracion_potencial", "razon"])


def evaluar(silver: dict[str, pd.DataFrame]) -> list[ResultadoRegla]:
    return reglas_estacion(silver["estacion_por_hoja"]) + reglas_normales(
        silver["normal_mensual_completa"], silver["normal_anual"]
    )


def hay_errores(resultados: list[ResultadoRegla]) -> bool:
    return any(r.estado == "fallida" for r in resultados)

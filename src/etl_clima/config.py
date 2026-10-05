"""Contrato de la fuente: qué hojas y bloques se cargan y cómo se validan.

Agregar otro ítem del archivo (Brillo Solar, Humedad Relativa...) es agregar
una entrada en HOJAS; el resto del pipeline no cambia.
"""

from __future__ import annotations

from dataclasses import dataclass

MESES = ("ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC")

# Columnas de identificación de la estación, en el orden en que vienen en la fuente.
COLUMNAS_ESTACION = {
    "CODIGO": "codigo",
    "CAT": "categoria",
    "NOMBRE": "nombre",
    "MUNICIPIO": "municipio",
    "DEPARTAMENTO": "departamento",
    "ELEV": "elevacion",
    "LONGITUD": "longitud",
    "LATITUD": "latitud",
}
# Algunas hojas del archivo usan ELEVACIÓN en lugar de ELEV.
ALIAS_ENCABEZADO = {"ELEVACION": "ELEV"}

ENCABEZADOS_ANUAL = ("ANUAL", "PROMEDIO ANUAL")

CATEGORIAS_ESTACION = {
    "SP": "Sinóptica principal",
    "SS": "Sinóptica secundaria",
    "AM": "Agrometeorológica",
    "CP": "Climatológica principal",
    "CO": "Climatológica secundaria",
    "PM": "Pluviométrica",
    "PG": "Pluviográfica",
    "ME": "Meteorológica especial",
    "RS": "Radiosonda",
}

# Caja que contiene el territorio continental e insular (San Andrés y Providencia).
LIMITES_COLOMBIA = {"lat_min": -4.3, "lat_max": 13.6, "lon_min": -82.0, "lon_max": -66.8}


@dataclass(frozen=True)
class Variable:
    codigo: str
    titulo_fuente: str  # encabezado del bloque normalizado (sin espacios, tildes ni unidad)
    unidad: str
    agregacion_anual: str  # cómo se compone el anual a partir de los meses: "suma" o "promedio"
    rango_mensual: tuple[float, float]  # límites físicos razonables; fuera de ellos es error
    tolerancia_anual: float  # diferencia admitida entre el anual de la fuente y el recalculado


@dataclass(frozen=True)
class Hoja:
    nombre: str  # nombre exacto de la hoja en el Excel
    tabla_raw: str  # nombre de la tabla en la capa raw
    variables: tuple[Variable, ...]


# Evaporación: medida en tanque. Evapotranspiración potencial: demanda de agua de la
# atmósfera estimada para una superficie con agua suficiente. Ambas en mm por mes.
HOJAS = (
    Hoja(
        nombre="Evaporación",
        tabla_raw="evaporacion",
        variables=(Variable("evaporacion", "EVAPORACION", "mm", "suma", (0, 400), 0.05),),
    ),
    Hoja(
        nombre="Evapotranspiración Potencial",
        tabla_raw="evapotranspiracion_potencial",
        variables=(
            Variable("evapotranspiracion_potencial", "EVAPOTRANSPIRACIONPOTENCIAL", "mm", "suma", (0, 300), 0.01),
        ),
    ),
)

# Razón evaporación / ETP admitida en una misma estación antes de marcarla para revisión.
RAZON_EVAPORACION_ETP = (0.5, 2.0)

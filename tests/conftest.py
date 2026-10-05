"""Excel mínimo con el mismo layout que la fuente: dos filas de encabezado, un bloque por hoja y leyenda al final."""

from pathlib import Path

import openpyxl
import pytest

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
ID = ["CODIGO", "CAT", "NOMBRE", "MUNICIPIO", "DEPARTAMENTO", "ELEV", "LONGITUD", "LATITUD"]

ESTACIONES = [
    (11111111, "CO", "Uno", "Pueblo A", "La Guajira", 10, "72°0'0,0\"W", "11°30'0,0\"N"),
    (22222222, "CP", "Dos", "Pueblo B", "Cundinamarca", 2600, "74°0'0,0\"W", "4°40'0,0\"N"),
    (33333333, "PM", "Tres", "Pueblo C", "Amazonas", 100, "70°0'0,0\"W", "1°0'0,0\"S"),
]
EVAPORACION = {11111111: [200.0] * 12, 22222222: [90.0] * 12}
ETP = {11111111: [160.0] * 12, 22222222: [80.0] * 12, 33333333: [120.0] * 12}


def _hoja(ws, titulo, valores, estaciones):
    ws.append([None] * 8 + [titulo])
    ws.append(ID + MESES + ["ANUAL"])
    for est in estaciones:
        meses = valores[est[0]]
        ws.append(list(est) + meses + [sum(meses)])
    ws.append([None])
    ws.append(["Convenciones"])
    ws.append(["CO: Climatológica secundaria"])


def construir_excel(ruta: Path, evaporacion=None) -> Path:
    evaporacion = evaporacion or EVAPORACION
    wb = openpyxl.Workbook()
    wb.active.title = "Evaporación"
    _hoja(wb.active, "E V A P O R A C I O N (mm)", evaporacion, [e for e in ESTACIONES if e[0] in evaporacion])
    _hoja(wb.create_sheet("Evapotranspiración Potencial"),
          "E V A P O T R A N S P I R A C I O N   P O T E N C I A L (mm)", ETP, ESTACIONES)
    wb.save(ruta)
    return ruta


@pytest.fixture
def excel(tmp_path) -> Path:
    return construir_excel(tmp_path / "fuente.xlsx")

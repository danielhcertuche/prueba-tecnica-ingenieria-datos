"""Parte 2: cada paso de la ETL hace lo que dice, probado con un Excel pequeño.

El Excel se arma en conftest.py con el mismo formato que el archivo real
(dos filas de encabezado y leyenda al final) y tres estaciones inventadas.
"""

import openpyxl
import pytest

from etl_clima import calidad
from etl_clima.config import HOJAS
from etl_clima.extraer import LayoutInesperado, extraer_hoja
from etl_clima.transformar import coordenada_a_decimal, transformar

from conftest import EVAPORACION, construir_excel

HOJA_EVAPORACION, HOJA_ETP = HOJAS


# ---------- Extracción ----------

def test_lee_solo_estaciones_y_descarta_la_leyenda(excel):
    etp = extraer_hoja(excel, HOJA_ETP)
    assert len(etp.datos) == 3, "tres estaciones en la hoja"
    assert etp.filas_descartadas == 3, "una fila vacía y dos de leyenda"
    assert etp.datos["fila_excel"].tolist() == [3, 4, 5], "guarda la fila de Excel para poder rastrear cada dato"


def test_ubica_cada_mes_en_su_columna(excel):
    etp = extraer_hoja(excel, HOJA_ETP).datos.iloc[0]
    assert float(etp["evapotranspiracion_potencial_ene"]) == 160
    assert float(etp["evapotranspiracion_potencial_anual"]) == 1920


def test_si_cambia_el_formato_del_excel_falla_con_mensaje_claro(tmp_path):
    ruta = construir_excel(tmp_path / "f.xlsx")
    wb = openpyxl.load_workbook(ruta)
    wb["Evaporación"].cell(row=2, column=10).value = "FEBRERO"  # el encabezado decía FEB
    wb.save(ruta)
    with pytest.raises(LayoutInesperado, match="evaporacion"):
        extraer_hoja(ruta, HOJA_EVAPORACION)


# ---------- Transformación ----------

@pytest.mark.parametrize(
    "texto, grados_decimales",
    [
        ("73°12'34.0\"W", -73.209444),  # oeste es negativo
        ("1°44'54.0\"S", -1.748333),    # sur es negativo
        ("6°22'34,6\"N", 6.376278),     # coma decimal, como viene en estas hojas
        ("sin dato", None),
    ],
    ids=["oeste", "sur", "coma_decimal", "texto_invalido"],
)
def test_convierte_coordenadas_a_grados_decimales(texto, grados_decimales):
    assert coordenada_a_decimal(texto) == grados_decimales


def test_deja_una_fila_por_estacion_variable_y_mes(excel):
    silver = transformar([extraer_hoja(excel, h) for h in HOJAS])
    mensual = silver["normal_mensual"]
    assert len(mensual) == 2 * 12 + 3 * 12, "evaporación en 2 estaciones y ETP en 3, 12 meses cada una"
    assert not mensual.duplicated(["codigo_estacion", "variable", "mes"]).any()


def test_una_estacion_aparece_una_sola_vez_aunque_este_en_las_dos_hojas(excel):
    estaciones = transformar([extraer_hoja(excel, h) for h in HOJAS])["estacion"].set_index("codigo")
    assert estaciones.index.is_unique
    assert estaciones.loc["11111111", "hojas"] == "Evaporación,Evapotranspiración Potencial"


# ---------- Calidad ----------

def _reglas(ruta) -> dict:
    silver = transformar([extraer_hoja(ruta, h) for h in HOJAS])
    return {r.regla: r for r in calidad.evaluar(silver)}


def test_archivo_correcto_no_tiene_reglas_fallidas(excel):
    assert [r.regla for r in _reglas(excel).values() if r.estado == "fallida"] == []


def test_valor_negativo_de_evaporacion_bloquea_la_carga(tmp_path):
    ruta = construir_excel(tmp_path / "f.xlsx", evaporacion={**EVAPORACION, 11111111: [200.0] * 11 + [-5.0]})
    regla = _reglas(ruta)["rango_fisico_evaporacion"]
    assert regla.estado == "fallida"
    assert regla.fallidas == 1
    assert regla.ejemplos == [{"codigo_estacion": "11111111", "mes": 12, "valor": -5.0}]


def test_evaporacion_muy_distinta_de_la_etp_queda_como_advertencia(tmp_path):
    """La estación 2 evapora 3 veces su ETP: es sospechoso, pero no imposible. Se publica y se marca."""
    ruta = construir_excel(tmp_path / "f.xlsx", evaporacion={**EVAPORACION, 22222222: [240.0] * 12})
    regla = _reglas(ruta)["coherencia_evaporacion_etp"]
    assert (regla.estado, regla.evaluadas, regla.fallidas) == ("advertencia", 2, 1)

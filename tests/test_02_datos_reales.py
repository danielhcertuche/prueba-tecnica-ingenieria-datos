"""Parte 2: la carga del archivo real coincide con lo que se ve al abrir el Excel.

Cada prueba indica la hoja y la fila donde se puede comprobar el dato a mano.
"""

from pathlib import Path

import duckdb
import pytest

from etl_clima.pipeline import FUENTE_POR_DEFECTO, ejecutar


@pytest.fixture(scope="module")
def bodega(tmp_path_factory) -> duckdb.DuckDBPyConnection:
    db = Path(tmp_path_factory.mktemp("real")) / "clima.duckdb"
    assert ejecutar(FUENTE_POR_DEFECTO, db) == "exitosa"
    return duckdb.connect(str(db), read_only=True)


def _uno(con, sql):
    return con.execute(sql).fetchone()


def test_cantidad_de_estaciones_por_hoja(bodega):
    """Filas con código numérico en cada hoja, sin contar la leyenda del final."""
    assert _uno(bodega, "SELECT count(*) FROM raw.evaporacion")[0] == 412
    assert _uno(bodega, "SELECT count(*) FROM raw.evapotranspiracion_potencial")[0] == 1952
    assert _uno(bodega, "SELECT count(*) FROM gold.perfil_estacion WHERE razon_evaporacion_etp IS NOT NULL")[0] == 344


def test_ningun_dato_del_archivo_viola_una_regla_bloqueante(bodega):
    fallidas = bodega.execute(
        "SELECT regla FROM audit.calidad_resultado WHERE estado = 'fallida'"
    ).fetchall()
    assert fallidas == []


def test_primera_estacion_de_la_hoja_etp(bodega):
    """Hoja 'Evapotranspiración Potencial', fila 3: Encanto El, enero 127 mm, anual 1325,6 mm."""
    fila = _uno(bodega, "SELECT codigo, nombre, evapotranspiracion_potencial_ene, evapotranspiracion_potencial_anual "
                        "FROM raw.evapotranspiracion_potencial WHERE fila_excel = 3")
    assert fila[:2] == ("47060010", "Encanto El")
    assert float(fila[2]) == 127
    assert float(fila[3]) == 1325.6


def test_anual_publicado_de_evaporacion_no_es_la_suma_de_los_meses(bodega):
    """Hoja 'Evaporación', fila 248 (Manaure): la columna ANUAL dice 2611,3 mm,
    pero los 12 meses suman 2902,8 mm. Se conservan los dos valores."""
    publicado, suma = _uno(bodega, "SELECT evaporacion_anual_publicada_mm, evaporacion_anual_mm "
                                   "FROM gold.perfil_estacion WHERE codigo_estacion = '15075030'")
    assert round(publicado, 1) == 2611.3
    assert round(suma, 1) == 2902.8


def test_coordenadas_se_convierten_bien(bodega):
    """Hoja 'Evaporación', fila 4 (A.Vasquez Cobo, Leticia): 69°56'27,3"W y 4°11'37,9"S."""
    lat, lon = _uno(bodega, "SELECT latitud, longitud FROM gold.dim_estacion WHERE codigo_estacion = '48015010'")
    assert lat == pytest.approx(-4.1939, abs=1e-4)
    assert lon == pytest.approx(-69.9409, abs=1e-4)

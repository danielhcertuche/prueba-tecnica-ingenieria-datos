"""Parte 2: comportamiento del pipeline completo (publicar, no duplicar, no romper lo publicado)."""

import duckdb

from etl_clima.pipeline import ejecutar

from conftest import EVAPORACION, construir_excel


def test_publica_gold_con_los_indicadores_calculados(excel, tmp_path):
    db = tmp_path / "clima.duckdb"
    assert ejecutar(excel, db) == "exitosa"
    con = duckdb.connect(str(db), read_only=True)
    filas = con.execute(
        "SELECT codigo_estacion, round(razon_evaporacion_etp, 3), banda_latitud, piso_termico_orden "
        "FROM gold.perfil_estacion ORDER BY codigo_estacion"
    ).fetchall()
    assert filas == [
        ("11111111", 1.25, "Norte (>= 7° N)", 1),      # 2400 / 1920 mm, a 10 m de altura
        ("22222222", 1.125, "Centro (2° - 7° N)", 3),  # 1080 / 960 mm, a 2600 m
        ("33333333", None, "Sur (< 2° N)", 1),         # sin evaporación medida: no hay razón
    ]


def test_tasa_diaria_corrige_la_duracion_del_mes(excel, tmp_path):
    """Mismo total en febrero y marzo (120 mm), pero febrero tiene menos días: su tasa diaria es mayor."""
    db = tmp_path / "clima.duckdb"
    ejecutar(excel, db)
    con = duckdb.connect(str(db), read_only=True)
    (febrero,), (marzo,) = con.execute(
        "SELECT valor_diario FROM gold.fact_normal_mensual "
        "WHERE codigo_estacion = '33333333' AND mes IN (2, 3) ORDER BY mes"
    ).fetchall()
    assert round(febrero, 3) == round(120 / 28.25, 3)
    assert round(marzo, 3) == round(120 / 31, 3)


def test_correr_dos_veces_el_mismo_archivo_no_recarga(excel, tmp_path):
    db = tmp_path / "clima.duckdb"
    assert ejecutar(excel, db) == "exitosa"
    assert ejecutar(excel, db) == "omitida"
    assert ejecutar(excel, db, forzar=True) == "exitosa"
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("SELECT count(*) FROM gold.fact_normal_mensual").fetchone()[0] == 60, "no se duplicó"


def test_archivo_con_error_no_reemplaza_lo_ya_publicado(excel, tmp_path):
    db = tmp_path / "clima.duckdb"
    assert ejecutar(excel, db) == "exitosa"

    con_error = construir_excel(tmp_path / "mala.xlsx", evaporacion={**EVAPORACION, 11111111: [200.0] * 11 + [-5.0]})
    assert ejecutar(con_error, db) == "fallida"

    con = duckdb.connect(str(db), read_only=True)
    minimo = con.execute("SELECT min(valor) FROM gold.fact_normal_mensual WHERE variable = 'evaporacion'").fetchone()[0]
    assert minimo == 90, "gold conserva la versión anterior, sin el -5"
    mensaje = con.execute("SELECT mensaje FROM audit.etl_ejecucion WHERE estado = 'fallida'").fetchone()[0]
    assert "rango_fisico_evaporacion" in mensaje, "la bitácora dice qué regla falló"

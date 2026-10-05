"""Parte 1: el query del top 10 de clientes devuelve lo que debe.

Se crea el modelo mejorado en una base DuckDB en memoria, se cargan los datos de
fixtures/modelo_relacional_datos.sql y se ejecuta sql/01_modelo_relacional/top10_clientes.sql
con el periodo 2025-10-01 a 2026-10-01. El resultado esperado está calculado a mano en
el encabezado del archivo de datos.
"""

from pathlib import Path

import duckdb
import pytest

RAIZ = Path(__file__).resolve().parents[1]
SQL = RAIZ / "sql" / "01_modelo_relacional"
DATOS = Path(__file__).parent / "fixtures" / "modelo_relacional_datos.sql"
PERIODO = {"fecha_desde": "2025-10-01", "fecha_hasta": "2026-10-01"}


@pytest.fixture(scope="module")
def top10() -> list[tuple]:
    """Filas (id_cliente, nombre, valor_compra) que devuelve el query."""
    con = duckdb.connect()
    con.execute((SQL / "ddl_modelo_mejorado.sql").read_text(encoding="utf-8"))
    con.execute(DATOS.read_text(encoding="utf-8"))
    query = (SQL / "top10_clientes.sql").read_text(encoding="utf-8")
    # Cada driver marca los parámetros a su manera (:nombre, @nombre, ?); DuckDB usa $nombre.
    return con.execute(query.replace(":fecha_", "$fecha_"), PERIODO).fetchall()


def test_devuelve_los_diez_clientes_esperados_en_orden(top10):
    esperado = [
        (2, 675_000), (1, 590_000), (3, 450_000), (4, 450_000), (5, 300_000),
        (6, 300_000), (7, 200_000), (8, 144_000), (9, 114_000), (10, 100_000),
    ]
    assert [(id_cliente, int(valor)) for id_cliente, _, valor in top10] == esperado


def test_empate_en_valor_se_desempata_por_id_de_cliente(top10):
    """Clientes 3 y 4 compran 450.000 cada uno: siempre sale primero el 3."""
    ids = [fila[0] for fila in top10]
    assert ids.index(3) < ids.index(4)
    assert ids.index(5) < ids.index(6)


def test_excluye_anuladas_y_ordenes_fuera_del_periodo(top10):
    ids = {fila[0] for fila in top10}
    assert 14 not in ids, "cliente 14: su única orden está anulada"
    assert 13 not in ids, "cliente 13: su única orden es del 2025-09-30 23:59, un minuto antes del periodo"


def test_limite_superior_del_periodo_es_abierto(top10):
    """El cliente 2 tiene además una orden de 1.000.000 el 2026-10-01 00:00, que ya es del periodo siguiente."""
    valor_cliente_2 = next(valor for id_cliente, _, valor in top10 if id_cliente == 2)
    assert int(valor_cliente_2) == 675_000

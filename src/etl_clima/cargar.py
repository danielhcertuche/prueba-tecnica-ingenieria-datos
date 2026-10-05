"""Carga en DuckDB con el patrón escribir-auditar-publicar.

raw, silver y gold se reemplazan dentro de una sola transacción. Si alguna regla
de severidad error falla, se hace rollback y la versión publicada anterior queda
intacta. La bitácora (audit) se escribe fuera de la transacción para que el
intento quede registrado aunque se cancele.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from etl_clima.calidad import ResultadoRegla

DIR_SQL = Path(__file__).resolve().parents[2] / "sql" / "02_etl_clima"


def conectar(ruta_db: Path) -> duckdb.DuckDBPyConnection:
    ruta_db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ruta_db))
    con.execute((DIR_SQL / "00_esquemas.sql").read_text(encoding="utf-8"))
    return con


def ya_cargado(con: duckdb.DuckDBPyConnection, sha256: str) -> bool:
    fila = con.execute(
        "SELECT count(*) FROM audit.etl_ejecucion WHERE sha256 = ? AND estado = 'exitosa'", [sha256]
    ).fetchone()
    return fila[0] > 0


def _reemplazar(con: duckdb.DuckDBPyConnection, tabla: str, df: pd.DataFrame) -> None:
    con.register("_df", df)
    con.execute(f"CREATE OR REPLACE TABLE {tabla} AS SELECT * FROM _df")
    con.unregister("_df")


def _insertar(con: duckdb.DuckDBPyConnection, tabla: str, df: pd.DataFrame) -> None:
    """Inserta respetando el esquema declarado en sql/silver (los tipos los define la tabla, no pandas)."""
    con.register("_df", df)
    columnas = ", ".join(df.columns)
    con.execute(f"INSERT INTO {tabla} ({columnas}) SELECT {columnas} FROM _df")
    con.unregister("_df")


def _ejecutar_carpeta(con: duckdb.DuckDBPyConnection, carpeta: str) -> None:
    for archivo in sorted((DIR_SQL / carpeta).glob("*.sql")):
        con.execute(archivo.read_text(encoding="utf-8"))


def publicar(
    con: duckdb.DuckDBPyConnection,
    raw: dict[str, pd.DataFrame],
    silver: dict[str, pd.DataFrame],
    catalogos: dict[str, pd.DataFrame],
) -> None:
    """Las constraints de silver (PK, NOT NULL, CHECK) son una segunda barrera: si algo
    las viola, la excepción hace rollback de todo."""
    con.execute("BEGIN TRANSACTION")
    try:
        for tabla, df in raw.items():
            _reemplazar(con, f"raw.{tabla}", df)
        _ejecutar_carpeta(con, "silver")
        for nombre, df in catalogos.items():
            _insertar(con, f"silver.{nombre}", df)
        _insertar(con, "silver.estacion", silver["estacion"])
        _insertar(con, "silver.normal_mensual", silver["normal_mensual"])
        _insertar(con, "silver.normal_anual", silver["normal_anual"])
        _ejecutar_carpeta(con, "gold")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def registrar(
    con: duckdb.DuckDBPyConnection, ejecucion: dict, resultados: list[ResultadoRegla]
) -> None:
    con.execute(
        """INSERT INTO audit.etl_ejecucion
           (id_ejecucion, inicio, fin, archivo, sha256, estado, filas_raw, filas_silver,
            reglas_fallidas, advertencias, mensaje)
           VALUES ($id_ejecucion, $inicio, $fin, $archivo, $sha256, $estado, $filas_raw, $filas_silver,
                   $reglas_fallidas, $advertencias, $mensaje)""",
        ejecucion,
    )
    if resultados:
        filas = pd.DataFrame([r.como_fila() for r in resultados])
        filas.insert(0, "id_ejecucion", ejecucion["id_ejecucion"])
        _insertar(con, "audit.calidad_resultado", filas)

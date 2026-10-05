"""Orquestación: extraer -> transformar -> calidad -> publicar -> bitácora.

Uso:
    python -m etl_clima --fuente data/raw/promedios_climatologicos_1981_2010.xlsx
    python -m etl_clima --forzar      # recarga aunque el archivo ya se haya cargado
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from etl_clima import calidad, cargar
from etl_clima.config import CATEGORIAS_ESTACION, HOJAS
from etl_clima.extraer import LayoutInesperado, extraer_hoja, hash_archivo
from etl_clima.transformar import transformar

RAIZ = Path(__file__).resolve().parents[2]
FUENTE_POR_DEFECTO = RAIZ / "data" / "raw" / "promedios_climatologicos_1981_2010.xlsx"
DB_POR_DEFECTO = RAIZ / "data" / "warehouse" / "clima.duckdb"

log = logging.getLogger("etl_clima")


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _catalogos() -> dict[str, pd.DataFrame]:
    return {
        "categoria_estacion": pd.DataFrame(
            {"categoria": list(CATEGORIAS_ESTACION), "descripcion": list(CATEGORIAS_ESTACION.values())}
        ),
        "variable": pd.DataFrame(
            [
                {"variable": v.codigo, "hoja": h.nombre, "unidad": v.unidad, "agregacion_anual": v.agregacion_anual}
                for h in HOJAS
                for v in h.variables
            ]
        ),
    }


def ejecutar(fuente: Path, ruta_db: Path, forzar: bool = False) -> str:
    """Corre el pipeline completo y devuelve el estado final de la ejecución."""
    ejecucion = {
        "id_ejecucion": uuid.uuid4().hex[:12],
        "inicio": _ahora(),
        "archivo": fuente.name,
        "sha256": hash_archivo(fuente),
        "filas_raw": None,
        "filas_silver": None,
        "reglas_fallidas": None,
        "advertencias": None,
    }
    con = cargar.conectar(ruta_db)
    resultados: list[calidad.ResultadoRegla] = []
    try:
        if not forzar and cargar.ya_cargado(con, ejecucion["sha256"]):
            ejecucion.update(estado="omitida", mensaje="El archivo ya se cargó con este mismo contenido")
            log.info("Sin cambios en la fuente (sha256 %s...), no se recarga", ejecucion["sha256"][:12])
            return "omitida"

        extraidas = [extraer_hoja(fuente, hoja) for hoja in HOJAS]
        for e in extraidas:
            log.info("Hoja %s: %d estaciones, %d filas de leyenda descartadas",
                     e.hoja.nombre, len(e.datos), e.filas_descartadas)
        raw = {e.hoja.tabla_raw: e.datos.assign(id_ejecucion=ejecucion["id_ejecucion"]) for e in extraidas}
        silver = transformar(extraidas)

        resultados = calidad.evaluar(silver)
        fallidas = [r for r in resultados if r.estado == "fallida"]
        ejecucion.update(
            filas_raw=sum(len(df) for df in raw.values()),
            filas_silver=len(silver["estacion"]) + len(silver["normal_mensual"]) + len(silver["normal_anual"]),
            reglas_fallidas=len(fallidas),
            advertencias=sum(r.estado == "advertencia" for r in resultados),
        )
        for r in resultados:
            nivel = logging.INFO if r.estado == "ok" else logging.WARNING
            log.log(nivel, "calidad %-40s %-11s %5d/%d", r.regla, r.estado, r.fallidas, r.evaluadas)

        if fallidas:
            ejecucion.update(estado="fallida", mensaje="Reglas bloqueantes: " + ", ".join(r.regla for r in fallidas))
            log.error(ejecucion["mensaje"])
            return "fallida"

        cargar.publicar(con, raw, silver, _catalogos())
        ejecucion.update(estado="exitosa", mensaje=None)
        log.info("Publicado en %s", ruta_db)
        return "exitosa"
    except LayoutInesperado as exc:
        ejecucion.update(estado="fallida", mensaje=f"Layout inesperado: {exc}")
        log.error(ejecucion["mensaje"])
        return "fallida"
    except Exception as exc:
        ejecucion.update(estado="fallida", mensaje=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        ejecucion["fin"] = _ahora()
        cargar.registrar(con, ejecucion, resultados)
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETL de normales climatológicas 1981-2010 (evaporación y evapotranspiración potencial)")
    parser.add_argument("--fuente", type=Path, default=FUENTE_POR_DEFECTO)
    parser.add_argument("--db", type=Path, default=DB_POR_DEFECTO)
    parser.add_argument("--forzar", action="store_true", help="recargar aunque la fuente no haya cambiado")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    estado = ejecutar(args.fuente, args.db, args.forzar)
    return 0 if estado in ("exitosa", "omitida") else 1


if __name__ == "__main__":
    sys.exit(main())

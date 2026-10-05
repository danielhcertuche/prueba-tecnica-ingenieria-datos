# Prueba técnica: ingeniería de datos

Solución de las dos partes de la prueba:

| Parte | Pregunta | Respuesta |
|---|---|---|
| 1 | Mejoras al modelo relacional de ventas por internet y query de los 10 mejores clientes del último año | [docs/01_modelo_relacional.md](docs/01_modelo_relacional.md) |
| 2 | ETL de evaporación y evapotranspiración potencial del archivo "Promedios Climatológicos 1981-2010", reporte y análisis | [docs/02_etl_clima.md](docs/02_etl_clima.md) y [reports/clima/reporte_clima.md](reports/clima/reporte_clima.md) |

## Estructura

```
├── data/
│   ├── raw/                      archivo fuente, sin modificar
│   └── warehouse/                bodega DuckDB (se genera, no se versiona)
├── docs/
│   ├── 01_modelo_relacional.md   respuestas de la parte 1
│   ├── 02_etl_clima.md           diseño de la ETL y análisis de la parte 2
│   └── diagramas/                modelo relacional mejorado (.drawio editable y .svg)
├── reports/clima/                reporte generado por la ETL (Markdown + gráficos)
├── sql/
│   ├── 01_modelo_relacional/     DDL del modelo mejorado y query del top 10
│   └── 02_etl_clima/             esquemas, tablas silver y modelos gold
├── src/etl_clima/                código de la ETL
│   ├── config.py                 contrato de la fuente: hojas, bloques, unidades, rangos
│   ├── extraer.py                lectura del Excel y validación del layout   (raw)
│   ├── transformar.py            tipado y formato largo                      (silver)
│   ├── calidad.py                reglas de calidad con severidad
│   ├── cargar.py                 carga transaccional en DuckDB               (gold)
│   ├── pipeline.py               orquestación y bitácora (CLI)
│   └── reporte.py                reporte desde gold
└── tests/                        pruebas de las dos partes y guía para validarlas a mano
```

## Cómo correrlo

Requiere Python 3.10 o superior.

```bash
make install    # crea .venv e instala dependencias
make run        # ETL (data/raw/ -> data/warehouse/clima.duckdb) y reporte (reports/clima/)
make test       # 25 pruebas, ver tests/README.md
make clean      # borra lo generado

make            # las tres primeras en orden
```

Sin `make` (por ejemplo en Windows):

```bash
python -m venv .venv
source .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
etl-clima                                # o: python -m etl_clima
etl-clima-reporte                        # o: python -m etl_clima.reporte
pytest -v
```

`etl-clima --forzar` recarga aunque el archivo no haya cambiado, y `etl-clima --fuente <ruta.xlsx> --db <ruta.duckdb>` permite apuntar a otro archivo o bodega.

Para consultar la bodega directamente:

```bash
.venv/bin/python -c "import duckdb; print(duckdb.connect('data/warehouse/clima.duckdb').sql('SELECT * FROM gold.resumen_departamento ORDER BY razon_evaporacion_etp_mediana DESC LIMIT 5'))"
```

## Convenciones

- Nombres en español y `snake_case` en tablas, columnas, módulos y archivos.
- SQL numerado por orden de ejecución (`00_`, `01_`...) y separado por capa (`silver/`, `gold/`).
- Capas raw → silver → gold, más `audit` para la bitácora de ejecuciones y los resultados de calidad.
- La fuente en `data/raw/` no se modifica; todo lo demás se puede regenerar desde ella.

VENV := .venv
PY   := $(VENV)/bin/python

.PHONY: all install run etl report test clean

all: install run test

install:            ## entorno virtual y dependencias
	python3 -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e ".[dev]"

run: etl report     ## ETL completa y reporte

etl:                ## carga data/raw/ en data/warehouse/clima.duckdb
	$(PY) -m etl_clima

report:             ## regenera reports/clima/ desde la capa gold
	$(PY) -m etl_clima.reporte

test:               ## pruebas de la parte 1 y la parte 2
	$(PY) -m pytest -v

clean:              ## borra lo que se genera al correr
	rm -rf data/warehouse .pytest_cache src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

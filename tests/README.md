# Pruebas

```bash
make test                       # o: pytest -v
```

Cada archivo cubre una parte de la prueba. Los nombres de las pruebas dicen qué se verifica, así que `pytest -v` se lee como una lista de chequeo.

| Archivo | Qué valida | Datos que usa |
|---|---|---|
| `test_01_top10_clientes.py` | El query de la parte 1: los 10 clientes correctos, en orden, sin anuladas, sin órdenes fuera del periodo y con desempate estable | `fixtures/modelo_relacional_datos.sql` (14 clientes con casos borde) |
| `test_02_etl_reglas.py` | Cada paso de la ETL por separado: lectura del Excel, conversión de coordenadas, formato largo, reglas de calidad | Excel pequeño armado en `conftest.py` |
| `test_02_etl_pipeline.py` | El pipeline completo: publica gold, corrige la duración del mes, no duplica si se corre dos veces y no daña lo publicado si llega un archivo con errores | Mismo Excel pequeño |
| `test_02_datos_reales.py` | La carga del archivo real coincide con lo que se ve en el Excel | `data/raw/promedios_climatologicos_1981_2010.xlsx` |

## Validar a mano

Las pruebas de `test_02_datos_reales.py` dicen en qué hoja y fila mirar. Por ejemplo:

- Hoja **Evapotranspiración Potencial**, fila 3: estación *Encanto El*, enero 127 mm, anual 1.325,6 mm.
- Hoja **Evaporación**, fila 248: estación *Manaure*. La columna ANUAL dice 2.611,3 mm, pero la suma de ENE a DIC da 2.902,8 mm. Es el caso que explica por qué la ETL guarda los dos valores.

Para la parte 1, el encabezado de `fixtures/modelo_relacional_datos.sql` tiene el resultado esperado calculado a mano, y cada caso borde dice qué cliente lo cubre.

Para ver los datos cargados después de `make run`:

```bash
.venv/bin/python -c "import duckdb; print(duckdb.connect('data/warehouse/clima.duckdb').sql('SELECT regla, estado, fallidas, evaluadas FROM audit.calidad_resultado ORDER BY estado DESC'))"
```

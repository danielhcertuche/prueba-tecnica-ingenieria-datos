-- Una fila por estación con los indicadores del reporte.
-- Los anuales se calculan como suma de los 12 meses para que sean comparables entre
-- variables; el anual publicado de evaporación se conserva aparte (difiere, ver docs).
CREATE OR REPLACE TABLE gold.perfil_estacion AS
WITH por_variable AS (
    SELECT
        codigo_estacion,
        variable,
        sum(valor)                       AS anual_mm,
        avg(valor_diario)                AS media_diaria_mm,
        max(valor_diario)                AS max_diaria_mm,
        min(valor_diario)                AS min_diaria_mm,
        arg_max(mes, valor_diario)       AS mes_max,
        arg_min(mes, valor_diario)       AS mes_min
    FROM gold.fact_normal_mensual
    GROUP BY codigo_estacion, variable
    HAVING count(*) = 12
),
evap AS (SELECT * FROM por_variable WHERE variable = 'evaporacion'),
etp  AS (SELECT * FROM por_variable WHERE variable = 'evapotranspiracion_potencial'),
publicado AS (
    SELECT codigo_estacion, valor_fuente AS evaporacion_anual_publicada_mm
    FROM silver.normal_anual
    WHERE variable = 'evaporacion'
)
SELECT
    d.codigo_estacion,
    d.nombre,
    d.municipio,
    d.departamento,
    d.elevacion_m,
    d.piso_termico,
    d.piso_termico_orden,
    d.banda_latitud,
    d.latitud,
    d.longitud,
    etp.anual_mm                                          AS etp_anual_mm,
    etp.media_diaria_mm                                   AS etp_diaria_mm,
    etp.mes_max                                           AS etp_mes_max,
    etp.mes_min                                           AS etp_mes_min,
    -- Estacionalidad: cuánto varía la tasa diaria entre el mes de mayor y el de menor demanda.
    (etp.max_diaria_mm - etp.min_diaria_mm) / etp.media_diaria_mm AS etp_estacionalidad,
    evap.anual_mm                                         AS evaporacion_anual_mm,
    p.evaporacion_anual_publicada_mm,
    evap.media_diaria_mm                                  AS evaporacion_diaria_mm,
    evap.mes_max                                          AS evaporacion_mes_max,
    evap.anual_mm / etp.anual_mm                          AS razon_evaporacion_etp
FROM gold.dim_estacion d
LEFT JOIN etp       USING (codigo_estacion)
LEFT JOIN evap      USING (codigo_estacion)
LEFT JOIN publicado p USING (codigo_estacion);

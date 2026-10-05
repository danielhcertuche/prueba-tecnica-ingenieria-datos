-- Indicadores por departamento. Se usa la mediana porque las estaciones no están
-- repartidas de forma pareja y unos pocos valores extremos mueven mucho el promedio.
CREATE OR REPLACE TABLE gold.resumen_departamento AS
SELECT
    departamento,
    count(etp_anual_mm)                   AS estaciones_etp,
    count(evaporacion_anual_mm)           AS estaciones_evaporacion,
    count(razon_evaporacion_etp)          AS estaciones_con_ambas,
    median(elevacion_m)                   AS elevacion_mediana_m,
    median(etp_anual_mm)                  AS etp_mediana_mm,
    median(evaporacion_anual_mm)          AS evaporacion_mediana_mm,
    median(razon_evaporacion_etp)         AS razon_evaporacion_etp_mediana
FROM gold.perfil_estacion
GROUP BY departamento;

-- Dimensión de estación. Piso térmico y banda de latitud se derivan de la propia estación.
CREATE OR REPLACE TABLE gold.dim_estacion AS
SELECT
    e.codigo                                  AS codigo_estacion,
    e.nombre,
    e.categoria,
    c.descripcion                             AS categoria_descripcion,
    e.municipio,
    e.departamento,
    e.elevacion_m,
    e.latitud,
    e.longitud,
    CASE
        WHEN e.elevacion_m < 1000 THEN 1
        WHEN e.elevacion_m < 2000 THEN 2
        WHEN e.elevacion_m < 3000 THEN 3
        ELSE 4
    END                                       AS piso_termico_orden,
    CASE
        WHEN e.elevacion_m < 1000 THEN 'Cálido (< 1.000 m)'
        WHEN e.elevacion_m < 2000 THEN 'Templado (1.000 - 2.000 m)'
        WHEN e.elevacion_m < 3000 THEN 'Frío (2.000 - 3.000 m)'
        ELSE 'Páramo (>= 3.000 m)'
    END                                       AS piso_termico,
    CASE
        WHEN e.latitud < 2 THEN 'Sur (< 2° N)'
        WHEN e.latitud < 7 THEN 'Centro (2° - 7° N)'
        ELSE 'Norte (>= 7° N)'
    END                                       AS banda_latitud,
    e.hojas LIKE '%Evaporación%'              AS mide_evaporacion,
    e.hojas LIKE '%Evapotranspiración%'       AS tiene_etp
FROM silver.estacion e
LEFT JOIN silver.categoria_estacion c USING (categoria);

-- Hecho a grano estación x variable x mes.
-- valor_diario divide el total del mes por sus días: sin eso, febrero siempre parece
-- un mes de baja evaporación solo por tener 28 días. Febrero usa 28,25 (promedio con bisiestos).
CREATE OR REPLACE TABLE gold.fact_normal_mensual AS
WITH calendario AS (
    SELECT * FROM (VALUES (1, 31.0), (2, 28.25), (3, 31.0), (4, 30.0), (5, 31.0), (6, 30.0),
                          (7, 31.0), (8, 31.0), (9, 30.0), (10, 31.0), (11, 30.0), (12, 31.0)) AS t (mes, dias_mes)
)
SELECT
    n.codigo_estacion,
    n.variable,
    v.unidad,
    n.mes,
    n.valor,
    k.dias_mes,
    n.valor / k.dias_mes AS valor_diario
FROM silver.normal_mensual n
JOIN silver.variable v USING (variable)
JOIN calendario k ON k.mes = n.mes;

-- Top 10 clientes por valor de compra en un periodo.
-- La aplicación envía el periodo como rango semiabierto [fecha_desde, fecha_hasta).
-- Ejemplo, 12 meses cerrados al 30 de septiembre de 2026: 2025-10-01 y 2026-10-01.
-- SQL estándar: PostgreSQL, Oracle 12c+, DuckDB. En SQL Server cambiar TRUE por 1.
SELECT c.id_cliente,
       c.nombre,
       SUM(d.cantidad * (d.precio_unitario - d.descuento_unitario)) AS valor_compra
FROM orden o
JOIN orden_detalle d ON d.id_orden = o.id_orden
JOIN estado_orden  e ON e.id_estado_orden = o.id_estado_orden
JOIN cliente       c ON c.id_cliente = o.id_cliente
WHERE o.fecha_orden >= :fecha_desde
  AND o.fecha_orden <  :fecha_hasta
  AND e.cuenta_como_venta = TRUE
GROUP BY c.id_cliente, c.nombre
ORDER BY valor_compra DESC, c.id_cliente
OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY;

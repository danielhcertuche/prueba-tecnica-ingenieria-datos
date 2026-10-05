-- Datos mínimos para probar el top 10. Fecha de corte del query: 2026-09-30.
-- Ventana: [2025-10-01 00:00, 2026-10-01 00:00).
-- Top esperado (ROW_NUMBER con desempate por id_cliente):
--   1 c2 675000 | 2 c1 590000 | 3 c3 450000 | 4 c4 450000 (empata con 3, RANK = 3)
--   5 c5 300000 | 6 c6 300000 (empata con 5, RANK = 5) | 7 c7 200000 | 8 c8 144000
--   9 c9 114000 | 10 c10 100000
-- Quedan por fuera c11 (40000) y c12 (20000) por posición; c13 (única orden un minuto antes
-- de la ventana) y c14 (orden anulada) no suman. Tampoco suman la orden devuelta de c11 ni
-- la de c2 del 2026-10-01 00:00, que cae en el límite superior abierto.

INSERT INTO tipo_documento VALUES (1,'CC','Cédula de ciudadanía'),(2,'CE','Cédula de extranjería'),(3,'NIT','NIT');
INSERT INTO ciudad VALUES (1,'11001','Bogotá D.C.','Bogotá D.C.'),(2,'05001','Medellín','Antioquia'),(3,'76001','Cali','Valle del Cauca');
INSERT INTO estado_orden VALUES (1,'PENDIENTE_PAGO',FALSE),(2,'PAGADA',TRUE),(3,'ENVIADA',TRUE),(4,'ENTREGADA',TRUE),(5,'ANULADA',FALSE),(6,'DEVUELTA',FALSE);
INSERT INTO estado_envio VALUES (1,'PREPARANDO'),(2,'EN_TRANSITO'),(3,'ENTREGADO');

INSERT INTO cliente (id_cliente,id_tipo_documento,documento,nombre,telefono,id_ciudad_residencia,creado_por) VALUES
(1,1,'1000000001','Cliente 01','3000000001',1,'carga_inicial'),(2,1,'1000000002','Cliente 02','3000000002',2,'carga_inicial'),
(3,1,'1000000003','Cliente 03','3000000003',3,'carga_inicial'),(4,1,'1000000004','Cliente 04','3000000004',1,'carga_inicial'),
(5,2,'2000000005','Cliente 05','3000000005',2,'carga_inicial'),(6,1,'1000000006','Cliente 06','3000000006',3,'carga_inicial'),
(7,1,'1000000007','Cliente 07','3000000007',1,'carga_inicial'),(8,3,'9000000008','Cliente 08','3000000008',2,'carga_inicial'),
(9,1,'1000000009','Cliente 09','3000000009',3,'carga_inicial'),(10,1,'1000000010','Cliente 10','3000000010',1,'carga_inicial'),
(11,1,'1000000011','Cliente 11','3000000011',2,'carga_inicial'),(12,1,'1000000012','Cliente 12','3000000012',3,'carga_inicial'),
(13,1,'1000000013','Cliente 13','3000000013',1,'carga_inicial'),(14,1,'1000000014','Cliente 14','3000000014',2,'carga_inicial');

INSERT INTO producto (id_producto,referencia,descripcion,tipo,precio_lista,creado_por) VALUES
(1,'REF-001','Auriculares inalámbricos','Electrónica',100000,'carga_inicial'),
(2,'REF-002','Lámpara de escritorio','Hogar',50000,'carga_inicial'),
(3,'REF-003','Monitor 24 pulgadas','Electrónica',250000,'carga_inicial'),
(4,'REF-004','Funda para portátil','Accesorios',20000,'carga_inicial');

INSERT INTO orden (id_orden,id_cliente,id_estado_orden,fecha_orden,creado_por) VALUES
(1,1,4,'2026-01-15 10:00:00','web'),(2,1,2,'2026-06-10 15:30:00','web'),(3,2,4,'2026-03-03 09:00:00','web'),
(4,3,3,'2026-08-20 12:00:00','web'),(5,4,4,'2025-11-05 18:00:00','web'),(6,5,2,'2026-02-14 11:00:00','web'),
(7,6,4,'2026-05-05 14:00:00','web'),(8,6,4,'2026-05-20 16:00:00','web'),(9,7,4,'2026-07-07 08:00:00','web'),
(10,8,2,'2026-04-01 13:00:00','web'),(11,9,3,'2026-09-30 23:30:00','web'),(12,10,4,'2025-12-12 10:00:00','web'),
(13,11,2,'2026-01-20 10:00:00','web'),(14,12,4,'2026-02-02 10:00:00','web'),(15,13,4,'2025-09-30 23:59:00','web'),
(16,14,5,'2026-06-01 10:00:00','web'),(17,11,6,'2026-03-01 10:00:00','web'),(18,2,2,'2026-10-01 00:00:00','web');

INSERT INTO orden_detalle (id_orden_detalle,id_orden,id_producto,cantidad,precio_unitario,descuento_unitario) VALUES
(1,1,3,2,250000,0),(2,2,2,2,50000,5000),(3,3,3,3,250000,25000),(4,4,1,5,100000,10000),
(5,5,3,1,250000,0),(6,5,1,2,100000,0),(7,6,1,3,100000,0),(8,7,2,4,50000,0),
(9,8,4,5,20000,0),(10,9,1,2,100000,0),(11,10,2,3,50000,2000),(12,11,4,6,20000,1000),
(13,12,4,5,20000,0),(14,13,4,2,20000,0),(15,14,4,1,20000,0),(16,15,3,10,250000,0),
(17,16,3,8,250000,0),(18,17,3,1,250000,0),(19,18,3,4,250000,0);

INSERT INTO orden_historial_estado VALUES
(16,'2026-06-01 10:00:00',1,'web',NULL),
(16,'2026-06-02 09:15:00',5,'analista_pagos','Pago rechazado por el banco');

INSERT INTO envio (id_envio,id_orden,id_estado_envio,id_ciudad_destino,direccion_destino,transportadora,numero_guia,fecha_envio,fecha_entrega,creado_por) VALUES
(1,1,3,1,'Calle 1 # 2-3','Transportadora Andina','G-0001','2026-01-16 08:00:00','2026-01-18 12:00:00','bodega');
INSERT INTO envio_detalle VALUES (1,1,2);

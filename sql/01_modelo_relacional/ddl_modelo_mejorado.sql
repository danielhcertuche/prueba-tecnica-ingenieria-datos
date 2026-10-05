-- Modelo relacional mejorado (ver docs/diagramas/modelo_relacional_mejorado.svg).
-- Corre en PostgreSQL y DuckDB. En SQL Server: BOOLEAN -> BIT, TIMESTAMP -> DATETIME2.

CREATE TABLE tipo_documento (
    id_tipo_documento SMALLINT PRIMARY KEY,
    codigo            VARCHAR(10) NOT NULL UNIQUE,
    descripcion       VARCHAR(60) NOT NULL
);

CREATE TABLE ciudad (
    id_ciudad    INTEGER PRIMARY KEY,
    codigo_dane  CHAR(5)     NOT NULL UNIQUE,
    nombre       VARCHAR(80) NOT NULL,
    departamento VARCHAR(80) NOT NULL
);

CREATE TABLE estado_orden (
    id_estado_orden   SMALLINT PRIMARY KEY,
    codigo            VARCHAR(20) NOT NULL UNIQUE,
    cuenta_como_venta BOOLEAN     NOT NULL
);

CREATE TABLE estado_envio (
    id_estado_envio SMALLINT PRIMARY KEY,
    codigo          VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE cliente (
    id_cliente           BIGINT PRIMARY KEY,
    id_tipo_documento    SMALLINT     NOT NULL REFERENCES tipo_documento (id_tipo_documento),
    documento            VARCHAR(30)  NOT NULL,
    nombre               VARCHAR(150) NOT NULL,
    telefono             VARCHAR(20),
    id_ciudad_residencia INTEGER      REFERENCES ciudad (id_ciudad),
    creado_en            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creado_por           VARCHAR(60)  NOT NULL,
    actualizado_en       TIMESTAMP,
    actualizado_por      VARCHAR(60),
    UNIQUE (id_tipo_documento, documento)
);

CREATE TABLE producto (
    id_producto     BIGINT PRIMARY KEY,
    referencia      VARCHAR(40)   NOT NULL UNIQUE,
    descripcion     VARCHAR(200)  NOT NULL,
    tipo            VARCHAR(40)   NOT NULL,
    precio_lista    DECIMAL(14,2) NOT NULL CHECK (precio_lista >= 0),
    creado_en       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creado_por      VARCHAR(60)   NOT NULL,
    actualizado_en  TIMESTAMP,
    actualizado_por VARCHAR(60)
);

CREATE TABLE orden (
    id_orden        BIGINT PRIMARY KEY,
    id_cliente      BIGINT      NOT NULL REFERENCES cliente (id_cliente),
    id_estado_orden SMALLINT    NOT NULL REFERENCES estado_orden (id_estado_orden),
    fecha_orden     TIMESTAMP   NOT NULL,
    moneda          CHAR(3)     NOT NULL DEFAULT 'COP',
    creado_en       TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creado_por      VARCHAR(60) NOT NULL,
    actualizado_en  TIMESTAMP,
    actualizado_por VARCHAR(60)
);

CREATE TABLE orden_detalle (
    id_orden_detalle   BIGINT PRIMARY KEY,
    id_orden           BIGINT        NOT NULL REFERENCES orden (id_orden),
    id_producto        BIGINT        NOT NULL REFERENCES producto (id_producto),
    cantidad           INTEGER       NOT NULL CHECK (cantidad > 0),
    precio_unitario    DECIMAL(14,2) NOT NULL CHECK (precio_unitario >= 0),
    descuento_unitario DECIMAL(14,2) NOT NULL DEFAULT 0,
    CHECK (descuento_unitario >= 0 AND descuento_unitario <= precio_unitario)
);

CREATE TABLE orden_historial_estado (
    id_orden        BIGINT       NOT NULL REFERENCES orden (id_orden),
    registrado_en   TIMESTAMP    NOT NULL,
    id_estado_orden SMALLINT     NOT NULL REFERENCES estado_orden (id_estado_orden),
    registrado_por  VARCHAR(60)  NOT NULL,
    observacion     VARCHAR(250),
    PRIMARY KEY (id_orden, registrado_en)
);

CREATE TABLE envio (
    id_envio          BIGINT PRIMARY KEY,
    id_orden          BIGINT       NOT NULL REFERENCES orden (id_orden),
    id_estado_envio   SMALLINT     NOT NULL REFERENCES estado_envio (id_estado_envio),
    id_ciudad_destino INTEGER      NOT NULL REFERENCES ciudad (id_ciudad),
    direccion_destino VARCHAR(250) NOT NULL,
    transportadora    VARCHAR(80),
    numero_guia       VARCHAR(40),
    fecha_envio       TIMESTAMP,
    fecha_entrega     TIMESTAMP,
    creado_en         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creado_por        VARCHAR(60)  NOT NULL,
    CHECK (fecha_entrega IS NULL OR fecha_envio IS NULL OR fecha_entrega >= fecha_envio)
);

CREATE TABLE envio_detalle (
    id_envio         BIGINT  NOT NULL REFERENCES envio (id_envio),
    id_orden_detalle BIGINT  NOT NULL REFERENCES orden_detalle (id_orden_detalle),
    cantidad         INTEGER NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (id_envio, id_orden_detalle)
);

CREATE INDEX ix_orden_fecha ON orden (fecha_orden, id_estado_orden, id_cliente);
CREATE INDEX ix_detalle_orden ON orden_detalle (id_orden);
CREATE INDEX ix_envio_orden ON envio (id_orden);

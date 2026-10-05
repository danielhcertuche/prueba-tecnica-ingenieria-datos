-- Esquema de silver: tipos y llaves declarados aquí, no inferidos de pandas.

CREATE OR REPLACE TABLE silver.categoria_estacion (
    categoria    VARCHAR PRIMARY KEY,
    descripcion  VARCHAR NOT NULL
);

CREATE OR REPLACE TABLE silver.variable (
    variable          VARCHAR PRIMARY KEY,
    hoja              VARCHAR NOT NULL,
    unidad            VARCHAR NOT NULL,
    agregacion_anual  VARCHAR NOT NULL CHECK (agregacion_anual IN ('suma', 'promedio'))
);

CREATE OR REPLACE TABLE silver.estacion (
    codigo        VARCHAR PRIMARY KEY,
    categoria     VARCHAR,
    nombre        VARCHAR NOT NULL,
    municipio     VARCHAR NOT NULL,
    departamento  VARCHAR NOT NULL,
    elevacion_m   INTEGER,
    latitud       DOUBLE,
    longitud      DOUBLE,
    hojas         VARCHAR NOT NULL       -- hojas de la fuente donde aparece la estación
);

-- Grano: estación x variable x mes.
CREATE OR REPLACE TABLE silver.normal_mensual (
    codigo_estacion  VARCHAR  NOT NULL,
    variable         VARCHAR  NOT NULL,
    mes              TINYINT  NOT NULL CHECK (mes BETWEEN 1 AND 12),
    valor            DOUBLE   NOT NULL,
    PRIMARY KEY (codigo_estacion, variable, mes)
);

-- Grano: estación x variable. valor_fuente es el anual publicado en el archivo.
CREATE OR REPLACE TABLE silver.normal_anual (
    codigo_estacion      VARCHAR NOT NULL,
    variable             VARCHAR NOT NULL,
    valor_fuente         DOUBLE,
    valor_calculado      DOUBLE,
    diferencia_relativa  DOUBLE,
    PRIMARY KEY (codigo_estacion, variable)
);

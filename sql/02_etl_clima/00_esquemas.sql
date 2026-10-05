CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS audit;

-- Bitácora de ejecuciones. Se conserva todo el historial, también los intentos fallidos.
CREATE TABLE IF NOT EXISTS audit.etl_ejecucion (
    id_ejecucion     VARCHAR PRIMARY KEY,
    inicio           TIMESTAMP NOT NULL,
    fin              TIMESTAMP NOT NULL,
    archivo          VARCHAR   NOT NULL,
    sha256           VARCHAR   NOT NULL,
    estado           VARCHAR   NOT NULL,   -- exitosa | fallida | omitida
    filas_raw        INTEGER,
    filas_silver     INTEGER,
    reglas_fallidas  INTEGER,
    advertencias     INTEGER,
    mensaje          VARCHAR
);

CREATE TABLE IF NOT EXISTS audit.calidad_resultado (
    id_ejecucion  VARCHAR NOT NULL,
    regla         VARCHAR NOT NULL,
    tabla         VARCHAR NOT NULL,
    severidad     VARCHAR NOT NULL,
    estado        VARCHAR NOT NULL,      -- ok | advertencia | fallida
    evaluadas     INTEGER NOT NULL,
    fallidas      INTEGER NOT NULL,
    descripcion   VARCHAR,
    ejemplos      VARCHAR,               -- JSON con hasta 5 filas de muestra
    PRIMARY KEY (id_ejecucion, regla)
);

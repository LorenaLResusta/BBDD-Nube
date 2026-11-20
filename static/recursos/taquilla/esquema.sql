-- TaquillaAlacant · esquema de la base de datos transaccional (PostgreSQL 15 o superior)
-- Uso: psql "host=... dbname=taquilla user=..." -f esquema.sql

CREATE TABLE IF NOT EXISTS recinto (
    id_recinto   SERIAL PRIMARY KEY,
    nombre       VARCHAR(80)  NOT NULL UNIQUE,
    municipio    VARCHAR(60)  NOT NULL DEFAULT 'Alicante',
    aforo        INTEGER      NOT NULL CHECK (aforo > 0)
);

CREATE TABLE IF NOT EXISTS evento (
    id_evento    SERIAL PRIMARY KEY,
    id_recinto   INTEGER      NOT NULL REFERENCES recinto(id_recinto),
    titulo       VARCHAR(120) NOT NULL,
    categoria    VARCHAR(20)  NOT NULL CHECK (categoria IN ('concierto','teatro','deporte','fiestas','infantil')),
    fecha        TIMESTAMP    NOT NULL,
    precio_base  NUMERIC(7,2) NOT NULL CHECK (precio_base >= 0),
    cartel_s3    VARCHAR(255)                       -- clave del objeto en el bucket de carteles
);

CREATE TABLE IF NOT EXISTS cliente (
    id_cliente   SERIAL PRIMARY KEY,
    email        VARCHAR(120) NOT NULL UNIQUE,
    nombre       VARCHAR(80)  NOT NULL,
    cp           CHAR(5),
    alta         TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS venta (
    id_venta     BIGSERIAL PRIMARY KEY,
    id_evento    INTEGER      NOT NULL REFERENCES evento(id_evento),
    id_cliente   INTEGER      NOT NULL REFERENCES cliente(id_cliente),
    fecha_venta  TIMESTAMP    NOT NULL DEFAULT now(),
    canal        VARCHAR(10)  NOT NULL CHECK (canal IN ('web','app','taquilla')),
    entradas     SMALLINT     NOT NULL CHECK (entradas BETWEEN 1 AND 10),
    importe      NUMERIC(8,2) NOT NULL CHECK (importe >= 0),
    pdf_s3       VARCHAR(255)                       -- clave del PDF de la entrada en S3
);

-- Índices pensados para las consultas habituales (UD04 los analiza con EXPLAIN)
CREATE INDEX IF NOT EXISTS ix_evento_fecha   ON evento (fecha);
CREATE INDEX IF NOT EXISTS ix_venta_evento   ON venta (id_evento);
-- Índice que falta a propósito para la práctica de optimización: venta (fecha_venta)

INSERT INTO recinto (nombre, municipio, aforo) VALUES
  ('Plaza de Toros de Alicante', 'Alicante', 11000),
  ('Teatro Principal', 'Alicante', 1300),
  ('Estadio José Rico Pérez', 'Alicante', 29500),
  ('ADDA Auditorio', 'Alicante', 1600),
  ('Centro de Congresos de Elche', 'Elche', 1000),
  ('Explanada de España', 'Alicante', 20000)
ON CONFLICT (nombre) DO NOTHING;

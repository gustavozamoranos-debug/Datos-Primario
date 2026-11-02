-- Ejecuta este SQL en el SQL Editor de Supabase

CREATE TABLE resumenes (
    id BIGSERIAL PRIMARY KEY,
    tag TEXT,
    archivo TEXT,
    hora INTEGER,
    fecha_proceso TIMESTAMPTZ DEFAULT NOW(),
    n INTEGER,
    promedio DOUBLE PRECISION,
    maximo DOUBLE PRECISION,
    minimo DOUBLE PRECISION,
    final DOUBLE PRECISION,
    inicio DOUBLE PRECISION,
    sobre_100_sin INTEGER DEFAULT 0,
    sobre_100_con INTEGER DEFAULT 0,
    sobre_150_sin INTEGER DEFAULT 0,
    sobre_150_con INTEGER DEFAULT 0,
    sobre_180_sin INTEGER DEFAULT 0,
    sobre_180_con INTEGER DEFAULT 0
);

-- Índices para consultas rápidas
CREATE INDEX idx_resumenes_tag ON resumenes(tag);
CREATE INDEX idx_resumenes_fecha ON resumenes(fecha_proceso DESC);
CREATE INDEX idx_resumenes_hora ON resumenes(hora);

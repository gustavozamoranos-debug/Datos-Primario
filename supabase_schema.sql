-- Ejecuta este SQL en el SQL Editor de Supabase

CREATE TABLE IF NOT EXISTS resumenes (
    id BIGSERIAL PRIMARY KEY,
    tag TEXT,
    archivo TEXT,
    fecha DATE,
    hora INTEGER,
    fecha_proceso TIMESTAMPTZ DEFAULT NOW(),
    n INTEGER,
    promedio DOUBLE PRECISION,
    promedio_sin_carga DOUBLE PRECISION DEFAULT 0,
    maximo DOUBLE PRECISION,
    minimo DOUBLE PRECISION,
    final DOUBLE PRECISION,
    inicio DOUBLE PRECISION,
    arranques INTEGER DEFAULT 0,
    sobre_100_sin INTEGER DEFAULT 0,
    sobre_100_con INTEGER DEFAULT 0,
    sobre_150_sin INTEGER DEFAULT 0,
    sobre_150_con INTEGER DEFAULT 0,
    sobre_180_sin INTEGER DEFAULT 0,
    sobre_180_con INTEGER DEFAULT 0,
    tiempo_con_carga DOUBLE PRECISION DEFAULT 0,
    tiempo_sin_carga DOUBLE PRECISION DEFAULT 0,
    tiempo_detenido DOUBLE PRECISION DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_resumenes_tag ON resumenes(tag);
CREATE INDEX IF NOT EXISTS idx_resumenes_fecha ON resumenes(fecha);
CREATE INDEX IF NOT EXISTS idx_resumenes_hora ON resumenes(hora);
CREATE INDEX IF NOT EXISTS idx_resumenes_tag_fecha_hora ON resumenes(tag, fecha, hora);

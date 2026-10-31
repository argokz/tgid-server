-- Водопровод (фаза 4, шаг 3): запорная арматура (задвижки) модели — для отключения участка. Задвижка стоит на трубе
-- у её конца (узла). Расстановка: «N−1» (strategic — у узла с N трубами задвижки на N−1 из них) или вручную (user);
-- позже — из ГИС водоканала. Только таблицы веба tgid_*. API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_water_valves.sql

CREATE TABLE IF NOT EXISTS tgid_water_valve (
    id          serial        PRIMARY KEY,
    model_id    integer       NOT NULL REFERENCES tgid_water_model (id) ON DELETE CASCADE,
    link_id     varchar(64)   NOT NULL,
    node_id     varchar(64)   NOT NULL,
    source      varchar(16)   NOT NULL DEFAULT 'user',   -- strategic | user | gis
    geom        geometry(Point, 4326),
    created_by  varchar(100),
    created_at  timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (model_id, link_id, node_id)
);

CREATE INDEX IF NOT EXISTS tgid_water_valve_geom_idx ON tgid_water_valve USING gist (geom);

COMMENT ON TABLE tgid_water_valve IS 'Водопровод (web): задвижки модели — на трубе у узла, для отключения участка';

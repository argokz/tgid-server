-- Водопровод (фаза 4): модели EPANET, сеть на карте и расчёты движка водопровода (water_engine). Только таблицы
-- веба tgid_*. API применяет сам (city_schema).
--
-- tgid_water_model — модель: текст .inp (из него считает движок), привязка к карте (своя СК или условное размещение).
-- tgid_water_node  — узлы (Junction, Reservoir, Tank) точками в 4326.
-- tgid_water_link  — участки (Pipe, Pump, Valve) линиями в 4326.
-- tgid_water_run   — расчёты: период, шаг, сводка и значения по шагам (jsonb).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_water.sql

CREATE TABLE IF NOT EXISTS tgid_water_model (
    id             serial        PRIMARY KEY,
    name           varchar(200)  NOT NULL,
    source         varchar(40)   NOT NULL,              -- library:Net3, file
    inp            text          NOT NULL,
    units_in_file  varchar(10),
    placement      jsonb         NOT NULL DEFAULT '{}', -- {mode: srid|schematic, srid | origin_lon, origin_lat, scale_m}
    summary        jsonb         NOT NULL DEFAULT '{}',
    created_by     varchar(100),
    created_at     timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tgid_water_node (
    model_id   integer       NOT NULL REFERENCES tgid_water_model (id) ON DELETE CASCADE,
    node_id    varchar(64)   NOT NULL,
    type       varchar(16)   NOT NULL,
    elevation  double precision,
    attrs      jsonb         NOT NULL DEFAULT '{}',
    geom       geometry(Point, 4326),
    PRIMARY KEY (model_id, node_id)
);

CREATE TABLE IF NOT EXISTS tgid_water_link (
    model_id     integer       NOT NULL REFERENCES tgid_water_model (id) ON DELETE CASCADE,
    link_id      varchar(64)   NOT NULL,
    type         varchar(16)   NOT NULL,
    start_node   varchar(64)   NOT NULL,
    end_node     varchar(64)   NOT NULL,
    length_m     double precision,
    diameter_mm  double precision,
    attrs        jsonb         NOT NULL DEFAULT '{}',
    geom         geometry(LineString, 4326),
    PRIMARY KEY (model_id, link_id)
);

CREATE TABLE IF NOT EXISTS tgid_water_run (
    id             serial        PRIMARY KEY,
    model_id       integer       NOT NULL REFERENCES tgid_water_model (id) ON DELETE CASCADE,
    duration_h     double precision,
    report_step_h  double precision,
    summary        jsonb         NOT NULL DEFAULT '{}',
    results        jsonb         NOT NULL DEFAULT '{}',
    created_by     varchar(100),
    created_at     timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tgid_water_node_geom_idx ON tgid_water_node USING gist (geom);
CREATE INDEX IF NOT EXISTS tgid_water_link_geom_idx ON tgid_water_link USING gist (geom);
CREATE INDEX IF NOT EXISTS tgid_water_run_model_idx ON tgid_water_run (model_id, id DESC);

COMMENT ON TABLE tgid_water_model IS 'Водопровод (web): модели EPANET для расчётного движка водопровода';

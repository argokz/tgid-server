-- Телеметрия (фаза 3 плана модернизации, «Цифровой двойник»): датчики давления, температуры и расхода с привязкой
-- к узлам и участкам сети, их показания и сравнение «факт против модели». Только таблицы веба tgid_*: десктоп их
-- не читает (его поля измеренного давления узла calcpressflow/calcpressret не трогаются). API применяет сам
-- (city_schema).
--
-- tgid_sensor         — датчик: код в SCADA / ОДПУ, что измеряет (давление, температура, расход), подача или
--                       обратка, единица, где стоит (узел или участок).
-- tgid_sensor_reading — показания: (датчик, время) → значение в единицах датчика. Обычная таблица PostgreSQL
--                       с BRIN по времени; если на сервере установлен TimescaleDB — становится гипертаблицей.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261031_telemetry.sql

CREATE TABLE IF NOT EXISTS tgid_sensor (
    id          serial        PRIMARY KEY,
    code        varchar(100)  NOT NULL UNIQUE,
    name        varchar(200)  NOT NULL,
    kind        varchar(20)   NOT NULL CHECK (kind IN ('pressure', 'temperature', 'flow')),
    pipe        varchar(10)   NOT NULL DEFAULT 'supply' CHECK (pipe IN ('supply', 'return')),
    unit        varchar(10)   NOT NULL,
    node_id     integer,
    line_id     integer,
    active      boolean       NOT NULL DEFAULT true,
    note        text          NOT NULL DEFAULT '',
    created_by  varchar(100)  NOT NULL DEFAULT '',
    created_at  timestamptz   NOT NULL DEFAULT now(),
    updated_at  timestamptz   NOT NULL DEFAULT now(),
    CHECK (node_id IS NOT NULL OR line_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS tgid_sensor_reading (
    sensor_id  integer           NOT NULL REFERENCES tgid_sensor (id) ON DELETE CASCADE,
    ts         timestamptz       NOT NULL,
    value      double precision  NOT NULL,
    PRIMARY KEY (sensor_id, ts)
);

CREATE INDEX IF NOT EXISTS tgid_sensor_reading_ts_brin ON tgid_sensor_reading USING brin (ts);

-- TimescaleDB установлен — показания в гипертаблицу (сжатие и удаление старого настраивает служба)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('tgid_sensor_reading', 'ts', if_not_exists => true, migrate_data => true);
    END IF;
END $$;

COMMENT ON TABLE tgid_sensor IS 'Датчики телеметрии (web): давление, температура, расход в узле или на участке';
COMMENT ON TABLE tgid_sensor_reading IS 'Показания датчиков телеметрии (web)';

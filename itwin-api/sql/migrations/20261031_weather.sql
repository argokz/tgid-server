-- Погода для прогноза нагрузки (фаза 3): температура наружного воздуха по часам — прогноз и факт.
-- Источники: Open-Meteo (WEATHER_PROVIDER, по умолчанию), ввод вручную, файл. Только таблицы веба tgid_*.
-- API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261031_weather.sql

CREATE TABLE IF NOT EXISTS tgid_weather (
    ts         timestamptz       NOT NULL,                       -- начало часа, UTC
    kind       varchar(10)       NOT NULL CHECK (kind IN ('forecast', 'fact')),
    t_air      double precision  NOT NULL,                       -- °C
    source     varchar(30)       NOT NULL,                       -- open-meteo, manual, file
    issued_at  timestamptz       NOT NULL DEFAULT now(),
    PRIMARY KEY (ts, kind)
);

COMMENT ON TABLE tgid_weather IS 'Температура наружного воздуха по часам для прогноза нагрузки (web): прогноз и факт';

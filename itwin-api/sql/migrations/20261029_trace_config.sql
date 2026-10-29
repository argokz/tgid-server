-- Именованные настройки трассировки (фаза 1, по образцу конфигураций трассировки ArcGIS Utility Network):
-- тип трассировки и барьеры по условию (задвижки, насосные, узлы заданного напора, источники).
-- Таблица веба: десктоп её не читает. Применять к сетевой БД города, НЕ к UsersDB.
-- API создаёт таблицу сам (database/city_schema.py).
--
-- params — {"trace_type": "...", "stop_at": ["valves", ...]}; shared = false — видна только автору.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261029_trace_config.sql

CREATE TABLE IF NOT EXISTS tgid_trace_config (
    id         serial       PRIMARY KEY,
    name       varchar(200) NOT NULL,
    params     jsonb        NOT NULL DEFAULT '{}'::jsonb,
    author     varchar(100),
    shared     boolean      NOT NULL DEFAULT false,
    created_at timestamptz  NOT NULL DEFAULT now(),
    updated_at timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE tgid_trace_config IS
    'Именованные настройки трассировки сети (web): тип и барьеры по условию';

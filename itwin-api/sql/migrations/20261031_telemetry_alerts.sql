-- Тревоги телеметрии (фаза 3, шаг 2): датчик перешёл в «расхождение» с моделью или «молчит» — и вернулся в норму.
-- Тревога становится событием для внешних систем (вебхуки, лента /api/v2/events). Только таблицы веба tgid_*.
-- API применяет сам (city_schema).
--
-- tgid_sensor.alert_status — последнее состояние для тревог: normal, bad, silent (переход — новая тревога).
-- tgid_sensor_alert        — тревоги: что случилось, показание и модель в тот момент, кто отметил «принято».
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261031_telemetry_alerts.sql

ALTER TABLE tgid_sensor ADD COLUMN IF NOT EXISTS alert_status varchar(10);
ALTER TABLE tgid_sensor ADD COLUMN IF NOT EXISTS alert_since timestamptz;

CREATE TABLE IF NOT EXISTS tgid_sensor_alert (
    id               serial            PRIMARY KEY,
    sensor_id        integer           NOT NULL REFERENCES tgid_sensor (id) ON DELETE CASCADE,
    status           varchar(10)       NOT NULL CHECK (status IN ('bad', 'silent', 'normal')),
    prev_status      varchar(10),
    at               timestamptz       NOT NULL DEFAULT now(),
    value            double precision,
    model            double precision,
    diff             double precision,
    pct              double precision,
    acknowledged_by  varchar(100),
    acknowledged_at  timestamptz
);

CREATE INDEX IF NOT EXISTS tgid_sensor_alert_at_idx ON tgid_sensor_alert (at DESC);

COMMENT ON TABLE tgid_sensor_alert IS 'Тревоги телеметрии (web): расхождение с моделью, датчик молчит, возврат в норму';

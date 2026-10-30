-- Тревоги баланса расхода по зонам (фаза 3, шаг 8): ночной расход вырос, небаланс сверх погрешности, возврат.
-- Тревога становится событием для внешних систем (вебхуки, лента /api/v2/events). Только таблицы веба tgid_*.
-- API применяет сам (city_schema).
--
-- tgid_balance_zone  — последнее состояние зоны (ключ зоны — наименьший id узла зоны, см. database/flow_balance.py).
-- tgid_balance_alert — переходы: что случилось, ночной расход и небаланс в тот момент, кто отметил «принято».
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261031_balance_alerts.sql

CREATE TABLE IF NOT EXISTS tgid_balance_zone (
    zone_key   integer      PRIMARY KEY,
    status     varchar(10)  NOT NULL,
    since      timestamptz  NOT NULL DEFAULT now(),
    boundary   integer[]    NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tgid_balance_alert (
    id               serial            PRIMARY KEY,
    zone_key         integer           NOT NULL,
    zone_kind        varchar(10)       NOT NULL,
    boundary         integer[]         NOT NULL DEFAULT '{}',
    status           varchar(10)       NOT NULL CHECK (status IN ('growth', 'leak', 'normal')),
    prev_status      varchar(10),
    at               timestamptz       NOT NULL DEFAULT now(),
    night            date,
    night_value      double precision,
    night_baseline   double precision,
    night_growth     double precision,
    excess           double precision,
    uncertainty      double precision,
    acknowledged_by  varchar(100),
    acknowledged_at  timestamptz
);

CREATE INDEX IF NOT EXISTS tgid_balance_alert_at_idx ON tgid_balance_alert (at DESC);

COMMENT ON TABLE tgid_balance_alert IS 'Тревоги баланса расхода по зонам (web): ночной рост, небаланс, возврат в норму';

-- Плановые и аварийные отключения (фаза 2): изоляция участка или узла → задвижки и потребители → уведомления.
-- Таблицы веба: десктоп их не читает. Связи с таблицами десктопа (linesobj, nodes) и нарядами — по id без
-- внешних ключей. Применять к сетевой БД города, НЕ к UsersDB. API создаёт таблицы сам (database/city_schema.py).
--
-- status: planned — запланировано; announced — объявлено потребителям; active — идёт; finished — завершено;
-- cancelled — отменено. valves и consumers — снимок расчёта изоляции на момент планирования (database/outages.py),
-- area — зона на карте (GeoJSON WGS 84), public — показывать ли на публичной карте (только зона и число).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_outages.sql

CREATE TABLE IF NOT EXISTS tgid_outage (
    id              serial       PRIMARY KEY,
    number          varchar(30)  NOT NULL DEFAULT '',
    title           varchar(300) NOT NULL,
    kind            varchar(20)  NOT NULL DEFAULT 'planned' CHECK (kind IN ('planned', 'emergency')),
    status          varchar(20)  NOT NULL DEFAULT 'planned'
                    CHECK (status IN ('planned', 'announced', 'active', 'finished', 'cancelled')),
    line_id         integer,
    node_id         integer,
    work_order_id   integer,
    fileid          integer,
    lon             double precision,
    lat             double precision,
    planned_start   timestamptz  NOT NULL,
    planned_end     timestamptz  NOT NULL,
    actual_start    timestamptz,
    actual_end      timestamptz,
    reason          text         NOT NULL DEFAULT '',
    public          boolean      NOT NULL DEFAULT false,
    public_note     text         NOT NULL DEFAULT '',
    consumers_count integer      NOT NULL DEFAULT 0,
    load_gcal_h     double precision NOT NULL DEFAULT 0,
    valves          jsonb        NOT NULL DEFAULT '[]'::jsonb,
    consumers       jsonb        NOT NULL DEFAULT '[]'::jsonb,
    area            jsonb,
    computed_at     timestamptz,
    created_by      varchar(100) NOT NULL DEFAULT '',
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_by      varchar(100),
    updated_at      timestamptz  NOT NULL DEFAULT now(),
    revision        integer      NOT NULL DEFAULT 1,
    CHECK (planned_end > planned_start)
);

CREATE INDEX IF NOT EXISTS tgid_outage_status_idx ON tgid_outage (status, planned_start);
CREATE INDEX IF NOT EXISTS tgid_outage_work_order_idx ON tgid_outage (work_order_id) WHERE work_order_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS tgid_outage_event (
    id          bigserial    PRIMARY KEY,
    outage_id   integer      NOT NULL REFERENCES tgid_outage (id) ON DELETE CASCADE,
    at          timestamptz  NOT NULL DEFAULT now(),
    by_user     varchar(100) NOT NULL DEFAULT '',
    from_status varchar(20),
    to_status   varchar(20),
    note        text         NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS tgid_outage_event_outage_idx ON tgid_outage_event (outage_id, at);

COMMENT ON TABLE tgid_outage IS 'Плановые и аварийные отключения (web): зона, задвижки, потребители, сроки';
COMMENT ON TABLE tgid_outage_event IS 'История отключения (web): смены статуса и комментарии';

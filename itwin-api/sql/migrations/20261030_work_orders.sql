-- Наряды и заявки (фаза 2): заявка или дефект → наряд → бригада → выполнение → закрытие.
-- Таблицы веба: десктоп их не читает. Связи с таблицами десктопа (defect, linesobj, nodes, brigades,
-- nachalniki_uchastkov) — по id без внешних ключей: десктоп удаляет и пересоздаёт свои записи сам.
-- Применять к сетевой БД города, НЕ к UsersDB. API создаёт таблицы сам (database/city_schema.py).
--
-- status: new — заявка; assigned — назначен бригаде; in_progress — в работе; done — выполнен (ждёт приёмки);
-- closed — закрыт (принят); cancelled — отменён. revision растёт при каждом изменении (409 при чужой правке).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_work_orders.sql

CREATE TABLE IF NOT EXISTS tgid_work_order (
    id             serial       PRIMARY KEY,
    number         varchar(30)  NOT NULL DEFAULT '',
    title          varchar(300) NOT NULL,
    kind           varchar(20)  NOT NULL DEFAULT 'repair'
                   CHECK (kind IN ('repair', 'inspection', 'pressure_test', 'excavation', 'maintenance', 'other')),
    priority       smallint     NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 3),
    status         varchar(20)  NOT NULL DEFAULT 'new'
                   CHECK (status IN ('new', 'assigned', 'in_progress', 'done', 'closed', 'cancelled')),
    defect_id      integer,
    line_id        integer,
    node_id        integer,
    fileid         integer,
    lon            double precision,
    lat            double precision,
    brigade_id     integer,
    responsible_id integer,
    planned_start  timestamptz,
    planned_finish timestamptz,
    started_at     timestamptz,
    finished_at    timestamptz,
    closed_at      timestamptz,
    description    text         NOT NULL DEFAULT '',
    result         text         NOT NULL DEFAULT '',
    created_by     varchar(100) NOT NULL DEFAULT '',
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_by     varchar(100),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    revision       integer      NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS tgid_work_order_status_idx ON tgid_work_order (status, priority);
CREATE INDEX IF NOT EXISTS tgid_work_order_defect_idx ON tgid_work_order (defect_id) WHERE defect_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS tgid_work_order_line_idx ON tgid_work_order (line_id) WHERE line_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS tgid_work_order_brigade_idx ON tgid_work_order (brigade_id) WHERE brigade_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS tgid_work_order_event (
    id          bigserial    PRIMARY KEY,
    order_id    integer      NOT NULL REFERENCES tgid_work_order (id) ON DELETE CASCADE,
    at          timestamptz  NOT NULL DEFAULT now(),
    by_user     varchar(100) NOT NULL DEFAULT '',
    from_status varchar(20),
    to_status   varchar(20),
    note        text         NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS tgid_work_order_event_order_idx ON tgid_work_order_event (order_id, at);

COMMENT ON TABLE tgid_work_order IS 'Наряды и заявки (web): дефект → наряд → бригада → закрытие';
COMMENT ON TABLE tgid_work_order_event IS 'История наряда (web): смены статуса и комментарии';

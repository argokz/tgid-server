-- Обход маршрутом и прибытие бригады (фаза 2, полевое приложение, шаг 4).
-- Только добавление к таблицам веба tgid_work_order*: десктоп их не читает. API применяет сам (city_schema).
--
-- tgid_work_order.inspection_id — наряд на осмотр по контуру осмотра десктопа (osmotr): маршрут — его участки
-- (osmotrdeployed), точки обхода — узлы этих участков; дефекты обхода получают osmotrid этого контура.
-- tgid_work_order.arrived_at — когда бригада впервые оказалась у места работ (по треку телефона, 100 м).
-- tgid_work_order_check — отметка узла маршрута: осмотрен или с дефектом (одна на узел, последняя побеждает);
-- client_id — повтор отправки из очереди телефона без дублей.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_work_order_route.sql

ALTER TABLE tgid_work_order ADD COLUMN IF NOT EXISTS inspection_id integer;
ALTER TABLE tgid_work_order ADD COLUMN IF NOT EXISTS arrived_at timestamptz;

CREATE TABLE IF NOT EXISTS tgid_work_order_check (
    id         serial       PRIMARY KEY,
    order_id   integer      NOT NULL REFERENCES tgid_work_order (id) ON DELETE CASCADE,
    node_id    integer      NOT NULL,
    state      varchar(10)  NOT NULL CHECK (state IN ('ok', 'defect')),
    note       varchar(500) NOT NULL DEFAULT '',
    defect_id  integer,
    client_id  uuid,
    lon        double precision,
    lat        double precision,
    by_user    varchar(100) NOT NULL DEFAULT '',
    at         timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (order_id, node_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS tgid_work_order_check_client_idx ON tgid_work_order_check (client_id)
    WHERE client_id IS NOT NULL;

COMMENT ON TABLE tgid_work_order_check IS 'Отметки обхода: узел маршрута осмотрен или с дефектом (web, полевое приложение)';

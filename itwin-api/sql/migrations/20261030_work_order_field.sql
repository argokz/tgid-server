-- Наряды в поле (фаза 2, полевое приложение): фото с места работ, координаты действий, повтор без дублей.
-- Только добавление к таблицам веба tgid_work_order*: десктоп их не читает. API применяет сам (city_schema).
--
-- tgid_work_order_photo — фото наряда (уменьшенное на телефоне, до 2 МБ), с координатами и временем съёмки;
-- хранится в базе, чтобы попадать в её бэкап.
-- tgid_work_order_event.client_id — ключ действия с устройства: повтор той же отправки (связь пропала после
-- записи) не создаёт второй переход или комментарий; lon/lat — где был телефон при действии.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_work_order_field.sql

CREATE TABLE IF NOT EXISTS tgid_work_order_photo (
    id           serial       PRIMARY KEY,
    order_id     integer      NOT NULL REFERENCES tgid_work_order (id) ON DELETE CASCADE,
    client_id    uuid,
    caption      varchar(500) NOT NULL DEFAULT '',
    content_type varchar(50)  NOT NULL,
    size         integer      NOT NULL,
    data         bytea        NOT NULL,
    lon          double precision,
    lat          double precision,
    taken_at     timestamptz,
    by_user      varchar(100) NOT NULL DEFAULT '',
    created_at   timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tgid_work_order_photo_order_idx ON tgid_work_order_photo (order_id);
CREATE UNIQUE INDEX IF NOT EXISTS tgid_work_order_photo_client_idx ON tgid_work_order_photo (client_id)
    WHERE client_id IS NOT NULL;

ALTER TABLE tgid_work_order_event ADD COLUMN IF NOT EXISTS client_id uuid;
ALTER TABLE tgid_work_order_event ADD COLUMN IF NOT EXISTS lon double precision;
ALTER TABLE tgid_work_order_event ADD COLUMN IF NOT EXISTS lat double precision;
CREATE UNIQUE INDEX IF NOT EXISTS tgid_work_order_event_client_idx ON tgid_work_order_event (client_id)
    WHERE client_id IS NOT NULL;

COMMENT ON TABLE tgid_work_order_photo IS 'Фото нарядов с места работ (web, полевое приложение)';

-- Формы обходов (фаза 2, п. 8 плана модернизации): конструктор форм осмотра (подмножество XLSForm), заполнение
-- бригадой в полевом приложении, ответы в карточке наряда. Только таблицы веба tgid_*: десктоп их не читает.
-- API применяет сам (city_schema).
--
-- tgid_form            — форма: название, где заполняется (scope: order — раз на наряд, point — на каждом узле
--                        маршрута обхода), текущая версия, действует ли.
-- tgid_form_version    — поля формы (schema) по версиям: правка формы — новая версия, прежние ответы показываются
--                        по своей версии.
-- tgid_form_submission — заполнение: наряд, узел (у обхода), ответы, где и когда, client_id — повтор отправки
--                        с телефона не дублирует. Фото полей «фото» — фото наряда (tgid_work_order_photo),
--                        в ответе — их client_id.
-- tgid_work_order.form_id — форма, которую бригада заполняет по наряду.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261031_forms.sql

CREATE TABLE IF NOT EXISTS tgid_form (
    id               serial        PRIMARY KEY,
    name             varchar(200)  NOT NULL,
    description      text          NOT NULL DEFAULT '',
    scope            varchar(10)   NOT NULL DEFAULT 'order' CHECK (scope IN ('order', 'point')),
    current_version  integer       NOT NULL DEFAULT 1,
    active           boolean       NOT NULL DEFAULT true,
    created_by       varchar(100)  NOT NULL DEFAULT '',
    created_at       timestamptz   NOT NULL DEFAULT now(),
    updated_by       varchar(100),
    updated_at       timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tgid_form_version (
    form_id     integer       NOT NULL REFERENCES tgid_form (id) ON DELETE CASCADE,
    version     integer       NOT NULL,
    schema      jsonb         NOT NULL,
    created_by  varchar(100)  NOT NULL DEFAULT '',
    created_at  timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (form_id, version)
);

CREATE TABLE IF NOT EXISTS tgid_form_submission (
    id             serial        PRIMARY KEY,
    form_id        integer       NOT NULL,
    version        integer       NOT NULL,
    work_order_id  integer,
    node_id        integer,
    answers        jsonb         NOT NULL,
    lon            double precision,
    lat            double precision,
    client_id      uuid          UNIQUE,
    filled_at      timestamptz,
    submitted_by   varchar(100)  NOT NULL DEFAULT '',
    created_at     timestamptz   NOT NULL DEFAULT now(),
    FOREIGN KEY (form_id, version) REFERENCES tgid_form_version (form_id, version)
);

CREATE INDEX IF NOT EXISTS tgid_form_submission_order_idx ON tgid_form_submission (work_order_id, created_at);
CREATE INDEX IF NOT EXISTS tgid_form_submission_form_idx ON tgid_form_submission (form_id, created_at);

ALTER TABLE tgid_work_order ADD COLUMN IF NOT EXISTS form_id integer;

COMMENT ON TABLE tgid_form IS 'Формы обходов (web): конструктор форм осмотра, подмножество XLSForm';
COMMENT ON TABLE tgid_form_version IS 'Поля формы обхода по версиям (web)';
COMMENT ON TABLE tgid_form_submission IS 'Заполненные формы обходов (web): наряд, узел, ответы';

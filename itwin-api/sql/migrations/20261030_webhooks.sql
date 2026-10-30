-- Вебхуки и лента событий API v2 (фаза 2 плана модернизации): ERP, биллинг, CRM, call-центр узнают о новых
-- дефектах, нарядах и отключениях без опроса журналов. Только таблицы веба tgid_*: десктоп их не читает.
-- API применяет сам (city_schema).
--
-- tgid_api_event        — журнал событий города: тип, объект, когда, короткие данные (без ПДн). Пишет фоновая
--                         задача API из истории нарядов и отключений и из журнала дефектов (там и записи десктопа);
--                         (source, source_id) — запись источника, повторный проход не дублирует. Хранится 30 дней.
-- tgid_api_event_cursor — до какой записи источника дошла задача; floor_id — максимум на момент включения
--                         (раньше него события наружу не уходят).
-- tgid_webhook          — подписка: адрес, типы событий, секрет подписи (HMAC-SHA256, Standard Webhooks).
-- tgid_webhook_delivery — доставка события подписке: попытки, ответ, следующая попытка.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_webhooks.sql

CREATE TABLE IF NOT EXISTS tgid_api_event (
    id           bigserial     PRIMARY KEY,
    type         varchar(40)   NOT NULL,
    object_id    integer,
    occurred_at  timestamptz   NOT NULL,
    data         jsonb         NOT NULL DEFAULT '{}'::jsonb,
    source       varchar(30)   NOT NULL,
    source_id    bigint        NOT NULL,
    created_at   timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS tgid_api_event_created_idx ON tgid_api_event (created_at);

CREATE TABLE IF NOT EXISTS tgid_api_event_cursor (
    source    varchar(30)  PRIMARY KEY,
    last_id   bigint       NOT NULL,
    floor_id  bigint       NOT NULL
);

CREATE TABLE IF NOT EXISTS tgid_webhook (
    id             serial        PRIMARY KEY,
    name           varchar(100)  NOT NULL,
    url            varchar(500)  NOT NULL,
    events         text[]        NOT NULL,
    secret         varchar(80)   NOT NULL,
    active         boolean       NOT NULL DEFAULT true,
    created_by     varchar(100)  NOT NULL DEFAULT '',
    created_at     timestamptz   NOT NULL DEFAULT now(),
    updated_at     timestamptz   NOT NULL DEFAULT now(),
    last_ok_at     timestamptz,
    failing_since  timestamptz,
    disabled_note  varchar(300)
);

CREATE TABLE IF NOT EXISTS tgid_webhook_delivery (
    id            bigserial     PRIMARY KEY,
    webhook_id    integer       NOT NULL REFERENCES tgid_webhook (id) ON DELETE CASCADE,
    event_id      bigint        REFERENCES tgid_api_event (id) ON DELETE CASCADE,
    event_type    varchar(40)   NOT NULL,
    payload       jsonb         NOT NULL,
    status        varchar(10)   NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ok', 'failed')),
    attempts      smallint      NOT NULL DEFAULT 0,
    next_at       timestamptz   NOT NULL DEFAULT now(),
    last_code     smallint,
    last_error    varchar(300),
    created_at    timestamptz   NOT NULL DEFAULT now(),
    delivered_at  timestamptz,
    UNIQUE (webhook_id, event_id)
);

CREATE INDEX IF NOT EXISTS tgid_webhook_delivery_due_idx ON tgid_webhook_delivery (next_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS tgid_webhook_delivery_hook_idx ON tgid_webhook_delivery (webhook_id, id DESC);

COMMENT ON TABLE tgid_api_event IS 'События для внешних систем (web): дефекты, наряды, отключения — вебхуки и /api/v2/events';
COMMENT ON TABLE tgid_webhook IS 'Подписки внешних систем на события (web): адрес, типы, секрет подписи';
COMMENT ON TABLE tgid_webhook_delivery IS 'Доставки событий подпискам (web): попытки и ответы';

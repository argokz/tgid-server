-- Комментарии на карте (фаза 2, п. 4 плана модернизации): ветки обсуждения в точке карты, @упоминания,
-- «решено», ссылка на вид. Только таблицы веба tgid_*: десктоп их не читает. API применяет сам (city_schema).
--
-- tgid_map_thread — ветка: точка (WGS84), вид карты при создании (zoom), необязательная привязка к объекту сети
-- (участок или узел), кто начал, когда последняя активность, решена ли.
-- tgid_map_comment — сообщения ветки; mentions — логины из @упоминаний; удалённое сообщение остаётся строкой
-- («удалено»), чтобы ответы на него не теряли смысл.
-- tgid_map_comment_seen — когда пользователь последний раз открывал ветку (непрочитанное для упоминаний и ответов).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_map_comments.sql

CREATE TABLE IF NOT EXISTS tgid_map_thread (
    id           serial           PRIMARY KEY,
    lon          double precision NOT NULL,
    lat          double precision NOT NULL,
    zoom         real,
    object_kind  varchar(10)      CHECK (object_kind IN ('line', 'node')),
    object_id    integer,
    created_by   varchar(100)     NOT NULL DEFAULT '',
    created_at   timestamptz      NOT NULL DEFAULT now(),
    last_at      timestamptz      NOT NULL DEFAULT now(),
    resolved_at  timestamptz,
    resolved_by  varchar(100)
);

CREATE INDEX IF NOT EXISTS tgid_map_thread_open_idx ON tgid_map_thread (last_at DESC) WHERE resolved_at IS NULL;

CREATE TABLE IF NOT EXISTS tgid_map_comment (
    id          serial       PRIMARY KEY,
    thread_id   integer      NOT NULL REFERENCES tgid_map_thread (id) ON DELETE CASCADE,
    body        text         NOT NULL,
    mentions    text[]       NOT NULL DEFAULT '{}',
    author      varchar(100) NOT NULL DEFAULT '',
    created_at  timestamptz  NOT NULL DEFAULT now(),
    edited_at   timestamptz,
    deleted_at  timestamptz
);

CREATE INDEX IF NOT EXISTS tgid_map_comment_thread_idx ON tgid_map_comment (thread_id, created_at);
CREATE INDEX IF NOT EXISTS tgid_map_comment_mentions_idx ON tgid_map_comment USING gin (mentions);

CREATE TABLE IF NOT EXISTS tgid_map_comment_seen (
    login      varchar(100) NOT NULL,
    thread_id  integer      NOT NULL REFERENCES tgid_map_thread (id) ON DELETE CASCADE,
    seen_at    timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (login, thread_id)
);

COMMENT ON TABLE tgid_map_thread IS 'Комментарии на карте: ветки обсуждения в точке (web)';
COMMENT ON TABLE tgid_map_comment IS 'Комментарии на карте: сообщения веток, @упоминания (web)';

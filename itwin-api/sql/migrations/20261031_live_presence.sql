-- Присутствие на карте (фаза 2, п. 11 плана модернизации): кто сейчас работает с картой города, где смотрит и
-- какой объект правит. Строку обновляет браузер раз в 20 с; старше минуты — человек ушёл. UNLOGGED: после сбоя
-- сервера базы таблица пустая — это нормально, браузеры заполнят её снова. Только таблица веба: десктоп её не читает.
-- API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261031_live_presence.sql

CREATE UNLOGGED TABLE IF NOT EXISTS tgid_live_presence (
    session_id     uuid          PRIMARY KEY,
    username       varchar(100)  NOT NULL,
    center_lon     double precision,
    center_lat     double precision,
    zoom           real,
    editing_kind   varchar(20),
    editing_id     integer,
    editing_label  varchar(200),
    started_at     timestamptz   NOT NULL DEFAULT now(),
    seen_at        timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tgid_live_presence_seen_idx ON tgid_live_presence (seen_at);

COMMENT ON TABLE tgid_live_presence IS 'Кто сейчас на карте (web): вид и объект правки, обновляется раз в 20 с';

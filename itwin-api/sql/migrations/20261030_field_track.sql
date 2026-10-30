-- Трек бригады (фаза 2, полевое приложение): точки телефона, пока бригада включила «Передавать местоположение».
-- Только таблица веба tgid_*: десктоп её не читает. API применяет сам (city_schema).
--
-- Точка — кто (вход), бригада, когда снята на телефоне, координаты WGS84 и точность GPS. Телефон без связи копит
-- точки и отправляет пачкой; повтор той же пачки не дублирует точки (ключ — пользователь и время снятия).
-- Старше 90 дней точки удаляются при записи новых (database/field_track.py, TRACK_KEEP_DAYS).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_field_track.sql

CREATE TABLE IF NOT EXISTS tgid_field_track (
    id          bigserial        PRIMARY KEY,
    by_user     varchar(100)     NOT NULL,
    brigade_id  integer,
    recorded_at timestamptz      NOT NULL,
    lon         double precision NOT NULL,
    lat         double precision NOT NULL,
    accuracy    real,
    created_at  timestamptz      NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS tgid_field_track_point_idx ON tgid_field_track (by_user, recorded_at);
CREATE INDEX IF NOT EXISTS tgid_field_track_time_idx ON tgid_field_track (recorded_at);
CREATE INDEX IF NOT EXISTS tgid_field_track_brigade_idx ON tgid_field_track (brigade_id, recorded_at);

COMMENT ON TABLE tgid_field_track IS 'Трек бригад из полевого приложения (web): точки телефона, хранятся 90 дней';

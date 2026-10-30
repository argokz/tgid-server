-- Социальные объекты (POI, фаза 2 плана модернизации): школы, детские сады, больницы, поликлиники, учреждения
-- соцзащиты — для выборок «в 500 м от школ» и приоритета при отключениях. Только таблица веба tgid_*: десктоп её
-- не читает. API применяет сам (city_schema).
--
-- tgid_poi — объект точкой WGS 84:
--   source      — откуда: consumers (найден по названию потребителя сети), file (файл акимата), osm (OpenStreetMap);
--   source_key  — ключ в источнике (узел и категория, номер строки файла, тип и id OSM): повторная загрузка
--                 обновляет, а не дублирует;
--   hidden      — администратор скрыл ошибочно найденный объект (повторная загрузка этот выбор не сбрасывает).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_poi.sql

CREATE TABLE IF NOT EXISTS tgid_poi (
    id          serial                 PRIMARY KEY,
    category    varchar(20)            NOT NULL,
    name        text                   NOT NULL DEFAULT '',
    address     text,
    shape       geometry(Point, 4326)  NOT NULL,
    source      varchar(20)            NOT NULL,
    source_key  varchar(120)           NOT NULL,
    hidden      boolean                NOT NULL DEFAULT false,
    attrs       jsonb,
    updated_at  timestamptz            NOT NULL DEFAULT now(),
    updated_by  varchar(100)           NOT NULL DEFAULT '',
    UNIQUE (source, source_key)
);

CREATE INDEX IF NOT EXISTS tgid_poi_shape_idx ON tgid_poi USING gist (shape);
CREATE INDEX IF NOT EXISTS tgid_poi_geog_idx ON tgid_poi USING gist ((shape::geography));
CREATE INDEX IF NOT EXISTS tgid_poi_category_idx ON tgid_poi (category) WHERE NOT hidden;

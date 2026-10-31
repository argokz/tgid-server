-- План перекладок (фаза 5, шаг 3): последствия аварии на каждом участке теплосети — кого отключит изоляция
-- задвижками (database/outage_consequence.py): потребители зоны и ниже закрытых задвижек, нагрузка, социальные
-- объекты. Оценка по топологии, как и изоляция. Только таблицы веба tgid_*, пересчёт — API. API применяет сам
-- (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_line_consequence.sql

CREATE TABLE IF NOT EXISTS tgid_line_consequence (
    lineid          integer           PRIMARY KEY,
    zone_consumers  integer           NOT NULL,   -- потребители в зоне отключения (между задвижками)
    zone_load       double precision  NOT NULL,   -- их нагрузка, Гкал/ч
    zone_social     integer           NOT NULL,   -- из них школы, детсады, больницы, поликлиники, соцучреждения
    down_consumers  integer           NOT NULL,   -- ниже закрытых задвижек, без обходного питания
    down_load       double precision  NOT NULL,
    down_social     integer           NOT NULL
);

-- отчёты пересчёта: сколько участков, потребителей, время
CREATE TABLE IF NOT EXISTS tgid_line_consequence_run (
    id          serial       PRIMARY KEY,
    report      jsonb        NOT NULL,
    created_by  varchar(100),
    created_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE tgid_line_consequence IS 'Теплосеть (web): кого отключит авария на участке (database/outage_consequence.py)';

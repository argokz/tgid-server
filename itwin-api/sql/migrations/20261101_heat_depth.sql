-- Общая карта коммуникаций (фаза 4, шаг 6): глубина заложения теплосети, вычисленная из отметок узлов
-- (database/heat_depth.py): отметка земли − отметка верха трубы на концах участка; где концы неизвестны — оценка по
-- ближайшим узлам сети. Поле паспорта pipelinelayingdepth в базах городов не заполнено (значение по умолчанию).
-- Только таблицы веба tgid_*, пересчёт — API. API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_heat_depth.sql

CREATE TABLE IF NOT EXISTS tgid_heat_depth (
    lineid       integer          PRIMARY KEY,
    depth_start  double precision,               -- до верха трубы у начала геометрии участка, м (минус — над землёй)
    depth_end    double precision,               -- у конца геометрии
    source       varchar(16)      NOT NULL,      -- nodes (оба конца) | node (один) | neighbors (оценка по сети)
    hops         smallint,                       -- для neighbors: через сколько участков найдены узлы с глубиной
    updated_at   timestamptz      NOT NULL DEFAULT now()
);

-- отчёты пересчёта: сколько участков с глубиной и точность оценки по соседям (holdout)
CREATE TABLE IF NOT EXISTS tgid_heat_depth_run (
    id          serial       PRIMARY KEY,
    report      jsonb        NOT NULL,
    created_by  varchar(100),
    created_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE tgid_heat_depth IS 'Теплосеть (web): глубина заложения участков из отметок узлов (database/heat_depth.py)';

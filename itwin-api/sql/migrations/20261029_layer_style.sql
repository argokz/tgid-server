-- Стили тематических карт (Smart Mapping, фаза 1, по образцу JSON-стиля слоя Felt FSL):
-- тема, способ классификации, границы классов, палитра, толщина. Таблица веба: десктоп её не читает.
-- Применять к сетевой БД города, НЕ к UsersDB. API создаёт таблицу сам (database/city_schema.py).
--
-- style — JSON (database/layer_styles.py, clean_style); revision растёт при каждом сохранении;
-- shared = false — виден только автору.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261029_layer_style.sql

CREATE TABLE IF NOT EXISTS tgid_layer_style (
    id         serial       PRIMARY KEY,
    name       varchar(200) NOT NULL,
    style      jsonb        NOT NULL DEFAULT '{}'::jsonb,
    revision   integer      NOT NULL DEFAULT 1,
    author     varchar(100),
    shared     boolean      NOT NULL DEFAULT false,
    created_at timestamptz  NOT NULL DEFAULT now(),
    updated_at timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE tgid_layer_style IS
    'Стили тематических карт сети (web): тема, классы, палитра — JSON';

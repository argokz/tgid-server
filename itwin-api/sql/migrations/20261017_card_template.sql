-- Шаблоны свойств объектов (веб: окно свойств — «Сохранить как шаблон», «Применить шаблон»,
-- «Шаблон для новых» при рисовании участков).
-- Применять к сетевой БД города (almatygid, astanagid_*, shatura, копии), НЕ к UsersDB (alembic).
-- API создаёт таблицу сам при первом обращении (тот же SQL), если у пользователя БД есть право.
--
-- values — {таблица (lower): {поле: значение}}; kind — вид объекта (line — участок).
-- shared = false — шаблон виден только автору.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261017_card_template.sql

CREATE TABLE IF NOT EXISTS card_template (
    id         serial PRIMARY KEY,
    kind       varchar(20)  NOT NULL,
    name       varchar(200) NOT NULL,
    "values"   jsonb        NOT NULL DEFAULT '{}'::jsonb,
    author     varchar(100),
    shared     boolean      NOT NULL DEFAULT false,
    created_at timestamptz  NOT NULL DEFAULT now(),
    updated_at timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS card_template_kind_idx ON card_template (kind);

COMMENT ON TABLE card_template IS
    'Шаблоны свойств объектов сети (web): значения полей карточки для новых и выбранных объектов';

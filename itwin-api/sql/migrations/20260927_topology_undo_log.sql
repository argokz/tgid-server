-- Журнал операций редактора топологии для отмены (этап 8, B5 undo).
-- Применять к сетевой БД (almatygid / копия), НЕ к UsersDB (alembic).
-- Без этой таблицы операции топологии работают, но отмена недоступна.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20260927_topology_undo_log.sql

CREATE TABLE IF NOT EXISTS topology_undo_log (
    id              bigserial PRIMARY KEY,
    -- совпадает с change_group_id записей audit_log этой операции
    change_group_id uuid         NOT NULL,
    actor           varchar(100),
    operation       varchar(32)  NOT NULL,
    summary         jsonb,
    -- [{"t": таблица, "id": id, "row": образ строки до операции | null — строка создана операцией}]
    before_rows     jsonb        NOT NULL,
    -- {"таблица:id": md5 образа строки после операции}: отмена только если строки не менялись
    after_hashes    jsonb        NOT NULL,
    -- таблицы без колонки id, затронутые операцией (такую операцию отменить нельзя)
    unsupported     jsonb,
    created_at      timestamp    NOT NULL DEFAULT now(),
    undone_at       timestamp,
    undone_by       varchar(100),
    undo_group_id   uuid
);

CREATE INDEX IF NOT EXISTS topology_undo_log_actor_open_idx
    ON topology_undo_log (actor, id DESC)
    WHERE undone_at IS NULL;

COMMENT ON TABLE topology_undo_log IS
    'Журнал операций редактора топологии (web): before-image затронутых строк для отмены последней операции';

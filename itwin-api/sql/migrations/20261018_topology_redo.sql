-- Повтор отменённой операции редактора топологии (Ctrl+Y).
-- Применять к сетевой БД после 20260927_topology_undo_log.sql. Без этих колонок отмена
-- работает как раньше, а повтор недоступен.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261018_topology_redo.sql

ALTER TABLE topology_undo_log
    -- [{"t": таблица, "id": id, "row": образ строки после операции | null}] — снимается при отмене
    ADD COLUMN IF NOT EXISTS after_rows jsonb,
    ADD COLUMN IF NOT EXISTS redone_at  timestamp;

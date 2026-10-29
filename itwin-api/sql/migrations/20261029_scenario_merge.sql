-- Перенос правок сценария в основу (database/scenario_merge.py): объект, добавленный в сценарии и
-- перенесённый в основу, получает строку соответствия «новый объект основы ← объект копии».
-- merge_group_id — группа операции переноса (topology_undo_log.change_group_id): после отмены
-- операции такие строки не учитываются, после повтора — снова учитываются.
-- Применять к сетевой БД города, НЕ к UsersDB.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261029_scenario_merge.sql

ALTER TABLE tgid_scenario_object ADD COLUMN IF NOT EXISTS merge_group_id uuid;

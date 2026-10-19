-- Автор объектов сети, созданных в вебе (право «только свои», permissions.py).
-- Применять к сетевой БД города (almatygid / astanagid_* / shatura / копии), НЕ к UsersDB.
-- Пишет журнал операций топологии (database/topology_journal.OperationJournal.commit).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261020_object_authorship.sql

CREATE TABLE IF NOT EXISTS object_authorship (
    table_name   varchar(64)  NOT NULL,
    record_id    integer      NOT NULL,
    created_by   varchar(100) NOT NULL,
    created_at   timestamp    NOT NULL DEFAULT now(),
    -- topology_undo_log.id операции, создавшей строку
    operation_id bigint,
    PRIMARY KEY (table_name, record_id)
);

CREATE INDEX IF NOT EXISTS object_authorship_created_by_idx ON object_authorship (created_by, created_at DESC);

COMMENT ON TABLE object_authorship IS
    'Кто создал объект сети в вебе: право «только свои» (удаление, перемещение, свойства)';

-- Роли PostgreSQL веба (DB_ROLE_SWITCH, sql/pg_auth): запись — тем, кто пишет журнал операций
DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['tgid_editor', 'tgid_admin', 'tgid_operator', 'tgid_calculator', 'tgid_viewer', 'tgid_cap_network', 'tgid_cap_network_struct'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('GRANT SELECT ON object_authorship TO %I', r);
            IF r NOT IN ('tgid_viewer', 'tgid_calculator') THEN
                EXECUTE format('GRANT INSERT ON object_authorship TO %I', r);
            END IF;
        END IF;
    END LOOP;
END $$;

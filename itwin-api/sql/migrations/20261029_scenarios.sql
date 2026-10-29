-- Сценарии «что если» (фаза 1): сценарий — копия фрагмента, как в десктопе, плюс соответствие
-- объектов копии объектам основы. По нему веб сравнивает сценарий с основой (database/scenarios.py).
-- Таблицы веба: десктоп их не читает; копия фрагмента для него — обычный фрагмент.
-- Применять к сетевой БД города (almatygid / astanagid_* / shatura / копии), НЕ к UsersDB.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261029_scenarios.sql

CREATE TABLE IF NOT EXISTS tgid_scenario (
    id           serial       PRIMARY KEY,
    name         varchar(200) NOT NULL,
    note         text,
    -- фрагмент-основа и его копия (fragments.id); без внешних ключей: десктоп может удалить фрагмент
    base_fileid  integer      NOT NULL,
    fileid       integer      NOT NULL UNIQUE,
    created_by   varchar(100),
    created_at   timestamp    NOT NULL DEFAULT now(),
    -- active — в работе, archived — убран из списка
    status       varchar(16)  NOT NULL DEFAULT 'active'
);

-- Объект копии (copy_id) ← объект основы (base_id) той же таблицы на момент создания сценария
CREATE TABLE IF NOT EXISTS tgid_scenario_object (
    scenario_id  integer      NOT NULL REFERENCES tgid_scenario (id) ON DELETE CASCADE,
    table_name   varchar(64)  NOT NULL,
    base_id      integer      NOT NULL,
    copy_id      integer      NOT NULL,
    -- md5 строки основы при создании (как её видит выгрузка .tgid, ссылки — в id основы):
    -- отличает правку сценария от правки основы и находит конфликты
    base_hash    varchar(32),
    PRIMARY KEY (scenario_id, table_name, copy_id)
);

COMMENT ON TABLE tgid_scenario IS
    'Сценарии «что если» веба: копия фрагмента-основы, в которой правят и считают вариант сети';
COMMENT ON TABLE tgid_scenario_object IS
    'Соответствие объектов копии-сценария объектам основы — для сравнения сценария с основой';

-- Роли PostgreSQL веба (DB_ROLE_SWITCH, sql/pg_auth): чтение всем, запись — тем, кто правит сеть
DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['tgid_editor', 'tgid_admin', 'tgid_operator', 'tgid_calculator', 'tgid_viewer', 'tgid_cap_network', 'tgid_cap_network_struct'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('GRANT SELECT ON tgid_scenario, tgid_scenario_object TO %I', r);
            IF r NOT IN ('tgid_viewer', 'tgid_calculator') THEN
                EXECUTE format('GRANT INSERT, UPDATE, DELETE ON tgid_scenario, tgid_scenario_object TO %I', r);
                EXECUTE format('GRANT USAGE ON SEQUENCE tgid_scenario_id_seq TO %I', r);
            END IF;
        END IF;
    END LOOP;
END $$;

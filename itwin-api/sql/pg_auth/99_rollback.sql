-- TGID: откат 02–04 в одной базе (политики RLS, права ролей tgid_*, схема tgid_auth).
-- Роли кластера не удаляет (они могут использоваться другими базами) — см. 99_drop_roles.sql.
--
--   psql ... -d almatygid_copy -v target_db=almatygid_copy -f 99_rollback.sql
--
-- До 02–04 в базах TGID не было ни политик RLS, ни default privileges (проверено 06.10.2026),
-- поэтому откат возвращает ровно исходное состояние.

\set ON_ERROR_STOP on
\if :{?target_db}
\else
  \echo 'Укажите базу: -v target_db=<имя базы>'
  \quit
\endif
SELECT current_database() = :'target_db' AS on_target \gset
\if :on_target
\else
  \echo 'Скрипт запущен не в той базе (ожидалась ' :'target_db' ')'
  \quit
\endif

BEGIN;

-- Политики tgid_* и RLS на таблицах public
DO $$
DECLARE p record;
BEGIN
    FOR p IN SELECT schemaname, tablename, policyname FROM pg_policies
              WHERE schemaname = 'public' AND policyname LIKE 'tgid\_%' LOOP
        EXECUTE format('DROP POLICY %I ON %I.%I', p.policyname, p.schemaname, p.tablename);
    END LOOP;
    FOR p IN SELECT c.relname FROM pg_class c
              WHERE c.relnamespace = 'public'::regnamespace AND c.relrowsecurity
                AND NOT EXISTS (SELECT 1 FROM pg_policies x WHERE x.schemaname = 'public' AND x.tablename = c.relname) LOOP
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', p.relname);
    END LOOP;
END $$;

-- Default privileges, выданные ролям tgid_*
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM tgid_anon, tgid_geoserver, tgid_worker, tgid_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM tgid_viewer, tgid_worker;

-- Все права ролей tgid_* в этой базе и объекты, которыми они владеют (схема tgid_auth)
DROP SCHEMA IF EXISTS tgid_auth CASCADE;
DROP OWNED BY tgid_owner, tgid_useradmin, tgid_api, tgid_worker, tgid_geoserver, tgid_users,
    tgid_anon, tgid_viewer, tgid_calculator, tgid_editor, tgid_admin,
    tgid_cap_network, tgid_cap_network_struct, tgid_cap_acts, tgid_cap_geo,
    tgid_cap_pts, tgid_cap_corrosion, tgid_cap_repairs;

DO $$ BEGIN
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM tgid_api, tgid_worker, tgid_geoserver, tgid_users',
                   current_database());
END $$;

COMMIT;

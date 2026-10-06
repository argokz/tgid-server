-- TGID: матрица прав (GRANT) по группам таблиц. В каждой базе TGID, от суперпользователя,
-- после 02_auth_schema.sql. Идемпотентно. Таблицы, которых нет в базе, пропускаются.
--
--   psql ... -d almatygid_copy -v target_db=almatygid_copy -f 03_grants.sql
--
-- Источник списков — реестры кода API (auth.MUTABLE_TABLES, journal_specs, dictionaries,
-- electrical_binding, fragment_transfer.IMPORT_ORDER) и права десктопа (gid8/gid8/any/rights.h).
-- Закрыто по умолчанию: таблицу, которой нет ни в одной группе, правит только tgid_admin.

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

CREATE OR REPLACE FUNCTION pg_temp.grant_on(p_privs text, p_tables text[], p_roles text[]) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE t text; r text; n integer := 0;
BEGIN
    FOREACH t IN ARRAY p_tables LOOP
        IF to_regclass(format('public.%I', t)) IS NULL THEN
            CONTINUE;
        END IF;
        FOREACH r IN ARRAY p_roles LOOP
            EXECUTE format('GRANT %s ON public.%I TO %I', p_privs, t, r);
        END LOOP;
        n := n + 1;
    END LOOP;
    RETURN n;
END $$;

-- ── Схемы и чтение ──────────────────────────────────────────────────────────────────────

-- Никто, кроме владельцев, не создаёт объекты в public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO tgid_anon, tgid_worker, tgid_geoserver;
DO $$ BEGIN
    IF to_regnamespace('net') IS NOT NULL THEN
        GRANT USAGE ON SCHEMA net TO tgid_anon, tgid_worker, tgid_geoserver;
        GRANT SELECT ON ALL TABLES IN SCHEMA net TO tgid_anon, tgid_worker, tgid_geoserver;
        GRANT ALL ON ALL TABLES IN SCHEMA net TO tgid_admin;
    END IF;
END $$;

-- Чтение всего public: аноним (карта при AUTH_REQUIRED_GET=false), GeoServer, воркер
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tgid_anon, tgid_geoserver, tgid_worker;
-- …кроме учётных данных десктопа и служебных журналов
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['passwords', 'password', 'audit_log', 'audit_group_comments', 'topology_undo_log'] LOOP
        IF to_regclass(format('public.%I', t)) IS NOT NULL THEN
            EXECUTE format('REVOKE ALL ON public.%I FROM tgid_anon, tgid_geoserver, tgid_worker', t);
        END IF;
    END LOOP;
END $$;
-- Имя оператора в карточках (operatorID → passwords.user_name, GID.lookup): только id и имя,
-- хеш пароля и маска прав закрыты
DO $$ BEGIN
    IF to_regclass('public.passwords') IS NOT NULL THEN
        GRANT SELECT (id, user_name) ON public.passwords TO tgid_anon, tgid_geoserver, tgid_worker;
    END IF;
END $$;
-- История правок — вошедшим пользователям (viewer и выше)
SELECT pg_temp.grant_on('SELECT', ARRAY['audit_log', 'audit_group_comments', 'topology_undo_log'], ARRAY['tgid_viewer']);
-- Запись в историю: триггеры аудита (SECURITY INVOKER) пишут от имени пользователя;
-- RLS (04_rls.sql) пропускает только changed_by = current_user
SELECT pg_temp.grant_on('INSERT', ARRAY['audit_log', 'audit_group_comments'], ARRAY['tgid_viewer', 'tgid_worker']);
-- Откат групповых операций помечает строки истории (только этот столбец)
DO $$ BEGIN
    IF to_regclass('public.audit_log') IS NOT NULL THEN
        GRANT UPDATE (is_rolled_back) ON public.audit_log TO tgid_editor, tgid_cap_network;
    END IF;
END $$;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tgid_viewer, tgid_worker;

-- Опасные функции — только владельцам
DO $$
DECLARE f regprocedure;
BEGIN
    FOR f IN SELECT p.oid::regprocedure FROM pg_proc p
              WHERE p.pronamespace = 'public'::regnamespace AND p.proname = 'find_file_deep' LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', f);
    END LOOP;
END $$;

-- ── Расчёты: calculator и воркер ────────────────────────────────────────────────────────

DO $$
DECLARE calc text[];
BEGIN
    SELECT array_agg(c.relname::text) INTO calc
      FROM pg_class c
     WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p')
       AND (c.relname LIKE '%\_out'
            OR c.relname IN ('calculation', 'calculation_iznos', 'temp_line', 'temp_node')
            OR c.relname LIKE 'heatloses%' OR c.relname LIKE 'heatlosses%'
            OR c.relname LIKE 'losesbyfilling%' OR c.relname LIKE 'heatpipesectionsharness%');
    PERFORM pg_temp.grant_on('INSERT, UPDATE, DELETE, TRUNCATE', calc, ARRAY['tgid_calculator', 'tgid_worker']);
END $$;

-- ── Журналы, ТУ, АЛСЕКО, электросеть, пьезометр, температурные графики, справочники: editor ─

SELECT pg_temp.grant_on('INSERT, UPDATE, DELETE', ARRAY[
    -- нарушения, шурфовки, осмотры, опрессовки (journal_specs) и их дочерние таблицы
    'defect', 'defectdocuments', 'defectchannel', 'defectkamera', 'defectmeropr', 'defectopis', 'defecttube',
    'defectsforshurfy',
    'shurfy', 'shurfdocuments', 'vidy_elementov_for_shurfy', 'nalichie_vblizi_kommunikacij_for_shurfy',
    'osmotr', 'osmotrdeployed', 'osmotrdocuments',
    'opres', 'opresdeployed', 'opresdocuments', 'opresacts', 'opresmeropr',
    'ochered_opressovok', 'opressovki_uchastok_ocheredi', 'list_opres_node1', 'list_opres_node2',
    -- технические условия, АЛСЕКО
    'tehnicheskie_usloviya', 'nagruzki', 'zdaniya_2',
    -- электросеть (electrical_binding.ALLOWED_TABLES) и документы
    'istochnik_elektrosnabzheniya', 'liniya_elektroperedach', 'priemnik_elektrosnabzheniya',
    'kabelnyy_kanal_es', 'mufta', 'opora_es', 'gilza_es',
    'kabelnyy_kanal_esdocuments', 'muftadocuments', 'opora_esdocuments', 'gilza_esdocuments',
    'electrodocuments', 'electrodocumentsist', 'electrodocumentspr',
    -- направления пьезометра, температурные графики
    'directions', 'deployeddirections', 'deployedtempgraphs', 'deployedtempgraphsfact',
    -- справочники (database/dictionaries.DICTIONARIES)
    'administrativnyy_rayon', 'calctemperatures', 'gvsloadgraphs', 'organizations',
    'rayon_ekspluatatsii', 'responsibles', 'specexpends', 'varcoefficients'
], ARRAY['tgid_editor']);

-- ── Предметные права (биты user_right) ──────────────────────────────────────────────────

-- Индикаторы коррозии (бит 128)
SELECT pg_temp.grant_on('INSERT, UPDATE, DELETE',
    ARRAY['indikator_korrozii', 'indikator_korrozii_po_godam', 'corrosionindicators'],
    ARRAY['tgid_cap_corrosion']);

-- Ремонты (бит 1024)
SELECT pg_temp.grant_on('INSERT, UPDATE, DELETE',
    ARRAY['remont2', 'remont2deployed', 'remontdocuments', 'remont', 'plan_remont'],
    ARRAY['tgid_cap_repairs']);

-- Производственная служба / ПТС (бит 64)
SELECT pg_temp.grant_on('INSERT, UPDATE, DELETE', ARRAY[
    'uchastok_ms', 'uchastok_rs', 'uchastki_ekspluatatsii', 'pasport_uchastka_ms', 'pasport_uchastka_rs',
    'sortlinesforuchastok', 'sortnodesforuchastok', 'magistrali', 'magistrals', 'raspredseti', 'nachalniki_uchastkov'
], ARRAY['tgid_cap_pts']);

-- Акты (бит 8, инвертирован)
SELECT pg_temp.grant_on('INSERT, UPDATE, DELETE', ARRAY['act'], ARRAY['tgid_cap_acts']);

-- Гидравлическая сеть (бит 4): атрибуты — UPDATE; добавление/удаление объектов (нет бита 32) — INSERT/DELETE
DO $$
DECLARE net text[] := ARRAY[
    'nodes', 'linesobj', 'heatpipesections', 'pipesections', 'connectnodes', 'internalnodes', 'setpressnodes',
    'externalcodes', 'texts',
    'realconsumers', 'generalizedconsumers', 'heatsources', 'pumpstations',
    'airheaters', 'buildingentries', 'bypass', 'consumptregulators', 'dampers', 'diaphragms', 'elevators',
    'heatchambers', 'heatexchangers', 'overgroundnodes', 'undergroundnodes', 'uninstallednodes', 'pavilions',
    'pressdropregulators', 'pressregulators', 'pumps', 'refillnodes', 'regularmatures', 'reversevalves',
    'systemradiators', 'threewayvalves', 'trps', 'wdodevices',
    'realconsumerdocuments1', 'realconsumerdocuments2', 'realconsumerdocuments3'];
BEGIN
    PERFORM pg_temp.grant_on('UPDATE', net, ARRAY['tgid_cap_network']);
    PERFORM pg_temp.grant_on('INSERT, DELETE', net, ARRAY['tgid_cap_network_struct']);
    PERFORM pg_temp.grant_on('INSERT, UPDATE', ARRAY['topology_undo_log'], ARRAY['tgid_cap_network']);
    PERFORM pg_temp.grant_on('SELECT', ARRAY['topology_undo_log'], ARRAY['tgid_cap_network']);
END $$;

-- Геобаза (бит 16, инвертирован): слои с геометрией, не вошедшие в группы выше
DO $$
DECLARE geo text[];
BEGIN
    SELECT array_agg(g.f_table_name::text) INTO geo
      FROM geometry_columns g
     WHERE g.f_table_schema = 'public'
       AND g.f_table_name NOT IN (
           'nodes', 'linesobj', 'defect', 'shurfy', 'indikator_korrozii', 'corrosionindicators', 'act',
           'remont', 'zdaniya_2', 'istochnik_elektrosnabzheniya', 'liniya_elektroperedach',
           'priemnik_elektrosnabzheniya', 'kabelnyy_kanal_es', 'mufta', 'opora_es', 'gilza_es');
    PERFORM pg_temp.grant_on('INSERT, UPDATE, DELETE', coalesce(geo, '{}'), ARRAY['tgid_cap_geo']);
END $$;

-- ── Администратор: всё ──────────────────────────────────────────────────────────────────

GRANT ALL ON ALL TABLES IN SCHEMA public TO tgid_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO tgid_admin;

-- ── Новые объекты (созданные postgres — миграции, скрипты десктопа) ─────────────────────

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT ON TABLES TO tgid_anon, tgid_geoserver, tgid_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT ALL ON TABLES TO tgid_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO tgid_viewer, tgid_worker;

-- Подключение к базе
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO tgid_api, tgid_worker, tgid_geoserver, tgid_users',
                   current_database());
END $$;

COMMIT;

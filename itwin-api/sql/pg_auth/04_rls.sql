-- TGID: row-level security — правка ограничена территорией пользователя (фрагменты),
-- чтение — вся сеть. В каждой базе TGID, от суперпользователя, после 03_grants.sql. Идемпотентно.
--
--   psql ... -d almatygid_copy -v target_db=almatygid_copy -f 04_rls.sql
--
-- Фрагмент строки определяется по первой найденной колонке: fileid → lineid (linesobj.fileid)
-- → nodeid / nodeid1 / nodeoprid1 (nodes.fileid). Строка без привязки (NULL) правится без ограничения
-- территории (права на таблицу всё равно нужны — 03_grants.sql).
-- RLS не включается принудительно (не FORCE): владелец таблиц postgres (десктоп до перехода,
-- миграции) работает как раньше.

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

-- Явная ошибка для правки/удаления чужой строки. Политика USING на UPDATE/DELETE молча
-- отфильтровала бы строку («обновлено 0 строк»), поэтому старую строку проверяет BEFORE-триггер
-- с понятным сообщением, а RLS WITH CHECK страхует новую строку (INSERT/UPDATE).
-- TG_ARGV[0]: 'fileid' | 'line:<кол>' | 'node:<кол>' | 'line_node:<кол линии>:<кол узла>'.
CREATE OR REPLACE FUNCTION tgid_auth.row_fragment(r jsonb, how text) RETURNS integer
LANGUAGE plpgsql STABLE SET search_path = pg_catalog AS $$
DECLARE p text[] := string_to_array(how, ':');
BEGIN
    RETURN CASE p[1]
        WHEN 'fileid' THEN (r ->> 'fileid')::integer
        WHEN 'line' THEN tgid_auth.line_fragment((r ->> p[2])::integer)
        WHEN 'node' THEN tgid_auth.node_fragment((r ->> p[2])::integer)
        WHEN 'line_node' THEN coalesce(tgid_auth.line_fragment((r ->> p[2])::integer),
                                       tgid_auth.node_fragment((r ->> p[3])::integer))
    END;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth.enforce_territory() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE
    f integer;
    sf integer[];
BEGIN
    -- администратор / суперпользователь (десктоп до перехода) / территория не задана — без проверок
    IF tgid_auth.is_admin() THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;
    sf := tgid_auth.scope_fragments();
    IF sf IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        f := tgid_auth.row_fragment(to_jsonb(OLD), TG_ARGV[0]);
        IF f IS NOT NULL AND NOT f = ANY (sf) THEN
            RAISE EXCEPTION 'Объект вне вашей территории: фрагмент %', f
                USING ERRCODE = '42501', DETAIL = format('%s %s', TG_TABLE_NAME, TG_OP),
                      HINT = 'territory';
        END IF;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        f := tgid_auth.row_fragment(to_jsonb(NEW), TG_ARGV[0]);
        IF f IS NOT NULL AND NOT f = ANY (sf) THEN
            RAISE EXCEPTION 'Объект вне вашей территории: фрагмент %', f
                USING ERRCODE = '42501', DETAIL = format('%s %s', TG_TABLE_NAME, TG_OP),
                      HINT = 'territory';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END $$;
ALTER FUNCTION tgid_auth.row_fragment(jsonb, text) OWNER TO tgid_owner;
ALTER FUNCTION tgid_auth.enforce_territory() OWNER TO tgid_owner;
REVOKE ALL ON FUNCTION tgid_auth.row_fragment(jsonb, text), tgid_auth.enforce_territory() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tgid_auth.row_fragment(jsonb, text), tgid_auth.enforce_territory()
    TO tgid_anon, tgid_worker;

CREATE OR REPLACE FUNCTION pg_temp.territory_rls(p_table text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE
    cols text[];
    expr text;
    how text;
    cond text;
BEGIN
    IF to_regclass(format('public.%I', p_table)) IS NULL THEN
        RETURN p_table || ': нет таблицы';
    END IF;
    SELECT array_agg(a.attname::text) INTO cols
      FROM pg_attribute a
     WHERE a.attrelid = format('public.%I', p_table)::regclass AND a.attnum > 0 AND NOT a.attisdropped;

    how := CASE
        WHEN 'fileid' = ANY (cols) THEN 'fileid'
        WHEN 'lineid' = ANY (cols) AND 'nodeid1' = ANY (cols) THEN 'line_node:lineid:nodeid1'
        WHEN 'lineid' = ANY (cols) AND 'nodeid' = ANY (cols) THEN 'line_node:lineid:nodeid'
        WHEN 'lineid' = ANY (cols) THEN 'line:lineid'
        WHEN 'nodeid' = ANY (cols) THEN 'node:nodeid'
        WHEN 'nodeid1' = ANY (cols) THEN 'node:nodeid1'
        WHEN 'nodeoprid1' = ANY (cols) THEN 'node:nodeoprid1'
    END;
    IF how IS NULL THEN
        RETURN p_table || ': нет колонки привязки — пропущено';
    END IF;
    expr := CASE split_part(how, ':', 1)
        WHEN 'fileid' THEN 'fileid'
        WHEN 'line' THEN format('tgid_auth.line_fragment(%I)', split_part(how, ':', 2))
        WHEN 'node' THEN format('tgid_auth.node_fragment(%I)', split_part(how, ':', 2))
        WHEN 'line_node' THEN format('coalesce(tgid_auth.line_fragment(%I), tgid_auth.node_fragment(%I))',
                                     split_part(how, ':', 2), split_part(how, ':', 3))
    END;
    cond := format('tgid_auth.can_edit_fragment(%s)', expr);

    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', p_table);
    EXECUTE format('DROP POLICY IF EXISTS tgid_read ON public.%I', p_table);
    EXECUTE format('DROP POLICY IF EXISTS tgid_insert ON public.%I', p_table);
    EXECUTE format('DROP POLICY IF EXISTS tgid_update ON public.%I', p_table);
    EXECUTE format('DROP POLICY IF EXISTS tgid_delete ON public.%I', p_table);
    EXECUTE format('CREATE POLICY tgid_read ON public.%I FOR SELECT USING (true)', p_table);
    EXECUTE format('CREATE POLICY tgid_insert ON public.%I FOR INSERT WITH CHECK (%s)', p_table, cond);
    -- старую строку проверяет триггер (явная ошибка вместо «0 строк»), новую — WITH CHECK
    EXECUTE format('CREATE POLICY tgid_update ON public.%I FOR UPDATE USING (true) WITH CHECK (%s)', p_table, cond);
    EXECUTE format('CREATE POLICY tgid_delete ON public.%I FOR DELETE USING (true)', p_table);
    EXECUTE format('DROP TRIGGER IF EXISTS tgid_territory ON public.%I', p_table);
    EXECUTE format('CREATE TRIGGER tgid_territory BEFORE INSERT OR UPDATE OR DELETE ON public.%I '
                   'FOR EACH ROW EXECUTE FUNCTION tgid_auth.enforce_territory(%L)', p_table, how);
    RETURN p_table || ': ' || how;
END $$;

SELECT pg_temp.territory_rls(t) AS rls
  FROM unnest(ARRAY[
    -- сеть и оборудование
    'nodes', 'linesobj', 'heatpipesections', 'pipesections', 'connectnodes', 'internalnodes', 'setpressnodes',
    'externalcodes', 'texts',
    'realconsumers', 'generalizedconsumers', 'heatsources', 'pumpstations',
    'airheaters', 'buildingentries', 'bypass', 'consumptregulators', 'dampers', 'diaphragms', 'elevators',
    'heatchambers', 'heatexchangers', 'overgroundnodes', 'undergroundnodes', 'uninstallednodes', 'pavilions',
    'pressdropregulators', 'pressregulators', 'pumps', 'refillnodes', 'regularmatures', 'reversevalves',
    'systemradiators', 'threewayvalves', 'trps', 'wdodevices',
    -- журналы с привязкой к сети (осмотры и ремонты — через контуры *deployed)
    'defect', 'shurfy', 'opres', 'opresdeployed', 'osmotrdeployed', 'remont2deployed', 'indikator_korrozii',
    -- направления пьезометра
    'directions', 'deployeddirections'
  ]) AS t;

-- История правок: читать — всем, у кого есть SELECT; писать — только от своего имени
DO $$ BEGIN
    IF to_regclass('public.audit_log') IS NOT NULL THEN
        ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS tgid_read ON public.audit_log;
        DROP POLICY IF EXISTS tgid_insert_own ON public.audit_log;
        DROP POLICY IF EXISTS tgid_rollback ON public.audit_log;
        CREATE POLICY tgid_read ON public.audit_log FOR SELECT USING (true);
        CREATE POLICY tgid_insert_own ON public.audit_log FOR INSERT WITH CHECK (changed_by = current_user::text);
        -- UPDATE разрешён только столбцу is_rolled_back (03_grants.sql)
        CREATE POLICY tgid_rollback ON public.audit_log FOR UPDATE USING (true) WITH CHECK (true);
    END IF;
END $$;

COMMIT;

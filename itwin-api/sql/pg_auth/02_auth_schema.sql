-- TGID: схема tgid_auth — пользователи, территории, проверки прав, администрирование.
-- В каждой базе TGID, от суперпользователя, после 01_roles.sql. Идемпотентно.
--
--   psql -h 127.0.0.1 -p 5440 -U postgres -d almatygid_copy -v target_db=almatygid_copy -f 02_auth_schema.sql
--
-- Пользователь = роль PostgreSQL tgid_u_<логин>. Строка в tgid_auth.users — профиль и признак
-- «пользователь этой базы». Проверки — функции SECURITY INVOKER поверх RLS на таблицах tgid_auth
-- (каждый видит свою строку, администратор — все). Создание ролей и пароли — SECURITY DEFINER
-- функции tgid_auth._*, владелец tgid_useradmin; вызываются только из обёрток с проверкой is_admin().

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

CREATE SCHEMA IF NOT EXISTS tgid_auth AUTHORIZATION tgid_owner;
REVOKE ALL ON SCHEMA tgid_auth FROM PUBLIC;
GRANT USAGE ON SCHEMA tgid_auth TO tgid_anon, tgid_worker, tgid_api, tgid_useradmin;

-- ── Таблицы ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tgid_auth.users (
    role_name            name PRIMARY KEY,
    login                text NOT NULL UNIQUE,
    display_name         text,
    full_name            text,
    web_access           boolean NOT NULL DEFAULT true,   -- бит 256 «Веб приложение»
    is_active            boolean NOT NULL DEFAULT true,
    must_change_password boolean NOT NULL DEFAULT false,
    password_set         boolean NOT NULL DEFAULT false,  -- пароль роли PG задан (SCRAM)
    legacy_passwords_id  integer,   -- passwords.id → operatorID десктопа
    legacy_usersdb_id    integer,
    legacy_auth_id       integer,   -- auth.users.id (QGIS)
    legacy_right         integer,   -- исходная маска user_right (для сверки)
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           name,
    updated_at           timestamptz,
    updated_by           name
);

CREATE TABLE IF NOT EXISTS tgid_auth.user_scope (
    id          serial PRIMARY KEY,
    role_name   name NOT NULL REFERENCES tgid_auth.users(role_name) ON DELETE CASCADE ON UPDATE CASCADE,
    fragment_id integer,
    uchastok_id integer,
    CHECK (fragment_id IS NOT NULL OR uchastok_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS user_scope_role_idx ON tgid_auth.user_scope (role_name);

-- Старые хеши на время перехода (MD5 passwords, bcrypt usersdb, sha256 auth.users).
-- Читают только функции входа API; строка удаляется после первого успешного входа.
CREATE TABLE IF NOT EXISTS tgid_auth.legacy_credentials (
    role_name name NOT NULL REFERENCES tgid_auth.users(role_name) ON DELETE CASCADE ON UPDATE CASCADE,
    source    text NOT NULL CHECK (source IN ('passwords', 'usersdb', 'auth')),
    hash      text NOT NULL,
    PRIMARY KEY (role_name, source)
);

ALTER TABLE tgid_auth.users OWNER TO tgid_owner;
ALTER TABLE tgid_auth.user_scope OWNER TO tgid_owner;
ALTER TABLE tgid_auth.legacy_credentials OWNER TO tgid_owner;
ALTER SEQUENCE tgid_auth.user_scope_id_seq OWNER TO tgid_owner;

REVOKE ALL ON ALL TABLES IN SCHEMA tgid_auth FROM PUBLIC;
GRANT SELECT ON tgid_auth.users, tgid_auth.user_scope TO tgid_anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON tgid_auth.users, tgid_auth.user_scope,
      tgid_auth.legacy_credentials TO tgid_useradmin;
GRANT USAGE ON SEQUENCE tgid_auth.user_scope_id_seq TO tgid_useradmin;

-- Свою строку видит каждый, все — администратор; tgid_useradmin (функции администрирования) — все
ALTER TABLE tgid_auth.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tgid_auth.user_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE tgid_auth.legacy_credentials ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS own_or_admin ON tgid_auth.users;
CREATE POLICY own_or_admin ON tgid_auth.users FOR SELECT
    USING (role_name = current_user OR pg_has_role(current_user, 'tgid_admin', 'USAGE'));
DROP POLICY IF EXISTS own_or_admin ON tgid_auth.user_scope;
CREATE POLICY own_or_admin ON tgid_auth.user_scope FOR SELECT
    USING (role_name = current_user OR pg_has_role(current_user, 'tgid_admin', 'USAGE'));
-- Своя строка: только признаки пароля (set_password для себя)
GRANT UPDATE (password_set, must_change_password, updated_at, updated_by) ON tgid_auth.users TO tgid_viewer;
DROP POLICY IF EXISTS own_password ON tgid_auth.users;
CREATE POLICY own_password ON tgid_auth.users FOR UPDATE
    USING (role_name = current_user) WITH CHECK (role_name = current_user);
DROP POLICY IF EXISTS useradmin_all ON tgid_auth.users;
CREATE POLICY useradmin_all ON tgid_auth.users TO tgid_useradmin USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS useradmin_all ON tgid_auth.user_scope;
CREATE POLICY useradmin_all ON tgid_auth.user_scope TO tgid_useradmin USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS useradmin_all ON tgid_auth.legacy_credentials;
CREATE POLICY useradmin_all ON tgid_auth.legacy_credentials TO tgid_useradmin USING (true) WITH CHECK (true);

-- ── Проверки (SECURITY INVOKER: current_user — пользователь после SET ROLE) ─────────────

CREATE OR REPLACE FUNCTION tgid_auth.is_admin() RETURNS boolean
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT pg_has_role(current_user, 'tgid_admin', 'USAGE')
$$;

CREATE OR REPLACE FUNCTION tgid_auth.has_cap(cap text) RETURNS boolean
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = cap)
           AND pg_has_role(current_user, cap, 'USAGE')
$$;

-- Фрагменты, которые пользователь может править: NULL — вся сеть (территория не задана),
-- '{}' — ничего (задана территория без фрагментов).
CREATE OR REPLACE FUNCTION tgid_auth.scope_fragments() RETURNS integer[]
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT CASE WHEN count(*) = 0 THEN NULL
                ELSE coalesce(array_agg(DISTINCT s.fragment_id) FILTER (WHERE s.fragment_id IS NOT NULL), '{}')
           END
      FROM tgid_auth.user_scope s
     WHERE s.role_name = current_user
$$;

-- Можно ли править объект фрагмента f. f IS NULL — объект без привязки к сети: можно.
CREATE OR REPLACE FUNCTION tgid_auth.can_edit_fragment(f integer) RETURNS boolean
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT f IS NULL
        OR tgid_auth.is_admin()
        OR (SELECT CASE WHEN sf IS NULL THEN true ELSE f = ANY (sf) END
              FROM (SELECT tgid_auth.scope_fragments() AS sf) x)
$$;

CREATE OR REPLACE FUNCTION tgid_auth.line_fragment(line_id integer) RETURNS integer
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT l.fileid FROM public.linesobj l WHERE l.id = line_id
$$;

CREATE OR REPLACE FUNCTION tgid_auth.node_fragment(node_id integer) RETURNS integer
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT n.fileid FROM public.nodes n WHERE n.id = node_id
$$;

-- Маска user_right для десктопа (gid8/gid8/any/rights.h). Инвертированы: 2 admin, 8 akt, 16 geo.
CREATE OR REPLACE FUNCTION tgid_auth.legacy_right() RETURNS integer
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT (CASE WHEN tgid_auth.is_admin() THEN 0 ELSE 2 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_network') THEN 4 ELSE 0 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_acts') THEN 0 ELSE 8 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_geo') THEN 0 ELSE 16 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_network')
                  AND NOT tgid_auth.has_cap('tgid_cap_network_struct') THEN 32 ELSE 0 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_pts') THEN 64 ELSE 0 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_corrosion') THEN 128 ELSE 0 END)
         + (CASE WHEN coalesce((SELECT u.web_access FROM tgid_auth.users u
                                 WHERE u.role_name = current_user), false) THEN 256 ELSE 0 END)
         + (CASE WHEN pg_has_role(current_user, 'tgid_editor', 'USAGE') THEN 512 ELSE 0 END)
         + (CASE WHEN tgid_auth.has_cap('tgid_cap_repairs') THEN 1024 ELSE 0 END)
$$;

CREATE OR REPLACE FUNCTION tgid_auth.my_legacy_id() RETURNS integer
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT u.legacy_passwords_id FROM tgid_auth.users u WHERE u.role_name = current_user
$$;

-- Базовая роль: наивысшая из иерархии, в которой состоит роль r
CREATE OR REPLACE FUNCTION tgid_auth.base_role_of(r name) RETURNS text
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT CASE
        WHEN pg_has_role(r, 'tgid_admin', 'USAGE') THEN 'admin'
        WHEN pg_has_role(r, 'tgid_editor', 'USAGE') THEN 'editor'
        WHEN pg_has_role(r, 'tgid_calculator', 'USAGE') THEN 'calculator'
        WHEN pg_has_role(r, 'tgid_viewer', 'USAGE') THEN 'viewer'
        ELSE 'anon' END
$$;

CREATE OR REPLACE FUNCTION tgid_auth.caps_of(r name) RETURNS text[]
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT coalesce(array_agg(substr(rolname, 10) ORDER BY rolname), '{}')
      FROM pg_roles
     WHERE rolname LIKE 'tgid\_cap\_%' AND pg_has_role(r, oid, 'USAGE')
$$;

-- Профиль текущего пользователя для /auth/me
CREATE OR REPLACE FUNCTION tgid_auth.me() RETURNS jsonb
LANGUAGE sql STABLE SET search_path = pg_catalog AS $$
    SELECT jsonb_build_object(
        'role_name', current_user,
        'login', u.login,
        'display_name', coalesce(u.display_name, u.login, current_user::text),
        'full_name', u.full_name,
        'base_role', tgid_auth.base_role_of(current_user),
        'caps', to_jsonb(tgid_auth.caps_of(current_user)),
        'fragments', to_jsonb(tgid_auth.scope_fragments()),
        'web_access', coalesce(u.web_access, false),
        'is_active', coalesce(u.is_active, false),
        'must_change_password', coalesce(u.must_change_password, false),
        'legacy_right', tgid_auth.legacy_right())
      FROM (SELECT 1) one
      LEFT JOIN tgid_auth.users u ON u.role_name = current_user
$$;

-- Список пользователей (RLS: администратору — все строки)
CREATE OR REPLACE VIEW tgid_auth.v_users WITH (security_invoker = true) AS
SELECT u.role_name, u.login, u.display_name, u.full_name, u.web_access, u.is_active,
       u.must_change_password, u.password_set, u.legacy_passwords_id, u.legacy_right,
       tgid_auth.base_role_of(u.role_name) AS base_role,
       tgid_auth.caps_of(u.role_name) AS caps,
       (SELECT array_agg(s.fragment_id ORDER BY s.fragment_id) FROM tgid_auth.user_scope s
         WHERE s.role_name = u.role_name AND s.fragment_id IS NOT NULL) AS fragments,
       r.rolcanlogin AS can_login, u.created_at, u.created_by, u.updated_at, u.updated_by
  FROM tgid_auth.users u
  LEFT JOIN pg_roles r ON r.rolname = u.role_name;
ALTER VIEW tgid_auth.v_users OWNER TO tgid_owner;
GRANT SELECT ON tgid_auth.v_users TO tgid_anon;

-- ── Администрирование ───────────────────────────────────────────────────────────────────
-- _impl (SECURITY DEFINER, владелец tgid_useradmin): роли PG и строки tgid_auth.
-- Обёртки (INVOKER): проверка is_admin() и запись audit_log от имени администратора.

-- Логин как есть, без lower(): lower() зависит от локали базы (кириллица в C-локали не меняется),
-- а десктоп вычисляет имя роли сам, до подключения. Логин чувствителен к регистру, как в десктопе.
CREATE OR REPLACE FUNCTION tgid_auth.role_for_login(p_login text) RETURNS name
LANGUAGE sql IMMUTABLE SET search_path = pg_catalog AS $$
    SELECT ('tgid_u_' || btrim(p_login))::name
$$;

CREATE OR REPLACE FUNCTION tgid_auth._check_access(p_base text, p_caps text[]) RETURNS void
LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog AS $$
BEGIN
    IF p_base NOT IN ('viewer', 'calculator', 'editor', 'admin') THEN
        RAISE EXCEPTION 'Неизвестная базовая роль: %', p_base USING ERRCODE = '22023';
    END IF;
    IF EXISTS (SELECT 1 FROM unnest(coalesce(p_caps, '{}')) c
                WHERE c NOT IN ('network', 'network_struct', 'acts', 'geo', 'pts', 'corrosion', 'repairs')) THEN
        RAISE EXCEPTION 'Неизвестное предметное право в %', p_caps USING ERRCODE = '22023';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth._grant_access(p_role name, p_base text, p_caps text[]) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE g text;
BEGIN
    PERFORM tgid_auth._check_access(p_base, p_caps);
    -- снять все группы tgid_ (кроме tgid_users) и выдать заново
    FOR g IN SELECT b.rolname FROM pg_auth_members m
               JOIN pg_roles b ON b.oid = m.roleid
               JOIN pg_roles u ON u.oid = m.member
              WHERE u.rolname = p_role
                AND (b.rolname IN ('tgid_viewer', 'tgid_calculator', 'tgid_editor', 'tgid_admin')
                     OR b.rolname LIKE 'tgid\_cap\_%') LOOP
        EXECUTE format('REVOKE %I FROM %I', g, p_role);
    END LOOP;
    EXECUTE format('GRANT %I TO %I', 'tgid_' || p_base, p_role);
    FOREACH g IN ARRAY coalesce(p_caps, '{}') LOOP
        EXECUTE format('GRANT %I TO %I', 'tgid_cap_' || g, p_role);
    END LOOP;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth._set_scope(p_role name, p_fragments integer[]) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    DELETE FROM tgid_auth.user_scope WHERE role_name = p_role;
    INSERT INTO tgid_auth.user_scope (role_name, fragment_id)
    SELECT p_role, f FROM (SELECT DISTINCT unnest(p_fragments) AS f) x WHERE f IS NOT NULL;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth._create_user(
    p_actor name, p_login text, p_base text, p_caps text[], p_fragments integer[],
    p_display_name text, p_full_name text, p_web_access boolean
) RETURNS name
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE r name := tgid_auth.role_for_login(p_login);
BEGIN
    IF btrim(coalesce(p_login, '')) = '' OR length(r) > 63 THEN
        RAISE EXCEPTION 'Недопустимый логин: %', p_login USING ERRCODE = '22023';
    END IF;
    PERFORM tgid_auth._check_access(p_base, p_caps);
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
        EXECUTE format('CREATE ROLE %I LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS', r);
    ELSIF EXISTS (SELECT 1 FROM tgid_auth.users WHERE role_name = r) THEN
        RAISE EXCEPTION 'Пользователь % уже есть', p_login USING ERRCODE = '23505';
    END IF;
    EXECUTE format('GRANT tgid_users TO %I', r);
    EXECUTE format('GRANT %I TO tgid_api WITH INHERIT FALSE, SET TRUE', r);
    PERFORM tgid_auth._grant_access(r, p_base, p_caps);
    INSERT INTO tgid_auth.users (role_name, login, display_name, full_name, web_access, created_by)
    VALUES (r, btrim(p_login), p_display_name, p_full_name, coalesce(p_web_access, true), p_actor);
    PERFORM tgid_auth._set_scope(r, p_fragments);
    RETURN r;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth._update_user(
    p_actor name, p_role name, p_base text, p_caps text[], p_fragments integer[],
    p_display_name text, p_full_name text, p_web_access boolean
) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tgid_auth.users WHERE role_name = p_role) THEN
        RAISE EXCEPTION 'Нет пользователя %', p_role USING ERRCODE = 'P0002';
    END IF;
    IF p_base IS NOT NULL THEN
        PERFORM tgid_auth._grant_access(p_role, p_base, p_caps);
    END IF;
    IF p_fragments IS NOT NULL THEN
        PERFORM tgid_auth._set_scope(p_role, p_fragments);
    END IF;
    UPDATE tgid_auth.users
       SET display_name = coalesce(p_display_name, display_name),
           full_name = coalesce(p_full_name, full_name),
           web_access = coalesce(p_web_access, web_access),
           updated_at = now(), updated_by = p_actor
     WHERE role_name = p_role;
END $$;

-- Пароль принимается только как SCRAM-верификатор (вычисляет API): открытый пароль не попадает
-- ни в текст SQL, ни в журнал сервера.
CREATE OR REPLACE FUNCTION tgid_auth._set_password(p_actor name, p_role name, p_verifier text, p_must_change boolean)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF p_verifier !~ '^SCRAM-SHA-256\$[0-9]+:[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+$' THEN
        RAISE EXCEPTION 'Ожидается SCRAM-SHA-256 верификатор' USING ERRCODE = '22023';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM tgid_auth.users WHERE role_name = p_role) THEN
        RAISE EXCEPTION 'Нет пользователя %', p_role USING ERRCODE = 'P0002';
    END IF;
    EXECUTE format('ALTER ROLE %I PASSWORD %L', p_role, p_verifier);
    UPDATE tgid_auth.users
       SET password_set = true, must_change_password = coalesce(p_must_change, false),
           updated_at = now(), updated_by = p_actor
     WHERE role_name = p_role;
    DELETE FROM tgid_auth.legacy_credentials WHERE role_name = p_role;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth._set_active(p_actor name, p_role name, p_active boolean) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tgid_auth.users WHERE role_name = p_role) THEN
        RAISE EXCEPTION 'Нет пользователя %', p_role USING ERRCODE = 'P0002';
    END IF;
    EXECUTE format('ALTER ROLE %I %s', p_role, CASE WHEN p_active THEN 'LOGIN' ELSE 'NOLOGIN' END);
    UPDATE tgid_auth.users SET is_active = p_active, updated_at = now(), updated_by = p_actor
     WHERE role_name = p_role;
END $$;

-- Вход API (вызывает только tgid_api): старые хеши и перенос пароля при первом входе
CREATE OR REPLACE FUNCTION tgid_auth._login_info(p_login text)
RETURNS TABLE (role_name name, is_active boolean, web_access boolean, password_set boolean,
               can_login boolean, legacy_source text, legacy_hash text)
LANGUAGE sql SECURITY DEFINER STABLE SET search_path = pg_catalog AS $$
    SELECT u.role_name, u.is_active, u.web_access, u.password_set, r.rolcanlogin, c.source, c.hash
      FROM tgid_auth.users u
      JOIN pg_roles r ON r.rolname = u.role_name
      LEFT JOIN tgid_auth.legacy_credentials c ON c.role_name = u.role_name
     WHERE u.role_name = tgid_auth.role_for_login(p_login)
$$;

CREATE OR REPLACE FUNCTION tgid_auth._migrate_password(p_role name, p_verifier text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tgid_auth.users WHERE role_name = p_role AND NOT password_set) THEN
        RAISE EXCEPTION 'Пароль уже перенесён' USING ERRCODE = '42501';
    END IF;
    PERFORM tgid_auth._set_password(p_role, p_role, p_verifier, false);
END $$;

-- Обёртки для администратора (INVOKER): проверка прав + audit_log от имени администратора
CREATE OR REPLACE FUNCTION tgid_auth._assert_admin() RETURNS void
LANGUAGE plpgsql STABLE SET search_path = pg_catalog AS $$
BEGIN
    IF NOT tgid_auth.is_admin() THEN
        RAISE EXCEPTION 'Требуется роль администратора' USING ERRCODE = '42501';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth._audit(p_op text, p_role name, p_data jsonb) RETURNS void
LANGUAGE sql SET search_path = pg_catalog AS $$
    INSERT INTO public.audit_log (operation, table_name, comment, new_data, changed_by, changed_at)
    VALUES (p_op, 'tgid_auth.users', p_role, p_data, current_user, now())
$$;

CREATE OR REPLACE FUNCTION tgid_auth.create_user(
    p_login text, p_base text, p_caps text[] DEFAULT '{}', p_fragments integer[] DEFAULT '{}',
    p_display_name text DEFAULT NULL, p_full_name text DEFAULT NULL, p_web_access boolean DEFAULT true
) RETURNS name
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE r name;
BEGIN
    PERFORM tgid_auth._assert_admin();
    r := tgid_auth._create_user(current_user, p_login, p_base, p_caps, p_fragments,
                                p_display_name, p_full_name, p_web_access);
    PERFORM tgid_auth._audit('INSERT', r, jsonb_build_object('login', p_login, 'base_role', p_base,
            'caps', p_caps, 'fragments', p_fragments, 'web_access', p_web_access));
    RETURN r;
END $$;

CREATE OR REPLACE FUNCTION tgid_auth.update_user(
    p_role name, p_base text DEFAULT NULL, p_caps text[] DEFAULT NULL, p_fragments integer[] DEFAULT NULL,
    p_display_name text DEFAULT NULL, p_full_name text DEFAULT NULL, p_web_access boolean DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    PERFORM tgid_auth._assert_admin();
    IF p_role = current_user AND p_base IS NOT NULL AND p_base <> 'admin' THEN
        RAISE EXCEPTION 'Нельзя снять с себя роль администратора' USING ERRCODE = '42501';
    END IF;
    PERFORM tgid_auth._update_user(current_user, p_role, p_base, p_caps, p_fragments,
                                   p_display_name, p_full_name, p_web_access);
    PERFORM tgid_auth._audit('UPDATE', p_role, jsonb_strip_nulls(jsonb_build_object('base_role', p_base,
            'caps', p_caps, 'fragments', p_fragments, 'display_name', p_display_name,
            'full_name', p_full_name, 'web_access', p_web_access)));
END $$;

-- Свой пароль: обычный ALTER ROLE на собственную роль (PostgreSQL разрешает это любой роли) —
-- DEFINER-функция здесь не нужна и не выдаётся рядовым пользователям. Чужой — только администратор.
CREATE OR REPLACE FUNCTION tgid_auth.set_password(p_role name, p_verifier text, p_must_change boolean DEFAULT true)
RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF p_role = current_user THEN
        IF p_verifier !~ '^SCRAM-SHA-256\$[0-9]+:[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+$' THEN
            RAISE EXCEPTION 'Ожидается SCRAM-SHA-256 верификатор' USING ERRCODE = '22023';
        END IF;
        EXECUTE format('ALTER ROLE %I PASSWORD %L', current_user, p_verifier);
        UPDATE tgid_auth.users SET password_set = true, must_change_password = false,
               updated_at = now(), updated_by = current_user
         WHERE role_name = current_user;
    ELSE
        PERFORM tgid_auth._assert_admin();
        PERFORM tgid_auth._set_password(current_user, p_role, p_verifier, p_must_change);
    END IF;
    PERFORM tgid_auth._audit('UPDATE', p_role, jsonb_build_object('password', 'changed'));
END $$;

CREATE OR REPLACE FUNCTION tgid_auth.set_active(p_role name, p_active boolean) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    PERFORM tgid_auth._assert_admin();
    IF p_role = current_user AND NOT p_active THEN
        RAISE EXCEPTION 'Нельзя заблокировать себя' USING ERRCODE = '42501';
    END IF;
    PERFORM tgid_auth._set_active(current_user, p_role, p_active);
    PERFORM tgid_auth._audit('UPDATE', p_role, jsonb_build_object('is_active', p_active));
END $$;

-- ── Владельцы и права на функции ────────────────────────────────────────────────────────

DO $$
DECLARE f regprocedure;
BEGIN
    FOR f IN SELECT p.oid::regprocedure FROM pg_proc p
              WHERE p.pronamespace = 'tgid_auth'::regnamespace LOOP
        EXECUTE format('ALTER FUNCTION %s OWNER TO tgid_owner', f);
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    END LOOP;
END $$;

-- DEFINER-функции — от имени tgid_useradmin (CREATEROLE, ADMIN на группы tgid_)
ALTER FUNCTION tgid_auth._grant_access(name, text, text[]) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._set_scope(name, integer[]) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._create_user(name, text, text, text[], integer[], text, text, boolean) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._update_user(name, name, text, text[], integer[], text, text, boolean) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._set_password(name, name, text, boolean) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._set_active(name, name, boolean) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._login_info(text) OWNER TO tgid_useradmin;
ALTER FUNCTION tgid_auth._migrate_password(name, text) OWNER TO tgid_useradmin;
GRANT EXECUTE ON FUNCTION tgid_auth._check_access(text, text[]), tgid_auth.role_for_login(text)
    TO tgid_useradmin;

-- Проверки — всем ролям TGID
GRANT EXECUTE ON FUNCTION
    tgid_auth.is_admin(), tgid_auth.has_cap(text), tgid_auth.scope_fragments(),
    tgid_auth.can_edit_fragment(integer), tgid_auth.line_fragment(integer), tgid_auth.node_fragment(integer),
    tgid_auth.legacy_right(), tgid_auth.my_legacy_id(), tgid_auth.base_role_of(name), tgid_auth.caps_of(name),
    tgid_auth.me(), tgid_auth.role_for_login(text)
  TO tgid_anon, tgid_worker, tgid_useradmin;

-- Администрирование — администраторам; impl — тоже им (вызываются из обёрток от их имени)
GRANT EXECUTE ON FUNCTION
    tgid_auth._assert_admin(), tgid_auth._audit(text, name, jsonb),
    tgid_auth.create_user(text, text, text[], integer[], text, text, boolean),
    tgid_auth.update_user(name, text, text[], integer[], text, text, boolean),
    tgid_auth.set_active(name, boolean),
    tgid_auth._create_user(name, text, text, text[], integer[], text, text, boolean),
    tgid_auth._update_user(name, name, text, text[], integer[], text, text, boolean),
    tgid_auth._set_active(name, name, boolean),
    tgid_auth._set_password(name, name, text, boolean)
  TO tgid_admin;
-- Смена своего пароля — любому пользователю (обёртка; DEFINER _set_password им не выдаётся)
GRANT EXECUTE ON FUNCTION
    tgid_auth.set_password(name, text, boolean), tgid_auth._assert_admin(), tgid_auth._audit(text, name, jsonb)
  TO tgid_viewer;

-- Вход — только логину API (без SET ROLE)
GRANT EXECUTE ON FUNCTION tgid_auth._login_info(text), tgid_auth._migrate_password(name, text),
    tgid_auth.role_for_login(text)
  TO tgid_api;

COMMIT;

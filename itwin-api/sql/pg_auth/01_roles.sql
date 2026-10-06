-- TGID: роли PostgreSQL (общие для всего кластера — выполняется один раз, от суперпользователя).
-- Идемпотентно. Пароли здесь НЕ задаются: LOGIN-ролям их назначает администратор БД вручную
-- (\password tgid_api и т. п.), до этого под ними войти нельзя.
--
--   psql -h 127.0.0.1 -p 5440 -U postgres -d postgres -f 01_roles.sql
--
-- Модель (docs/pg-auth.md):
--   tgid_owner        — владелец объектов схемы (миграции)
--   tgid_api          — логин пула API: сам прав не имеет, делает SET LOCAL ROLE на роль пользователя
--   tgid_worker       — Celery / sety: расчёты
--   tgid_geoserver    — GeoServer: только чтение
--   tgid_useradmin    — владелец функций администрирования пользователей (CREATEROLE)
--   tgid_anon ⊂ tgid_viewer ⊂ tgid_calculator ⊂ tgid_editor ⊂ tgid_admin — базовые роли
--   tgid_cap_*        — предметные права (биты user_right десктопа)
--   tgid_u_<логин>    — пользователи (создаются функциями tgid_auth.*); все входят в tgid_users —
--                       маркер без прав для pg_hba («host … +tgid_users <сеть ЛВС> scram-sha-256»)

DO $$
DECLARE
  r text;
BEGIN
  -- групповые роли без входа
  FOREACH r IN ARRAY ARRAY[
    'tgid_owner', 'tgid_users', 'tgid_anon', 'tgid_viewer', 'tgid_calculator', 'tgid_editor', 'tgid_admin',
    'tgid_cap_network', 'tgid_cap_network_struct', 'tgid_cap_acts', 'tgid_cap_geo',
    'tgid_cap_pts', 'tgid_cap_corrosion', 'tgid_cap_repairs'
  ] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS', r);
    END IF;
  END LOOP;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tgid_useradmin') THEN
    CREATE ROLE tgid_useradmin NOLOGIN NOSUPERUSER NOCREATEDB CREATEROLE NOBYPASSRLS;
  END IF;

  -- служебные логины (пароль задаёт администратор БД)
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tgid_api') THEN
    CREATE ROLE tgid_api LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS CONNECTION LIMIT 60;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tgid_worker') THEN
    CREATE ROLE tgid_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS CONNECTION LIMIT 20;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tgid_geoserver') THEN
    CREATE ROLE tgid_geoserver LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS CONNECTION LIMIT 80;
  END IF;
END $$;

-- GeoServer: даже лишний GRANT не даст записать
ALTER ROLE tgid_geoserver SET default_transaction_read_only = on;

-- Иерархия базовых ролей
GRANT tgid_anon       TO tgid_viewer;
GRANT tgid_viewer     TO tgid_calculator;
GRANT tgid_calculator TO tgid_editor;
GRANT tgid_editor     TO tgid_admin;

-- Структура сети (добавление/удаление объектов) включает правку атрибутов сети
GRANT tgid_cap_network TO tgid_cap_network_struct;

-- Администратор имеет все предметные права
GRANT tgid_cap_network_struct, tgid_cap_acts, tgid_cap_geo, tgid_cap_pts,
      tgid_cap_corrosion, tgid_cap_repairs TO tgid_admin;

-- API переключается на эти роли (аноним, режим AUTH_DISABLED), но не наследует их права
GRANT tgid_anon, tgid_viewer, tgid_calculator, tgid_editor, tgid_admin
  TO tgid_api WITH INHERIT FALSE, SET TRUE;

-- Администрирование пользователей: tgid_useradmin выдаёт группы, сам их прав не получает
GRANT tgid_users, tgid_viewer, tgid_calculator, tgid_editor, tgid_admin,
      tgid_cap_network, tgid_cap_network_struct, tgid_cap_acts, tgid_cap_geo,
      tgid_cap_pts, tgid_cap_corrosion, tgid_cap_repairs
  TO tgid_useradmin WITH ADMIN TRUE, INHERIT FALSE, SET FALSE;
-- Созданных им пользователей tgid_useradmin выдаёт tgid_api (GRANT tgid_u_x TO tgid_api
-- WITH INHERIT FALSE, SET TRUE): в PG16 создатель роли автоматически получает на неё ADMIN.

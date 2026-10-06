# Права доступа через роли PostgreSQL

Права пользователей задаются ролями PostgreSQL и проверяются самой базой (GRANT, row-level security,
триггер территории) — для веба, десктопа и QGIS одинаково. API не ходит в базу суперпользователем: на каждый
запрос он переключается на роль пользователя (`SET ROLE`), и ошибка в коде API не даёт лишних прав.

Файлы: `sql/pg_auth/01–04` (роли, схема `tgid_auth`, права, RLS), `99_rollback.sql`,
`scripts/pg_auth/migrate_users.py` (перенос пользователей), тесты `tests/pg` (на копии, `PG_AUTH_TESTS=1`),
`tests/test_pg_auth_*.py`.

## Модель

| Роль | Назначение |
|---|---|
| `tgid_u_<логин>` | пользователь (логин как есть, с регистром; `tgid_auth.role_for_login`) — тот же пароль у веба и десктопа |
| `tgid_viewer` ⊂ `tgid_calculator` ⊂ `tgid_editor` ⊂ `tgid_admin` | базовые роли (как раньше в вебе) |
| `tgid_cap_*` | предметные права из битов `user_right` десктопа |
| `tgid_anon` | аноним (чтение карты при `AUTH_REQUIRED_GET=false`) |
| `tgid_api` | логин API: прав не имеет, только `SET ROLE` на пользователей и группы |
| `tgid_worker` | Celery и sety: расчёты (`calculation`, `*_out`, теплопотери) |
| `tgid_geoserver` | GeoServer: только чтение (`default_transaction_read_only`) |
| `tgid_useradmin` | владелец функций администрирования (CREATEROLE, PG16 — только свои роли) |
| `tgid_users` | маркер всех пользователей для pg_hba |

Биты `user_right` (gid8/gid8/any/rights.h, инвертированы 2, 8, 16):

| Бит | Десктоп | Новая модель |
|---|---|---|
| 2 (инв.) | Администратор | `tgid_admin` — **все** права (в gid8 админ без бита 4 не правил сеть) |
| 4 | Группа режимов (правка сети) | `tgid_cap_network`; базовая роль не ниже calculator |
| 32 | Нельзя добавлять/удалять | без `tgid_cap_network_struct` |
| 8 (инв.) | Акты | `tgid_cap_acts` |
| 16 (инв.) | Геобаза | `tgid_cap_geo` |
| 64 | Производственная служба | `tgid_cap_pts` |
| 128 | Индикаторы коррозии | `tgid_cap_corrosion` |
| 256 | Веб приложение | `tgid_auth.users.web_access` |
| 512 | Веб: запись | базовая роль `tgid_editor` |
| 1024 | Ремонты | `tgid_cap_repairs` |

`tgid_auth.legacy_right()` возвращает маску для десктопа.

**Территория** — фрагменты, в которых пользователь может править (`tgid_auth.user_scope`); пусто — вся сеть,
чтение — всегда вся сеть. Проверка на 45 таблицах сети, оборудования и журналов: строка без фрагмента
(`fileid` пуст) правится без ограничения. Чужой объект — ошибка `42501` «Объект вне вашей территории:
фрагмент N» (BEFORE-триггер `tgid_territory` + RLS `WITH CHECK`), API отдаёт 403 с этим текстом.

**История правок**: триггеры аудита пишут `changed_by = current_user` — после `SET ROLE` это пользователь;
политика RLS не даёт записать строку от чужого имени, удалять и править историю нельзя (кроме отметки отката).

## API

| Переменная | Значение |
|---|---|
| `DB_ROLE_SWITCH=true` | `SET ROLE` пользователя на каждое соединение пула (хук `setup`, `database/db_role.py`) |
| `AUTH_BACKEND=pg` | вход по ролям PostgreSQL (`database/pg_users.py`); `usersdb` — как раньше |
| `DB_DEV_ROLE` | роль при `AUTH_DISABLED=true` (по умолчанию `tgid_admin` — поведение как раньше) |
| `AUTH_LIVE_USER_CHECK` | живая сверка (блокировка, роль, права) по `tgid_auth.me()`, кеш 30 с — для `pg` нужна |

Вход (`/auth/login`): пароль проверяет PostgreSQL — короткое подключение под ролью пользователя (SCRAM).
Пока пароль роли не задан, принимается старый хеш (MD5 `passwords` в UTF-8 и cp1251, bcrypt UsersDB, sha256
`auth.users`), и при успехе пароль переносится в роль. В БД передаётся только SCRAM-верификатор
(`utils/scram.py`): открытый пароль не попадает ни в SQL, ни в журнал сервера.

Права в API (`require_roles(..., cap=...)`): пользователю PostgreSQL — администратор или предметное право
(оборудование и установщики — `network`, топология и импорт — `network_struct`, ПТС — `pts`, ремонты —
`repairs`), иначе — минимальная роль. Окончательно права проверяет БД.

## Выкатка на прод (выполняет администратор БД)

Копия `almatygid_copy` уже переведена (06.10.2026): роли, схема, права, RLS, 38 пользователей.

1. Бэкап: `pg_dump -s almatygid`, `pg_dumpall --roles-only --no-role-passwords`.
2. **pg_hba до паролей.** Сейчас `host all all 0.0.0.0/0 scram-sha-256`: любая роль с паролем входит в любую
   базу из интернета. Добавить выше общих строк:
   ```
   host  almatygid  +tgid_users  192.168.0.0/24  scram-sha-256
   host  almatygid  +tgid_users  127.0.0.1/32    scram-sha-256
   host  all        +tgid_users  0.0.0.0/0       reject
   host  all        tgid_api,tgid_worker,tgid_geoserver  127.0.0.1/32  scram-sha-256
   host  all        tgid_api,tgid_worker,tgid_geoserver  0.0.0.0/0     reject
   ```
3. `01_roles.sql` (база `postgres`) — уже выполнен на кластере 06.10; повтор безопасен.
4. Пароли служебных ролей: `\password tgid_api`, `\password tgid_worker`, `\password tgid_geoserver`.
5. `02`–`04` на прод: `psql -d almatygid -v target_db=almatygid -f sql/pg_auth/0X_….sql`.
6. Пользователи: `migrate_users.py` (сначала план, затем `--apply --prod`) с env прода.
7. API: `DB_ROLE_SWITCH=true` (пока `DB_USER=postgres` — проверка), затем `DB_USER=tgid_api`;
   воркер — `DB_USER=tgid_worker`. Перезапуск tgid-api и tgid-worker.
8. `AUTH_BACKEND=pg` и `AUTH_DISABLED=false` — отдельное решение (QA F75).
9. GeoServer: хранилища `AlmatyGIS`/`public` → `tgid_geoserver`; удалить слои `login`, `get_file`,
   `read_file`, `file` (новый веб их не использует; `login` нужен только старому вебу).
10. Десктоп gid8: вход под ролью пользователя вместо общего логина `kls/config.ini`, права —
    `SELECT tgid_auth.legacy_right()`, `operatorID` — `tgid_auth.my_legacy_id()`.

Откат: `99_rollback.sql` (политики, права, схема `tgid_auth`), API — `DB_ROLE_SWITCH=false`,
`AUTH_BACKEND=usersdb`, `DB_USER=postgres`.

## Ограничения и находки

- В Алматы у 69 384 участков с трубами `linesobj.fileid` пуст — они вне фрагментов, и территория их не
  ограничивает (правит любой с правом сети). Привязка к участкам эксплуатации (`uchastok_id` в
  `user_scope`) зарезервирована: трубы Алматы к участкам не привязаны.
- Веб-редактор топологии требует `network_struct`: пользователь только с `network` (бит 32) правит атрибуты,
  но не перемещает вершины через веб.
- Найдено при переносе: в `passwords` у «Акты раздела» (администратор), «Группа режимов», «Просмотр»
  пустой пароль — десктоп пускает их без пароля; в `auth.users` (QGIS) администратор `admin` с паролем `admin`.
  Перенесены заблокированными. У двух логинов в `passwords` по две записи (взята последняя).
- GeoServer ходит в базу суперпользователем; публичный слой `login` позволяет перебор паролей
  (`MD5('%password%')`), `get_file`/`read_file` читают файлы сервера (`pg_read_binary_file`).

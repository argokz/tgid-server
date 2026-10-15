-- Протоколы расчётов sety (веб: панель «Протокол расчёта», список расчётов).
-- Применять к сетевой БД города (almatygid, astanagid_*, копии), НЕ к UsersDB (alembic).
-- Воркер создаёт таблицу сам при первой записи (тот же SQL), если у пользователя БД есть право.
--
-- Строка — один запуск sety (при расчёте по списку — по строке на фрагмент): разобранные
-- ошибки/предупреждения (entries, utils/calc_protocol.py), сводка и исходный HTML-вывод.
-- Не *_out: удаление расчёта (DELETE /api/v1/calculations/{id}) протокол не трогает.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261015_calculation_protocol.sql

CREATE TABLE IF NOT EXISTS calculation_protocol (
    id            serial PRIMARY KEY,
    request_id    varchar(64)  NOT NULL,
    task_id       varchar(64),
    calculationid int,                      -- строка calculation, созданная запуском (NULL — не записан)
    fileid        int,                      -- фрагмент
    created_at    timestamptz  NOT NULL DEFAULT now(),
    author        varchar(100),
    mode          varchar(20),              -- plan / emergency
    params        text,
    status        varchar(20)  NOT NULL,    -- success / error
    errors        int          NOT NULL DEFAULT 0,
    warnings      int          NOT NULL DEFAULT 0,
    summary       jsonb,
    entries       jsonb,
    output        text
);

CREATE INDEX IF NOT EXISTS calculation_protocol_request_idx ON calculation_protocol (request_id);
CREATE INDEX IF NOT EXISTS calculation_protocol_created_idx ON calculation_protocol (created_at DESC);
CREATE INDEX IF NOT EXISTS calculation_protocol_calc_idx ON calculation_protocol (calculationid);

COMMENT ON TABLE calculation_protocol IS
    'Протоколы расчётов sety (web): ошибки и предупреждения с объектами сети, исходный вывод';

-- Индекс износа участков и приоритет ремонта (веб: «Износ и план ремонтов», database/wear.py).
-- Применять к сетевой БД города (almatygid, astanagid_*, shatura, копии), НЕ к UsersDB (alembic).
-- API доводит схему сам (database/city_schema.py); скрипт — для ручного применения.
--
-- Шапка расчёта — десктопная calculation_iznos (id, tn, daterascheta, name); строки по участкам
-- (heatpipesections → linesobj) — здесь, т.к. десктопная iznos ключуется по pipesections,
-- которых в Алматы нет. Имя *_out и колонка calculationid — как у остальных результатов.

CREATE TABLE IF NOT EXISTS calculation_iznos (
    id           serial PRIMARY KEY,
    tn           double precision,
    daterascheta timestamp,
    name         text
);

CREATE TABLE IF NOT EXISTS wear_out (
    id               serial PRIMARY KEY,
    calculationid    int NOT NULL,              -- calculation_iznos.id
    lineid           int NOT NULL,              -- linesobj.id
    pipesectionid    int,                       -- pipesections.id (если участки ПТС есть)
    fileid           int,                       -- фрагмент
    age_years        double precision,          -- срок эксплуатации от прокладки/перекладки
    age_source       varchar(16),               -- firstpic | lasttrans | none
    srok_ball        smallint,                  -- 1..5 по сроку (gid6 tgid_iznos.sql)
    n_defects        int NOT NULL DEFAULT 0,    -- повреждений по участку (defect)
    koef_povr        double precision,          -- повреждаемость, шт./100 м
    koef_povr_ball   smallint,
    vnesniivid       smallint,                  -- баллы из heatpipesections (0 — нет данных)
    sostoborudovania smallint,
    kategorii        smallint,
    vnesnkorrozia    smallint,
    vnunrenkorrozia  smallint,
    sostkonstrukz    smallint,
    factors_filled   smallint NOT NULL DEFAULT 0, -- сколько из 8 факторов заполнено
    wear_pct         double precision,          -- формула gid6 (незаполненные факторы = 0)
    wear_pct_known   double precision,          -- то же, нормировано на заполненные факторы
    category         smallint,                  -- 1..5 по wear_pct_known
    consequence      double precision,          -- множитель последствий отключения (1..2.6)
    flow_t_h         double precision,          -- расход по последнему расчёту фрагмента
    priority         double precision           -- wear_pct_known/100 × consequence × (1 + поток)
);

CREATE INDEX IF NOT EXISTS wear_out_calculationid_idx ON wear_out (calculationid);
CREATE INDEX IF NOT EXISTS wear_out_calc_priority_idx ON wear_out (calculationid, priority DESC);
CREATE INDEX IF NOT EXISTS wear_out_lineid_idx ON wear_out (lineid);

COMMENT ON TABLE wear_out IS
    'Индекс износа участков (формула gid6 tgid_iznos.sql) и приоритет ремонта по участкам; шапка — calculation_iznos';

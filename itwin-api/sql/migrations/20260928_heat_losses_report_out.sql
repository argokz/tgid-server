-- Листы расчёта нормативных теплопотерь (этап 9, перенос десктопного poteriNewPg).
-- Применять к сетевой БД (almatygid / копия), НЕ к UsersDB (alembic).
--
-- Десктоп выгружает результаты модуля «Теплопотери» только в Excel (в БД не пишет ничего,
-- кроме исходных heatLoses*). Веб сохраняет расчёт: строку calculation (fileid = NULL,
-- calc_params.module = "heat_losses_norm"), удельные потери по участкам — в ut_teplo_out,
-- листы по источникам — сюда. Имя *_out и колонка calculationid: DELETE /api/v1/calculations/{id}
-- удаляет строки этой таблицы вместе с расчётом.
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20260928_heat_losses_report_out.sql

CREATE TABLE IF NOT EXISTS heatlosses_report_out (
    id            serial PRIMARY KEY,
    calculationid int          NOT NULL,
    heatsourceid  int,                      -- NULL — итог по всем источникам расчёта
    sheet         varchar(40)  NOT NULL,    -- material_characteristics, month_temperatures, winter_norms, …
    rows          jsonb        NOT NULL
);

CREATE INDEX IF NOT EXISTS heatlosses_report_out_calculationid_idx
    ON heatlosses_report_out (calculationid);

COMMENT ON TABLE heatlosses_report_out IS
    'Листы расчёта нормативных теплопотерь (web, перенос gid8 poteriNewPg): строки листов Excel по источникам';

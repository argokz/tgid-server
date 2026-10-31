-- Прогноз аварийности (фаза 5, шаг 1): расчёты модели и риск участков (database/failure_forecast.py).
-- Только таблицы веба tgid_*. API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_failure_forecast.sql

CREATE TABLE IF NOT EXISTS tgid_failure_run (
    id               serial        PRIMARY KEY,
    horizon_years    smallint      NOT NULL,
    cutoffs          jsonb         NOT NULL,             -- срезы: обучение, проверка, итоговая модель, «сегодня»
    metrics          jsonb         NOT NULL,             -- проверка по времени: AUC, доля в верхних 10 %, ориентиры
    importance       jsonb         NOT NULL,             -- вклад признаков итоговой модели
    population       integer       NOT NULL,
    expected_events  double precision,                   -- ожидаемое число повреждений за горизонт (сумма вероятностей)
    took_s           double precision,
    created_by       varchar(100),
    created_at       timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tgid_failure_risk (
    run_id    integer           NOT NULL REFERENCES tgid_failure_run (id) ON DELETE CASCADE,
    lineid    integer           NOT NULL,
    prob      double precision  NOT NULL,                -- вероятность повреждения участка за горизонт
    rank_pct  double precision  NOT NULL,                -- место в рейтинге: 1 — самый рискованный
    hist_all  integer,
    near200   integer,
    age       double precision,
    len_m     double precision,
    PRIMARY KEY (run_id, lineid)
);

CREATE INDEX IF NOT EXISTS tgid_failure_risk_prob_idx ON tgid_failure_risk (run_id, prob DESC);

COMMENT ON TABLE tgid_failure_run IS 'Прогноз аварийности (web): расчёты модели, проверка по времени';

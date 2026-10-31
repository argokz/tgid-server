-- План перекладок (фаза 5, шаг 2): расценки перекладки за метр по диаметру (database/relay_plan.py). Заполняет
-- пользователь (право «Справочники»); пусто — план считается в километрах, а не в деньгах. Только таблицы веба
-- tgid_*. API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_relay_plan.sql

CREATE TABLE IF NOT EXISTS tgid_relay_price (
    dn_max_mm    integer           PRIMARY KEY,         -- класс: условный диаметр до этого значения включительно
    price_per_m  double precision  NOT NULL CHECK (price_per_m > 0),
    currency     varchar(8)        NOT NULL DEFAULT 'KZT',
    source       varchar(300),
    updated_by   varchar(100),
    updated_at   timestamptz       NOT NULL DEFAULT now()
);

COMMENT ON TABLE tgid_relay_price IS 'План перекладок (web): стоимость перекладки за метр по классу диаметра';

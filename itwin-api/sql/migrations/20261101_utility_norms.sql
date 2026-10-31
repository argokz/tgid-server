-- Общая карта коммуникаций (фаза 4, шаг 5): нормативные расстояния между сетями разных видов — для проверки
-- сближений и пересечений (database/utility_conflicts.py). Значения правит пользователь (право «Справочники»):
-- нормы различаются по странам и редакциям, засев — только подтверждённое по источнику. Только таблицы веба tgid_*.
-- API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_utility_norms.sql

CREATE TABLE IF NOT EXISTS tgid_utility_norm (
    kind_a        varchar(16)   NOT NULL,              -- heat | water (дальше — gas, power, sewer)
    kind_b        varchar(16)   NOT NULL,
    horizontal_m  double precision,                    -- по горизонтали в свету; NULL — нормы нет
    vertical_m    double precision,                    -- по вертикали в свету при пересечении; NULL — не задано
    source        varchar(300),
    updated_by    varchar(100),
    updated_at    timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (kind_a, kind_b),
    CHECK (kind_a <= kind_b)
);

INSERT INTO tgid_utility_norm (kind_a, kind_b, horizontal_m, vertical_m, source)
VALUES ('heat', 'water', 1.5, NULL,
        'СНиП РК 3.01-01-2008, табл. 12.6: водопровод — тепловые сети (от наружной стенки канала, тоннеля '
        'или оболочки бесканальной прокладки)')
ON CONFLICT (kind_a, kind_b) DO NOTHING;

COMMENT ON TABLE tgid_utility_norm IS 'Общая карта коммуникаций (web): нормативные расстояния между сетями разных видов';

-- Водопровод (фаза 4, шаг 2): зоны водоучёта (DMA). Расходомеры модели — трубы-вводы зон, их задаёт пользователь;
-- зоны и баланс считает API (database/water_zones.py) из сети модели и расчётов. Только таблицы веба tgid_*.
-- API применяет сам (city_schema).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261101_water_zones.sql

ALTER TABLE tgid_water_model ADD COLUMN IF NOT EXISTS meters jsonb NOT NULL DEFAULT '[]';

COMMENT ON COLUMN tgid_water_model.meters IS 'Водопровод (web): трубы с расходомерами — границы зон водоучёта (DMA)';

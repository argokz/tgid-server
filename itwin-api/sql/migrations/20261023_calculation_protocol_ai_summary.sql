-- Кеш объяснения протокола расчёта помощником ИИ (ai/calc_protocol.py).
-- Применять к сетевой БД города (almatygid, astanagid_*, shatura, копии), НЕ к UsersDB (alembic).
-- API доводит схему сам (database/city_schema.py), скрипт — для ручного применения.

ALTER TABLE calculation_protocol ADD COLUMN IF NOT EXISTS ai_summary jsonb;
ALTER TABLE calculation_protocol ADD COLUMN IF NOT EXISTS ai_summary_at timestamptz;

COMMENT ON COLUMN calculation_protocol.ai_summary IS
    'Объяснение протокола помощником ИИ (ai/calc_protocol.py): JSON ProtocolExplanation';

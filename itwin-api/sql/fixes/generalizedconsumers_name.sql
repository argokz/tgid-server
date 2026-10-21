-- Старые версии конвертера десктопа (база Шымкента) не создают generalizedconsumers.name
-- (название обобщённого потребителя; в новых — varchar(255)). Без неё падают слои GeoServer
-- find_node и id_generalizedconsumers, выборки потребителей API (отключения, анализ режима).
-- Пустая колонка, данные не меняются. Идемпотентно.

ALTER TABLE generalizedconsumers ADD COLUMN IF NOT EXISTS name varchar(255);

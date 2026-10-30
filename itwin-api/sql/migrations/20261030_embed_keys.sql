-- Встраиваемые карты (фаза 2, п. 14 плана модернизации): ключи для карты ТГИД в iframe на портале акимата,
-- ЕДДС, в кабинете потребителя. Только таблица веба tgid_*: десктоп её не читает. API применяет сам (city_schema).
--
-- tgid_embed_key — ключ встраивания. Сам ключ не хранится — только SHA-256 и первые символы для списка.
--   origins   — сайты, которым можно показывать карту в iframe (frame-ancestors) и слать события postMessage;
--   layers    — какие слои сети видны (pipes, nodes, consumers, heat_sources, valves);
--   fragments — только эти фрагменты (NULL — все);
--   outages   — слой публичных отключений (если служба включила PUBLIC_OUTAGES_ENABLED);
--   view      — начальный вид {"center": [lon, lat], "zoom": z} (NULL — охват сети).
--
--   psql -h <host> -p <port> -U <user> -d <db> -f sql/migrations/20261030_embed_keys.sql

CREATE TABLE IF NOT EXISTS tgid_embed_key (
    id            serial        PRIMARY KEY,
    name          varchar(100)  NOT NULL,
    key_hash      char(64)      NOT NULL UNIQUE,
    key_prefix    varchar(12)   NOT NULL,
    origins       text[]        NOT NULL,
    layers        text[]        NOT NULL,
    fragments     integer[],
    outages       boolean       NOT NULL DEFAULT false,
    view          jsonb,
    created_by    varchar(100)  NOT NULL DEFAULT '',
    created_at    timestamptz   NOT NULL DEFAULT now(),
    expires_at    timestamptz,
    revoked_at    timestamptz,
    revoked_by    varchar(100),
    last_used_at  timestamptz
);

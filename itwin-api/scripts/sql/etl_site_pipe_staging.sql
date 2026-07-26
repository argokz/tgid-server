-- Staging + apply для привязок участок↔линии (passport DoD).
-- Источник: desktop-дамп Access/SQL Server (heatpipesections.magistralSite/distSite).
-- На текущей almatygid все site-поля пусты — без ETL Excel-паспорт не соберёт граф.

CREATE TABLE IF NOT EXISTS etl_site_pipe_staging (
    lineid          integer PRIMARY KEY,
    magistralsite   integer,
    distsite        integer,
    source_note     text,
    loaded_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE etl_site_pipe_staging IS
  'Импорт site↔pipe из desktop; apply обновляет heatpipesections.*Site';

-- Пример загрузки (psql \copy или COPY FROM):
-- \copy etl_site_pipe_staging(lineid, magistralsite, distsite, source_note)
--   FROM 'site_pipe.csv' WITH (FORMAT csv, HEADER true);

BEGIN;

UPDATE heatpipesections h
   SET magistralsite = s.magistralsite,
       distsite      = s.distsite
  FROM etl_site_pipe_staging s
 WHERE h.lineid = s.lineid
   AND (
        s.magistralsite IS NOT NULL
     OR s.distsite IS NOT NULL
   );

-- После apply: backfill nodes.belong* из incident lines
-- (см. scripts/sql/backfill_belong_site.sql)

COMMIT;

-- Контроль
-- SELECT count(*) FILTER (WHERE magistralsite IS NOT NULL AND magistralsite <> 0) AS ms,
--        count(*) FILTER (WHERE distsite IS NOT NULL AND distsite <> 0) AS rs
--   FROM heatpipesections;

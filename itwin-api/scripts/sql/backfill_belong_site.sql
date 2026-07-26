-- Backfill nodes.belongMagistralSite / belongDistSite from heatpipesections.
-- Run on a DB *copy* first. Prefer API fallback (passport_site.py) if you cannot write.
--
-- Rule: for each node, take the most frequent non-null magistralSite among incident
-- lines; else most frequent distSite. Do not overwrite existing non-null values.

BEGIN;

WITH line_sites AS (
  SELECT
    lo.nodeid1 AS node_id,
    NULLIF(hps.magistralsite, 0) AS ms,
    NULLIF(hps.distsite, 0) AS rs
  FROM linesobj lo
  JOIN heatpipesections hps ON hps.lineid = lo.id
  UNION ALL
  SELECT
    lo.nodeid2,
    NULLIF(hps.magistralsite, 0),
    NULLIF(hps.distsite, 0)
  FROM linesobj lo
  JOIN heatpipesections hps ON hps.lineid = lo.id
),
ms_pick AS (
  SELECT node_id, ms AS site_id,
         ROW_NUMBER() OVER (PARTITION BY node_id ORDER BY COUNT(*) DESC) AS rn
  FROM line_sites
  WHERE ms IS NOT NULL
  GROUP BY node_id, ms
),
rs_pick AS (
  SELECT node_id, rs AS site_id,
         ROW_NUMBER() OVER (PARTITION BY node_id ORDER BY COUNT(*) DESC) AS rn
  FROM line_sites
  WHERE rs IS NOT NULL
  GROUP BY node_id, rs
)
UPDATE nodes n
SET belongmagistralsite = m.site_id
FROM ms_pick m
WHERE n.id = m.node_id
  AND m.rn = 1
  AND (n.belongmagistralsite IS NULL OR n.belongmagistralsite = 0);

WITH line_sites AS (
  SELECT
    lo.nodeid1 AS node_id,
    NULLIF(hps.distsite, 0) AS rs
  FROM linesobj lo
  JOIN heatpipesections hps ON hps.lineid = lo.id
  UNION ALL
  SELECT
    lo.nodeid2,
    NULLIF(hps.distsite, 0)
  FROM linesobj lo
  JOIN heatpipesections hps ON hps.lineid = lo.id
),
rs_pick AS (
  SELECT node_id, rs AS site_id,
         ROW_NUMBER() OVER (PARTITION BY node_id ORDER BY COUNT(*) DESC) AS rn
  FROM line_sites
  WHERE rs IS NOT NULL
  GROUP BY node_id, rs
)
UPDATE nodes n
SET belongdistsite = r.site_id
FROM rs_pick r
WHERE n.id = r.node_id
  AND r.rn = 1
  AND (n.belongdistsite IS NULL OR n.belongdistsite = 0)
  AND (n.belongmagistralsite IS NULL OR n.belongmagistralsite = 0);

COMMIT;

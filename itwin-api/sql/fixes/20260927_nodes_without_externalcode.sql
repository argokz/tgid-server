-- Узлы без кода (externalcodeid), созданные web-редактором до 27.09.2026 (до п. 8.5):
-- участки на таких узлах не видны ни в слое карты (SQL view GeoServer `heatpipesections`
-- делает JOIN externalcodes по обоим узлам), ни в расчёте (sety: JOIN externalCodes).
-- Код и признак подачи/обратки берутся у ближайшего узла того же фрагмента и той же схемы
-- в радиусе 300 м, иначе — первый код фрагмента (externalcodes.fileid), как новый узел
-- получает их сейчас (topology._new_node_reference, явный fileid).
-- Идемпотентно; применять вручную, сначала посмотреть выборку (первый SELECT).
-- Только основная сеть (internalnodeid IS NULL): узлы внутренних схем без кода есть в данных
-- десктопа (прод: 91111–91114, схема узла 91098) — их не трогаем.
-- На 27.09.2026: прод almatygid — 0 узлов; копия — 604338, 604339, 604344 (фрагмент 89, исправлены).

SELECT n.id, n.fileid, ref.id AS ref_node,
       COALESCE(ref.externalcodeid, (SELECT min(ec.id) FROM externalcodes ec
                                     WHERE ec.fileid = n.fileid AND COALESCE(ec.removed, 0) = 0)) AS externalcodeid,
       round(ref.dist::numeric, 1) AS dist_m
FROM nodes n
LEFT JOIN LATERAL (
    SELECT r.id, r.externalcodeid, ST_Distance(r.shape, n.shape) AS dist
    FROM nodes r
    WHERE r.fileid = n.fileid AND r.externalcodeid IS NOT NULL AND COALESCE(r.removed, 0) = 0
      AND r.internalnodeid IS NOT DISTINCT FROM n.internalnodeid AND r.shape IS NOT NULL
      AND ST_DWithin(r.shape, n.shape, 300)
    ORDER BY r.shape <-> n.shape
    LIMIT 1
) ref ON true
WHERE COALESCE(n.removed, 0) = 0 AND n.externalcodeid IS NULL AND n.internalnodeid IS NULL AND n.fileid IS NOT NULL AND n.shape IS NOT NULL;

BEGIN;
UPDATE nodes n
SET externalcodeid = COALESCE(ref.externalcodeid, (SELECT min(ec.id) FROM externalcodes ec
                                                   WHERE ec.fileid = x.fileid AND COALESCE(ec.removed, 0) = 0)),
    externalsignid = COALESCE(n.externalsignid, ref.externalsignid, 1),
    archivechangedate = now()
FROM nodes x
LEFT JOIN LATERAL (
    SELECT r.externalcodeid, r.externalsignid
    FROM nodes r
    WHERE r.fileid = x.fileid AND r.externalcodeid IS NOT NULL AND COALESCE(r.removed, 0) = 0
      AND r.internalnodeid IS NOT DISTINCT FROM x.internalnodeid AND r.shape IS NOT NULL
      AND ST_DWithin(r.shape, x.shape, 300)
    ORDER BY r.shape <-> x.shape
    LIMIT 1
) ref ON true
WHERE n.id = x.id
  AND COALESCE(x.removed, 0) = 0 AND x.externalcodeid IS NULL AND x.internalnodeid IS NULL AND x.fileid IS NOT NULL AND x.shape IS NOT NULL;
COMMIT;

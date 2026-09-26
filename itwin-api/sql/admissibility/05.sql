SELECT * FROM (
WITH base AS (
  SELECT 
    n.id AS node_id, 
    n.fileID, 
    n.externalNodeName,
    rc.id AS consumer_id,

    ptOut.QFact,
    ptOut.QTreb,
    ptOut.Q_obesp_otopl_min
  FROM nodes n
  LEFT JOIN realConsumers rc ON rc.nodeID = n.id
  LEFT JOIN (
      SELECT c.fileID, MAX(c.id) AS cid
      FROM CALCULATION c
      LEFT JOIN fragments fr ON fr.id = c.fileID
      GROUP BY c.fileID
  ) calc ON calc.fileID = n.fileID
  LEFT JOIN PT_OUT ptOut 
         ON ptOut.nodeID = n.id 
        AND ptOut.calculationID = calc.cid
  WHERE n.removed = 0
    AND n.fileID = $1
    AND rc.id IS NOT NULL
    AND n.externalSignID = 1
    AND n.internalNodeID IS NULL
),
with_pct AS (
  SELECT
    node_id,
    externalNodeName,
    Q_obesp_otopl_min,
    SUM(QFact) OVER (PARTITION BY consumer_id) AS q1_cons,
    SUM(QTreb) OVER (PARTITION BY consumer_id) AS q2_cons,
    SUM(QFact) OVER () AS q1_total,
    SUM(QTreb) OVER () AS q2_total,
    100.0 * SUM(QFact) OVER () / NULLIF(SUM(QTreb) OVER (), 0) AS q_total,
    Q_obesp_otopl_min AS pct_cons
  FROM base
)
SELECT
  node_id AS id,
  externalNodeName,
  q1_cons AS "Получ. тепл. нагрузка ТП, Гкал/ч.",
  q2_cons AS "Треб. тепл. нагрузка ТП, Гкал/ч.",
  pct_cons  AS "Теплообесп.СО, %",
  CASE
    WHEN pct_cons  IS NULL THEN 'Нет данных'
    WHEN pct_cons  < 70     THEN 'Дефицит тепла'
    WHEN pct_cons  > 100    THEN 'Перерасход тепла'
    ELSE 'Норма'
  END AS "Режим (отд. потреб.)",
  q1_total AS "Сумм. получ. тепл. нагрузка, Гкал/ч.",
  q2_total AS "Сумм. треб. тепл. нагрузка, Гкал/ч.",
  q_total  AS "Теплообесп. совокуп. потреб., %",
  CASE
    WHEN q_total IS NULL THEN 'Нет данных'
    WHEN q_total < 70     THEN 'Дефицит тепла'
    WHEN q_total > 100    THEN 'Перерасход тепла'
    ELSE 'Норма'
  END AS "Режим (совокупно)"
FROM with_pct
WHERE NOT (
    (pct_cons IS NOT NULL AND pct_cons BETWEEN 70 AND 100)
)
) src

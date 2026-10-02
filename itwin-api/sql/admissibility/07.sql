SELECT * From (SELECT *
FROM (
  SELECT
      n.id               AS "ID узла",
      n.externalNodeName AS "Наименование",

      Qotz_treb  AS "Треб. отопл. (зав.), Гкал/ч",
      Qotn_treb  AS "Треб. отопл. (незав.), Гкал/ч",
      Qvent_treb AS "Треб. вент., Гкал/ч",

      Qotz  AS "Получ. отопл. (зав.), Гкал/ч",
      Qotn  AS "Получ. отопл. (незав.), Гкал/ч",
      dop12 AS "Получ. вент., Гкал/ч",

      /* Теплообеспечение СО, % */
      ROUND(
        (
          (COALESCE(Qotz, 0.0) + COALESCE(Qotn, 0.0))
          / NULLIF(COALESCE(Qotz_treb, 0.0) + COALESCE(Qotn_treb, 0.0), 0.0)
          * 100
        )::numeric, 2
      ) AS "Теплообесп. СО, %",

      /* Теплообеспечение СВ, % */
      ROUND(
        (
          COALESCE(dop12, 0.0)
          / NULLIF(COALESCE(Qvent_treb, 0.0), 0.0)
          * 100
        )::numeric, 2
      ) AS "Теплообесп. СВ, %",

      /* Суммарное теплообеспечение, % */
      ROUND(
        (
          (COALESCE(Qotz, 0.0) + COALESCE(Qotn, 0.0) + COALESCE(dop12, 0.0))
          / NULLIF(COALESCE(Qotz_treb, 0.0) + COALESCE(Qotn_treb, 0.0) + COALESCE(Qvent_treb, 0.0), 0.0)
          * 100
        )::numeric, 2
      ) AS "Теплообесп., %",

      CASE
        WHEN (
          (COALESCE(Qotz, 0.0) + COALESCE(Qotn, 0.0) + COALESCE(dop12, 0.0))
          / NULLIF(COALESCE(Qotz_treb, 0.0) + COALESCE(Qotn_treb, 0.0) + COALESCE(Qvent_treb, 0.0), 0.0)
          * 100
        ) IS NULL THEN 'Нет данных'
        WHEN (
          (COALESCE(Qotz, 0.0) + COALESCE(Qotn, 0.0) + COALESCE(dop12, 0.0))
          / NULLIF(COALESCE(Qotz_treb, 0.0) + COALESCE(Qotn_treb, 0.0) + COALESCE(Qvent_treb, 0.0), 0.0)
          * 100
        ) < 70 THEN 'Дефицит тепла'
        WHEN (
          (COALESCE(Qotz, 0.0) + COALESCE(Qotn, 0.0) + COALESCE(dop12, 0.0))
          / NULLIF(COALESCE(Qotz_treb, 0.0) + COALESCE(Qotn_treb, 0.0) + COALESCE(Qvent_treb, 0.0), 0.0)
          * 100
        ) > 100 THEN 'Перерасход тепла'
        ELSE 'Допустимо'
      END AS "Режим"

  FROM nodes n
  LEFT JOIN realConsumers        rc   ON rc.nodeID = n.id
  LEFT JOIN generalizedConsumers gc   ON gc.nodeID = n.id
  LEFT JOIN heatSources          ist  ON ist.nodeID = n.id
  LEFT JOIN pumpStations         hs   ON hs.nodeID = n.id
  LEFT JOIN threeWayValves       c3   ON c3.nodeID = n.id
  LEFT JOIN connectNodes         us2  ON us2.nodeID = n.id

  LEFT JOIN (
      SELECT c.fileID, MAX(c.id) FILTER (WHERE $2::int IS NULL OR c.id = $2::int) AS cid
      FROM CALCULATION c
      LEFT JOIN fragments fr ON fr.id = c.fileID
      GROUP BY c.fileID
  ) calc ON calc.fileID = n.fileID

  LEFT JOIN US_OUT usP   ON usP.nodeID = n.id AND usP.externalSign = 1 AND usP.calculationID = calc.cid
  LEFT JOIN US_OUT usO   ON usO.nodeID = n.id AND usO.externalSign = 2 AND usO.calculationID = calc.cid
  LEFT JOIN PT_OUT ptOut ON ptOut.nodeID = n.id AND ptOut.calculationID = calc.cid
  LEFT JOIN DR_OUT       ON DR_OUT.nodeID = n.id AND DR_OUT.calculationID = calc.cid

  WHERE
      n.removed = 0
      AND n.fileID = $1
      AND gc.id IS NOT NULL
      AND n.externalSignID = 1
      AND n.internalNodeID IS NULL
      AND (
        (COALESCE(Qotz, 0.0) + COALESCE(Qotn, 0.0) + COALESCE(dop12, 0.0))
        / NULLIF(COALESCE(Qotz_treb, 0.0) + COALESCE(Qotn_treb, 0.0) + COALESCE(Qvent_treb, 0.0), 0.0)
        * 100
      ) NOT BETWEEN 70 AND 100
) t) src

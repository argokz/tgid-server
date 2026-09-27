-- gid6 excel2/sql2/OUT_Насосные_агрегаты.sql: режим работы насосов (шаблон G_NSA)
-- ns_out.a19 хранит id типоразмера (standardpumps) строкой.
-- $1: фрагмент, $2: расчёт
SELECT eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
       '' AS name_soder,
       ec1.name AS kod1, n1.externalnodename AS uzel1,
       CASE o.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       o.a4,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE o.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       o.a8,
       sp.h_min AS a9,
       sp.q_min AS a10,
       sp.h_max AS a11,
       sp.q_max AS a12,
       o.a13, o.a14, o.a15, o.a16, o.a17, o.a18,
       sp.tip_nas,
       hs.sourcename
  FROM ns_out o
  JOIN linesobj l ON l.id = o.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
  LEFT JOIN externalcodes eci ON eci.id = ni.externalcodeid
  LEFT JOIN externalsigns esi ON esi.id = ni.externalsignid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
  LEFT JOIN standardpumps sp ON sp.id::text = o.a19
 WHERE n1.fileid = $1 AND o.calculationid = $2 AND l.removed = 0
 ORDER BY eci.name NULLS FIRST, ni.externalnodename NULLS FIRST, ec1.name, n1.externalnodename, l.id

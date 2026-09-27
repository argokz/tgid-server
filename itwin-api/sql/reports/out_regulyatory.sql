-- gid6 excel2/sql2/OUT_Регуляторы.sql: режим сетевых регуляторов (шаблон G_RS)
-- $1: фрагмент, $2: расчёт
SELECT eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
       ec1.name AS kod1, n1.externalnodename AS uzel1,
       CASE o.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       n1.geomarktoptube AS geod1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE o.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       n2.geomarktoptube AS geod2,
       ec3.name AS kod3, n3.externalnodename AS uzel3,
       CASE reg.pipelinesignid WHEN 1 THEN 'П' WHEN 2 THEN 'О' END AS pr3,
       o.a11, o.a12, o.a13, o.a14, o.a15, o.a16, o.a17, o.a18, o.a19,
       hs.sourcename
  FROM rs_out o
  JOIN linesobj l ON l.id = o.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  JOIN externalsignline esl ON esl.id = o.externalsignlineid
  LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
  LEFT JOIN externalcodes eci ON eci.id = ni.externalcodeid
  LEFT JOIN externalsigns esi ON esi.id = ni.externalsignid
  LEFT JOIN pressregulators reg ON reg.lineid = l.id
  LEFT JOIN nodes n3 ON n3.id = reg.nodeid
  LEFT JOIN externalcodes ec3 ON ec3.id = n3.externalcodeid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
 WHERE n1.fileid = $1 AND o.calculationid = $2 AND l.removed = 0
 ORDER BY eci.name NULLS FIRST, ni.externalnodename NULLS FIRST, ec1.name, n1.externalnodename, l.id, o.externalsignlineid

-- gid6 excel2/sql2/Задвижки.sql: входные данные задвижек (шаблон gzd / G_ZD, лист 1)
-- $1: фрагмент
SELECT l.id,
       das.name AS sost,
       d.dispatcherswitch AS name_zd,
       eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
       ec1.name AS kod1,
       n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2,
       n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       d.diametercondit AS diametr,
       d.relatleakage AS otn_kv,
       d.partdempopen AS proz_kv,
       l.hydrores AS sopr,
       '' AS aa1,
       '' AS aa2,
       hs.sourcename
  FROM dampers d
  JOIN linesobj l ON l.id = d.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON n1.externalcodeid = ec1.id
  JOIN externalsigns es1 ON n1.externalsignid = es1.id
  JOIN externalcodes ec2 ON n2.externalcodeid = ec2.id
  JOIN externalsigns es2 ON n2.externalsignid = es2.id
  LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
  LEFT JOIN externalcodes eci ON ni.externalcodeid = eci.id
  LEFT JOIN externalsigns esi ON ni.externalsignid = esi.id
  JOIN damperarmaturestates das ON das.id = d.damperarmaturestateid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
 WHERE n1.fileid = $1 AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY eci.name NULLS FIRST, ni.externalnodename NULLS FIRST, ec1.name, n1.externalnodename, l.id

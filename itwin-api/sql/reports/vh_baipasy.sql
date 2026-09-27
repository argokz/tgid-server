-- gid6 excel2/sql2/Байпасы.sql (шаблон gbp / G_BP, лист 1)
-- $1: фрагмент
SELECT l.id,
       rs.name AS sost,
       ec1.name AS kod1, n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       ec3.name AS kod3, n3.externalnodename AS uzel3,
       CASE b.pipelinesignid WHEN 1 THEN 'П' WHEN 2 THEN 'О' END AS pr3,
       b.q AS q,
       b.deltaq AS delta_q,
       b.length AS dln,
       b.diameterinternal AS diam,
       b.tuberoughness AS scher,
       b.rescoeffssum AS sum_m_s,
       l.hydrores AS sopr,
       b.locinstall AS ustanovka,
       hs.sourcename
  FROM bypass b
  JOIN linesobj l ON l.id = b.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  LEFT JOIN externalcodes ec1 ON n1.externalcodeid = ec1.id
  LEFT JOIN externalcodes ec2 ON n2.externalcodeid = ec2.id
  LEFT JOIN regulatorstates rs ON rs.id = b.regulatorstateid
  LEFT JOIN nodes n3 ON n3.id = b.nodeid
  LEFT JOIN externalcodes ec3 ON ec3.id = n3.externalcodeid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
 WHERE n1.fileid = $1 AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY ec1.name, n1.externalnodename, l.id

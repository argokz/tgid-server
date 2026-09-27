-- gid6 excel2/sql2/OUT_Байпасы.sql: результаты расчёта байпасов (шаблон G_BP, лист 2)
-- $1: фрагмент, $2: расчёт (calculation.id)
SELECT ec1.name AS kod1, n1.externalnodename AS uzel1,
       CASE o.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       o.a4,
       o.a5,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE o.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       o.a9,
       o.a10,
       esl.name AS externalsignline,
       o.a11, o.a12, o.a13, o.a14, o.a15, o.a16, o.a17, o.a18
  FROM bp_out o
  JOIN linesobj l ON l.id = o.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  JOIN externalsignline esl ON esl.id = o.externalsignlineid
 WHERE n1.fileid = $1 AND o.calculationid = $2 AND l.removed = 0
 ORDER BY ec1.name, n1.externalnodename, l.id, o.externalsignlineid

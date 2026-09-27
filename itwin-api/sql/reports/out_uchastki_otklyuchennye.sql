-- gid6 excel2/sql2/OUT_Участки Отключенные.sql: участки без результатов расчёта или закрытые (шаблон G_UT, лист 4)
-- $1: фрагмент, $2: расчёт
SELECT l.id,
       CASE WHEN (u.id IS NULL OR u.externalsignlineid IN (1, 2, 4)) AND hps.pipesectstateidflow = 2
             AND (u.id IS NULL OR u.externalsignlineid IN (1, 3, 5)) AND hps.pipesectstateidret = 2
            THEN 'закр' ELSE '' END AS sost,
       ec1.name AS kod1, n1.externalnodename AS uzel1,
       CASE COALESCE(u.externalsignlineid, l.externalsignlineid)
            WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE COALESCE(u.externalsignlineid, l.externalsignlineid)
            WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       hps.pipesectlength AS dlina,
       hps.diameterinternal AS diametr,
       hs.sourcename
  FROM linesobj l
  LEFT JOIN ut_out u ON u.lineid = l.id AND u.calculationid = $2
  JOIN heatpipesections hps ON hps.lineid = l.id
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
  JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
  LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
 WHERE n1.fileid = $1 AND n1.internalnodeid IS NULL AND l.removed = 0
   AND (u.id IS NULL
        OR (hps.pipesectstateidflow = 2 AND u.externalsignlineid IN (1, 2, 4))
        OR (hps.pipesectstateidret = 2 AND u.externalsignlineid IN (1, 3, 5)))
 ORDER BY ec1.name, n1.externalnodename, l.id, u.externalsignlineid

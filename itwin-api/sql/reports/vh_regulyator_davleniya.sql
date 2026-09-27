-- gid6 excel2/sql2/Регулятор давления.sql (шаблон grd)
-- $1: фрагмент
SELECT l.id,
       eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
       ec1.name AS kod1,
       n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       prec.name AS uzu_k, prn.externalnodename AS uzu, pres.name AS przu,
       pr.h AS h_uzu, pr.deltah AS delta, pr.regvalverelcap AS kv, pr.relleakage AS otn_kv,
       pr.consdrip AS g_tep_poteri, pr.valvehydroresopen AS min_sm,
       l.registnum AS registr, l.firstpicdate AS datenew, l.lastmaintdate AS dateend_to,
       l.displaysign AS podp, l.archivechangedate AS date_archives,
       pr.valvehydroresclose AS max_sm, rs.name AS sost, pls.name AS przu1, wa.name AS pr_raboti,
       o.name AS operator, org.name AS kod_owner, ni.fileid
  FROM pressregulators pr
  JOIN linesobj l ON l.id = pr.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON n1.externalcodeid = ec1.id
  JOIN externalcodes ec2 ON n2.externalcodeid = ec2.id
  LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
  LEFT JOIN externalcodes eci ON ni.externalcodeid = eci.id
  LEFT JOIN externalsigns esi ON ni.externalsignid = esi.id
  LEFT JOIN nodes prn ON prn.id = pr.nodeid
  LEFT JOIN externalcodes prec ON prec.id = prn.externalcodeid
  LEFT JOIN externalsigns pres ON pres.id = prn.externalsignid
  LEFT JOIN workattributes wa ON wa.id = pr.workattrid
  LEFT JOIN regulatorstates rs ON rs.id = pr.regulatorstateid
  LEFT JOIN pipelinesigns pls ON pls.id = pr.pipelinesignid
  LEFT JOIN operators o ON o.id = l.operatorid
  LEFT JOIN organizations org ON org.id = l.organizationid
 WHERE n1.fileid = $1 AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY eci.name NULLS FIRST, ni.externalnodename NULLS FIRST, ec1.name, n1.externalnodename, l.id

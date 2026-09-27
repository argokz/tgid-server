-- gid6 excel2/sql2/Регулятор перепада.sql (шаблон gre). В исходнике признаки П/О были
-- испорчены двойной перекодировкой; здесь восстановлены.
-- $1: фрагмент
SELECT eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
       ec1.name AS kod1,
       n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       pdrec.name AS uzu_k, pdrn.externalnodename AS uzu, pdres.name AS przu,
       pdr.deltah AS delta, pdr.regvalverelcap AS kv, pdr.maxleakageclosevalve AS otn_kv, pdr.regvalvehydrores AS sm,
       pdr.consthroughregvalve AS g, pdr.thrustdropmean AS h_fakt, pdr.consdrip AS g_tep_poteri,
       rs.name AS sost, pdr.workattrid AS pr_raboti_id,
       l.registnum AS registr, l.firstpicdate AS datenew, l.lastmaintdate AS dateend_to, l.displaysign AS podp,
       l.archivechangedate AS date_archives,
       wa.name AS pr_raboti,
       o.name AS operator, org.name AS kod_owner, ni.fileid
  FROM pressdropregulators pdr
  JOIN linesobj l ON l.id = pdr.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON n1.externalcodeid = ec1.id
  JOIN externalcodes ec2 ON n2.externalcodeid = ec2.id
  JOIN nodes ni ON ni.id = n1.internalnodeid
  JOIN externalcodes eci ON ni.externalcodeid = eci.id
  JOIN externalsigns esi ON ni.externalsignid = esi.id
  JOIN nodes pdrn ON pdrn.id = pdr.nodeid
  JOIN externalcodes pdrec ON pdrec.id = pdrn.externalcodeid
  JOIN externalsigns pdres ON pdres.id = pdrn.externalsignid
  LEFT JOIN workattributes wa ON wa.id = pdr.workattrid
  LEFT JOIN regulatorstates rs ON rs.id = pdr.regulatorstateid
  LEFT JOIN operators o ON o.id = l.operatorid
  LEFT JOIN organizations org ON org.id = l.organizationid
 WHERE n1.fileid = $1 AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY eci.name, ni.externalnodename, ec1.name, n1.externalnodename, l.id

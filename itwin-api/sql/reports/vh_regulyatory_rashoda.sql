-- gid6 excel2/sql2/Регуляторы расхода.sql (шаблон grr)
-- $1: фрагмент
SELECT l.id,
       eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
       ec1.name AS kod1,
       n1.externalnodename AS uzel1,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' END AS pr1,
       ec2.name AS kod2, n2.externalnodename AS uzel2,
       CASE l.externalsignlineid WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'О' WHEN 5 THEN 'П' END AS pr2,
       cr.regconsmean AS q_zad, cr.deltah AS delta, cr.regvalvecap AS kv, cr.relatleakage AS otn_kv,
       cr.plumsconsumption AS g_tep_poteri,
       cr.hydroresopen AS min_sm, cr.hydroresclose AS max_sm, cr.opc AS opc, cr.regulatorstateid AS sost_id,
       l.registnum AS registr, l.firstpicdate AS datenew, l.lastmaintdate AS dateend_to,
       l.displaysign AS podp, l.archivechangedate AS date_archives,
       wa.name AS pr_raboti, o.name AS operator, org.name AS kod_owner, rs.name AS sost, ni.fileid
  FROM consumptregulators cr
  JOIN linesobj l ON l.id = cr.lineid
  JOIN nodes n1 ON n1.id = l.nodeid1
  JOIN nodes n2 ON n2.id = l.nodeid2
  JOIN externalcodes ec1 ON n1.externalcodeid = ec1.id
  JOIN externalcodes ec2 ON n2.externalcodeid = ec2.id
  LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
  LEFT JOIN externalcodes eci ON ni.externalcodeid = eci.id
  LEFT JOIN externalsigns esi ON ni.externalsignid = esi.id
  LEFT JOIN workattributes wa ON wa.id = cr.workattrid
  LEFT JOIN regulatorstates rs ON rs.id = cr.regulatorstateid
  LEFT JOIN operators o ON o.id = l.operatorid
  LEFT JOIN organizations org ON org.id = l.organizationid
 WHERE n1.fileid = $1 AND l.removed = 0 AND n1.removed = 0 AND n2.removed = 0 AND n1.fileid = n2.fileid
 ORDER BY eci.name NULLS FIRST, ni.externalnodename NULLS FIRST, ec1.name, n1.externalnodename, l.id

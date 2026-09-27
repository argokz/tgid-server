-- gid6 excel2/sql2/OUT_Потребители2.sql: гидравлический режим потребителей (шаблон G_PT, лист 4)
-- $1: фрагмент, $2: расчёт
SELECT n.id,
       CASE WHEN COALESCE(gc.consumerstateid, rc.consumerstateid) = 1 THEN ' ' ELSE 'закр' END AS stateid,
       CASE WHEN gc.consumerstateid IS NOT NULL THEN 'О' ELSE ' ' END AS prizn,
       ec.name AS kod, n.externalnodename AS uzel,
       rc.name AS name_building,
       p.a4,
       p.a5,
       p.a6,
       p.a11,
       p.a12, p.a13, p.a14,
       p.a15, p.a16, p.a17,
       p.a21, p.a22,
       p.a23,
       p.gneob,
       hs.name AS kod_ist
  FROM pt_out p
  JOIN nodes n ON n.id = p.nodeid
  JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN generalizedconsumers gc ON gc.nodeid = n.id
  LEFT JOIN realconsumers rc ON rc.nodeid = n.id
  LEFT JOIN heatsources hs ON hs.id = ec.heatsourceid
 WHERE n.fileid = $1 AND p.calculationid = $2 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id

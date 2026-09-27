-- gid6 excel2/sql2/OUT_PT_Тепло.sql: тепловой режим потребителей (шаблон G_PT, лист 5)
-- $1: фрагмент, $2: расчёт
SELECT n.id,
       CASE WHEN n.cstatename = 'открыто' THEN ' ' ELSE 'закр' END AS cstatename,
       n.obob AS po_pr,
       n.externalcode, n.externalnodename, n.name_building,
       round(p.t1::numeric, 1) AS t1,
       round(p.t2::numeric, 1) AS t2,
       round(p.qotz::numeric, 3) AS qotz,
       round(p.qotn::numeric, 3) AS qotn,
       COALESCE(p.dop12, 0) + COALESCE(p.dop13, 0) AS dop12_13,
       round(p.dop17::numeric, 3) AS dop17,
       round(p.dop18::numeric, 3) AS dop18,
       round(p.dop19::numeric, 3) AS dop19,
       round(p.dop20::numeric, 3) AS dop20,
       round(p.qsum_z::numeric, 3) AS qsum_z,
       round(p.dop18::numeric, 3) AS dop18_2,
       round(p.dop19::numeric, 3) AS dop19_2,
       round(p.qotz_treb::numeric, 3) AS qotz_treb,
       round(p.qotn_treb::numeric, 3) AS qotn_treb,
       round(p.qvent_treb::numeric, 3) AS qvent_treb,
       p.qgvz_treb,
       n.avghlgvsopenflow, n.avghlgvsopenret,
       n.rez_q,
       COALESCE(p.qotz_treb, 0) + COALESCE(p.qotn_treb, 0) + COALESCE(p.qvent_treb, 0)
         + COALESCE(p.qgvz_treb, 0) AS qsum,
       n.avghlgvsopenflow AS avghlgvsopenflow2,
       n.avghlgvsopenret AS avghlgvsopenret2,
       hs.name
  FROM ({{_consumerview}}) n
  JOIN pt_out p ON p.nodeid = n.id AND p.calculationid = $2
  LEFT JOIN externalcodes ec ON ec.id = n.kod_ist
  LEFT JOIN heatsources hs ON hs.id = ec.heatsourceid
 WHERE n.fileid = $1
 ORDER BY n.obob, n.externalcode, n.externalnodename, n.id

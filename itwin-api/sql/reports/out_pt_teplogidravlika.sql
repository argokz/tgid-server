-- gid6 excel2/sql2/OUT_PT_ТеплоГидравл.sql: теплогидравлический режим потребителей (шаблон G_PT, лист 6)
-- $1: фрагмент, $2: расчёт
SELECT n.id,
       CASE WHEN n.cstatename = 'открыто' THEN ' ' ELSE 'закр' END AS cstatename,
       n.obob AS po_pr,
       n.externalcode, n.externalnodename, n.name_building,
       p.a4,
       p.a5,
       p.a6 + p.a7 AS a6_7,
       p.a11,
       p.a12,
       p.a13,
       p.a14,
       p.a15,
       p.a16,
       p.a17,
       round(p.a21::numeric, 1) AS a21,
       round(p.a22::numeric, 1) AS a22,
       round(p.a23::numeric, 1) AS a23,
       round(p.t1::numeric, 1) AS t1,
       round(p.t2::numeric, 1) AS t2,
       round(p.qotz::numeric, 3) AS qotz, round(p.qotn::numeric, 3) AS qotn,
       COALESCE(p.dop12, 0) + COALESCE(p.dop13, 0) AS dop12_13,
       round(p.dop17::numeric, 3) AS dop17,
       round(p.dop18::numeric, 3) AS dop18,
       round(p.dop19::numeric, 3) AS dop19,
       round(p.dop20::numeric, 3) AS dop20,
       round(p.qsum_z::numeric, 3) AS qsum_z,
       round(p.dop18::numeric, 3) AS dop18_2,
       round(p.dop19::numeric, 3) AS dop19_2,
       COALESCE(p.qotz_treb, 0) + COALESCE(p.qotn_treb, 0) + COALESCE(p.qvent_treb, 0)
         + COALESCE(p.qgvz_treb, 0) AS qsum,
       CASE WHEN COALESCE(p.dop18, 0) = 0 AND COALESCE(p.dop19, 0) = 0 THEN 0
            ELSE p.qgvop_treb * COALESCE(p.dop18, 0) / (COALESCE(p.dop18, 0) + COALESCE(p.dop19, 0)) END AS dop18_1,
       CASE WHEN COALESCE(p.dop18, 0) = 0 AND COALESCE(p.dop19, 0) = 0 THEN 0
            ELSE p.qgvoo_treb * COALESCE(p.dop19, 0) / (COALESCE(p.dop18, 0) + COALESCE(p.dop19, 0)) END AS dop19_1,
       round(p.gneob::numeric, 3) AS gneob,
       hs.name
  FROM ({{_consumerview}}) n
  JOIN pt_out p ON p.nodeid = n.id AND p.calculationid = $2
  LEFT JOIN externalcodes ec ON ec.id = n.kod_ist
  LEFT JOIN heatsources hs ON hs.id = ec.heatsourceid
 WHERE n.fileid = $1
 ORDER BY n.obob, n.externalcode, n.externalnodename, n.id

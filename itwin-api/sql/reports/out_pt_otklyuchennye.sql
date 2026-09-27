-- gid6 excel2/sql2/OUT_PT_Отключенные.sql: потребители, закрытые или не попавшие в расчёт
-- (нет строки PT_OUT выбранного расчёта). Шаблон G_PT, лист 7.
-- Десктоп брал последний расчёт каждого фрагмента; здесь расчёт задаётся явно ($2).
-- В сумме z обобщённых потребителей десктоп пропускал отопление по независимой схеме; добавлено.
-- $1: фрагмент, $2: расчёт
WITH c AS (
    SELECT nn.id, nn.fileid, rc.consumerstateid,
           ' ' AS prizn,
           nn.externalcodeid,
           nn.externalnodename AS uzel,
           rc.name AS name_building,
           rc.calchldep AS otoplz,
           rc.calchlindep AS otopln,
           rc.calchlventil + rc.avghlcond AS ventil,
           rc.avghlgvscloseparall + rc.avghlgvsclosemix + rc.avghlgvscloseconseq + rc.avghlgvsclosepreon AS gvz,
           rc.avghlgvsopenflow AS gvop,
           rc.avghlgvsopenret AS gvoo,
           rc.circhlosopen AS rez,
           rc.calchldep + rc.calchlindep + rc.calchlventil + rc.avghlcond
             + rc.avghlgvscloseparall + rc.avghlgvsclosemix + rc.avghlgvscloseconseq + rc.avghlgvsclosepreon AS z,
           rc.avghlgvsopenflow AS op,
           rc.avghlgvsopenret AS oo
      FROM realconsumers rc
      JOIN nodes nn ON nn.id = rc.nodeid
     WHERE nn.removed = 0
    UNION ALL
    SELECT nn.id, nn.fileid, gc.consumerstateid,
           'О' AS prizn,
           nn.externalcodeid,
           nn.externalnodename AS uzel,
           '' AS name_building,
           gc.calchldep
             + CASE WHEN gc.schemeparallid = 3 THEN 0 ELSE gc.calchlparall END
             + CASE WHEN gc.schememixid = 3 THEN 0 ELSE gc.calchlmix END
             + CASE WHEN gc.schemeconseqid = 3 THEN 0 ELSE gc.calchlconseq END
             + CASE WHEN gc.schemepreonid = 3 THEN 0 ELSE gc.calchlpreon END AS otoplz,
           gc.calchlindep
             + CASE WHEN gc.schemeparallid = 3 THEN gc.calchlparall ELSE 0 END
             + CASE WHEN gc.schememixid = 3 THEN gc.calchlmix ELSE 0 END
             + CASE WHEN gc.schemeconseqid = 3 THEN gc.calchlconseq ELSE 0 END
             + CASE WHEN gc.schemepreonid = 3 THEN gc.calchlpreon ELSE 0 END AS otopln,
           gc.calchlventil AS ventil,
           gc.calchlgvsparall + gc.calchlgvsmix + gc.calchlgvsconseq + gc.calchlgvspreon AS gvz,
           gc.avghlgvsopensysflow AS gvop,
           gc.avghlgvsopensysret AS gvoo,
           gc.avghlcompopen AS rez,
           gc.calchldep + gc.calchlindep + gc.calchlparall + gc.calchlmix + gc.calchlconseq + gc.calchlpreon
             + gc.calchlventil
             + gc.calchlgvsparall + gc.calchlgvsmix + gc.calchlgvsconseq + gc.calchlgvspreon AS z,
           gc.avghlgvsopensysflow AS op,
           gc.avghlgvsopensysret AS oo
      FROM generalizedconsumers gc
      JOIN nodes nn ON nn.id = gc.nodeid
     WHERE nn.removed = 0
)
SELECT c.id,
       CASE WHEN c.consumerstateid = 1 THEN ' ' ELSE 'закр' END AS stateid,
       c.prizn,
       ec.name AS kod,
       c.uzel,
       c.name_building,
       c.otoplz, c.otopln, c.ventil, c.gvz, c.gvop, c.gvoo, c.rez, c.z, c.op, c.oo,
       hs.name
  FROM c
  LEFT JOIN externalcodes ec ON ec.id = c.externalcodeid
  LEFT JOIN heatsources hs ON hs.id = ec.heatsourceid
 WHERE c.fileid = $1
   AND (c.consumerstateid = 2
        OR NOT EXISTS (SELECT 1 FROM pt_out p WHERE p.calculationid = $2 AND p.nodeid = c.id))
 ORDER BY c.prizn, ec.name, c.uzel, c.id

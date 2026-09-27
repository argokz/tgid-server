-- Подзапрос consumerview десктопа (gid6 dop/converter_old32/sql/Excel2019/consumerview.sql и его
-- копия внутри OUT_PT_Расчетные нагрузки.sql): реальные и обобщённые потребители в одном наборе.
-- Не отчёт: подставляется в отчёты через {{_consumerview}}. В ветке обобщённых десктоп дважды
-- вычитал calcInternHDdep вместо calcInternHDdep + calcInternHDindep; здесь исправлено.
SELECT n.id,
       n.fileid,
       cst.name AS cstatename,
       ' ' AS obob,
       ec.id AS kod_ist,
       ec.name AS externalcode,
       n.externalnodename,
       addr.name_building,
       COALESCE(rc.calchldep, 0) AS otoplz,
       COALESCE(rc.calchlindep, 0) AS otopln,
       COALESCE(rc.calchlventil, 0) AS ventil,
       COALESCE(rc.avghlcond, 0) AS kondiz,
       rc.avghlgvsopenflow,
       rc.avghlgvsopenret,
       (rc.contavghlgvsopenflow + rc.contavghlgvsopenret) * rc.circhlosopen / 100 AS rez_q,
       rc.avghlgvscloseparall,
       rc.avghlgvsclosemix,
       rc.avghlgvscloseconseq,
       rc.avghlgvsclosepreon,
       CASE WHEN cst.name = 'закрыто' THEN 0
            ELSE rc.calchldep + rc.calchlindep - rc.calcinternhd + rc.calchlventil + rc.avghlcond
                 + (rc.avghlgvsopenflow + rc.avghlgvsopenret) * (rc.circhlosopen / 100)
                 + rc.avghlgvscloseparall + rc.avghlgvsclosemix + rc.avghlgvscloseconseq + rc.avghlgvsclosepreon
       END AS qz,
       rc.volwaterhs,
       rc.volwatervs,
       org.name AS orgname
  FROM realconsumers rc
  JOIN nodes n ON n.id = rc.nodeid
  LEFT JOIN consumerstates cst ON cst.id = rc.consumerstateid
  LEFT JOIN organizations org ON org.id = n.organizationid
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN addresses addr ON addr.id = n.addressid
 WHERE n.removed = 0
UNION ALL
SELECT n.id,
       n.fileid,
       cst.name AS cstatename,
       'О' AS obob,
       ec.id AS kod_ist,
       ec.name AS externalcode,
       n.externalnodename,
       addr.name_building,
       COALESCE(gc.calchldep, 0)
         + CASE WHEN gc.schemeparallid = 1 THEN 0 ELSE COALESCE(gc.calchlparall, 0) END
         + CASE WHEN gc.schemeconseqid = 1 THEN 0 ELSE COALESCE(gc.calchlconseq, 0) END
         + CASE WHEN gc.schemepreonid = 1 THEN 0 ELSE COALESCE(gc.calchlpreon, 0) END
         + CASE WHEN gc.schememixid = 1 THEN 0 ELSE COALESCE(gc.calchlmix, 0) END AS otoplz,
       COALESCE(gc.calchlindep, 0)
         + CASE WHEN gc.schemeparallid = 1 THEN COALESCE(gc.calchlparall, 0) ELSE 0 END
         + CASE WHEN gc.schemeconseqid = 1 THEN COALESCE(gc.calchlconseq, 0) ELSE 0 END
         + CASE WHEN gc.schemepreonid = 1 THEN COALESCE(gc.calchlpreon, 0) ELSE 0 END
         + CASE WHEN gc.schememixid = 1 THEN COALESCE(gc.calchlmix, 0) ELSE 0 END AS otopln,
       COALESCE(gc.calchlventil, 0) AS ventil,
       COALESCE(gc.calchlcond, 0) AS kondiz,
       gc.avghlgvsopensysflow,
       gc.avghlgvsopensysret,
       (gc.avghlgvsopensysflow + gc.avghlgvsopensysret) * gc.avghlcompopen / 100 AS rez_q,
       gc.calchlgvsparall,
       gc.calchlgvsmix,
       gc.calchlgvsconseq,
       gc.calchlgvspreon,
       CASE WHEN cst.name = 'закрыто' THEN 0
            ELSE gc.calchldep + gc.calchlindep + gc.calchlparall + gc.calchlconseq + gc.calchlpreon + gc.calchlmix
                 - (gc.calcinternhddep + gc.calcinternhdindep + gc.internhdparall + gc.internhdconseq
                    + gc.internhdpreon + gc.internhdmix)
                 + gc.calchlventil + COALESCE(gc.calchlcond, 0)
                 + (gc.avghlgvsopensysflow + gc.avghlgvsopensysret) * (gc.avghlcompopen / 100)
                 + gc.calchlgvsparall + gc.calchlgvsmix + gc.calchlgvsconseq + gc.calchlgvspreon
       END AS qz,
       gc.volwaterhs,
       gc.volwatervs,
       org.name AS orgname
  FROM generalizedconsumers gc
  JOIN nodes n ON n.id = gc.nodeid
  LEFT JOIN consumerstates cst ON cst.id = gc.consumerstateid
  LEFT JOIN organizations org ON org.id = n.organizationid
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN addresses addr ON addr.id = n.addressid
 WHERE n.removed = 0

-- gid6 excel2/sql2/Потребители обобщенные.sql (шаблон gpo / G_PT, лист 2)
-- $1: фрагмент
SELECT n.id,
       CASE WHEN cst.name = 'открыто' THEN ' ' ELSE 'закр' END AS sost,
       'О' AS po_pr,
       ec.name AS kod,
       n.externalnodename AS uzel,
       '' AS name_building,
       n.geomarktoptube AS geodz,
       se.specexpendid AS kodur, ct.calctemperatureid AS kodtr,
       gc.maxbuildingheight AS h,
       gc.calchldep AS otoplz,
       gc.calchlindep AS otopln,
       gc.calcinternhddep + gc.calcinternhdindep + gc.internhdparall + gc.internhdmix
         + gc.internhdconseq + gc.internhdpreon AS otopl_tp,
       gc.calchlventil AS ventil,
       gc.calchlcond AS kondiz,
       gc.calchlparall + gc.calchlmix + gc.calchlconseq + gc.calchlpreon AS q1,
       gc.internhdparall + gc.internhdmix + gc.internhdconseq + gc.internhdpreon AS q2,
       gc.avghlgvsopensysflow AS gv_op,
       gc.avghlgvsopensysret AS gv_oo,
       gc.avghlcompopen AS rez,
       gc.calchlgvsparall AS gvpr,
       gc.calchlgvsmix AS gvsm,
       gc.calchlgvsconseq AS gvps,
       gc.calchlgvspreon AS gvpw,
       gc.setleakageflow AS utechp,
       gc.setleakageret AS utecho,
       vc.kodkv AS kodkv,
       hms.name AS pr_avar_tp,
       gc.hydroresclosesys AS gsz,
       cscs2.name AS gszpr,
       gc.hydroreswdoflow AS gsop,
       slcscs2.name AS prznp,
       gc.hydroreswdoret AS gsoo,
       slcscs3.name AS przno,
       hs.name
  FROM generalizedconsumers gc
  JOIN nodes n ON n.id = gc.nodeid
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN consumerstates cst ON cst.id = gc.consumerstateid
  LEFT JOIN closesyscalcsigns cscs2 ON cscs2.id = gc.closesyscalcsignid
  LEFT JOIN setloadclosesyscalcsigns slcscs2 ON slcscs2.id = gc.calcsignsetloadopensysflow
  LEFT JOIN setloadclosesyscalcsigns slcscs3 ON slcscs3.id = gc.calcsignsetloadopensysret
  LEFT JOIN varcoefficients vc ON vc.id = gc.varcoeffid
  LEFT JOIN calctemperatures ct ON ct.id = gc.calctemperatureid
  LEFT JOIN specexpends se ON se.id = gc.specexpendid
  LEFT JOIN hydromodesigns hms ON hms.id = gc.hydromodesignid
  LEFT JOIN externalcodes ecm ON ec.belongmagistral = ecm.id AND ec.objectid = 2
  LEFT JOIN heatsources hs ON hs.id = CASE WHEN ec.objectid <> 2 THEN ec.heatsourceid ELSE ecm.heatsourceid END
 WHERE n.fileid = $1 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id

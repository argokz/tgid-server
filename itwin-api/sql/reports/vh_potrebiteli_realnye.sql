-- gid6 excel2/sql2/Потребители реальные.sql (шаблон gpt, лист 1 / G_PT, лист 1)
-- $1: фрагмент
SELECT n.id,
       CASE WHEN cst.name = 'открыто' THEN ' ' ELSE 'закр' END AS sost,
       ' ' AS po_pr,
       ec.name AS kod, n.externalnodename AS uzel,
       rc.name AS name_building,
       n.geomarktoptube AS geodz,
       se.specexpendid AS kodur, ct.calctemperatureid AS kodtr,
       rc.buildheight AS h,
       rc.calchldep AS otoplz,
       rc.calchlindep AS otopln,
       rc.relloadfacade AS otn_fs,
       rc.calcinternhd AS otopl_tp,
       rc.calchlventil AS ventil,
       rc.avghlcond AS kondiz,
       rc.avghlgvsopenflow AS gvop,
       rc.avghlgvsopenret AS gvoo,
       rc.circhlosopen AS rez,
       rc.avghlgvscloseparall AS gvpr,
       rc.avghlgvsclosemix AS gvsm,
       rc.avghlgvscloseconseq AS gvps,
       rc.avghlgvsclosepreon AS gvpw,
       rc.setleakageflow AS utechp,
       rc.setleakageret AS utecho,
       vc.kodkv AS kodkv,
       hms.name AS pr_avar_tp,
       cscs2.name AS gszpr,
       rc.hydroresclosesys AS gsz,
       slcscs2.name AS prznp,
       rc.hydroreswdoflow AS gsop,
       slcscs3.name AS przno,
       rc.hydroreswdoret AS gsoo,
       hs.name,
       org.name AS kod_owner
  FROM realconsumers rc
  JOIN nodes n ON n.id = rc.nodeid
  LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
  LEFT JOIN consumerstates cst ON cst.id = rc.consumerstateid
  LEFT JOIN closesyscalcsigns cscs2 ON cscs2.id = rc.closesyscalcsignid
  LEFT JOIN setloadclosesyscalcsigns slcscs2 ON slcscs2.id = rc.calcsignsetloadopensysflow
  LEFT JOIN setloadclosesyscalcsigns slcscs3 ON slcscs3.id = rc.calcsignsetloadopensysret
  LEFT JOIN varcoefficients vc ON vc.id = rc.varcoeffid
  LEFT JOIN calctemperatures ct ON ct.id = rc.calctemperatureid
  LEFT JOIN specexpends se ON se.id = rc.specexpendid
  LEFT JOIN hydromodesigns hms ON hms.id = rc.hydromodesignid
  LEFT JOIN organizations org ON org.id = n.organizationid
  LEFT JOIN externalcodes ecm ON ec.belongmagistral = ecm.id AND ec.objectid = 2
  LEFT JOIN heatsources hs ON hs.id = CASE WHEN ec.objectid <> 2 THEN ec.heatsourceid ELSE ecm.heatsourceid END
 WHERE n.fileid = $1 AND n.removed = 0
 ORDER BY ec.name, n.externalnodename, n.id

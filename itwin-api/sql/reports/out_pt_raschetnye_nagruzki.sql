-- gid6 excel2/sql2/OUT_PT_Расчетные нагрузки.sql: расчётные нагрузки потребителей (шаблон G_PT, лист 3).
-- Расчёт не нужен: данные исходные.
-- $1: фрагмент
SELECT n.id,
       CASE WHEN n.cstatename = 'открыто' THEN ' ' ELSE 'закр' END AS sost,
       n.obob AS po_pr,
       n.externalcode, n.externalnodename, n.name_building,
       n.otoplz,
       n.otopln,
       0 AS otopl_tp,
       n.ventil,
       n.kondiz,
       n.avghlgvsopenflow AS gvop1,
       n.avghlgvsopenret AS gvoo1,
       n.rez_q,
       n.avghlgvscloseparall AS gvpr,
       n.avghlgvsclosemix AS gvsm,
       n.avghlgvscloseconseq AS gvps,
       n.avghlgvsclosepreon AS gvpw,
       n.qz,
       n.avghlgvsopenflow AS gvop,
       n.avghlgvsopenret AS gvoo,
       (n.otoplz + n.otopln) * n.volwaterhs AS v_otop,
       (n.ventil + n.kondiz) * n.volwatervs AS v_vent,
       n.orgname
  FROM ({{_consumerview}}) n
 WHERE n.fileid = $1
 ORDER BY n.obob, n.externalcode, n.externalnodename, n.id

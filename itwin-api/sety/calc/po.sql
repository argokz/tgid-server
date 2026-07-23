SELECT 
 n.id as nodes_id,

 usP.pih AS calc_pihP,
 usO.pih AS calc_pihO,

 usP.t AS calc_tP1,
 usO.t AS calc_tO1,

--  PT_OUT.a3 AS calc_a3,
  PT_OUT.a4 AS calc_a4,
  PT_OUT.a5 AS calc_a5,
  PT_OUT.a6 AS calc_a6,
  PT_OUT.a7 AS calc_a7,
  PT_OUT.a8 AS calc_a8,
  PT_OUT.a9 AS calc_a9,
  PT_OUT.a10 AS calc_a10,
  PT_OUT.a11 AS calc_a11,
  PT_OUT.a12 AS calc_a12,
  PT_OUT.a13 AS calc_a13,
  PT_OUT.a14 AS calc_a14,
  PT_OUT.a15 AS calc_a15,
  PT_OUT.a16 AS calc_a16,
  PT_OUT.a17 AS calc_a17,
  PT_OUT.a18 AS calc_a18,
  PT_OUT.a19 AS calc_a19,
  PT_OUT.a20 AS calc_a20,
  PT_OUT.a21 AS calc_a21,
  PT_OUT.a22 AS calc_a22,
  PT_OUT.a23 AS calc_a23,
  PT_OUT.Gsm AS calc_Gsm,
  PT_OUT.Gm AS calc_Gm,
  PT_OUT.Gx AS calc_Gx,
  PT_OUT.Ggws AS calc_Ggws,
  PT_OUT.t1 AS calc_t1,
  PT_OUT.t2 AS calc_t2,
  PT_OUT.t01 AS calc_t01,
  PT_OUT.t02 AS calc_t02,
  PT_OUT.t03 AS calc_t03,
  PT_OUT.t2co AS calc_t2co,
  PT_OUT.t2gws AS calc_t2gws,
  PT_OUT.tv AS calc_tv,
  PT_OUT.tg AS calc_tg,
  PT_OUT.dop8 AS calc_dop8,
  PT_OUT.dop9 AS calc_dop9,
  PT_OUT.Qotz AS calc_Qotz,
  PT_OUT.Qotn AS calc_Qotn,
  PT_OUT.dop12 AS calc_dop12,
  PT_OUT.dop13 AS calc_dop13,
  PT_OUT.dop14 AS calc_dop14,
  PT_OUT.dop15 AS calc_dop15,
  PT_OUT.dop16 AS calc_dop16,
  PT_OUT.dop17 AS calc_dop17,
  PT_OUT.dop18 AS calc_dop18,
  PT_OUT.dop19 AS calc_dop19,
  PT_OUT.dop20 AS calc_dop20,
  PT_OUT.Qsum_z AS calc_Qsum_z,
  PT_OUT.dop22 AS calc_dop22,
  PT_OUT.dop23 AS calc_dop23,
  PT_OUT.Gneob AS calc_Gneob,
  PT_OUT.Qras_gv_z AS calc_Qras_gv_z,
  PT_OUT.Qotz_treb AS calc_Qotz_treb,
  PT_OUT.Qotn_treb AS calc_Qotn_treb,
  PT_OUT.Qvent_treb AS calc_Qvent_treb,
  PT_OUT.Qgvz_treb AS calc_Qgvz_treb,
  PT_OUT.Qgvop_treb AS calc_Qgvop_treb,
  PT_OUT.Qgvoo_treb AS calc_Qgvoo_treb,
  PT_OUT.Qrez_treb AS calc_Qrez_treb,
  PT_OUT.Qtreb AS calc_Qtreb,
  PT_OUT.Qfact AS calc_Qfact,
  PT_OUT.Q_obesp_min AS calc_Q_obesp_min,
  PT_OUT.Q_obesp_otopl_min AS calc_Q_obesp_otopl_min,
  PT_OUT.Q_obesp_gvs_min AS calc_Q_obesp_gvs_min
--  PT_OUT.tzam AS calc_tzam







FROM nodes n
join generalizedconsumers po on n.id=po.nodeid and n.removed=0


LEFT JOIN 
(
SELECT 
c.fileID,
max(c.id) AS cid
FROM CALCULATION c
LEFT JOIN fragments fr ON fr.id=c.fileID
GROUP BY c.fileID
) calc ON calc.fileID=n.fileID

LEFT JOIN US_OUT usP ON usP.nodeID=n.id AND usP.externalSign=1 AND usP.calculationID=calc.cid
LEFT JOIN US_OUT usO ON usO.nodeID=n.id AND usO.externalSign=2 AND usO.calculationID=calc.cid
LEFT JOIN PT_OUT ON PT_OUT.nodeID=n.id AND PT_OUT.calculationID=calc.cid
LEFT JOIN DR_OUT ON DR_OUT.nodeID=n.id AND DR_OUT.calculationID=calc.cid


where n.removed=0
and n.fileID=$fileID$
and n.internalnodeid is null
order by n.id

SELECT 
 n.id::int as nodes_id,

 

 usP.pih::float AS calc_pihP,
 usO.pih::float AS calc_pihO,

 usP.t::float AS calc_tP1,
 usO.t::float AS calc_tO1,


--  PT_OUT.a3::float AS calc_a3,
  PT_OUT.a4::float AS calc_a4,
  PT_OUT.a5::float AS calc_a5,
  PT_OUT.a6::float AS calc_a6,
  PT_OUT.a7::float AS calc_a7,
  PT_OUT.a8::float AS calc_a8,
  PT_OUT.a9::float AS calc_a9,
  PT_OUT.a10::float AS calc_a10,
  PT_OUT.a11::float AS calc_a11,
  PT_OUT.a12::float AS calc_a12,
  PT_OUT.a13::float AS calc_a13,
  PT_OUT.a14::float AS calc_a14,
  PT_OUT.a15::float AS calc_a15,
  PT_OUT.a16::float AS calc_a16,
  PT_OUT.a17::float AS calc_a17,
  PT_OUT.a18::float AS calc_a18,
  PT_OUT.a19::float AS calc_a19,
  PT_OUT.a20::float AS calc_a20,
  PT_OUT.a21::float AS calc_a21,
  PT_OUT.a22::float AS calc_a22,
  PT_OUT.a23::float AS calc_a23,
  PT_OUT.Gsm::float AS calc_Gsm,
  PT_OUT.Gm::float AS calc_Gm,
  PT_OUT.Gx::float AS calc_Gx,
  PT_OUT.Ggws::float AS calc_Ggws,
  PT_OUT.t1::float AS calc_t1,
  PT_OUT.t2::float AS calc_t2,
  PT_OUT.t01::float AS calc_t01,
  PT_OUT.t02::float AS calc_t02,
  PT_OUT.t03::float AS calc_t03,
  PT_OUT.t2co::float AS calc_t2co,
  PT_OUT.t2gws::float AS calc_t2gws,
  PT_OUT.tv::float AS calc_tv,
  PT_OUT.tg::float AS calc_tg,
  PT_OUT.dop8::float AS calc_dop8,
  PT_OUT.dop9::float AS calc_dop9,
  PT_OUT.Qotz::float AS calc_Qotz,
  PT_OUT.Qotn::float AS calc_Qotn,
  PT_OUT.dop12::float AS calc_dop12,
  PT_OUT.dop13::float AS calc_dop13,
  PT_OUT.dop14::float AS calc_dop14,
  PT_OUT.dop15::float AS calc_dop15,
  PT_OUT.dop16::float AS calc_dop16,
  PT_OUT.dop17::float AS calc_dop17,
  PT_OUT.dop18::float AS calc_dop18,
  PT_OUT.dop19::float AS calc_dop19,
  PT_OUT.dop20::float AS calc_dop20,
  PT_OUT.Qsum_z::float AS calc_Qsum_z,
  PT_OUT.dop22::float AS calc_dop22,
  PT_OUT.dop23::float AS calc_dop23,
  PT_OUT.Gneob::float AS calc_Gneob,
  PT_OUT.Qras_gv_z::float AS calc_Qras_gv_z,
  PT_OUT.Qotz_treb::float AS calc_Qotz_treb,
  PT_OUT.Qotn_treb::float AS calc_Qotn_treb,
  PT_OUT.Qvent_treb::float AS calc_Qvent_treb,
  PT_OUT.Qgvz_treb::float AS calc_Qgvz_treb,
  PT_OUT.Qgvop_treb::float AS calc_Qgvop_treb,
  PT_OUT.Qgvoo_treb::float AS calc_Qgvoo_treb,
  PT_OUT.Qrez_treb::float AS calc_Qrez_treb,
  PT_OUT.Qtreb::float AS calc_Qtreb,
  PT_OUT.Qfact::float AS calc_Qfact,
  PT_OUT.Q_obesp_min::float AS calc_Q_obesp_min,
  PT_OUT.Q_obesp_otopl_min::float AS calc_Q_obesp_otopl_min,
  PT_OUT.Q_obesp_gvs_min::float AS calc_Q_obesp_gvs_min







FROM nodes n
join realconsumers pr on n.id=pr.nodeid and n.removed=0


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

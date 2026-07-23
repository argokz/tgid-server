SELECT 
 l.id as linesobj_id,

 utP.sos  AS calc_pod_sos,
 utP.a7  AS calc_pod_a7,
 utP.a8  AS calc_pod_a8,
 utP.a9  AS calc_pod_a9,
 utP.a10  AS calc_pod_a10,
 utP.a11  AS calc_pod_a11,
 utP.a12  AS calc_pod_a12,
 utP.a13  AS calc_pod_a13,
 utP.a14  AS calc_pod_a14,
 utP.a15  AS calc_pod_a15,
 utP.a16  AS calc_pod_a16,
 utP.a17  AS calc_pod_a17,
 utP.a18  AS calc_pod_a18,
 utP.a19  AS calc_pod_a19,
 utP.a20  AS calc_pod_a20,
 utP.a21  AS calc_pod_a21,
 utP.tpot  AS calc_pod_tpot,
 utP.t1  AS calc_pod_t1,
 utP.t2  AS calc_pod_t2,
 utP.qq  AS calc_pod_qq,
 utP.tzam  AS calc_pod_tzam,


 utO.sos  AS calc_obr_sos,
 utO.a7  AS calc_obr_a7,
 utO.a8  AS calc_obr_a8,
 utO.a9  AS calc_obr_a9,
 utO.a10  AS calc_obr_a10,
 utO.a11  AS calc_obr_a11,
 utO.a12  AS calc_obr_a12,
 utO.a13  AS calc_obr_a13,
 utO.a14  AS calc_obr_a14,
 utO.a15  AS calc_obr_a15,
 utO.a16  AS calc_obr_a16,
 utO.a17  AS calc_obr_a17,
 utO.a18  AS calc_obr_a18,
 utO.a19  AS calc_obr_a19,
 utO.a20  AS calc_obr_a20,
 utO.a21  AS calc_obr_a21,
 utO.tpot  AS calc_obr_tpot,
 utO.t1  AS calc_obr_t1,
 utO.t2  AS calc_obr_t2,
 utO.qq  AS calc_obr_qq,
 utO.tzam  AS calc_obr_tzam,

 utP.b101  AS calc_pod_b101,    --  Расчетная тепловая нагрузка, Гкал/ч               
 utP.b102  AS calc_pod_b102,    --  Расчетная тепловая нагрузка на отопление, Гкал/ч  
 utP.b103  AS calc_pod_b103,    --  Расчетная тепловая нагрузка на вентиляцию, Гкал/ч 
 utP.b104  AS calc_pod_b104,    --  Расчетная тепловая нагрузка на ГВС, Гкал/ч        

 utO.b101  AS calc_obr_b101,    --  Расчетная тепловая нагрузка, Гкал/ч               
 utO.b102  AS calc_obr_b102,    --  Расчетная тепловая нагрузка на отопление, Гкал/ч  
 utO.b103  AS calc_obr_b103,    --  Расчетная тепловая нагрузка на вентиляцию, Гкал/ч 
 utO.b104  AS calc_obr_b104    --  Расчетная тепловая нагрузка на ГВС, Гкал/ч        


FROM linesobj l
join heatpipesections hps on l.id=hps.lineid
join nodes n1 on n1.id=l.nodeid1 

left join generalizedconsumers gc1 on gc1.nodeid = n1.id
left join realconsumers rc1 on rc1.nodeid = n1.id
left join heatsources hs1 on hs1.nodeid = n1.id
left join pumpstations ps1 on ps1.nodeid = n1.id


join nodes n2 on n2.id=l.nodeid2
left join generalizedconsumers gc2 on gc2.nodeid = n2.id
left join realconsumers rc2 on rc2.nodeid = n2.id
left join heatsources hs2 on hs2.nodeid = n2.id
left join pumpstations ps2 on ps2.nodeid = n2.id





LEFT JOIN 
(
SELECT 
c.fileID,
max(c.id) AS cid
FROM CALCULATION c
LEFT JOIN fragments fr ON fr.id=c.fileID
GROUP BY c.fileID
) calc ON calc.fileID=n1.fileID

LEFT JOIN UT_OUT utP ON utP.lineID=l.id AND utP.calculationID=calc.cid and utP.externalSignLineID=2
LEFT JOIN UT_OUT utO ON utO.lineID=l.id AND utO.calculationID=calc.cid and utO.externalSignLineID=3

where l.removed=0
and n1.internalNodeid is null
and n2.internalNodeid is null
and n1.fileID=$fileID$
order by l.id

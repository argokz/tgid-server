SELECT 
 n.id::int as nodes_id,

 usP.pih::float AS calc_pihP,
 usO.pih::float AS calc_pihO,

 usP.t::float AS calc_tP1,
 usO.t::float AS calc_tO1



FROM nodes n
left join heatsources hs on hs.nodeid = n.id
left join realconsumers rc on rc.nodeid = n.id
left join generalizedconsumers gc on gc.nodeid = n.id
left join pumpstations pc on pc.nodeid = n.id

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



where hs.id is null and rc.id is null and gc.id is null and pc.id is null and n.removed=0
and n.fileID=$fileID$
and n.internalnodeid is null
order by n.id

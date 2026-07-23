SELECT 
 n.id as nodes_id,

 usP.pih AS calc_pihP,
 usO.pih AS calc_pihO,

 usP.t AS calc_tP1,
 usO.t AS calc_tO1


FROM nodes n
join pumpstations nst on n.id=nst.nodeid


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


where n.removed=0
and n.fileID=$fileID$
and n.internalnodeid is null
order by n.id

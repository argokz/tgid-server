CREATE OR REPLACE VIEW zd_view AS 

SELECT

    l.id,
    'dampers'::text AS name_object,
    'line'::text AS type_object,
    n1.fileid as "fileid",

l.displaySign,
l.organizationID,

dampers.damperArmatureStateID  AS pipeSectStateIDflow,
dampers.damperArmatureStateID  AS pipeSectStateIDret,

dampers.id AS id2,

ZD_OUT_P.id AS nomgP,
ZD_OUT_O.id AS nomgO,

ZD_OUT_P.a14 AS pod_q,
ZD_OUT_O.a14 AS obr_q,
       
l.shape

FROM linesobj l
JOIN nodes n1 ON n1.id=l.nodeID1
JOIN nodes n2 ON n2.id=l.nodeID2

JOIN dampers               ON dampers              .lineID=l.id

LEFT JOIN 
(
SELECT 
c.fileID,
max(c.id) AS cid
FROM CALCULATION c
LEFT JOIN fragments fr ON fr.id=c.fileID
GROUP BY c.fileID
) calc ON calc.fileID=n1.fileID

LEFT JOIN ZD_OUT   ZD_OUT_P     ON ZD_OUT_P .lineID=l.id AND ZD_OUT_P .externalSignLineID IN (2,4) AND ZD_OUT_P .calculationID=calc.cid
LEFT JOIN ZD_OUT   ZD_OUT_O     ON ZD_OUT_O .lineID=l.id AND ZD_OUT_O .externalSignLineID IN (3,5) AND ZD_OUT_O .calculationID=calc.cid

WHERE l.removed=0 AND n1.fileID=n2.fileID

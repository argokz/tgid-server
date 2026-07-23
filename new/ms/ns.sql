IF OBJECT_ID('dbo.ns_view', 'V') IS NOT NULL
    DROP VIEW dbo.ns_view;
GO

CREATE VIEW dbo.ns_view AS

SELECT

    l.id,
    'pumps' AS name_object,
    'line' AS type_object,
    n1.fileid as [fileid],

l.displaySign,
l.organizationID,

pumps.stateID  AS pipeSectStateIDflow,
pumps.stateID  AS pipeSectStateIDret,

pumps.id AS id2,

NS_OUT_P.id AS nomgP,
NS_OUT_O.id AS nomgO,

NS_OUT_P.ist AS istP,
NS_OUT_O.ist AS istO,


NS_OUT_P.a14 AS pod_q,
NS_OUT_O.a14 AS obr_q,
       
l.shape

FROM linesobj l
JOIN nodes n1 ON n1.id=l.nodeID1
JOIN nodes n2 ON n2.id=l.nodeID2

JOIN pumps               ON pumps              .lineID=l.id

LEFT JOIN 
(
SELECT 
c.fileID,
max(c.id) AS cid
FROM CALCULATION c
LEFT JOIN fragments fr ON fr.id=c.fileID
GROUP BY c.fileID
) calc ON calc.fileID=n1.fileID

LEFT JOIN NS_OUT   NS_OUT_P     ON NS_OUT_P .lineID=l.id AND NS_OUT_P .externalSignLineID IN (2,4) AND NS_OUT_P .calculationID=calc.cid
LEFT JOIN NS_OUT   NS_OUT_O     ON NS_OUT_O .lineID=l.id AND NS_OUT_O .externalSignLineID IN (3,5) AND NS_OUT_O .calculationID=calc.cid

WHERE l.removed=0 AND n1.fileID=n2.fileID

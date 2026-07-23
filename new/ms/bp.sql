IF OBJECT_ID('dbo.bp_view', 'V') IS NOT NULL
    DROP VIEW dbo.bp_view;
GO

CREATE VIEW dbo.bp_view AS
SELECT
    l.id,
    'bypass' AS name_object,
    'line' AS type_object,
    n1.fileid AS [fileid],

    l.displaySign,
    l.organizationID,

    bypass.regulatorStateID AS pipeSectStateIDflow,
    bypass.regulatorStateID AS pipeSectStateIDret,

    bypass.id AS id2,

    RS_OUT_P.id AS nomgP,
    RS_OUT_O.id AS nomgO,

    RS_OUT_P.a14 AS pod_q,
    RS_OUT_O.a14 AS obr_q,

    l.shape
FROM linesobj l
JOIN nodes n1 ON n1.id = l.nodeID1
JOIN nodes n2 ON n2.id = l.nodeID2

JOIN bypass ON bypass.lineID = l.id

LEFT JOIN (
    SELECT 
        c.fileID,
        MAX(c.id) AS cid
    FROM CALCULATION c
    LEFT JOIN fragments fr ON fr.id = c.fileID
    GROUP BY c.fileID
) AS calc ON calc.fileID = n1.fileID

LEFT JOIN RS_OUT RS_OUT_P ON RS_OUT_P.lineID = l.id AND RS_OUT_P.externalSignLineID IN (2, 4) AND RS_OUT_P.calculationID = calc.cid
LEFT JOIN RS_OUT RS_OUT_O ON RS_OUT_O.lineID = l.id AND RS_OUT_O.externalSignLineID IN (3, 5) AND RS_OUT_O.calculationID = calc.cid

WHERE l.removed = 0 AND n1.fileID = n2.fileID;

IF OBJECT_ID('dbo.us_view', 'V') IS NOT NULL
    DROP VIEW dbo.us_view;
GO

CREATE VIEW dbo.us_view AS
SELECT 
    t.id,
    'nodes' AS name_object,
    'node' AS type_object,
    t.fileid AS [fileid],
    t0.name AS [externalCodeID],
    t.externalnodename AS [externalNodeName],
    t.nodetypeid AS [nodeTypeID],
    t.organizationid AS [organizationID],
    t.operatorid AS [operatorID],

    t.geoMarkTopTube AS [geoMarkTopTube],
    t.geoMarkNodeArea AS [geoMarkNodeArea],

    usP.ist AS [istP],
    usO.ist AS [istO],

    usP.pih AS [pihP],
    usO.pih AS [pihO],
    usP.t AS [tP],
    usO.t AS [tO],
    t.shape
FROM nodes t
LEFT JOIN externalcodes t0 ON t0.id = t.externalcodeid
LEFT JOIN organizations t6 ON t6.id = t.organizationid
LEFT JOIN passwords t12 ON t12.id = t.operatorid
LEFT JOIN realconsumers rc ON rc.nodeid = t.id
LEFT JOIN generalizedconsumers gc ON gc.nodeid = t.id
LEFT JOIN heatsources ist ON ist.nodeid = t.id
LEFT JOIN pumpstations hs ON hs.nodeid = t.id
LEFT JOIN threewayvalves c3 ON c3.nodeid = t.id
LEFT JOIN connectnodes us2 ON us2.nodeid = t.id
LEFT JOIN (
    SELECT 
        c.fileid,
        MAX(c.id) AS cid
    FROM calculation c
    LEFT JOIN fragments fr ON fr.id = c.fileid
    GROUP BY c.fileid
) AS calc ON calc.fileid = t.fileid
LEFT JOIN US_OUT usP ON usP.calculationid = calc.cid AND usP.nodeid = t.id AND usP.externalSign = 1
LEFT JOIN US_OUT usO ON usO.calculationid = calc.cid AND usO.nodeid = t.id AND usO.externalSign = 2
WHERE 
    t.removed = 0 AND
    rc.id IS NULL AND
    ist.id IS NULL AND
    hs.id IS NULL AND
    c3.id IS NULL AND
    us2.id IS NULL AND
    t.internalnodeid IS NULL;

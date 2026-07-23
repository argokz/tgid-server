IF OBJECT_ID('dbo.ut_view', 'V') IS NOT NULL
    DROP VIEW dbo.ut_view;
GO

CREATE VIEW dbo.ut_view AS
SELECT 
    l.id,
    'heatPipeSections' AS name_object,
    'line' AS type_object,
    n1.fileid AS [fileid],

    l.externalsignlineid,
    l.displaysign,
    l.organizationid,
    hps.magistral,
    hps.distsite AS rs,
    hps.magistralsite AS ms,
    hps.tubingtypeid,
    hps.diameterinternal,
    hps.diameterexternal,
    hps.diametercondit,
    hps.pipesectlength,
    hps.wallthickness,
    hps.pipesectstateidflow,
    hps.pipesectstateidret,
    hps.id AS hps_id,
    utp.id AS nomgp,
    uto.id AS nomgo,

--    utp.ist AS istP,
--    uto.ist AS istO,

    utp.b101 AS pod_b101,
    utp.b102 AS pod_b102,
    utp.b103 AS pod_b103,
    utp.b104 AS pod_b104,
    uto.b101 AS obr_b101,
    uto.b102 AS obr_b102,
    uto.b103 AS obr_b103,
    uto.b104 AS obr_b104,
    utp.a13 AS pod_q,
    uto.a13 AS obr_q,
    utp.a9 AS pod_v,
    uto.a9 AS obr_v,
    utp.a10 AS pod_w,

    l.shape
FROM linesobj l
JOIN nodes n1 ON n1.id = l.nodeid1
JOIN nodes n2 ON n2.id = l.nodeid2
LEFT JOIN heatpipesections hps ON hps.lineid = l.id
LEFT JOIN (
    SELECT 
        c.fileid,
        MAX(c.id) AS cid
    FROM calculation c
    LEFT JOIN fragments fr ON fr.id = c.fileid
    GROUP BY c.fileid
) AS calc ON calc.fileid = n1.fileid
LEFT JOIN ut_out utp ON utp.lineid = l.id AND utp.externalsignlineid IN (2, 4) AND utp.calculationid = calc.cid
LEFT JOIN ut_out uto ON uto.lineid = l.id AND uto.externalsignlineid IN (3, 5) AND uto.calculationid = calc.cid
WHERE l.removed = 0 AND n1.fileid = n2.fileid;

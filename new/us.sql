CREATE OR REPLACE VIEW us_view AS 

SELECT 

--usP.externalSign,
--usO.externalSign,

t.id,
    'nodes'::text AS name_object,
    'node'::text AS type_object,
    t.fileid as "fileid",
    t0.name AS "externalCodeID",
    t.externalnodename AS "externalNodeName",
    t.nodetypeid AS "nodeTypeID",
    t.organizationid AS "organizationID",
    t.operatorid AS "operatorID",

    t.geoMarkTopTube AS "geoMarkTopTube",     -- Геодезическая отметка оси трубы, м        
    t.geoMarkNodeArea AS "geoMarkNodeArea",   -- Геодезическая отметка поверхности земли, м
    
    usP.ist AS "istP",                        -- Источник на подаче
    usO.ist AS "istO",                        -- Источник на обратке

    usP.pih as "pihP",                        -- Пьез.напор на подаче, м.вод.ст
    usO.pih as "pihO",                        -- Пьез.напор на обратке, м.вод.ст
    usP.t as "tP",                            -- Темп. на подаче
    usO.t as "tO",                            -- Темп. на обратке
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
            max(c.id) AS cid
        FROM calculation c
        LEFT JOIN fragments fr ON fr.id = c.fileid
        GROUP BY c.fileid) calc ON calc.fileid = t.fileid
        
     left join US_OUT usP on usP.calculationid=calc.cid and usP.nodeid=t.id and usP.externalSign=1
     left join US_OUT usO on usO.calculationid=calc.cid and usO.nodeid=t.id and usO.externalSign=2


  WHERE t.removed = 0 AND rc.id IS NULL AND ist.id IS NULL AND hs.id IS NULL AND c3.id IS NULL AND us2.id IS NULL AND t.internalnodeid IS NULL;

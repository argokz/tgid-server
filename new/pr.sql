CREATE OR REPLACE VIEW pr_view AS 

SELECT t.id AS object_id,
    n.id,
    'realConsumers'::text AS name_object,
    'node'::text AS type_object,
    n.fileid as "fileid",
    n0.name AS "externalCodeID",
    n.externalnodename AS "externalNodeName",

    n.geoMarkTopTube AS "geoMarkTopTube",     -- Геодезическая отметка оси трубы, м        
    n.geoMarkNodeArea AS "geoMarkNodeArea",   -- Геодезическая отметка поверхности земли, м
    
    usP.ist AS "istP",                        -- Источник на подаче
    usO.ist AS "istO",                        -- Источник на обратке

    usP.pih as "pihP",                        -- Пьез.напор на подаче, м.вод.ст
    usO.pih as "pihO",                        -- Пьез.напор на обратке, м.вод.ст
    usP.t as "tP",                            -- Темп. на подаче
    usO.t as "tO",                            -- Темп. на обратке

    PT_OUT.a15 AS "qz",
    PT_OUT.a16 AS "qP",
    PT_OUT.a17 AS "qO",

    t.name,

    n.shape
   FROM realconsumers t
     LEFT JOIN nodes n ON n.id = t.nodeid
     LEFT JOIN externalcodes n0 ON n0.id = n.externalcodeid
     LEFT JOIN organizations n6 ON n6.id = n.organizationid
     LEFT JOIN passwords n12 ON n12.id = n.operatorid
     LEFT JOIN fragments n13 ON n13.id = n.fileid
     LEFT JOIN specexpends t20 ON t20.id = t.specexpendid
     LEFT JOIN calctemperatures t21 ON t21.id = t.calctemperatureid
     LEFT JOIN varcoefficients t22 ON t22.id = t.varcoeffid
     LEFT JOIN heatsources t29 ON t29.id = t.heatsourceptsid
     LEFT JOIN heatpoint t30 ON t30.id = t.heatpointid
     LEFT JOIN streets t110 ON t110.id = t.streetid
     LEFT JOIN ( SELECT responsibles.id,
            responsibles.name,
            responsibles.statusid
           FROM responsibles
          WHERE responsibles.statusid = 15) t119 ON t119.id = t.responsibleid

     LEFT JOIN ( 
        SELECT 
            c.fileid,
            max(c.id) AS cid
        FROM calculation c
        LEFT JOIN fragments fr ON fr.id = c.fileid
        GROUP BY c.fileid) calc ON calc.fileid = n.fileid
        
     left join US_OUT usP on usP.calculationid=calc.cid and usP.nodeid=n.id and usP.externalSign=1
     left join US_OUT usO on usO.calculationid=calc.cid and usO.nodeid=n.id and usO.externalSign=2
     left join PT_OUT on PT_OUT.calculationid=calc.cid and PT_OUT.nodeid=n.id

  WHERE n.removed = 0 AND n.internalnodeid IS NULL;
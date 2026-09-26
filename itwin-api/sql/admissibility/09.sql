SELECT * From (SELECT 
    n.id, 
   
    n.externalNodeName, 
    
    usP.t AS "t сет. воды, подача,°C",
    usO.t AS "t сет. воды, обратка,°C",
    tg.t2 as "t сет. воды, обратка,°C (темп. график)",
    ist2.name,

        (
        CASE WHEN ROUND(usO.t) <  tg.t2 - 0.5 
         THEN 'В обратном трубопроводе температура сетевой воды ниже температурного графика; ' 
         ELSE '' END ||
    CASE WHEN ROUND(usO.t) > tg.t2 + 0.5
         THEN 'В обратном трубопроводе температура сетевой воды выше температурного графика ' 
         ELSE '' END
) AS "Анализ режима"


FROM nodes n

LEFT JOIN realConsumers rc ON rc.nodeID = n.id
LEFT JOIN generalizedConsumers gc ON gc.nodeID = n.id
LEFT JOIN heatSources ist ON ist.nodeID = n.id
LEFT JOIN pumpStations hs ON hs.nodeID = n.id
LEFT JOIN threeWayValves c3 ON c3.nodeID = n.id
LEFT JOIN connectNodes us2 ON us2.nodeID = n.id

LEFT JOIN (
    SELECT 
        c.fileID,
        MAX(c.id) AS cid
    FROM CALCULATION c
    LEFT JOIN fragments fr ON fr.id = c.fileID
    GROUP BY c.fileID
) calc ON calc.fileID = n.fileID

LEFT JOIN US_OUT usP ON usP.nodeID = n.id AND usP.externalSign = 1 AND usP.calculationID = calc.cid
LEFT JOIN US_OUT usO ON usO.nodeID = n.id AND usO.externalSign = 2 AND usO.calculationID = calc.cid
LEFT JOIN PT_OUT ptOut ON ptOut.nodeID = n.id AND ptOut.calculationID = calc.cid
LEFT JOIN DR_OUT ON DR_OUT.nodeID = n.id AND DR_OUT.calculationID = calc.cid
LEFT JOIN CALCULATION calc2 ON calc2.id = calc.cid
LEFT JOIN deployedtempgraphs tg ON  tg.hsourceid = usP.ist and tg.tn= calc2.tn
LEFT JOIN heatSources ist2 ON ist2.id = usP.ist

WHERE 
    n.removed = 0
    and n.fileID = $1
    AND gc.id IS NOT NULL
    AND n.externalSignID = 1
    AND n.internalNodeID IS NULL

    AND (
        
            usP.t IS NOT NULL AND usO.t IS NOT NULL AND
            (ROUND(usO.t) <  tg.t2 - 0.5  
        OR ROUND(usO.t) > tg.t2 + 0.5
            )
        
    )
) src

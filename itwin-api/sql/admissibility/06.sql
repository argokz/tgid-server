SELECT * From (SELECT 
    n.id, 
    
    n.externalNodeName, 
  

    rc.calctemphr as "t в помещ., °C (расч.)",
    ptOut.tv as "t в помещ., °C (факт.)",

    rc.calcTempVS as "t нагрет. возд. в сист.вент., °C (исх.)",
    ptOut.dop8 as "t нагрет. возд. в сист.вент.,°C(расч.)",
    usP.t AS "t сет. воды, подача,°C",
    usO.t AS "t сет. воды, обратка,°C",
    tg.t2 as "t сет. воды, обратка,°C (темп. график)",
    ist2.name,

    (
    CASE WHEN ptOut.tv < rc.calctemphr - 0.5 
         THEN 'Факт. температура в помещениях ниже расчетной; ' 
         ELSE '' END ||
    CASE WHEN ptOut.tv > 1.05 * rc.calctemphr 
         THEN 'Факт. температура в помещениях выше допустимой (больше 5% от расчетной); ' 
         ELSE '' END ||

    CASE WHEN (ptOut.dop8 != null AND ptOut.dop8 != 0 AND ptOut.dop8 < 0.9 * rc.calcTempVS) 
         THEN 'Расч. температура нагрет. возд. в сист.вент. ниже допустимой (более 10% от исходной); ' 
         ELSE '' END ||
    CASE WHEN (ptOut.dop8 != null AND ptOut.dop8 != 0 AND ptOut.dop8 > 1.1 * rc.calcTempVS)
         THEN 'Расч. температура нагрет. возд. в сист.вент. выше допустимой (более 10% от исходной); ' 
         ELSE '' END ||

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
    SELECT c.fileID, MAX(c.id) AS cid FROM CALCULATION c LEFT JOIN fragments fr ON fr.id = c.fileID GROUP BY c.fileID
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
    AND rc.id IS NOT NULL
    AND n.externalSignID = 1
    AND n.internalNodeID IS NULL
   

    AND (
        ptOut.tv < rc.calctemphr - 0.5
        OR ptOut.tv > 1.05 * rc.calctemphr
        OR (ptOut.dop8 != null AND ptOut.dop8 != 0 and ptOut.dop8 < 0.9 * rc.calcTempVS)
        OR (ptOut.dop8 != null AND ptOut.dop8 != 0 and ptOut.dop8 > 1.1 * rc.calcTempVS)
        OR ROUND(usO.t) <  tg.t2 - 0.5  
        OR ROUND(usO.t) > tg.t2 + 0.5
        
    )
) src

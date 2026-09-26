SELECT * From (SELECT 
    n.id, 

    n.externalNodeName, 
    

    usP.pih as "Получ. напор на подаче, м",
    usO.pih AS "Получ. напор на обратке, м",

    -- Qo = сумма трёх компонентов
    (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) AS "Расч. тепл. нагрузка, Гкал/ч",
    -- Hнро = разность давлений
    (usP.pih - usO.pih) AS "Полученный расп. напор, м",

    -- Причина нарушения
    CASE
        WHEN (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) <= 10 AND 
             (usP.pih - usO.pih NOT BETWEEN 20 AND 25) THEN 'При Qo≤10, диапазон [20–25]'
        WHEN (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) > 10 AND 
             (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) <= 20 AND 
             (usP.pih - usO.pih NOT BETWEEN 30 AND 35) THEN 'При 10<Qo≤20, диапазон [30–35]'
        WHEN (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) > 20 AND 
             (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) <= 30 AND 
             (usP.pih - usO.pih NOT BETWEEN 40 AND 45) THEN 'При 20<Qo≤30, диапазон [40–45]'
        WHEN (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) > 30 AND 
             (usP.pih - usO.pih NOT BETWEEN 45 AND 50) THEN 'При Qo>30, диапазон [45–50]'
        ELSE 'Допустимо'
    END AS "Необх. распол. напор, м"

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

WHERE 
    n.removed = 0
    and n.fileID = $1
    AND gc.id IS NOT NULL
    AND n.externalSignID = 1
    AND n.internalNodeID IS NULL
    -- Только недопустимые по Hнро в зависимости от Qo
    AND (
        ((ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) <= 10 AND (usP.pih - usO.pih NOT BETWEEN 20 AND 25)) OR
        ((ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) > 10 AND (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) <= 20 AND (usP.pih - usO.pih NOT BETWEEN 30 AND 35)) OR
        ((ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) > 20 AND (ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) <= 30 AND (usP.pih - usO.pih NOT BETWEEN 40 AND 45)) OR
        ((ptOut.qsum_z + ptOut.dop22 + ptOut.dop23) > 30 AND (usP.pih - usO.pih NOT BETWEEN 45 AND 50))
    )
) src

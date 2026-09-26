SELECT * From (SELECT 
    n.id,
    n.externalNodeName, 

    usP.pih AS "Получ. напор на подаче, м.вд.ст.",
    usO.pih AS "Получ. напор на обратке, м.вд.ст.",

    PT_OUT.Gneob AS "Необходимый расп. напор, м.вд.ст.",                                     -- необходимый напор
    (usP.pih - usO.pih) AS "Полученный расп. напор, м.вд.ст.",                              -- полученный напор

    CASE
        WHEN (usP.pih - usO.pih) >= PT_OUT.Gneob AND (usP.pih - usO.pih) >= 0 THEN 'Режим допустим'
        when (usP.pih is null
			and usO.pih is null) THEN 'Потребитель не подключен'
		when (usP.pih < usO.pih) THEN 'Отрицательные перепады'
        ELSE 'Ниже допустимого'
    END AS Режим

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
LEFT JOIN PT_OUT ON PT_OUT.nodeID = n.id AND PT_OUT.calculationID = calc.cid
LEFT JOIN DR_OUT ON DR_OUT.nodeID = n.id AND DR_OUT.calculationID = calc.cid

WHERE n.removed = 0
AND NOT rc.id IS NULL
and n.fileID = $1
AND n.externalSignID = 1
AND n.internalNodeID IS NULL

-- Условия недопустимости:
AND (
    (usP.pih - usO.pih) < PT_OUT.Gneob OR 
    (usP.pih - usO.pih) < 0 OR 
    (usP.pih is null
			and usO.pih is null)
)
) src

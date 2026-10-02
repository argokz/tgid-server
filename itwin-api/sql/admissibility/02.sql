select
	*
from
	(
	select
		n.id,
		n.externalNodeName,
		usP.pih as "Верхний доп. пьез.напор, м.вод.ст.",
		5 as "Нижний доп. пьез.напор, м.вод.ст.",
		usO.pih as "Полученный напор, м.вод.ст.",
		case
			when usO.pih <= usP.pih
			and usO.pih >= 5
        then 'Режим допустим'
			when usO.pih > usP.pih
        then 'Превышает допустимый'
			when usO.pih < 5
        then 'Ниже допустимого'
			when n.id in (
			select
				internalnodeid
			from
				nodes n
			where
				n.removed = 0
				and n.internalnodeid is not null
    )
        then 'Узел с внутренней схемой'
			when usP.pih is null
			and usO.pih is null
    	 then 'Узел не подключен'
			when usP.pih is null
			and usO.pih is not null
    	then 'Только обратка'
			else 'Нет данных'
		end as Режим
	from
		nodes n
	left join realConsumers rc on
		rc.nodeID = n.id
	left join generalizedConsumers gc on
		gc.nodeID = n.id
	left join heatSources ist on
		ist.nodeID = n.id
	left join pumpStations hs on
		hs.nodeID = n.id
	left join threeWayValves c3 on
		c3.nodeID = n.id
	left join connectNodes us2 on
		us2.nodeID = n.id
	left join (
		select
			c.fileID,
			MAX(c.id) FILTER (WHERE $2::int IS NULL OR c.id = $2::int) as cid
		from
			CALCULATION c
		left join fragments fr on
			fr.id = c.fileID
		group by
			c.fileID
) calc on
		calc.fileID = n.fileID
	left join US_OUT usP on
		usP.nodeID = n.id
		and usP.externalSign = 1
		and usP.calculationID = calc.cid
	left join US_OUT usO on
		usO.nodeID = n.id
		and usO.externalSign = 2
		and usO.calculationID = calc.cid
	left join PT_OUT on
		PT_OUT.nodeID = n.id
		and PT_OUT.calculationID = calc.cid
	left join DR_OUT on
		DR_OUT.nodeID = n.id
		and DR_OUT.calculationID = calc.cid
	where
		n.removed = 0
		and n.fileID = $1
		and n.internalNodeID is null
		and (n.externalSignID = 1
			or n.externalSignID = 3)
		and rc.id is null
		and gc.id is null
		and ist.id is null
		and hs.id is null
		and c3.id is null
		and us2.id is null
		-- Условия по напору
		and (usO.pih is null
			or usP.pih is null
			or usO.pih > usP.pih
			or usO.pih < 5)
		and not (usP.pih is not null
			and usO.pih is null)) src

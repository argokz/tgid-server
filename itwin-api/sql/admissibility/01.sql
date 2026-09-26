select
	*
from
	(
	select
		n.id,
		n.externalNodeName,
		150 as "Верхний доп. пьез.напор, м.вод.ст.",
		greatest(0, ROUND(0.535 * usP.t::numeric - 49.2, 2)) as "Нижний доп. пьез.напор, м.вод.ст.",
		usP.pih "Полученный напор, м.вод.ст.",
		usP.t as "Температура сет. воды, Град.C",
		case
			when usP.pih <= 150
			and usP.pih >= greatest(0, ROUND(0.535 * usP.t::numeric - 49.2, 2))
        then 'Режим допустим'
			when usP.pih > 150
        then 'Превышает допустимый'
			when usP.pih < greatest(0, ROUND(0.535 * usP.t::numeric - 49.2, 2))
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
			MAX(c.id) as cid
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
			or n.externalSignID = 2)
		and rc.id is null
		and gc.id is null
		and ist.id is null
		and hs.id is null
		and c3.id is null
		and us2.id is null
		and (usP.t is null
			or usP.pih is null
			or usP.pih > 150
			or usP.pih < greatest(0, ROUND(0.535 * usP.t::numeric - 49.2, 2)))
		and not (usP.pih is null
			and usO.pih is not null)
    ) src

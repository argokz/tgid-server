select
	id,
	externalNodeName,
	pihO as "Получ. напор на подаче, м.вд.ст.",
	pihP as "Получ. напор на обратке, м.вд.ст.",
	Hpr as "Полученный расп. напор, м.вд.ст.",
	Hpr_min as "Нижний доп. пьез.напор, м.вод.ст.",
	Hpr_max as "Верхний доп. пьез.напор, м.вод.ст.",
	тип_схемы "Тип Схемы",
	"Режим напора потребителя"
from
	(with consumers as (
	select
		n.id,
		n.externalNodeName,
		usP.pih as pihP,
		usO.pih as pihO,
		usP.t as tP1,
		usO.t as tO1,
		rc.schemeNum,
		rc.buildHeight,
		-- Тип схемы
        case
			when rc.schemeNum in ('1.5', '1.6') then 'Независимая'
			when rc.schemeNum in ('1.3', '1.4')
			or split_part(rc.schemeNum, '.', 2)::INT in (1, 2, 3, 4, 5, 6, 7, 8) then 'Зависимая'
			when split_part(rc.schemeNum, '.', 2)::INT in (9, 10, 11, 12) then 'Независимая'
			else 'Неопределенно'
		end as тип_схемы,
		PT_OUT.Gneob as Hnr,
		(usP.pih - usO.pih) as Hpr,
		(rc.buildHeight + 5) as Hpr_min,
		case
			when rc.schemeNum in ('1.5', '1.6') then 100
			when rc.schemeNum in ('1.3', '1.4')
			or split_part(rc.schemeNum, '.', 2)::INT in (1, 2, 3, 4, 5, 6, 7, 8) then 60
			when split_part(rc.schemeNum, '.', 2)::INT in (9, 10, 11, 12) then 100
			else null
		end as Hpr_max
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
		and not rc.id is null
		and n.externalSignID = 1
		and n.internalNodeID is null
)
	select
		*,
		case
			when Hpr between Hpr_min and Hpr_max then 'допустимо'
			when Hpr > Hpr_max then 'Выше допустимого предела'
			when Hpr < Hpr_min then 'Ниже допустимого предела'
			when (pihP is null and pihO is null) then 'Потребитель не подключен'
			when (pihP is null or pihO is null) then 'Недостаточно данных'
			when (pihP < pihO) then 'Отрицательные перепады'
			else 'недопустимо'
		end as "Режим напора потребителя"
	from
		consumers
	where
		(Hpr < Hpr_min
			or Hpr > Hpr_max)
		or pihO is null
		or pihP is null)

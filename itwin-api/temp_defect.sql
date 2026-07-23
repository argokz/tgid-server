select  top 2147483647
    t.obj_id as id,

    CONCAT ( t.vysotaPovrezhdenia,', мм | ', t.shirinaPovrezhdenia,', мм | ',t.ploshchadPovrezhdenia, ', мм') as 'Размер повреждения',

    predsedatel,
    dolzhnost_predsedatelya,
    chlen_tn_1,
    dolzhnost_tn_1,
    chlen_tn_2,
    dolzhnost_tn_2,
    chlen_tn_3,
    dolzhnost_tn_3,

	CASE WHEN n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ' THEN n1.externalNodeName ELSE  n1.nodeName END as 'Наименование начального узла',
	ec1.name as 'Код расчетной схемы начального узла',
	CASE WHEN n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ' THEN n2.externalNodeName ELSE  n2.nodeName END as 'Наименование конечного узла',
	ec2.name as 'Код расчетной схемы конечного узла',
	es.name as 'Признак участка трубопровода',
	hpss.firstPICdateHP as 'Дата первичного ввода в эксплуатацию',
	hpss.lastTransDate as 'Дата последней перекладки',
	--hpss.netType as 'Вид сети',
	magistrali.naimenovanie_magistrali as 'Магистраль',
	CASE WHEN pss.magistralSite is not NULL THEN  re_ms.naimenovanie_rayona_ekspluatatsii_istochnika_tepla ELSE  re_rs.naimenovanie_rayona_ekspluatatsii_istochnika_tepla END as 'Район эксплуатации',
	CASE WHEN pss.magistralSite is not NULL THEN  ue_ms.nomer_uchastka ELSE  ue_rs.nomer_uchastka END as 'Участок эксплуатации',
	CASE WHEN pss.magistralSite is not NULL THEN  ist_ms.naimenovanie ELSE  ist_rs.naimenovanie END as 'Источник теплоснабжения',
	CASE WHEN ms.opisanie_uchastka_ms is not NULL THEN  ms.opisanie_uchastka_ms ELSE  rs.naimenovanie_uchastka_rs END as 'Наименование участка',
	CASE WHEN pss.magistralSite is not NULL THEN  'магистраль' ELSE  'распредсеть' END as 'Признак сети',
	t.organization as 'Владелец участка теплопровода',
	CASE WHEN nu_ms.fio is not NULL THEN  nu_ms.fio ELSE  nu_rs.fio END as 'Начальник участка',
	tubingTypes.name as 'Тип прокладки',
	hpss.diameterExternal as 'Диаметр наружный, мм',
	hpss.wallThickness AS 'Толщина стенки, мм',
	hpss.pipeSectLength AS 'Длина участка теплопровода, м',
	im.name as 'Материал тепловой изоляции',
	isolationTypes.name as 'Тип изоляции ППУ',
	externalMaterials.name as 'Материал наружного покрытия',
	anticorrMaterials.name as 'Материал антикоррозийного покрытия',
    deft.name as 'Режим',
---    FORMAT(t.data_osmotra,'yyyy-MM-dd' ) as 'Дата обнаружения нарушения',
    FORMAT(t.data_osmotra,'dd.MM.yyyy' ) as 'Дата обнаружения нарушения',
    t.vremya_osmotra as 'Время обнаружения повреждения',
    CONCAT(st.name, '', t.nomer_doma) as 'Адрес',
    es.name as 'Поврежденный трубопровод',
    t.rasstoyanieDoPovrezhdeniyaNachKamery as 'Расстояние до нарушения от ближайшей камеры, м',
	CASE WHEN node_bizhajshej_kamery.nodeName is NULL or node_bizhajshej_kamery.nodeName = '' or node_bizhajshej_kamery.nodeName = ' ' THEN node_bizhajshej_kamery.externalNodeName ELSE  node_bizhajshej_kamery.nodeName END as 'Наименование ближайшей камеры',
    tp.name as 'Поверхность в месте раскопки',
    t.defectDescription as 'Описание повреждения',
    op.name as 'Наименование контура опрессовки',
	t.nomer_akta as 'Номер акта',
	t.data_sostavleniya_akta as 'Дата составления акта',
	t.nomer_prikaza as 'Номер приказа',
	t.data_prikaza_vvoda_v_ekspluataciyu as 'Дата приказа ввода в эксплуатацию',
    vn.code as 'Код нарушения',
    vn.name as 'Вид нарушения',
    vid_rabot.name as 'Вид работ',
    rc.name as 'Категория нарушения',
    'Поврежденный элемент' =
		STUFF(
		( SELECT concat(', ', rtt2.name) AS n FROM defect r2 
		LEFT JOIN povrezhdennyiElementForDefect rt2 ON r2.id=rt2.objID
		LEFT JOIN povrezhdennyiElement rtt2 ON rtt2.id=rt2.activityID
		WHERE r2.id=t.obj_id 
		FOR XML PATH('')
		, TYPE
		).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),
    tpov.name as 'Характер повреждения',
    t.tsentrPovrezhdenia as 'Место расположения центра повреждения на трубопроводе, часов',
    t.vysotaPovrezhdenia as 'Высота повреждения',
    t.shirinaPovrezhdenia as 'Ширина повреждения',
	t.ploshchadPovrezhdenia as 'Площадь повреждения',
    'Причины нарушения (технические)' =
        STUFF(
        ( SELECT concat(', ', rtt2.name) AS n FROM defect r2 
        LEFT JOIN prichinyPovrezhdeniaForDefect rt2 ON r2.id=rt2.objID
        LEFT JOIN prichinyPovrezhdenia rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id=t.obj_id 
        FOR XML PATH('')
        , TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),
    'Причины нарушения (организационные)' =
        STUFF(
        ( SELECT concat(', ', rtt2.name) AS n FROM defect r2 
        LEFT JOIN prichiny_narusheniya_organizacionnye_for_defect rt2 ON r2.id=rt2.objID
        LEFT JOIN prichiny_narusheniya_organizacionnye rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id=t.obj_id 
        FOR XML PATH('')
        , TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),
    'Сопутствующие причины' =
        STUFF(
        ( SELECT concat(', ', rtt2.name) AS n FROM defect r2 
        LEFT JOIN soputstvuiushchiePrichinyForDefect rt2 ON r2.id=rt2.objID
        LEFT JOIN soputstvuiushchiePrichiny rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id=t.obj_id 
        FOR XML PATH('')
        , TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),
    'Состояние конструкции канала' = 
        STUFF(
        ( SELECT concat(', ', rtt2.name) AS n FROM defect r2 
        LEFT JOIN sostKonstruktsiiKanalaForDefect rt2 ON r2.id=rt2.objID
        LEFT JOIN sostKonstruktsiiKanala rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id=t.obj_id 
        FOR XML PATH('')
        , TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),		
    'Состояние конструкции камеры' = 
        STUFF(
        ( SELECT concat(', ', rtt2.name) AS n FROM defect r2 
        LEFT JOIN sostKonstruktsiiKameryForDefect rt2 ON r2.id=rt2.objID
        LEFT JOIN sostKonstruktsiiKamery rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id=t.obj_id
        FOR XML PATH('')
        , TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),
    sostT.name as 'Состояние теплоизоляции теплопроводов',
    sostNP.name as 'Состояние наружной поверхности теплопроводов',
    sostVP.name as 'Состояние внутренней поверхности поврежденной трубы',
	stateDefect.name as 'Состояние',
	CASE WHEN uzel_nach_otcl.nodeName is NULL or uzel_nach_otcl.nodeName = '' or uzel_nach_otcl.nodeName = ' ' THEN uzel_nach_otcl.externalNodeName ELSE  uzel_nach_otcl.nodeName END as 'Начальная камера отключения от сети',
	CASE WHEN uzel_konec_otcl.nodeName is NULL or uzel_konec_otcl.nodeName = '' or uzel_konec_otcl.nodeName = ' ' THEN uzel_konec_otcl.externalNodeName ELSE  uzel_konec_otcl.nodeName END as 'Конечная камера отключения от сети',
    t.meropriyatiya as 'Способ ликвидации нарушения',
--	t.data_shurfovki as 'Дата шурфовки',
    t.data_nachala_remonta as 'Дата начала ремонтных работ',
    t.vremiaNachalaRemonta as 'Время начала ремонтных работ',
    t.data_zaversheniya_remonta as 'Дата завершения ремонтных работ',
    t.vremiaZaversheniaRemonta as 'Время завершения  ремонтных работ',
	t.trudozatratyNaRemont as 'Трудозатраты на ремонт',
	t.stoimostRemonta as 'Стоимость ремонтных работ, тг',
	t.otchet_po_defektu as 'Примечание',
	t.kolichestvo_otklyuchennyh_potrebitelej as 'Количество отключенных потребителей',
	t.kolichestvo_nedootpushchennoj_teplovoj_energii as 'Количество недоотпущенной тепловой энергии, Гкал',
	t.zatraty_na_vosstanovlenie as 'Затраты на восстановление, тг',
	t.inye_socialnye_posledstviya as 'Иные социальные последствия',
    'Ремонт трубопровода и элементов' = 
        STUFF(
        ( SELECT distinct concat(CASE WHEN rtt2.name != '' THEN  CONCAT(' ELSE  ', rtt2.name, ':' END, ''), STUFF (
            (select concat(',',se.name) as n from defectTube dt
        LEFT JOIN spisokElementov se ON se.id=dt.elementID
        where objId = t.obj_id and activityID = rt2.activityID
        FOR XML PATH('')
        , TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, '')
        ) AS n FROM defect r2 
        LEFT JOIN defectTube rt2 ON r2.id=rt2.objID
        LEFT JOIN remontTruboprovodaSpisok rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id=t.obj_id 
        FOR XML PATH('')
        , TYPE ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''),
		t.shirinaZaplatki as 'Ширина заплатки',
		t.vysotaZaplatki as 'Высота заплатки',
		t.len_tube_cur as 'Длина заменённой трубы, м',
		remontIzolKonstruktsii.name as 'Ремонт теплоизоляционной конструкции',
		t.len_izol_cur as 'Длина заменённой изоляции, м',
		remont_kanala.name as 'Ремонт канала',
		t.len_channel_cur as 'Длина участка ремонта канала',
		remont_kamery.name as 'Ремонт камеры'		
from (
		select
			distinct
			l.lineID,
			organizations.name as 'organization',
			d.id as obj_id,
			d.remontTypeID,
			d.data_osmotra,
			d.vremya_osmotra,
			d.nomer_doma,
			d.ulicaID,
			d.priznak_truboprovoda,
			d.nodeID_bizhajshej_kamery,
			d.rasstoyanieDoPovrezhdeniyaNachKamery,
			d.tipPoverhnostiID,
			d.dreniruemyj_truboprovodID,
			d.defectDescription,
			d.opresID,
			d.data_sostavleniya_akta,
			d.nomer_akta,
			d.nomer_prikaza,
			d.data_prikaza_vvoda_v_ekspluataciyu,
			d.vid_narusheniyaID,
			d.remontCatID,
			d.stateID,
			d.sostTeploizolID,
			d.sostKonstruktsiiKameryID,
			d.sostKonstruktsiiKanalaID,
			d.sostNaruzhnoiPoverkhnostiID,
			d.sostVnutrenneiPoverkhnostiID,
			d.vid_rabotID,
			d.nodeID1,
			d.nodeID2,
			d.tipPovrezhdeniaID,
			d.tsentrPovrezhdenia,
			d.vysotaPovrezhdenia,
			d.shirinaPovrezhdenia,
			d.ploshchadPovrezhdenia,
			d.meropriyatiya,
			d.data_shurfovki,
			d.data_nachala_remonta,
			d.vremiaNachalaRemonta,
			d.data_zaversheniya_remonta,
			d.vremiaZaversheniaRemonta,
			d.trudozatratyNaRemont,
			d.stoimostRemonta,
			d.otchet_po_defektu,
			d.kolichestvo_otklyuchennyh_potrebitelej,
			d.kolichestvo_nedootpushchennoj_teplovoj_energii,
			d.zatraty_na_vosstanovlenie,
			d.inye_socialnye_posledstviya,
			d.shirinaZaplatki,
			d.vysotaZaplatki,
			d.len_tube_cur,
			d.remontIzolKonstruktsiiID,
			d.len_izol_cur,
			d.remont_kanalaID,
			d.len_channel_cur,
			d.remont_kameryID,

            d.predsedatel,

            d.dolzhnost_predsedatelya,
            d.chlen_tn_1,
            d.dolzhnost_tn_1,
            d.chlen_tn_2,
            d.dolzhnost_tn_2,
            d.chlen_tn_3,
            d.dolzhnost_tn_3
		
        
        from defect d
		JOIN (
			select 
				k.lineID,
				k.obj_id,
				k.organizationID
			from (
				select
					distinct
						l.id as lineID,
						d.id as obj_id,
                        d.stateID,
						l.organizationID,
						lST_Distance(l.shape, d.shape) as length,
						MIN(lST_Distance(l.shape, d.shape)) OVER(PARTITION BY d.id ) AS "min_len"
				from defect d
				JOIN linesobj l ON ( l.removed = 0 and lST_Distance(l.shape, d.shape) < 0.1 )
			)k
		where k.min_len = k.length
	) l on l.obj_id = d.id
	left join organizations on organizations.id = l.organizationID
  
  where   
  $state_cond$
  (
  (d.data_osmotra $season_condition$)
  )
)t
LEFT JOIN heatPipeSections hpss ON hpss.lineID=t.lineID $and_condition2$
LEFT JOIN pipeSections pss ON pss.id = hpss.pipeSectionID
JOIN nodes n1 ON ( n1.id = pss.nodeID1 and n1.removed = 0)
LEFT JOIN nodes n2 ON n2.id = pss.nodeID2
left join nodes uzel_nach_otcl on uzel_nach_otcl.id = t.nodeID1 
left join nodes uzel_konec_otcl on uzel_konec_otcl.id = t.nodeID2 
left join externalCodes ec1 ON ec1.id = n1.externalCodeID
left join externalCodes ec2 ON ec2.id = n2.externalCodeID
left join nodes node_bizhajshej_kamery on node_bizhajshej_kamery.id = t.nodeID_bizhajshej_kamery
LEFT JOIN defectTypes deft ON deft.id = t.remontTypeID
left join stateDefect on stateDefect.id = t.stateID
left join tipPoverhnosti tp on tp.id = t.tipPoverhnostiID
left join externalSigns  es on es.id = t.priznak_truboprovoda 
left join vid_narusheniya vn on vn.id = t.vid_narusheniyaID
left join vid_rabot on vid_rabot.id = t.vid_rabotID
left join remontCat rc ON rc.id = t.remontCatID
left join remontIzolKonstruktsii on remontIzolKonstruktsii.id = t.remontIzolKonstruktsiiID
left join ulitsy st ON st.id = t.ulicaID
left join opres op ON op.id = t.opresID
left join tipPovrezhdenia tpov ON  tpov.id = t.tipPovrezhdeniaID
left join sostTeploizol sostT ON sostT.id = t.sostTeploizolID
left join sostNaruzhnoiPoverkhnosti sostNP ON sostNP.id = t.sostNaruzhnoiPoverkhnostiID
left join sostVnutrenneiPoverkhnosti sostVP ON sostVP.id = t.sostVnutrenneiPoverkhnostiID
left join remont_kanala on remont_kanala.id = t.remont_kanalaID
left join remont_kamery on remont_kamery.id = t.remont_kameryID
left join isolMaterials im on im.id = hpss.isolMaterialID
LEFT JOIN tubingTypes ON tubingTypes.id=hpss.tubingTypeID
left join isolationTypes on isolationTypes.id = hpss.isolationTypeID
left join externalMaterials on externalMaterials.id = hpss.externMaterialID
left join anticorrMaterials on anticorrMaterials.id = hpss.anticorrMaterialID

left join magistrali on magistrali.id = hpss.magistral

left join uchastok_ms ms ON ms.id = pss.magistralSite
left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka

left join rayon_ekspluatatsii re_ms ON re_ms.id = ue_ms.rayon_ekspluatatsii
left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka

left join uchastok_rs rs ON rs.id = pss.distSite
left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka

left join rayon_ekspluatatsii re_rs ON re_rs.id = ue_rs.rayon_ekspluatatsii
left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka

LEFT JOIN istochniki_tepla ist_ms ON ist_ms.id=ue_ms.istochnik_tepla
LEFT JOIN istochniki_tepla ist_rs ON ist_rs.id=ue_rs.istochnik_tepla


WHERE 
   -- n1.fileID in (58) and
    ( (not ec1.name in ('П1','П2') or not ec2.name in ('П1','П2')) or (ec1.name is null AND ec2.name is null) ) 
--	$and_condition$

ORDER BY 'Начальник участка','Наименование участка',t.data_osmotra desc

'''
select 
s.ORDINAL_POSITION,
s.TABLE_NAME,
s.COLUMN_NAME,
rc.oldName,
hlp.hlp
--,rt.oldName

FROM INFORMATION_SCHEMA.COLUMNS s

LEFT JOIN renamed_tables rt ON s.TABLE_NAME=rt.newName
LEFT JOIN renamed_columns rc ON rc.newName=s.COLUMN_NAME
LEFT JOIN vsp.dbo.HELP_OLD hlp ON hlp.tab=rt.oldName AND hlp.en=rc.oldName
JOIN tables_columns tc ON tc.columnID=rc.id and TC.tableID=RT.id

WHERE s.TABLE_NAME = 'realConsumers'
ORDER BY
s.ORDINAL_POSITION


    TIP_TEPLO, 1, 1, TIP_US,  "US",  ST_US,   "",                       "Узел",                   "Ненагруженный узел", "US_OUT",
    TIP_TEPLO, 0, 1, TIP_PR,  "PR",  ST_PR,   "realConsumers",          "Потребитель реальный",   "Потребитель реальный", "PT_OUT",
    TIP_TEPLO, 0, 1, TIP_PO,  "PO",  ST_PO,   "generalizedConsumers",   "Потребитель обобщенный", "Потребитель обобщенный", "PT_OUT",
//  0, 1, TIP_UP,  "UP",  ST_UP,   "",                       "Узел подпитки"),         "Узлы подпитки и прис.баков-аккумуляторов", NULL,
    TIP_TEPLO, 0, 1, TIP_IS,  "IS",  ST_IS,   "heatSources",            "Источник тепла",         "Источник тепла", "US_OUT",
    TIP_TEPLO, 0, 1, TIP_HS,  "HS",  ST_HS,   "pumpStations",           "Насосная станция",       "Насосная станция", "US_OUT",
    TIP_TEPLO, 0, 1, TIP_C3,  "C3",  ST_C3,   "threeWayValves",         "Клапан трехходовой",     "Клапан трехходовой", "US_OUT",
//  0, 1, TIP_ZP,  "ZP",  ST_ZP,   "",                       "ЦТП",                    "ЦТП", "US_OUT",
//    TIP_TEPLO, 1, 1, TIP_US2, "US2", ST_US2, "connectNodes",            "Узел",                   "Ненагруженный узел", "US_OUT",
    TIP_TEPLO, 1, 1, TIP_US2, "US2", ST_US2, "connectNodes",            "Узел присоединения",                   "Узел присоединения", "US_OUT",



    TIP_TEPLO, 1, 0, TIP_UT,  "UT",   ST_UT,     "heatPipeSections",     "Участок",     "Участок теплопровода", "UT_OUT", "", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_HC,  "HC",   ST_HC,     "pumps",                "Насос",       "Насосы(насосные станции расчетной схемы", "NS_OUT", "stateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_RD,  "RD",   ST_RD,     "pressRegulators",      "Регул. давл.", "Сетевые регуляторы давления", "RS_OUT", "regulatorStateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_RR,  "RR",   ST_RR,     "consumptRegulators",   "Регул. расх.", "Сетевые регуляторы расхода", "RS_OUT", "regulatorStateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_ZD,  "ZD",   ST_ZD,     "dampers",              "Задвижка",    "Задвижка", "ZD_OUT", "damperArmatureStateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_ZD2, "ZD2",  ST_ZD2,    "regulArmatures",       "Регулирующая арматура", "Регулирующая арматура", "ZD2_OUT", "damperArmatureStateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_BP,  "BP",   ST_BP,     "bypass",               "Байпас",      "Байпаc", "BP_OUT", "regulatorStateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_DR,  "DR",   ST_DR,     "diaphragms",           "Диафрагма",   "Диафрагма", "DRO_OUT", "stateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_EL,  "EL",   ST_EL,     "elevators",            "Элеватор",    "Элеватор", "ANY_OUT", "stateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_RO,  "RO",   ST_RO,     "systemRadiators",      "Радиатор",    "Радиатор", "ANY_OUT", "stateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_TO,  "TO",   ST_TO,     "heatExchangers",       "Теплообменник","Теплообменник", "ANY_OUT", "stateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_KU,  "KU",   ST_KU,     "airHeaters",           "Калориферная установка",  "Калориферная установка", "ANY_OUT", "", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_RP,  "RP",   ST_RP,     "pressDropRegulators",  "Регул. переп.", "Регулятор перепада давления", "RS_OUT", "regulatorStateID", -1, -1, -1,
    TIP_TEPLO, 1, 0, TIP_OK,  "OK",   ST_OK,     "reverseValves",        "Обратный клапан", "Обратный клапан", "OK_OUT", "stateID", -1, -1, -1,

Для OUT

select 

s.COLUMN_NAME, s.COLUMN_DEFAULT,
h.hlp,*

FROM INFORMATION_SCHEMA.COLUMNS s
join vsp.dbo.HELP_OLD h on h.en=s.COLUMN_NAME and s.TABLE_NAME=h.tab

WHERE s.TABLE_NAME = 'UT_OUT'


'''

#-----------------------------------------------

#Абонент

tab_ab = {
    'consumer_status': 'przp',   #VARCHAR(255), Состояние aбонента.                                       
    'calculation_code': 'kod',   #VARCHAR(255), Код расчетной схемы                                       
    'water_network_attachment_node': 'uzel',   #VARCHAR(255), Узел присоединения на водопров. сети                      
    'geodetic_axis_elevation': 'geodz',   #FLOAT, Геодезич. отметка оси труб на вводе, м.                   
    'highest_building_floor': 'hz',   #INT, Этажность наиболее высокого здания                        
    'floor_height': 'h',   #FLOAT, Расчетная высота этажа, м.                                
    'summer_daily_water_consumption_code': 'kodsg_l',   #VARCHAR(255), Код летнего суточного графика водопотребления             
    'winter_daily_water_consumption_code': 'kodsg_z',   #VARCHAR(255), Код зимнего суточного графика водопотребления             
    'calculated_flow_rate': 'r_q',   #FLOAT, Расчетный расход, м3/ч                                    
    'max_flow_rate': 'm_q',   #FLOAT, Максимальный расход, м3/ч                                 
    'required_headroom': 'sv_p',   #FLOAT, Требуемый свободный напор, м                              
    'coefficient_variation_group_code': 'kodkv',   #VARCHAR(255), Код группы коэффициентов вариации                         
    'dominant_point_membership': 'prz_dt',   #BIT, Принадлежность к диктующей точке                          
    'subscriber_name': 'name_ab',   #VARCHAR(255), Наименование абонента                                     
    'subscriber_type': 'prz_ab',   #VARCHAR(255), Признак абонента                                          
    'calculated_head_loss_up_to_dominant_point': 'poteri_dt',   #FLOAT, Расчетные потери напора до диктующей точки ответвления, м.
}

#-----------------------------------------------

#Участки трубопроводов расчетной схемы

tab_ut = {
    'segment_status': 'key_ut',   #INT, Состояние участка.                                                
    'input_node_calculation_code': 'kod1',   #INT, Код расчетной схемы начального узла.               
    'input_node_name': 'uzel1',   #NVARCHAR(255), Имя начального узла.                                           
    'output_node_calculation_code': 'kod2,',   #INT, Код расчетной схемы конечного узла.                    
    'output_node_name': 'uzel2,',   #NVARCHAR(255), Имя конечного узла.                                                
    'segment_length': 'dlina',   #FLOAT, Длина участка, м.                                               
    'pipe_diameter': 'diametr',   #FLOAT, Внутренний диаметр трубопровода, мм.                            
    'sum_of_local_resistance_coefficients': 'mestnoe',   #FLOAT, Сумма коэффициентов местных сопротивлений.  
    'pipe_material': 'material',   #INT, Материал трубы.                                                    
    'pipe_surface_condition': 'poverhn',   #INT, Состояние поверхности трубы.                              
    'hydraulic_resistance_segment': 'sopr',   #FLOAT, Гидравлическое сопротивление участка.               
}

#-----------------------------------------------

# Транзитный узел
tab_tu = {
    'calculation_code': 'kod',   #VARCHAR(255), Код расчетной схемы                 
    'node_name': 'uzel',   #VARCHAR(255), Наименование узла                   
    'terrain_elevation': 'h',   #FLOAT, Геодезическая отметка местности, м. 
    'dominant_point_membership': 'pr_dt',   #INT, Принадлежность к диктующей точке    
    'node_description': 'name_tu',   #VARCHAR(255), Содержательное наименование узла    
}

#-----------------------------------------------

tab_nodes = {
    'externalNodeName': 'externalNodeName',
    'externalCodeID': 'externalCodeID',
    'internalNodeID': 'internalNodeID',
    'fileID': 'fileID',
}

#-----------------------------------------------

tab_linesobj = {
    'externalSignLineID': 'externalSignLineID',  
    'hydroRes': 'sopr',
}

#-----------------------------------------------

tab_heatPipeSections = {
#    'pipeSectStateIDflow': 'pipeSectStateIDflow',
#    'pipeSectStateIDret': 'pipeSectStateIDret',

    'pipeSectStateIDflow': 'key_ut_p',
    'pipeSectStateIDret': 'key_ut_o',

    'standardID': 'standard',
    'tubesCount': 'truba',
    'diameterInternal': 'diametr',
    'diameterCondit': 'diametr_usl',
    'diameterExternal': 'Диаметр внешний',
    'wallThickness': 'tol',
    'pipeSectLength': 'dlina',
    'tubeRoughness': 'scher',
    'localLosesShare': 'dolja',
    'localResSum': 'mestnoe',
    'varCoeffIDflow': 'kodkvp',
    'varCoeffIDret': 'kodkvo',
    'calcHeatLosSignID': 'name_calctpr',
    'tubingTypeID': 'name_typ',

    'lastTransDate': 'dateend',  # Дата последней перекладки
    'signNumWork' : 'kolwork',  # Признак Числа работы в год <5000часов
    'heatTestsCoeff' : 'kti',  # Коэффициент тепловых испытаний


####     
####     '''
####     'pipeSectStateIDflow' : 'key_ut_p',  # Состояние участка подающего теплопровода
####     'pipeSectStateIDret' : 'key_ut_o',  # Состояние участка обратного теплопровода
####     'standardID' : 'standard',  # Стандарт труб на участке
####     'standardTubeLink' : 'kod_truba',  # Ссылка на стандартную трубу
####     'tubesCount' : 'truba',  # Количество труб на участке
####     'diameterInternal' : 'diametr',  # Диаметр внутренний
####     'diameterCondit' : 'diametr_usl',  # Диаметр условный
####     'diameterExternal' : 'Диаметр',  # внешний NULL
####     'wallThickness' : 'tol',  # Толщина стенки
####     'pipeSectLength' : 'dlina',  # Длина участка теплопровода
####     'tubeRoughness' : 'scher',  # Эквивалентная шероховатость
####     'localLosesShare' : 'dolja',  # Доля местных потерь
####     'localResSum' : 'mestnoe',  # Сумма коэффициентов местных сопротивлений
####     'varCoeffIDflow' : 'kodkvp',  # Код коэфф.вариации параметров по подающей трубе
####     'varCoeffIDret' : 'kodkvo',  # Код коэфф.вариации параметров по обратной трубе
####     'calcHeatLosSignID' : 'name_calctpr',  # Метод расчета тепловых потерь
####     'tubingTypeID' : 'name_typ',  # Вид прокладки
####     'channelID' : 'kog_canal',  # Код канала
#### #    'channelID' : 'kog_canal',  # Код канала
####     'constrChanWidth' : 'chan_width',  # NULL
####     'constrChanHeight' : 'chan_height',  # NULL
####     'heatTestsCoeff' : 'kti',  # Коэффициент тепловых испытаний
####     'signNumWork' : 'kolwork',  # Признак Числа работы в год <5000часов
####     'isolMaterialID' : 'kod_izol',  # Материал тепловой изоляции
####     'isolThickness' : 'thickizol',  # Толщина изоляции
####     'isolMaterialHCcoeff' : 'k_izol',  # Коэффициент поправки теплопроводности изоляционного материала
####     'pipelineLayingDepth' : 'depth',  # Глубина заложения до оси теплопровода
####     'isolHTcoeffAbove' : 'izoloutair',  # Теплоотдача от изоляции трубопровода к окружающему воздуху
####     'isolHTcoeffUnder' : 'izol_air',  # Коэфф.теплоотдачи от изоляции трубопровода к воздуху канала
####     'airGroundHTcoeffUnder' : 'air_ground',  # Коэфф.теплоотдачи от воздуха канала к грунту
####     'groundHCcoeff' : 'tpground',  # Теплопроводность грунта
####     'pipelineAxesDist' : 'distance',  # Расстояние между осями теплопроводов
####     'damageNum' : 'kol_pereklad',  # Количество повреждений (ремонтов) с начала эксплуатации
####     'lastTransDate' : 'dateend',  # Дата последней перекладки
####     'lastIsolDate' : 'dateend_izol',  # Дата последней замены изоляционной конструкции
####     'repairDateCapital' : 'datenew_kapital',  # Дата вывода в последний капитальный ремонт
####     'PICdateCapital' : 'dateend_kapital',  # Дата ввода в эксплуатацию после последнего капитального ремонта
####     'repairDateMaint' : 'datenew_repair',  # Дата вывода в последний текущий ремонт
####     'PICdateMaint' : 'dateend_repair',  # Дата ввода в эксплуатацию после последнего текущего ремонта
####     'sectExploitPeriod' : 'f_kol_let',  # Срок эксплуатации участка
#### #    'specDamageCoeff' : 'f_koef_povr',  # Коэффициент удельной повреждаемости
#### #    'specDamageCoeff2' : 'f_koef_povr_2goda',  # Коэфф.уд.повреждаемости за последние 2 года
#### #    'powCabInstCount10' : 'f_10_elektro',  # Кол.паралл.прокладок силового кабеля, >10м от трубопр.
#### #    'powCabInstCount5' : 'f_5_elektro',  # Кол.паралл.прокладок силового кабеля,  10-5м от трубопр.
#### #    'powCabInstCount3' : 'f_3_elektro',  # Кол.паралл.прокладок силового кабеля,  5-3м от трубопр.
#### #    'powCabInstCount1' : 'f_1_elektro',  # Кол.паралл.прокладок силового кабеля,  3-1м от трубопр.
#### #    'powCabInstCount0' : 'f_0_elektro',  # Кол.паралл.прокладок силового кабеля, <1м от трубопр.
#### #    'powCabIntersCount' : 'f_peres_elektro',  # Количество пересечений силового кабеля трубопровод
#### #    'gasECPcount10' : 'f_10_gas',  # Кол.паралл.прокладок электрохимзащиты газопровода, >10м от трубопр.
#### #    'gasECPcount5' : 'f_5_gas',  # Кол.паралл.прокладок электрохимзащиты газопровода,  10-5м от трубопр.
#### #    'gasECPcount3' : 'f_3_gas',  # Кол.паралл.прокладок электрохимзащиты газопровода,  5-3м от трубопр.
#### #    'gasECPcount1' : 'f_1_gas',  # Кол.паралл.прокладок электрохимзащиты газопровода,  3-1м от трубопр.
#### #    'gasECPcount0' : 'f_0_gas',  # Кол.паралл.прокладок электрохимзащиты газопровода, <1м от трубопр.
#### #    'gasECPIntersCount' : 'f_peres_gas',  # Кол.пересечений электрохимзащиты газопровода трубопровода
#### #    'elTranspCount10' : 'f_10_transp',  # Кол.паралл.прокладок элетротранспорта >10м от трубопровода
#### #    'elTranspCount5' : 'f_5_transp',  # Кол.паралл.прокладок элетротранспорта,  10-5м от трубопр.
#### #    'elTranspCount3' : 'f_3_transp',  # Кол.паралл.прокладок элетротранспорта,  5-3м от трубопр.
#### #    'elTranspCount1' : 'f_1_transp',  # Кол.паралл.прокладок элетротранспорта,  3-1м от трубопр.
#### #    'elTranspCount0' : 'f_0_transp',  # Количество параллельных прокладок элетротранспорта <1м от трубопровода
#### #    'elTranspIntersCount' : 'f_peres_transp',  # Количество пересечений элетротранспорта
#### #    'potentialDiffLevelID' : 'f_elektropotenz',  # Уровень разности электропотенциалов
#### #    'corrosionDegOutID' : 'f_nar_korroz',  # Степень внешней коррозии
#### #    'corrosionDegInID' : 'f_vnu_korroz',  # Степень внутренней коррозии
#### #    'floodIntensityGWid' : 'f_grund_water',  # Интенсивность подтопления грунтовыми водами
#### #    'floodIntensityFWid' : 'f_pavod_water',  # Интенсивность подтопления паводковыми водами
#### #    'floodIntensityTWid' : 'f_vod_water',  # Интенсивность подтопления водопроводными водами
#### #    'floodIntensityBWid' : 'f_fek_water',  # Интенсивность подтопления фекальными водами
#### #    'jointsTightnessInfr' : 'f_st_stik',  # Нарушение герметичности стыков
#### #    'chanConstrFract' : 'f_st_islom',  # Излом конструкций перекрытия и стен канала
#### #    'projSolDeviation' : 'f_st_otkl',  # Отклононение от проекта в процессе эксплуатации
#### #    'constrBearReduce' : 'f_st_nes',  # Снижение несущей способности конструкций
#### #    'fixedSuppDestr' : 'f_st_opor',  # Разрушение неподвижных опор
#### #    'sectWaterDumpID' : 'f_water_otved',  # Водоотведение на участке
#### #    'breakComplexityID' : 'f_otkl',  # Сложность откл.участка для устранения повреждений
#### #    'breakConsumVolID' : 'f_okl_pot',  # Объем отключаемых потребителей, при  повреждении
#### #    'ERWdifficultyID' : 'f_slog_arbeit',  # Сложность выполнения аварийно-восстановительных работ
#### #    'tubingPedestrianID' : 'f_tratuar',  # Прокладка трубопроводов под пешеходными зонами
#### #    'tubingWayID' : 'f_doroga',  # Прокладка трубопроводов под авто и ж/д дорогами
#### #    'populDamageID' : 'f_ucherb_narod',  # Нанесение ущерба населению от подтопления
#### #    'infrastrDamageID' : 'f_ucherb_gorod',  # Нанесение ущерба инфраструктуре города от подтопления
#### #    'hydraTestsDate' : 'date_isp_gid',  # Дата гидравлических испытаний
#### #    'sectExpend' : 'G_isp_gid',  # Расход на участке при гидравлических испытаниях
#### #    'sectThrustLoses' : 'dP_isp_gid',  # Потери напора на участке при гидравлических испытаниях
#### #    'heatTestsDate' : 'date_isp_tep',  # Дата тепловых испытаний
#### #    'temperOutAir' : 'tn_isp_tep',  # Температура наружного воздуха при тепловых испытаниях
#### #    'temperGround' : 'tg_isp_tep',  # Температура грунта  при тепловых испытаниях
#### #    'expendDWflow' : 'G1_isp_tep',  # Расход сетевой воды при тепловых испытаниях, подача
#### #    'expendDWret' : 'G2_isp_tep',  # Расход сетевой воды при тепловых испытаниях, обратка
#### #    'temperCoolFlow' : 'dt1_isp_tep',  # Температура остывания при тепловых испытаниях, подача
#### #    'temperCoolRet' : 'dt2_isp_tep',  # Температура остывания при тепловых испытаниях, обратка
#### #    'temperDWflow' : 't1_isp_tep',  # Температура сетевой воды при тепловых испытаниях, подача
#### #    'temperDWret' : 't2_isp_tep',  # Температура сетевой воды при тепловых испытаниях, обратка
#### #    'opc' : 'opc',  # Измеренный расход
#### #    'tubeCharactID' : 'Характеристика',  # трубы  Характеристика трубы
#### #    'tubeTypeID' : 'Тип',  # трубы    Тип трубы
#### #    'tubeMaterial' : 'Материал',  # трубы NULL
#### #    'temperMax' : 'Максимально',  # допустимая температура    NULL
#### #    'factoryManufID' : 'Завод',  # изготовитель   NULL
#### #    'externMaterialID' : 'Материал',  # наружного покрытия    NULL
#### #    'isolationTypeID' : 'Тип',  # изоляции    Тип изоляции
#### #    'externCoverThick' : 'Толщина',  # наружного покрытия, мм NULL
#### #    'anticorrMaterialID' : 'Материал',  # антикоррозийного покрытия   NULL
#### #    'magistralSite' : 'Участок',  # МС    NULL
#### #    'distSite' : 'Участок',  # РС NULL
#### #    'exploitReg' : 'Район',  # эксплуатации   NULL
#### #    'net' : 'Сеть',  # NULL
#### #    'magistral' : 'Магистраль',  # NULL
#### #    'exploitSite' : 'Участок',  # эксплуатации    NULL
#### #    'netType' : 'Вид',  # сети    NULL
#### #    'crimpingQueSite' : 'Участок',  # очереди опрессовки  NULL
#### #    'deltaH' : 'delta',  # NULL
#### #    'deltaQ' : 'delta_q',  # NULL
#### #    'q' : 'q_uzu',  # NULL
####       '''

}



#-----------------------------------------------

tab_realConsumers = {
    'name': 'name_building',  # Содержательное наименование здания
    'consumerStateID': 'sost',  # Состояние потребителя
#    'automDegID': 'pr_avtomat',  # Степень автоматизации
#    'sectConsumerCode': 'kod_cekz_p',  # Краткое содержательное наименование секционированного потребителя


#----- для Дросселей
    'schemeNum': 'cxema',  # Номер расчетной схемы
    'buildHeight': 'h',  # Высота здания


#    'accumCoeff': 'k_akkuml',  # Коэффициент аккумуляции здания
    'specExpendID': 'kodur',  # Код удельных расходов тепло/вода
    'calcTemperatureID': 'kodtr',  # Код расчетных температур
#    'gvsLoadGraphID': 'kod_gvs',  # Код графика суточного нагрузки ГВ
    'varCoeffID': 'kodkv',  # Код группы коэффициентов вариации
    'calcHLdep': 'otoplz',  # Расчетная тепловая нагрузка на  отопление
    'calcHLindep': 'otopln',  # Расчетная тепловая нагрузка на  отопление
#    'relLoadFacade': 'otn_fs',  # Относительная нагрузка уличного фасада
    'calcInternHD': 'otopl_tp',  # Расчетные внутренние тепловыделения
#    'contCalcHLdep': 'f_otoplz',  # Договорная  тепловая нагрузка на  отопление
#    'contcalcHLindep': 'f_otopln',  # Договорная тепловая нагрузка на  отопление
#    'contRelLoadFacade': 'f_otn_fs',  # Договорная относит. нагрузка уличного фасада
#    'contInternHD': 'f_otopl_tp',  # Договорные внутренние тепловыделения
#    'perspCalcHLdep': 'p_otoplz',  # Перспективная тепловая нагрузка на  отопление
#    'perspcalcHLindep': 'p_otopln',  # Перспективная тепловая нагрузка на  отопление
#    'perspRelLoadFacade': 'p_otn_fs',  # Перспективная относит. нагрузка уличного фасада
#    'perspInternHD': 'p_otopl_tp',  # Перспективные внутренние тепловыделения
    'calcHLventil': 'ventil',  # Расчетная тепловая нагрузка  на вентиляцию
#    'expendHWpart': 'dolja_vent',  # Доля расхода воды через КУ, при отключении её по воздуху
#    'contCalcHLventil': 'f_ventil',  # Договорная расчетная нагрузка  на вентиляцию
#    'perspCalcHLventil': 'p_ventil',  # Перспективная расчетная нагрузка  на вентиляцию
    'avgHLcond': 'kondiz',  # Расчетная  тепловая нагрузка на кондиционирование
#    'contAvgHLcond': 'f_kondiz',  # Договорная расч.нагрузка на кондиционирование
#    'perspAvgHLcond': 'p_kondiz',  # Договорная расч.нагрузка на кондиционирование
    'avgHLcloseSys': 'txz',  # Расчетная тепловая нагрузка на технологию в закрытой системе
    'avgHLopenSysFlow': 'txop',  # Расчетная нагрузка на технологию в открытой системе из подающего теплопровода
    'avgHLopenSysRet': 'txoo',  # Расчетная нагрузка на технологию в открытой системе из обратного теплопровода
#    'contAvgHLcloseSys': 'f_txz',  # Договорная нагрузка на технологию в закрытой системе
#    'contAvgHLopenSysFlow': 'f_txop',  # Договор.среднечас. нагрузка на технологию из подающего теплопр.
#    'contAvgHLopenSysRet': 'f_txoo',  # Договор.среднечас. нагрузка на технологию из обратного теплопр.
#    'perspAvgHLclose': 'p_txz',  # Договорная нагрузка на технологию в закрытой системе
#    'perspAvgHLopenFlow': 'p_txop',  # Договор.среднечас. нагрузка на технологию из подающего теплопр.
#    'contAvgHLopenRet': 'p_txoo',  # Перспективн.среднечас. нагрузка на технологию из обратного теплопр.
    'avgHLGVSopenFlow': 'gvop',  # Средняя тепловая нагрузка на горячее водоснабжение
    'avgHLGVSopenRet': 'gvoo',  # Средняя тепловая нагрузка на горячее водоснабжение
    'avgHLGVScloseParall': 'gvpr',  # Средняя тепловая нагрузка на горячее водоснабжение
    'avgHLGVScloseMix': 'gvsm',  # Средняя тепловая нагрузка на горячее водоснабжение
    'avgHLGVScloseConseq': 'gvps',  # Средняя тепловая нагрузка на горячее водоснабжение
    'avgHLGVSclosePreON': 'gvpw',  # Средняя тепловая нагрузка на горячее водоснабжение
#    'contAvgHLGVSopenFlow': 'f_gvop',  # Договорная средняя нагрузка на ГВ
#    'contAvgHLGVSopenRet': 'f_gvoo',  # Договорная средняя нагрузка на ГВ
#    'contAvgHLGVScloseParall': 'f_gvpr',  # Договорная средняя нагрузка на ГВ
#    'contAvgHLGVScloseMix': 'f_gvsm',  # Договорная средняя нагрузка на ГВ
#    'contAvgHLGVScloseConseq': 'f_gvps',  # Договорная средняя нагрузка на ГВ
#    'contAvgHLGVSclosePreON': 'f_gvpw',  # Договорная средняя нагрузка на ГВ
#    'perspAvgHLGVSopenFlow': 'p_gvop',  # Перспективная средняя нагрузка на ГВ
#    'perspAvgHLGVSopenRet': 'p_gvoo',  # Перспективная средняя нагрузка на ГВ
#    'perspAvgHLGVScloseParall': 'p_gvpr',  # Перспективная средняя нагрузка на ГВ
#    'perspAvgHLGVScloseMix': 'p_gvsm',  # Перспективная средняя нагрузка на ГВ
#    'perspAvgHLGVScloseConseq': 'p_gvps',  # Перспективная средняя нагрузка на ГВ
#    'perspAvgHLGVSclosePreON': 'p_gvpw',  # Перспективная средняя нагрузка на ГВ
#    'hydroModeSignID': 'pr_avar_TP',  # Признак расчета аварийного режима потребителя
    'mixFactCoeff': 'uf',  # Коэффициент  смешения  элеватора
    'hourIrregCoeff': 'gvs_max',  # Коэфф.часовой неравномерности нагрузки горячего водоснабжения
    'circHLosOpen': 'rez',  # Расчетные тепловые потери в рециркуляц. контуре ГВС
    'tempRecircPipe': 'T_pot_rez',  # Температура в рециркуляционном трубопроводе ГВС
#    'setLeakageFlow': 'utechp',  # Заданная утечка из подающего теплопровода
#    'setLeakageRet': 'utecho',  # Заданная утечка из обратного  теплопровода
#    'WEmeteringDeviceID': 'pr_uchet',  # Признак установки прибора учета

#----- для Дросселей
    'volWaterHS': 'a24',  # Удельный объем воды в системе отопления
    'volWaterVS': 'a25',  # Удельный объем воды в системе вентиляции

    'hydroResCloseSys': 'gsz',  # Гидравл.сопротивление закрыт. системы теплопотребления
    'hydroResCloseSysSummer': 'gszl',  # Гидравл.сопротивление потребителя в летний перид
#    'closeSysCalcSignID': 'gszpr',  # Признак расчета гидравл.сопротивл. закр.системы
    'hydroResWDOFlow': 'gsop',  # Гидравл.сопротивление откр. ГВС
#    'calcSignOpenSysFlowID': 'gsoppr',  # Признак расчета гидравл.сопротивления откр. ГВС
    'hydroResWDORet': 'gsoo',  # Гидравл.сопротивление открытой ГВС
#    'calcSignResWDORetID': 'gsoopr',  # Признак расчета гидравл.сопротивления откр. ГВС
#    'calcSignSetLoadCloseSys': 'prznz',  # Признак расчета гидравл. режима закрытых систем теплопотребл.
#    'calcSignSetLoadOpenSysFlow': 'prznp',  # Признак расчета гидравл. режима открытых ГВС, из подающего трубопровода
#    'calcSignSetLoadOpenSysRet': 'przno',  # Признак расчета гидравл. режима открытых ГВС, из обратного трубопровода
#    'hydroThrustIn': 'pP',  # Пьезом.напор на входе теплового пункта, плановый режим
#    'hydroThrustOut': 'pO',  # Пьезом.напор на выходе теплового пункта, плановый режим

    'calcExpendDep': 'GG_otoplz',  # Расчетный расход на  отопление
    'calcExpendIndep': 'GG_otopln',  # Расчетный расход на  отопление
    'calcExpendVentil': 'GG_ventil',  # Расчетный расход на  вентиляцию
    'calcExpendCond': 'GG_kondiz',  # Расчетный расход на  кондиционирование
    'calcExpendHWFlow': 'GG_gvop',  # Расчетный расход на горячее водоснабжение
    'calcExpendHWRet': 'GG_gvoo',  # Расчетный расход на ГВС, в открытой системе
    'calcExpendRecircOpen': 'GG_rez',  # Расчетный расход на рециркуляцию в открытой ГВС
    'calcExpendHWparall': 'GG_gvpr',  # Расчетный расход на горячее водоснабжение
    'calcExpendHWmix': 'GG_gvsm',  # Расчетный расход на горячее водоснабжение
    'calcExpendHWconseq': 'GG_gvps',  # Расчетный расход на горячее водоснабжение
    'calcExpendHWpreON': 'GG_gvpw',  # Расчетный расход на горячее водоснабжение

# Для дросселей
    'throtStageSignID': 'a13',  # Признак ступени дросселирования
    'diameterThrotDiaph': 'a15',  # Диаметр дроссельной диафрагмы минимально допустимый
    'diameterElevNozzle': 'a14',  # Диаметр сопла элеватора минимально допустимый
    'temperChartSignID': 'a17',  # Признак температурного графика

#    'calcSignRes': 'pr_sopr',  # Метод расчета сопротивления в фактическом режиме
#    'calcSignHL': 'pr_teplo',  # Метод расчета тепловой нагрузки в фактическом режиме

    'parallHeatersCount1': 'a18',  # Число параллельно включенных подогревателей 1 ступени
    'parallHeatersCount2': 'a19',  # Число параллельно включенных подогревателей 2 ступени


#    'parallHeatersCountIndep': 'a19_co',  # Число параллельно включенных подогревателей СО


# Для дросселей
    'calcThrustLosHS': 'a7',  # Расчетные потери напора в отопит.системе (подогревателе)
    'calcThrustLosAH': 'a8',  # Расчетные потери напора в калориферах
    'calcThrustLosAC': 'a9',  # Расчетные потери напора в кондиционерах
    'calcThrustLosFlow': 'a10',  # Расч.потери напора в подающем трубопроводе ГВС
    'calcThrustLosFlowCirc': 'a11',  # Расчетные потери напора в циркул. трубопроводе ГВС
    'calcThrustInWDO': 'a12',  # Расчетный напор на входе водоразборных приборов
    'calcThrustLosHeaters1': 'a22',  # Расчетные потери напора на подогревателе 1-ой ступени ГВС
    'calcThrustLosHeaters2': 'a23',  # Расчетные потери напора на подогревателе 2-ой ступени ГВС


#    'PDvalveInstallLocID': 'pr_per_PD',  # Место установки клапана перепада напора
#    'setPDonRegulator': 'p_per_PD',  # Заданный перепад напора на регуляторе
    'calcFerDiameterSignID': 'pr_shaibi',  # Признак  записи шайбы в потребитель
    'calcTempHR': 'Tr_tv_co',  # Расчетная температура в отапливаемых помещений
    'calcTempVS': 'Tr_tv_cv',  # Расчетная температура нагретого воздуха после КУ
    'calcTempHWDO': 'Tr_gvs',  # Расчетная температура горячей воды
#    'responsibleID': 'otv',  # Техник
#    'contractNumber': 'contract',  # Номер договора с теплоснабжающей организацией
#    'stopValveTypeID': 'Запорная',  # арматура    NULL
#    'meterDevWorkSign': 'Признак',  # работы прибора учета    NULL
#    'meterDevSafety': 'Сохранность',  # пломбы прибора учета  NULL
#    'meterDevStampNum': 'Номер',  # пломбы прибора учета  NULL
#    'isolationType': 'Изоляция',  # Изоляция

# Это добавил  Диаметры дросселей

     'b23': 'b23',  # Отопление
     'b28': 'b28',  # Вентиляция (воздушного отопления)
     'b32': 'b32',  # ГВС; закрытая
     'b20': 'b20',  # Подпорная
     'b14': 'b14',  # Вход теплового пункта
     'b38': 'b38',  # Ограничительная в циркуляционном контуре ГВС
     'b35': 'b35',  # На входе подающего трубопровода открытой ГВС
     'b36': 'b36',  # Подпорно-циркуляционная в открытой ГВС

     'zd7': 'zd7', # Вход ТП
     'zd8': 'zd8', # Выход ТП
     'zd27': 'zd27', # Вход СО
     'zd48': 'zd48', # Вход СВ
     'zd28': 'zd28', # Вх.II ступен.ГВ
     'zd36': 'zd36', # ОткрГВ подача
     'zd38': 'zd38', # ОткрГВ обратка
     'zd39': 'zd39', # Летняя СО для открытой ГВС обратка
     'zd49': 'zd49', # СО посл, предв
     'zd50': 'zd50', # Летняя СО посл, предв

     'diameterNozzle': 'du_elevat',   #  Диаметр сопла элеватора, установленный
}

#-----------------------------------------------

tab_specExpends = {
    'specExpendID': 'kodur',  # Код удельных расходов
    'hSourceCode': 'kod_ist',  # Код источника тепла
    'calcHLdep': 'otoplz',  # Удельный  расход  потребителя  на  отопление, зависимая схема
    'calcHLindep': 'otopln',  # Удельный  расход  потребителя  на  отопление,  независимая схема
    'calcHLventil': 'ventil',  # Удельный  расход  потребителя   на вентиляцию
    'calcHLcond': 'kondiz',  # Удельный  расход  потребителя   на  кондиционирование
    'calcHLcloseSys': 'txz',  # Удельный расход потребителя на технологические процессы в закрытой ТС
    'calcHLopenSys': 'txo',  # Удельный расход потребителя на технологические процессы в открытой ТС
    'calcExpendHWopen': 'gvo',  # Удельный  расход  на  горячее  водоснабжение при открытой ТС
    'circHLosOpen': 'rez',  # Удельный рециркуляционный расход на компенсацию тепловых потерь открытой  ГВС
    'avgHLGVScloseParall': 'gvpr',  # Удельный расход на горячее водоснабжение при параллельной ГВС
    'avgHLGVScloseMix': 'gvsm',  # Удельный  расход на горячее водоснабжение при смешанной ГВС
    'avgHLGVScloseConseq': 'gvps',  # Удельный  расход на горячее водоснабжение при последовательной ГВС
    'avgHLGVSclosePreON': 'gvpw',  # Удельный  расход на горячее водоснабжение при предвключенной ГВС
    'avgHLGVScloseSummer': 'gvz_leto',  # Удельный  расход  на  ГВ  в закрытой системе в летнем периоде
    'avgHLGVSopenSummer': 'gvo_leto',  # Удельный  расход  на  ГВ  в открытой системе в летнем периоде
}

#-----------------------------------------------

tab_pumps = {
#    'offReason': 'pr_otkl',   #  Причина отключения
#    'pumpStationID': 'name_nas_stanzii',   #  Наименование района местонахождения теплопровода
#    'number': 'nomer_nas_agregata',   #  Номер насосного агрегата
    'thrust': 'h',   #  Заданный рабочий напор
#    'standardPumpID': 'tip_nas',   #  Тип насосного агрегата
#    'parallAgregCount': 'k_nas',   #  Количество параллельно включенных агрегатов в группе
#    'parallAgregCount': 'k_nas',   #  Количество параллельно включенных агрегатов в группе
#    'driveTypeID': 'pr_privod',   #  Привод
#    'rotorDiameterTypeID': 'pr_diametr',   #  Диаметр рабочего колеса
#    'standardEMID': 'tip_el',   #  Тип установленного электродвигателя
#    'r0': 'r0',   #  Коэффициент  апроксимации R0 характеристики напора H(G)
#    'r1': 'r1',   #  Коэффициент  апроксимации R1 характеристики напора H(G)
#    'r2': 'r2',   #  Коэффициент  апроксимации R2 характеристики напора H(G)
#    'e0': 'e0',   #  Коэффициент  апроксимации E0 характеристики мощности N(G)
#    'e1': 'e1',   #  Коэффициент  апроксимации E1 характеристики  мощности N(G)
#    'e2': 'e2',   #  Коэффициент  апроксимации E2 характеристики  мощности N(G)
#    'k0': 'k0',   #  Коэффициент  апроксимации K0 характеристики КПД K(G)
#    'k1': 'k1',   #  Коэффициент  апроксимации K1 характеристики КПД K(G)
#    'k2': 'k2',   #  Коэффициент  апроксимации K2 характеристики КПД K(G)
    'r0_z': 'r0_z',   #  Коэффициент  апроксимации R0 характеристики напора H(G)
    'r1_z': 'r1_z',   #  Коэффициент  апроксимации R1 характеристики напора H(G)
    'r2_z': 'r2_z',   #  Коэффициент  апроксимации R2 характеристики напора H(G)
#    'e0_z': 'e0_z',   #  Коэффициент  апроксимации E0 характеристики мощности N(G)
#    'e1_z': 'e1_z',   #  Коэффициент  апроксимации E1 характеристики  мощности N(G)
#    'e2_z': 'e2_z',   #  Коэффициент  апроксимации E2 характеристики  мощности N(G)
#    'k0_z': 'k0_z',   #  Коэффициент  апроксимации K0 характеристики КПД K(G)
#    'k1_z': 'k1_z',   #  Коэффициент  апроксимации K1 характеристики КПД K(G)
#    'k2_z': 'k2_z',   #  Коэффициент  апроксимации K2 характеристики КПД K(G)
#    'rotorRotSpeedSet': 'rate_zad',   #  Частота вращения рабочего колеса заданная
#    'rotorDiameterSet': 'd_zad',   #  Диаметр рабочего колеса заданный
#    'lastPumpReplaceDate': 'dateend_nasos',   #  Дата последней замены  насоса
#    'lastEMreplaceDate': 'dateend_electric',   #  Дата последней замены электродвигателя
#    'lastAgregReplaceDate': 'dateend_pump',   #  Дата последней замены насосного агрегата
#    'repairCountPump': 'kol_nasos',   #  Количество ремонтов насоса с начала эксплуатации
#    'replaceCountAgreg': 'kol_pump',   #  Количество замен насосного агрегата
#    'repairCountEM': 'kol_electric',   #  Количество ремонтов электродвигателя с начала эксплуатации
#    'opc': 'opc',   #  NULL
    'stateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_pressRegulators = {
    'valveHydroResOpen': 'min_sm',   #  Гидравлическое   сопротивление    клапана   в    открытом  состоянии
    'valveHydroResClose': 'max_sm',   #  Гидравлическое   сопротивление    клапана   в   закрытом  состоянии
    'regValveRelCap': 'kv',   #  Пропускная  способность  регулирующего  клапана
    'relLeakage': 'otn_kv',   #  Относительная   протечка   в   %   от  KV (негерметичность  затвора)
    'consDrip': 'g_tep_poteri',   #  Расход на слив
    'workAttrID': 'pr_raboti',   #  Период работы
    'deltaH': 'delta',   #  Допустимое  отклонение  напора  от  заданного  значения
    'regulatorStateID': 'sost',   #  Состояние
    'nodeID': 'nodeID',   #  
    'h': 'h_uzu',   #  Значение  регулируемого  напора
    'pipelineSignID': 'przu',   #  Признак  трубопровода узла с регулируемым напором
}

#-----------------------------------------------

tab_consumptRegulators = {
    'regConsMean': 'q_zad',   #  Значение регулируемого  расхода
    'workAttrID': 'pr_raboti',   #  Период работы
    'hydroResOpen': 'min_sm',   #  Гидравлическое сопротивление клапана в открытом  состоянии
    'hydroResClose': 'max_sm',   #  Гидравлическое сопротивление клапана в закрытом  состоянии
    'regValveCap': 'kv',   #  Пропускная способность регулирующего клапана
    'relatLeakage': 'otn_kv',   #  Относительная протечка в % от KV(негерметичность  затвора)
    'plumsConsumption': 'g_tep_poteri',   #  Расход на слив
#    'opc': 'opc',   #  NULL
    'deltaH': 'delta',   #  Допустимое отклонение расхода от заданного значения
    'regulatorStateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_dampers = {
    'dispatcherSwitch': 'name_zd',   #  Место установки
    'diameterCondit': 'diametr',   #  Диаметр условный
    'partDempOpen': 'proz_kv',   #  Частичное открытие задвижки в % от KV
    'name': 'name',   #  Содержательное наименование
    'standardDampLink': 'name_zc',   #  Тип задвижки
    'turnCount': 'obor',   #  Фактическое количество оборотов маховика
    'gateControl': 'zemla',   #  Признак возможности управления затвором с поверхности земли
    'clue': 'kluch',   #  Возможность закрытия ключом
    'thrustCollar': 'kolza',   #  Наличие упорных колец
    'relatLeakage': 'otn_kv',   #  Относительная протечка в % от KV (негерметичность затвора)
    'opc': 'opc',   #  NULL
    'damperArmatureStateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_regulArmatures = {
    'regPDmean': 'q_zad',   #  NULL
    'diameterCondit': 'diametr',   #  Диаметр условный
    'name': 'name',   #  Содержательное наименование
    'regArmType': 'tip_armatur',   #  Вид арматуры
    'regArmSign': 'name_zc',   #  Тип арматуры
    'damperOpenDeg': 'proz_kv',   #  Степень открытие арматуры в % от KV
    'rotationCount': 'obor',   #  Фактическое количество оборотов маховика
    'gateControl': 'zemla',   #  Признак возможности управления затвором с поверхности земли
    'clue': 'kluch',   #  Возможность закрытия ключом
    'thrustCollar': 'kolza',   #  Наличие упорных колец
    'relLeakage': 'otn_kv',   #  Относительная протечка в % от KV (негерметичность затвора)
    'opc': 'opc',   #  NULL
    'deltaH': 'delta',   #  NULL
    'deltaQ': 'delta_q',   #  NULL
    'q': 'q_uzu',   #  NULL
    'damperArmatureStateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_bypass = {
    'pipelineSignID': 'przu',   #  Признак теплопровода с  регулируемым   напором
    'standardID': 'standard',   #  Стандарт труб на участке
    'standardTubeLink': 'kod_truba',   #  Ссылка на стандартную трубу
    'length': 'dln',   #  Длина
    'diameterInternal': 'diam',   #  Внутренний диаметр
    'tubeRoughness': 'scher',   #  Эквивалентная шероховатость  трубы
    'resCoeffsSum': 'sum_m_s',   #  Сумма коэффициентов местных сопротивлений
    'locInstall': 'ustanovka',   #  Место установки
    'deltaH': 'delta',   #  NULL
    'deltaQ': 'delta_q',   #  Допустимое отклонение расхода от требуемого
    'nodeID': 'nodeID',   #  
    'h': 'h',   #  Значение регулируемого напора
    'q': 'q',   #  Значение регулируемого расхода
    'regulatorStateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_diaphragms = {
    'throtDiaphLoc': 'name_mesto',   #  Место установки
    'diameterInternal': 'dru_home',   #  Внутренний диаметр диафрагмы
    'consInstDiaphCount': 'kol_home',   #  Количество последовательно установленных диафрагм
    'entryMark': 'name_home',   #  Признак изпользования рассчитанной диафрагмы
    'stateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_elevators = {
    'elevatorType': 'nomer_elv',   #  Тип элеватора
    'elevatorNumInst': 'a5',   #  Номер элеватора, установленный
    'diameterNozzle': 'du_elevat',   #  Диаметр сопла элеватора, установленный
    'entryMark': 'pr_elevat',   #  Признак изпользования рассчитанного элеватора
    'diameterChamber': 'd_chamber',   #  Диаметр камеры смешения (горловины),
    'length': 'dlina',   #  Длина корпуса
    'diameterInletFlange': 'd_entry',   #  Диаметр входного фланца
    'diameterOutletFlange': 'd_exit',   #  Диаметр выходного фланца
    'diameterSuctionPipe': 'd_infiltration',   #  Диаметр фланца патрубка подсоса
    'material': 'material',   #  Материал корпуса
    'stateID': 'sost',   #  NULL
}

#-----------------------------------------------

tab_systemRadiators = {
    'name': 'name_ra',   #  Наименование отопительного прибора конвективно-излучающего типа
    'type': 'typ_ra',   #  Тип прибора
    'count': 'kol_ra',   #  Количество приборов
    'totalEquivSurface': 'f_ra',   #  Суммарная эквивалентная поверхность нагрева приборов
    'stateID': 'sost',   #  NULL
}

#-----------------------------------------------

tab_heatExchangers = {
    'heatExchType': 'tip_to',   #  Тип теплообменника
    'heatExchCode': 'kod_to',   #  Выбор типоразмера теплообменника
    'location': 'mesto',   #  Функциональное назначение
    'stateID': 'sost',   #  NULL
}

#-----------------------------------------------

tab_airHeaters = {
    'fanInstall': 'ventilator',   #  Признак установки вентилятора
    'scheme': 'cxema',   #  Схема соединения калориферов
    'airHeatersCount': 'kol_radiator',   #  Количество калориферов в ряду
    'rowsCount': 'kol_row',   #  Количество рядов
    'storesCount': 'kol_stor',   #  Количество этажей
    'airHeaterType': 'name_kl',   #  Тип калорифера
    'contaminCoeff': 'mud',   #  Коэффициент загрязнения калориферов
    'pressCoeff': 't_napor',   #  Поправочный коэффициент снижения температурного напора
    'location': 'mesto',   #  Функциональное назначение
}

#-----------------------------------------------

tab_pressDropRegulators = {
    'pressDropMean': 'h_regular',   #  NULL
    'regValveHydroRes': 'sm',   #  Гидравлическое   сопротивление    клапана   регулятора
    'consThroughRegValve': 'g',   #  Расход через  клапан регулятора
    'thrustDropMean': 'h_fakt',   #  Полученное значение перепада напора
    'regValveRelCap': 'kv',   #  Условная пропускная  способность  регулирующего  клапана  регулятора
    'maxLeakageCloseValve': 'otn_kv',   #  Относительная  протечка   через закрытый клапан (негерметичность  затвора)
    'consDrip': 'g_tep_poteri',   #  Расход на слив
    'workAttrID': 'pr_raboti',   #  Период работы
    'deltaH': 'delta',   #  Допустимое  отклонение  перепада давления от  заданного  значения
    'regulatorStateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_reverseValves = {
    'hydroResOpen': 'min_sm',   #  Гидравлическое   сопротивление    клапана   в    открытом  состоянии
    'hydroResClose': 'max_sm',   #  Гидравлическое   сопротивление    клапана   в    закрытом  состоянии
    'locInstall': 'ustanovka',   #  Место установки обратного клапана
    'standardRevValveID': 'name_zc',   #  Тип обратного клапана, ссылка на стандартный обратный клапан
    'standardID': 'standard',   #  Стандарт труб на участке теплопровода
    'tubeID': 'kod_truba',   #  Ссылка на стандартную трубу
    'pipelineLength': 'dln',   #  Длина теплопровода
    'diameterInternal': 'diam',   #  Внутренний диаметр теплопровода
    'tubeRoughness': 'scher',   #  Эквивалентная  шероховатость  трубы теплопровода
    'resCoeffsSum': 'sum_m_s',   #  Сумма  коэффициентов  местных  сопротивлений участка теплопровода
    'revValveCap': 'kv',   #  Пропускная способность обраного клапана
    'relatLeakage': 'otn_kv',   #  Относительная протечка в % от KV (негерметичность затвора)
    'stateID': 'sost',   #  Состояние
}

#-----------------------------------------------

tab_generalizedConsumers = {
#    'quarter': 'kvartal',   #  Квартал
    'name': 'name_building',  # Содержательное наименование

    'maxBuildingHeight': 'h',   #  Наибольшая высота здания
    'accumCoeff': 'k_akkuml',   #  Коэффициент аккумуляции здания
    'hydroModeSignID': 'pr_avar_TP',   #  Признак расчета аварийного режима потребителя
    'specExpendID': 'kodur',   #  Код удельных расходов тепло/вода
    'calcTemperatureID': 'kodtr',   #  Код расчетных температур
    'gvsLoadGraphID': 'kod_gvs',   #  Код графика суточного нагрузки ГВ
    'varCoeffID': 'kodkv',   #  Код группы коэффициентов вариации
    'normHLosFlow': 'tpotepi__pod',   #  Норм.тепловые потери в подающем теплопроводе распр.сети
    'normHLosRet': 'tpotepi__obr',   #  Норм.тепловые потери в обратном теплопроводе распр.сети
    'calcHLdep': 'otopl_zco',   #  Расчетная тепловая нагрузка на  отопление
    'calcInternHDdep': 'otopl_tp_zco',   #  Расчетные внутренние тепловыделения
#    'adjCalcHLdep': 'f_otopl_zco',   #  Договорная нагрузка на  отопление
#    'adjCalcHDdep': 'f_otopl_tp_zco',   #  Договорные внутренние тепловыделения
#    'perspCalcHLdep': 'p_otopl_zco',   #  Перспективная нагрузка на  отопление
#    'perspCalcInternHDdep': 'p_otopl_tp_zco',   #  Перспективные внутренние тепловыделения
    'calcTempDep': 'Tr_tv_co_zco',   #  Расчетная температура воздуха в отапливаемых помещениях
    'connectionSchemeID': 'cx_zco',   #  Схема присоединения СО
    'mixFactCoeffDep': 'uf_zco',   #  Фактический коэффициент смешения
    'calcHLindep': 'otopl_nco',   #  Расчетная тепловая нагрузка на  отопление
    'calcInternHDindep': 'otopl_tp_nco',   #  Расчетные внутренние тепловыделения
#    'adjCalcHLindep': 'f_otopl_nco',   #  Договорная тепловая нагрузка на  отопление
#    'adjCalcInternHDindep': 'f_otopl_tp_nco',   #  Договорные внутренние тепловыделения
#    'perspCalcHLindep': 'p_otopl_nco',   #  Перспективная тепловая нагрузка на  отопление
#    'perspCalcInternHDindep': 'p_otopl_tp_nco',   #  Перспективные внутренние тепловыделения
    'calcTempIndep': 'Tr_tv_co_nco',   #  Расчетная температура воздуха в отапливаемых помещениях
    'mixFactCoeffIndep': 'uf_nco',   #  Фактический коэффициент смешения
    'calcHLventil': 'ventil_cv',   #  Расчетная тепловая нагрузка  на вентиляцию
#    'adjCalcHLventil': 'f_ventil_cv',   #  Договорная нагрузка  на вентиляцию
#    'perspCalcHLventil': 'p_ventil_cv',   #  Перспективная нагрузка  на вентиляцию
    'calcHLcond': 'kondiz',   #  Расчетная тепловая нагрузка на кондиционирование
#    'adjCalcHLcond': 'f_kondiz',   #  Договорная нагрузка на кондиционирование
#    'perspCalcHLcond': 'p_kondiz',   #  Перспективная нагрузка на кондиционирование
    'calcHLcloseSys': 'txz',   #  Расчетная тепловая нагрузка на технологию в закрытой системе
    'calcHLopenSysFlow': 'txop',   #  Средняя нагрузка на технологию в открытой системе из подающего теплопровода
    'calcHLopenSysRet': 'txoo',   #  Средняя нагрузка на технологию в открытой системе из обратного теплопровода
#    'adjCalcHLcloseSys': 'f_txz',   #  Договорная нагрузка на технологию в закрытой системе
#    'adjCalcHLopenSysFlow': 'f_txop',   #  NULL
#    'adjCalcHLopenSysRet': 'f_txoo',   #  NULL
#    'perspCalcHLcloseSys': 'p_txz',   #  Перспективная нагрузка на технологию в закрытой системе
#    'perspCalcHLopenSysFlow': 'p_txop',   #  NULL
#    'perspCalcHLopenSysRet': 'p_txoo',   #  NULL
    'expendHWpart': 'dolja_vent_cv',   #  Доля расхода сет.воды  через КУ от расчётного, при откл.её  по воздуху
    'calcTempHA': 'Tr_tv_cv',   #  Расчетная температура нагретого воздуха
    'calcHLparall': 'otopl_pr',   #  Расчетная тепловая нагрузка на отопление
    'internHDparall': 'otopl_tp_pr',   #  Внутренние тепловыделения
#    'adjCalcHLparall': 'f_otopl_pr',   #  Договорная нагрузка на отопление
#    'adjInternHDparall': 'f_otopl_tp_pr',   #  Договорные внутренние тепловыделения
#    'perspCalcHLparall': 'p_otopl_pr',   #  Перспективная нагрузка на отопление
#    'perspInternHDparall': 'p_otopl_tp_pr',   #  Перспективные внутренние тепловыделения
    'schemeParallID': 'cx_co_pr',   #  Схема присоединения СО
    'calcHLGVSparall': 'gv_pr',   #  Средняя тепловая нагрузка на ГВС
#    'adjCalcHLGVSparall': 'f_gv_pr',   #  NULL
#    'perspCalcHLGVSparall': 'p_gv_pr',   #  NULL
    'hourIrregCoeffParall': 'gvs_max_pr',   #  Коэффициент часовой неравномерности нагрузки ГВС
    'avgHLcompParall': 'rez_pr',   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    'tempRecircPipeParall': 'T_pot_rez_pr',   #  Температура в рециркуляционном трубопроводе ГВС
    'calcTempHRparall': 'Tr_tv_co_pr',   #  Расчетная температура воздуха в отапливаемых помещениях
    'calcTempHWDOparall': 'Tr_gvs_pr',   #  Расчетная температура горячей воды в местах водоразбора
    'AMRdepParall': 'uf_zco_pr',   #  Фактический коэффициент смешения СО
    'calcHLmix': 'otopl_sm',   #  Расчетная тепловая нагрузка на  отопление
    'internHDmix': 'otopl_tp_sm',   #  Внутренние тепловыделения
#    'adjCalcHLmix': 'f_otopl_sm',   #  Договорная тепловая нагрузка на  отопление
#    'adjInternHDmix': 'f_otopl_tp_sm',   #  Договорные внутренние тепловыделения
#    'perspCalcHLmix': 'p_otopl_sm',   #  Перспективная тепловая нагрузка на  отопление
#    'perspInternHDmix': 'p_otopl_tp_sm',   #  Перспективные внутренние тепловыделения
    'schemeMixID': 'cx_co_sm',   #  Схема присоединения системы отопления
    'calcHLGVSmix': 'gv_sm',   #  Средняя тепловая нагрузка на ГВС.
#    'adjCalcHLGVSmix': 'f_gv_sm',   #  NULL
#    'perspCalcHLGVSmix': 'p_gv_sm',   #  NULL
    'hourIrregCoeffMix': 'gvs_max_sm',   #  Коэффициент часовой неравномерности нагрузки ГВС
    'avgHLcompMix': 'rez_sm',   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    'tempRecircPipeMix': 'T_pot_rez_sm',   #  Температура в рециркуляционном трубопроводе ГВС
    'calcTempHRmix': 'Tr_tv_co_sm',   #  Расчетная температура воздуха  в отапливаемых помещениях
    'calcTempHWDOmix': 'Tr_gvs_sm',   #  Расчетная температура горячей воды в местах водоразбора
    'AMRdepMix': 'uf_zco_sm',   #  Фактический коэффициент смешения зависимой СО
    'calcHLconseq': 'otopl_ps',   #  Расчетная тепловая нагрузка на  отопление
    'internHDconseq': 'otopl_tp_ps',   #  Внутренние тепловыделения
#    'adjCalcHLconseq': 'f_otopl_ps',   #  Договорная нагрузка на  отопление
#    'adjInternHDconseq': 'f_otopl_tp_ps',   #  Договорные внутренние тепловыделения
#    'perspCalcHLconseq': 'p_otopl_ps',   #  Перспективная нагрузка на  отопление
#    'perspInternHDconseq': 'p_otopl_tp_ps',   #  Перспективные внутренние тепловыделения
    'schemeConseqID': 'cx_co_ps',   #  Схема присоединения системы отопления
    'calcHLGVSconseq': 'gv_ps',   #  Средняя тепловая нагрузка на ГВС
#    'adjCalcHLGVSconseq': 'f_gv_ps',   #  NULL
#    'perspCalcHLGVSconseq': 'p_gv_ps',   #  NULL
    'hourIrregCoeffConseq': 'gvs_max_ps',   #  Коэффициент часовой неравномерности нагрузки ГВС
    'avgHLcompconseq': 'rez_ps',   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    'tempRecircPipeConseq': 'T_pot_rez_ps',   #  Температура в рециркуляционном трубопроводе ГВС
    'calcTempHRconseq': 'Tr_tv_co_ps',   #  Расчетная температура воздуха в отапливаемых помещениях
    'calcTempHWDOconseq': 'Tr_gvs_ps',   #  Расчетная температура горячей воды в местах водоразбора
    'AMRdepConseq': 'uf_zco_ps',   #  Фактический коэффициент смешения зависимой СО
    'calcHLpreON': 'otopl_pw',   #  Расчетная тепловая нагрузка на  отопление
    'internHDpreON': 'otopl_tp_pw',   #  Внутренние тепловыделения
#    'adjCalcHLpreON': 'f_otopl_pw',   #  Договорная нагрузка на  отопление
#    'adjInternHDpreON': 'f_otopl_tp_pw',   #  Договорные внутренние тепловыделения
#    'perspCalcHLpreON': 'p_otopl_pw',   #  Перспективная нагрузка на  отопление
#    'perspInternHDpreON': 'p_otopl_tp_pw',   #  Перспективные внутренние тепловыделения
    'schemePreONID': 'cx_co_pw',   #  Схема присоединения системы отопления
    'calcHLGVSpreON': 'gv_pw',   #  Средняя тепловая нагрузка на ГВС
#    'adjCalcHLGVSpreON': 'f_gv_pw',   #  NULL
#    'perspCalcHLGVSpreON': 'p_gv_pw',   #  NULL
    'hourIrregCoeffPreON': 'gvs_max_pw',   #  Коэффициент часовой неравномерности нагрузки ГВС
    'avgHLcompPreON': 'rez_pw',   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    'tempRecircPipePreON': 'T_pot_rez_pw',   #  Температура в рециркуляционном трубопроводе ГВС
    'calcTempHRpreON': 'Tr_tv_co_pw',   #  Расчетная температура воздуха в отапливаемых помещениях
    'calcTempHWDOpreON': 'Tr_gvs_pw',   #  Расчетная температура горячей воды в местах водоразбора
    'AMRdepPreON': 'uf_zco_pw',   #  Фактический коэффициент смешения зависимой СО
    'avgHLGVSopenSysFlow': 'gv_op',   #  Средняя тепловая нагрузка на ГВС, подающий трубопровод
    'avgHLGVSopenSysRet': 'gv_oo',   #  Средняя тепловая нагрузка на ГВС, обратный трубопровод
#    'adjAvgHLGVSopenSysFlow': 'f_gv_op',   #  NULL
#    'adjAvgHLGVSopenSysRet': 'f_gv_oo',   #  NULL
#    'perspAvgHLGVSopenSysFlow': 'p_gv_op',   #  NULL
#    'perspAvgHLGVSopenSysRet': 'p_gv_oo',   #  NULL
    'hourIrregCoeffOpen': 'gvs_max_o',   #  Коэффициент часовой неравномерности нагрузки ГВС
    'avgHLcompOpen': 'rez_op',   #  Расчетные тепловые потери в рециркуляц. контуре ГВС
    'tempRecircPipeOpen': 'T_pot_rez_op',   #  Температура в рециркуляционном трубопроводе ГВС
    'calcTempHWDOopen': 'Tr_gvs_oo_op',   #  Расчетная температура горячей воды в местах водоразбора, откр.ГВС
    'PDvalveInstallLocID': 'pr_per_PD',   #  Место установки клапана перепада давления
    'setPDonRegulator': 'p_per_PD',   #  Заданный перепад давления на регуляторе перепада
    'setLeakageFlow': 'utechp',   #  Заданная утечка из подающего трубопровода
    'setLeakageRet': 'utecho',   #  Заданная утечка из обратного  трубопровода
    'WEmeteringDeviceID': 'pr_uchet',   #  Признак установки прибора учета
    'volWaterHS': 'a24',   #  Удельный объем воды в системе отопления
    'volWaterVS': 'a25',   #  Удельный объем воды в системе вентиляции
    'minThrustDS': 'p_min',   #  Мин.располагаемый напор в распред.сетях
    'hydroResCloseSys': 'gsz',   #  Гидравл.сопротивление закрыт.системы теплопотребления
    'hydroResCloseSysSummer': 'gszl',   #  Гидр.сопротивление закрыт.систем  в летний период
    'closeSysCalcSignID': 'gszpr',   #  Признак расчета гидравл.сопротивл. в закр.системе
    'hydroResWDOFlow': 'gsop',   #  Гидравл.сопротивл.откр.ГВС, подающ.трубопр.
    'calcSignOpenSysFlowID': 'gsoppr',   #  Признак расчета гидравл.сопротивл.откр. ГВС, подающ.трубопров.
    'hydroResWDORet': 'gsoo',   #  Гидравл.сопрот.откр.ГВС, при водоразборе из обратн.труб.
    'calcSignResWDORetID': 'gsoopr',   #  Признак расчета гидравл.сопротивл.откр. ГВС, обрат.трубопров
    'calcSignSetLoadCloseSys': 'prznz',   #  Признак расчета на заданную нагрузку в закр.системах теплопотр.
    'calcSignSetLoadOpenSysFlow': 'prznp',   #  Признак расчета на  заданную нагрузку  откр. ГВС, под.трубопр.
    'calcSignSetLoadOpenSysRet': 'przno',   #  Признак расчета на  заданную нагрузку  откр. ГВС, обр.трубопр.
    'hydroThrustIn': 'pP',   #  Пьезом.напор на входе теплового пункта, плановый режим
    'hydroThrustOut': 'pO',   #  Пьезом.напор на выходе теплового пункта, плановый режим

    'calcExpendDep': 'GG_otoplz',   #  Расчетный расход на  отопление
    'calcExpendIndep': 'GG_otopln',   #  Расчетный расход на  отопление
    'calcExpendVentil': 'GG_ventil',   #  Расчетный расход на  вентиляцию
    'calcExpendCond': 'GG_kondiz',   #  Расчетный расход на  кондиционирование
    'calcExpendHWFlow': 'GG_gvop',   #  Расчетный расход на горячее водоснабжение
    'calcExpendHWRet': 'GG_gvoo',   #  Расчетный расход на ГВС, в открытой системе
    'calcExpendRecircOpen': 'GG_rez',   #  Расчетный расход на рециркуляцию в открытой ГВС
    'calcExpendHWparall': 'GG_gvpr',   #  Расчетный расход на горячее водоснабжение
    'calcExpendHWmix': 'GG_gvsm',   #  Расчетный расход на горячее водоснабжение
    'calcExpendHWconseq': 'GG_gvps',   #  Расчетный расход на горячее водоснабжение
    'calcExpendHWpreON': 'GG_gvpw',   #  Расчетный расход на горячее водоснабжение

    'calcThrustInWSD': 'a12',   #  Расчетный напор на входе водоразборных приборов
    'consumerStateID': 'sost',   #  Состояние потребителя
}

#-----------------------------------------------

tab_heatSources = {
    'sourceName': 'kod_ist',   #  Код теплогенерирующей установки источника тепла
    'name': 'name_ist',   #  Наименование источника тепла
    'stateID': 'sost',   #  Состояние теплогенерирующей установки источника тепла
#    'hSourceTypeID': 'tip',   #  Тип источника теплоснабжения
#    'hSourceTypeID': 'tip',   #  Тип графика
#    'hSourcePower': 'n_rasp',   #  Располагаемая тепловая мощность
#    'hSourcePowerInst': 'n_ustan',   #  Установленная мощность
#    'hSeasonBeginDate': 'begin_year',   #  Дата начала отопительного периода
#    'hSeasonEndDate': 'end_year',   #  Дата окончания отопительного периода
    'temperDWflowSummer': 't1_leto',   #  Температура сетевой воды в подающем трубопроводе в летний период
    'temperDWretSummer': 't2_leto',   #  Температура сетевой воды в обратном трубопроводе в летний период
#    'specVolHS': 'a24',   #  Уд.объем воды в системе отопления обобщенного потребителя
#    'specVolVent': 'a25',   #  Уд.объем воды в системе вентиляции обобщенного потребителя
#    'expendDWnorm1': 'G1n_ist_1',   #  Нормативный расход сетевой воды на выводе источника тепла
#    'expendDWnorm2': 'G1n_ist_2',   #  Нормативный расход сетевой воды на выводе источника тепла
#    'expendDWnorm3': 'G1n_ist_3',   #  Нормативный расход сетевой воды на выводе источника тепла
#    'expendDWnorm4': 'G1n_ist_4',   #  Нормативный расход сетевой воды на выводе источника тепла
#    'expendDWnorm5': 'G1n_ist_5',   #  Нормативный расход сетевой воды на выводе источника тепла
#    'managerPhone': 'phone_manager',   #  Телефон/факс руководителя
#    'controllerPhone': 'phone_controller',   #  Телефон/факс диспетчера
#    'powerSet': 'Тепловая',   #  мощность установленная NULL
#    'powerSet': 'Тепловая',   #  мощность установленная NULL
#    'powerAvailable': 'Тепловая',   #  мощность располагаемая NULL
#    'powerAvailable': 'Тепловая',   #  мощность располагаемая NULL
#    'heightTubeMark': 'Высотная',   #  отметка оси трубы  NULL
#    'heightAreaMark': 'Высотная',   #  отметка местности  NULL
#    'repairWorks': 'Ремонтные',   #  работы    NULL

#---------------------------

#    'year': 'year',  # Календарный год
    'name': 'name',  # Наименование температурного графика
    'tn_1': 'tn_1',  # Температура наружного воздуха начала/конца отопительного сезона
    'tn_5': 'tn_5',  # Расчетная температура наружного воздуха для отопления
    'tvn_r': 'tvn_r',  # Расчетная температура воздуха внутри отапливаемых помещений
    't1_r': 't1_r',  # Расчетная температура сетевой воды в подающем теплопроводе
    't2_r': 't2_r',  # Расчетная температура сетевой воды в обратном трубопроводе
    't3_r': 't3_r',  # Расчетная температура сетевой воды после узла смешения
    'q_r': 'q_r',  # Расчетная тепловая нагрузка на отопление
    't1_2r': 't1_2r',  # Температура сетевой воды нижней срезки графика
    't1_4r': 't1_4r',  # Температура сетевой воды верхней срезки графика
    'tvb_tr': 'tvb_tr',  # Требуемая температура воздуха внутри отапливаемых помещений
    'uf': 'uf',  # Фактический коэффициент смещения
    't2_2r': 't2_2r',  # Температура сетевой воды нижней срезки обратной воды
    'q_gv': 'q_gv',  # Расчетная тепловая нагрузка на горячее  водоснабжение
    'tg_r': 'tg_r',  # Температура горячей воды в точках водоразбора
    'tx_r': 'tx_r',  # Температура холодной воды
    't2_gv': 't2_gv',  # Температура воды в обратном трубопроводе для переключения водоразбора
    'pr': 'pr',  # Признак способа водоразбора горячей воды: c переключением,из подающего, из обратного, из обоих
    'g1': 'g1',  # Коэффициент гидравлической устойчивости подающего трубопровода
    'g2': 'g2',  # Коэффициент гидравлической устойчивости обратного трубопровода
    't_gv1': 't_gv1',  # Величина недогрева в первой ступени подогревателя
    'v': 'v',  # Скорость ветра
    'date_on': 'date_on',  # Дата иcполнения
    'name_exe': 'name_exe',  # Исполнитель
    'name_manager': 'name_manager',  # NULL
    'dt2_co': 'dt2_co',  # Разница между расч.обратными температурами после  незав. и зависимой СО
    't2pod_parl': 't2pod_parl',  # Температура сет. воды в т.изл. темп.графика после подогревателя ГВ, при парал. схеме ГВ
    'dt2v_sm_noavm': 'dt2v_sm_noavm',  # Недогрев водопров.воды до обратной после СО, при частично автомат.смеш. схеме ГВ
    'dt2v_sm_avm': 'dt2v_sm_avm',  # Недогрев водопров.воды до обратной после СО,  при автоматизир. смеш. схеме ГВ
    't1pod_sm': 't1pod_sm',  # Температура обратной  воды после СО в т.излома темп.графика, при смешанной схеме ГВ
    't1pod_posll': 't1pod_posll',  # Температура обратной  воды после СО в т.излома темп.графика, при последовательной схеме ГВ
    'dt2v_posl': 'dt2v_posl',  # Недогрев водопроводной воды до обратной из СО, при последовательной схеме ГВ


}

#-----------------------------------------------

tab_pumpStations = {
#    'name': 'Наименование',   #  NULL
#    'purpose': 'Назначение',   #  NULL
#    'capacity': 'Производительность',   #  NULL
#    'pumpCountFlow': 'Количество',   #  насосов на подаче    NULL
#    'pumpCountRet': 'Количество',   #  насосов на обратке   NULL
    'state': 'sost',   #  Состояние насосной станции
#    'heightTubeMark': 'Высотная',   #  отметка оси трубы  NULL
#    'heightAreaMark': 'Высотная',   #  отметка местности  NULL
}


# Узел подпитки

tab_refillNodes = {
    'refillExpend': 'r_p',  # Расход  на  подпитку
    'WDO': 'r_v',  # Расход на водоразбор
    'refillLoss': 'r_ut',  # Расход подпитки  в % отношении от общей суммы утечки
    'diameterInternal': 'diam',  # Внутренний диаметр бака
    'waterVolUp': 'urov_v',  # Верхний допустимый уровень воды в баке
    'waterVolDown': 'urov_n',  # Нижний допустимый уровень воды в баке
    'waterVolUpSet': 'urov_z',  # Заданный уровень воды в баке
    'potsCount': 'kol',  # Количество  баков
    'potsSumVol': 'v_sum',  # Суммарный  объём  баков-аккумуляторов
    'potWorkingSign': 'prz_r',  # Признак режима  работы бака
    'chargeExpend': 'r_z',  # Расход  на  зарядку
    'dischargeExpend': 'r_r',  # Расход  на  разрядку
    'setPressRet': 'napor',  # Заданный напор в обратном теплопроводе
}


tab_WDOdevices = {
    'WDO': 'r_v',  # Водоразбор
    'hydroRes': 'sopr',  # Гидр.сопротивление полностью откр.прибора
}



#-----------------------------------------------

tab_threeWayValves = {
#    'structure': 'structure',   #  Структурированное описание
    'state': 'sost',   #  Состояние клапана
#    'purpose': 'prz_klan',   #  Назначение
#    'calcMixFactCoeff': 'u',   #  Расчетный коэффициент смешения
#    'calcThrustLos': 'dP_pot',   #  Расчетные потери напора в регулируемом контуре
#    'expendCharStraight': 'h_1',   #  Расходная характеристика прямого хода
#    'expendCharVert': 'h_2',   #  Расходная характеристика вертикального хода
#    'authority': 'A_treb',   #  Требуемый авторитет клапана
#    'calcCapDeviation': 'k_kvs_treb',   #  Отклонение расчетной пропускной способности от требуемой
#    'type': 'tip_klap',   #  Марка клапана
#    'capacity': 'kv_s',   #  Расчетная пропускная способность
#    'regulator': 'organ',   #  Регулирующий орган
#    'maxPD': 'dP',   #  Допустимый перепад давления на клапане
#    'diameterNomin': 'DN',   #  Диаметр номинальный
#    'calcExpendNodeMix': 'Gmax',   #  Расчетный расход на регулируемом участке
#    'pumpStationName': 'name_nas_stanzii',   #  Наименование района местонахождения теплопровода
}

tab_varCoefficients = {
    'kodkv': 'kodkv',   #  Код группы коэффициентов вариации
    'kvpot': 'kvpot',   #  Коэффициент вариации нагрузки по всем видам теплопотребления
    'otoplz': 'otoplz',   #  Коэффициент вариации нагрузки на отопление, зависимая схема
    'otopln': 'otopln',   #  Коэффициент вариации  нагрузки на отопление, независимая схема
    'ventil': 'ventil',   #  Коэффициент вариации нагрузки на вентиляцию
    'kondiz': 'kondiz',   #  Коэффициент вариации нагрузки  на кондиционирование
    'txz': 'txz',   #  Коэффициент вариации нагрузки на  технологические процессы в закрытой системе
    'txop': 'txop',   #  Коэффициент вариации нагрузки на технологические процессы из подающего трубопровода
    'txoo': 'txoo',   #  Коэффициент вариации нагрузки на технологические процессы из обратного трубопровода
    'gvz': 'gvz',   #  Коэффициент вариации нагрузки на горячее водоснабжение в закрытой  системе
    'gvop': 'gvop',   #  Коэффициент вариации нагрузки на горячее водоснабжение из подающего трубопровода
    'gvoo': 'gvoo',   #  Коэффициент вариации нагрузки на горячее водоснабжение из обратного трубопровода
    'ut': 'ut',   #  Коэффициент вариации значений  расходов на утечку  в узлах расчетной схемы
    'cher': 'cher',   #  Изменение значений эквивалентной шероховатости участка
    'diam': 'diam',   #  Изменение  значений  диаметров  труб  участка
}

#-----------------------------------------------

tab_calcTemperatures = {
    'calcTemperatureID': 'kodtr',  # Код расчетных температур
    'Tx': 'Tx',  # Расчетная температура холодной водопроводной воды
    'Tn_r': 'Tn_r',  # Расчетная температура наружного воздуха для отопления
    'Tn_r_v': 'Tn_r_v',  # Расчетная температура  наружного воздуха для вентиляции и воздушного отопления
    'tn_isl': 'tn_isl',  # Температура наружного воздуха излома температурного графика
    'T1_isl_2stup': 'T1_isl_2stup',  # Расчетная температура сет.воды на входе ТП  в т.изл.темп. граф.
    'Tr_co_1_zco': 'Tr_co_1_zco',  # Расчетная температура сет.воды в подающем трубопроводе, зависимой СО
    'Tr_co_2_zco': 'Tr_co_2_zco',  # Расчетная температура  сет.воды в обратном  трубопроводе, зависимой СО
    'Tr_co_3_zco': 'Tr_co_3_zco',  # Расчетная температура сет.воды после узла смешения, зависимой СО
    'Tr_to_1_nco': 'Tr_to_1_nco',  # Расчетная температура сет.воды на входе подогревателя, незав.СО
    'Tr_to_2_nco': 'Tr_to_2_nco',  # Расчетная температура сет.воды на выходе подогревателя, незав.СО
    'Tr_co_1m_nco': 'Tr_co_1m_nco',  # Расчетная температура воды в под.трубопроводе местной СО, незав.СО
    'Tr_co_2m_nco': 'Tr_co_2m_nco',  # Расчетная температура  воды в обрат.трубопроводе местной СО, незав.СО
    'Tr_co_3m_nco': 'Tr_co_3m_nco',  # Расчетная температура воды после узла смешения  местной СО, незав.СО
    'Tr_1_cv': 'Tr_1_cv',  # Расчетная температура сетевой воды на входе КУ
    'Tr_2_cv': 'Tr_2_cv',  # Расчетная температура сетевой воды на выходе КУ
    'Tr_co_1_zco_pr': 'Tr_co_1_zco_pr',  # Расчетная температура сет.воды в под.трубопр.зав.СО, парал.ГВС
    'Tr_co_2_zco_pr': 'Tr_co_2_zco_pr',  # Расчетная температура  сет.воды в обратн.трубопр.зав.СО, парал.ГВС
    'Tr_co_3_zco_pr': 'Tr_co_3_zco_pr',  # Расчетная температура сет.воды после узла смешения зав.СО, парал.ГВС
    'Tr_to_1_pr': 'Tr_to_1_pr',  # Расчетная температура сет.воды на входе подогревателя незав. СО, парал.ГВС
    'Tr_to_2_pr': 'Tr_to_2_pr',  # Расчетная температура сет.воды на выходе подогревателя незав. СО, парал.ГВС
    'Tr_co_1m_nco_pr': 'Tr_co_1m_nco_pr',  # Расчетная температура воды в под.труб. местной СО, незав. СО, парал.ГВС
    'Tr_co_2m_nco_pr': 'Tr_co_2m_nco_pr',  # Расчетная температура  воды в обратн.труб. местной СО, незав. СО, парал.ГВС
    'Tr_co_3m_nco_pr': 'Tr_co_3m_nco_pr',  # Расчетная температура воды после узла смешения местной СО, незав. СО, парал.ГВС
    'T2_isl_2stup_pr': 'T2_isl_2stup_pr',  # Температура сет.воды на вых. 2 ступ. ГВС в т.изл.темп.граф., парал.ГВС
    'Tr_co_1_zco_sm': 'Tr_co_1_zco_sm',  # Расчетная температура сет.воды в под.трубопроводе зав.СО,смеш.ГВС
    'Tr_co_2_zco_sm': 'Tr_co_2_zco_sm',  # Расчетная температура  сет.воды в обратн.трубопроводе зав.СО,смеш.ГВС
    'Tr_co_3_zco_sm': 'Tr_co_3_zco_sm',  # Расчетная температура сет.воды после узла смешения зав.СО,смеш.ГВС
    'Tr_to_1_sm': 'Tr_to_1_sm',  # Расчетная температура сет.воды на входе подогревателя незав.СО,смеш.ГВС
    'Tr_to_2_sm': 'Tr_to_2_sm',  # Расчетная температура сет.воды на выходе подогревателя незав.СО,смеш.ГВС
    'Tr_co_1m_nco_sm': 'Tr_co_1m_nco_sm',  # Расчетная температура воды в под.трубопр. местной СО,незав.СО, смеш.ГВС
    'Tr_co_2m_nco_sm': 'Tr_co_2m_nco_sm',  # Расчетная температура воды в обр.трубопр. местной СО,незав.СО, смеш.ГВС
    'Tr_co_3m_nco_sm': 'Tr_co_3m_nco_sm',  # Расчетная температура воды после узла смешения  местной СО,незав.СО, смеш.ГВС
    'T2_isl_2stup_sm': 'T2_isl_2stup_sm',  # Температура сет.воды на вых.СО  в т.изл.темп. граф., смеш.ГВС
    'delta_tg_sm': 'delta_tg_sm',  # Недогрев водопроводной воды в 1 ступени ГВС до обратной СО в т.изл.темп. граф., смеш.ГВС
    'Tr_co_1_zco_ps': 'Tr_co_1_zco_ps',  # Расчетная температура воды в под.трубопроводе зав.СО, посл.ГВС
    'Tr_co_2_zco_ps': 'Tr_co_2_zco_ps',  # Расчетная температура  сет.воды в обратн.трубопроводе зав.СО, посл.ГВС
    'Tr_co_3_zco_ps': 'Tr_co_3_zco_ps',  # Расчетная температура сет.воды после узла смешения зав.СО, посл.ГВС
    'Tr_to_1_ps': 'Tr_to_1_ps',  # Расчетная температура сет.воды на вх.подогревателя незав.СО, посл.ГВС
    'Tr_to_2_ps': 'Tr_to_2_ps',  # Расчетная температура сет.воды на вых.подогревателя незав.СО, посл.ГВС
    'Tr_co_1m_nco_ps': 'Tr_co_1m_nco_ps',  # Расчетная температура воды в под.труб. местной СО, посл.ГВС
    'Tr_co_2m_nco_ps': 'Tr_co_2m_nco_ps',  # Расчетная температура  воды в обратн.труб. местной СО, посл.ГВС
    'Tr_co_3m_nco_ps': 'Tr_co_3m_nco_ps',  # Расчетная температура воды после узла смешения  местной СО, посл.ГВС
    'T2_isl_2stup_ps': 'T2_isl_2stup_ps',  # Температура сет.воды на вых. СО в т.изл.темп. граф., посл.ГВС
    'delta_tg_ps': 'delta_tg_ps',  # Недогрев водопров.воды в 1 ступ.ГВС до обратной СО в т.изл.темп. граф., посл.ГВС
    'Tr_co_1_zco_pw': 'Tr_co_1_zco_pw',  # Расчетная температура воды в под.трубопроводе зав., предвкл.ГВС
    'Tr_co_2_zco_pw': 'Tr_co_2_zco_pw',  # Расчетная температура  сет.воды в обратн.трубопроводе зав.СО, предвкл.ГВС
    'Tr_co_3_zco_pw': 'Tr_co_3_zco_pw',  # Расчетная температура сет.воды после узла смешения зав.СО, предвкл.ГВС
    'Tr_to_1_pw': 'Tr_to_1_pw',  # Расчетная температура сет.воды на вх.подогревателя незав.СО, предвкл.ГВС
    'Tr_to_2_pw': 'Tr_to_2_pw',  # Расчетная температура сет.воды на вых.подогревателя незав.СО, предвкл.ГВС
    'Tr_co_1m_nco_pw': 'Tr_co_1m_nco_pw',  # Расчетная температура воды в под.труб. местной СО, незав.СО, предвкл.ГВС
    'Tr_co_2m_nco_pw': 'Tr_co_2m_nco_pw',  # Расчетная температура  воды в обратн.труб. местной СО, незав.СО, предвкл.ГВС
    'Tr_co_3m_nco_pw': 'Tr_co_3m_nco_pw',  # Расчетная температура воды после узла смешения  местной СО, незав.СО, предвкл.ГВС
    'T2_isl_2stup_pw': 'T2_isl_2stup_pw',  # Температура сет.воды на вых. СО в т.изл.темп. граф.,  предвкл.ГВС
}

#-----------------------------------------------

tab_heatSystem = {
    'nasel_point': 'nasel_point',  # Наименование населенного пункта
    'year': 'year',  # Календарный год начала отопительного сезона
    't_or': 't_or',  # Расчетная температура наружного воздуха для отопления
    't_vr': 't_vr',  # Расчетная температура наружного воздуха для вентиляции
    't_vnew': 't_vnew',  # Температура наружн. воздуха конца/начала отопит.периода
    'tx': 'tx',  # Расч.температура водопроводной воды в отопит.период
    'tx_leto': 'tx_leto',  # Расчетная температура водопроводной воды в летний период
    'tip_Qgvs': 'tip_Qgvs',  # Задаваемая нагрузка горячего водоснабжения
    'begin_year': 'begin_year',  # Дата начала отопительного/летнего периода
    'begin_year': 'begin_year',  # Дата начала отопительного сезона
    'end_year': 'end_year',  # Дата окончания отопительного/летнего периода
    'end_year': 'end_year',  # Дата окончания отопительного сезона
    'tn_god': 'tn_god',  # Среднесезонная температура наружного воздуха, отопит.период
    'tg_god': 'tg_god',  # Среднесезонная  температура грунта, отопит.период
    'tn_god_leto': 'tn_god_leto',  # Среднесезонная температура наружного воздуха, летний период
    'tg_god_leto': 'tg_god_leto',  # Среднесезонная температура грунта, летний период
    'a': 'a',  # Нормативная потеря сетевой воды с утечкой
    'year_audit': 'year_audit',  # Дата аудита
#    'tvn_1': 'tvn_1',  # NULL
#    'tvn_2': 'tvn_2',  # NULL
#    'tvn_3': 'tvn_3',  # NULL
#    'tvn_4': 'tvn_4',  # NULL
#    'tvn_5': 'tvn_5',  # NULL
#    'G1n_sys_1': 'G1n_sys_1',  # NULL
#    'G1n_sys_2': 'G1n_sys_2',  # NULL
#    'G1n_sys_3': 'G1n_sys_3',  # NULL
#    'G1n_sys_4': 'G1n_sys_4',  # NULL
#    'G1n_sys_5': 'G1n_sys_5',  # NULL
#    'G2n_sys_1': 'G2n_sys_1',  # NULL
#    'G2n_sys_2': 'G2n_sys_2',  # NULL
#    'G2n_sys_3': 'G2n_sys_3',  # NULL
#    'G2n_sys_4': 'G2n_sys_4',  # NULL
#    'G2n_sys_5': 'G2n_sys_5',  # NULL
#    'Gnz_sys_1': 'Gnz_sys_1',  # NULL
#    'Gnz_sys_2': 'Gnz_sys_2',  # NULL
#    'Gnz_sys_3': 'Gnz_sys_3',  # NULL
#    'Gnz_sys_4': 'Gnz_sys_4',  # NULL
#    'Gnz_sys_5': 'Gnz_sys_5',  # NULL
#    'Qn_pot_1': 'Qn_pot_1',  # NULL
#    'Qn_pot_2': 'Qn_pot_2',  # NULL
#    'Qn_pot_3': 'Qn_pot_3',  # NULL
#    'Qn_pot_4': 'Qn_pot_4',  # NULL
#    'Qn_pot_5': 'Qn_pot_5',  # NULL
#    'Qn_gv_pot_1': 'Qn_gv_pot_1',  # NULL
#    'Qn_gv_pot_2': 'Qn_gv_pot_2',  # NULL
#    'Qn_gv_pot_3': 'Qn_gv_pot_3',  # NULL
#    'Qn_gv_pot_4': 'Qn_gv_pot_4',  # NULL
#    'Qn_gv_pot_5': 'Qn_gv_pot_5',  # NULL
#    'Q1n_tp_1': 'Q1n_tp_1',  # NULL
#    'Q1n_tp_2': 'Q1n_tp_2',  # NULL
#    'Q1n_tp_3': 'Q1n_tp_3',  # NULL
#    'Q1n_tp_4': 'Q1n_tp_4',  # NULL
#    'Q1n_tp_5': 'Q1n_tp_5',  # NULL
#    'Q2n_tp_1': 'Q2n_tp_1',  # NULL
#    'Q2n_tp_2': 'Q2n_tp_2',  # NULL
#    'Q2n_tp_3': 'Q2n_tp_3',  # NULL
#    'Q2n_tp_4': 'Q2n_tp_4',  # NULL
#    'Q2n_tp_5': 'Q2n_tp_5',  # NULL
#    't1n_pot_1': 't1n_pot_1',  # NULL
#    't1n_pot_2': 't1n_pot_2',  # NULL
#    't1n_pot_3': 't1n_pot_3',  # NULL
#    't1n_pot_4': 't1n_pot_4',  # NULL
#    't1n_pot_5': 't1n_pot_5',  # NULL
#    't2n_pot_1': 't2n_pot_1',  # NULL
#    't2n_pot_2': 't2n_pot_2',  # NULL
#    't2n_pot_3': 't2n_pot_3',  # NULL
#    't2n_pot_4': 't2n_pot_4',  # NULL
#    't2n_pot_5': 't2n_pot_5',  # NULL
#    't1n_sys_1': 't1n_sys_1',  # NULL
#    't1n_sys_2': 't1n_sys_2',  # NULL
#    't1n_sys_3': 't1n_sys_3',  # NULL
#    't1n_sys_4': 't1n_sys_4',  # NULL
#    't1n_sys_5': 't1n_sys_5',  # NULL
#    't2n_sys_1': 't2n_sys_1',  # NULL
#    't2n_sys_2': 't2n_sys_2',  # NULL
#    't2n_sys_3': 't2n_sys_3',  # NULL
#    't2n_sys_4': 't2n_sys_4',  # NULL
#    't2n_sys_5': 't2n_sys_5',  # NULL
#    'phone_manager': 'phone_manager',  # Телефон/факс руководителя
}

#-----------------------------------------------

tab_externalCodes = {
    'name': 'name',
    'belongMagistral': 'belongMagistral',
    'objectID': 'objectID',
    'exploitRegionID': 'exploitRegionID',
    'exploitSite': 'exploitSite',
    'heatSourceID': 'heatSourceID',
#    'master': 'master',
#    'performer': 'performer',
#    'displaySign': 'displaySign',
#    'fillDate': 'fillDate',
#    'powerSystem': 'powerSystem',
#    'region': 'region',
#    'passportNum': 'passportNum',
#    'networkType': 'networkType',
#    'heatSource': 'heatSource',
#    'projectOrganization': 'projectOrganization',
#    'projectNum': 'projectNum',
#    'avgWayLength': 'avgWayLength',
#    'operPressure': 'operPressure',
#    'operTemperature': 'operTemperature',
#    'constructDate': 'constructDate',
#    'exploitInitDate': 'exploitInitDate',
#    'balanceValue': 'balanceValue',
#    'balanceValueYear': 'balanceValueYear',
#    'initChamber': 'initChamber',
#    'finalChamber': 'finalChamber',
#    'lifetime': 'lifetime',
#    'calcLifetime': 'calcLifetime',
#    'calcStartsNum': 'calcStartsNum',
#    'purpose': 'purpose',
#    'connectNode': 'connectNode',
#    'finalNode': 'finalNode',
#    'kod2': 'kod2',
#    'uzel2': 'uzel2',
#    'registNum': 'registNum',
#    'owner': 'owner',
#    'ownerAddress': 'ownerAddress',
#    'workingEnv': 'workingEnv',
#    'projectDocuments': 'projectDocuments',
#    'responsiblePerson': 'responsiblePerson',
#    'passport': 'passport',
#    'fileID': 'fileID',
}
#-----------------------------------------------

tab_s28 = {
    'pr': 'pr',
    'sm': 'sm',
    'ps': 'ps',
    'pw': 'pw',
    'o': 'o',
}

#-----------------------------------------------

tab_s30 = {
    'pr': 'pr',
    'diametr': 'diametr',
    'beta_mag': 'beta_mag',
    'beta_ras': 'beta_ras',
}

#-----------------------------------------------

def lower_key(m):
    m = {k.lower(): v for k,v in m.items()} 
    return m


#-----------------------------------------------

tab_list = {
    '28_Koeffitsienty_rascheta_balansovoy_nagruzki_GV':  lower_key(tab_s28),
    '30_koeffitsienty_mestnyh_teplovyh_poter':  lower_key(tab_s30),

    'WaterConsumers':  lower_key(tab_ab),
    'TransitNodes':  lower_key(tab_tu),
    'PipelineSegments':  lower_key(tab_ut),
    'nodes':  lower_key(tab_nodes),
    'generalizedConsumers':  lower_key(tab_nodes),
    'linesobj':  lower_key(tab_linesobj),

    'realConsumers':  lower_key(tab_realConsumers),
    'generalizedConsumers':  lower_key(tab_generalizedConsumers),
    'heatSources':  lower_key(tab_heatSources),
    'pumpStations':  lower_key(tab_pumpStations),
    'threeWayValves':  lower_key(tab_threeWayValves),

    'refillNodes':  lower_key(tab_refillNodes),  #       "Узел подпитки"),         "Узлы подпитки и прис.баков-аккумуляторов", NULL)
    'WDOdevices':  lower_key(tab_WDOdevices),     #       Водоразборный прибор

    'heatSystem':  lower_key(tab_heatSystem),              # Система теплоснабжения

    'specExpends':  lower_key(tab_specExpends),            #  Удельные расходы
    'varCoefficients':  lower_key(tab_varCoefficients) ,   #  Коэффициенты вариации
    'calcTemperatures':  lower_key(tab_calcTemperatures),  # Расчетные температуры
    'externalCodes':  lower_key(tab_externalCodes),        # Расчетные схемы

#    'heatPipeSections':  lower_key(tab_heatPipeSections)
#    'pumps':  lower_key(tab_pumps)

    'heatPipeSections':  lower_key(tab_heatPipeSections),  #,     "Участок",     "Участок теплопровода", "UT_OUT", "", -1, -1, -1)
    'pumps':  lower_key(tab_pumps),  #),                "Насос"),       "Насосы(насосные станции расчетной схемы"), "NS_OUT"), "stateID"), -1), -1), -1)
    'pressRegulators':  lower_key(tab_pressRegulators),  #),      "Регул. давл."), "Сетевые регуляторы давления"), "RS_OUT"), "regulatorStateID"), -1), -1), -1)
    'consumptRegulators':  lower_key(tab_consumptRegulators),  #),   "Регул. расх."), "Сетевые регуляторы расхода"), "RS_OUT"), "regulatorStateID"), -1), -1), -1)
    'dampers':  lower_key(tab_dampers),  #),              "Задвижка"),    "Задвижка"), "ZD_OUT"), "damperArmatureStateID"), -1), -1), -1)
    'regulArmatures':  lower_key(tab_regulArmatures),  #),       "Регулирующая арматура"), "Регулирующая арматура"), "ZD2_OUT"), "damperArmatureStateID"), -1), -1), -1)
    'bypass':  lower_key(tab_bypass),  #),               "Байпас"),      "Байпаc"), "BP_OUT"), "regulatorStateID"), -1), -1), -1)
    'diaphragms':  lower_key(tab_diaphragms),  #),           "Диафрагма"),   "Диафрагма"), "DRO_OUT"), "stateID"), -1), -1), -1)
    'elevators':  lower_key(tab_elevators),  #),            "Элеватор"),    "Элеватор"), "ANY_OUT"), "stateID"), -1), -1), -1)
    'systemRadiators':  lower_key(tab_systemRadiators),  #),      "Радиатор"),    "Радиатор"), "ANY_OUT"), "stateID"), -1), -1), -1)
    'heatExchangers':  lower_key(tab_heatExchangers),  #),       "Теплообменник","Теплообменник"), "ANY_OUT"), "stateID"), -1), -1), -1)
    'airHeaters':  lower_key(tab_airHeaters),  #),           "Калориферная установка"),  "Калориферная установка"), "ANY_OUT"), ""), -1), -1), -1)
    'pressDropRegulators':  lower_key(tab_pressDropRegulators),  #),  "Регул. переп."), "Регулятор перепада давления"), "RS_OUT"), "regulatorStateID"), -1), -1), -1)
    'reverseValves':  lower_key(tab_reverseValves),  #),        "Обратный клапан"), "Обратный клапан"), "OK_OUT"), "stateID"), -1), -1), -1)
}

#-----------------------------------------------

map_tn = {
    'bypass':  'Байпас',
    'diaphragms':  'Диафрагма',
    'elevators':  'Элеватор',
    'heatSources':  'Источник тепла',
    'airHeaters':  'Калориферная установка',
    'threeWayValves':  'Клапан трехходовой',
    'pumps':  'Насосный агрегат',
    'pumpStations':  'Насосная станция',
    'reverseValves':  'Обратный клапан',
    'generalizedConsumers':  'Потребитель обобщенный',
    'realConsumers':  'Потребитель реальный',
    'systemRadiators':  'Радиаторы системы отопления',
    'pressRegulators':  'Регулятор давления',
    'consumptRegulators':  'Регулятор расхода',
    'pressDropRegulators':  'Регулятор перепада давления',
    'regulArmatures':  'Регулирующая арматура',
    'heatExchangers':  'Теплообменник',
    'heatPipeSections':  'Участок теплопровода',
    'dampers':  'Задвижка',
    'linesObj':  'ОбщееЛинейныеОбъекты',
    'nodes':  'ОбщееТочечныеОбъекты',
    'addresses':  'Адрес',
    'pavilions':  'Павильон',
    'trps':  'ТРП',
    'heatChambers':  'Тепловая камера',
    'undergroundNodes':  'Подземный узел',
    'overgroundNodes':  'Надземный узел',
    'buildingEntries':  'Ввод в здание',
    'uninstalledNodes':  'Неустановленный узел',
    'pumpStations':  'Насосная станция2',
    'heatSources':  'Источник тепла2',
    'nodes':  'Узел',
    'standardPumps':  'NC_Насос стандартный',
    'standardPressRegulators':  'DC_Регуляторы давления стандартные',
    'standardPressRegulators':  'DC_Регуляторы давления стандартные',
    'localHydroResistances':  'SM_Местные гидравлические сопротивления',
    'standardPressRegulators':  'DC_Регуляторы давления стандартные',
    'standardElevators':  'EV_Элеватор стандартный',
    'standardCompensators':  'KC_Компесаторы стандартные',
    'standardAirHeaters':  'KL_Калориферы стандартные',
    'standardReverseValves':  'KO_Клапан обратный стандартный',
    'standardManometers':  'MN_Манометр стандартный',
    'standardPlateHeatExchangers':  'PL_Теплообменники пластинчатые стандартные',
    'standardTempRegulators':  'PT_Регулятор температуры стандартные',
    'standardConsRegulators':  'RC_Регуляторы расхода стандартные',
    'standardFlowmeters':  'RD_Расходомер стандартный',
    'standardPressDropRegulators':  'RP_Регулятор перепада стандартные',
    'standardTubHeatExchangers':  'TB_Теплообменники трубчатые стандартные',
    'standardThermometers':  'TO_Термометр стандартный',
    'standardTubes':  'TP_Трубы стандартные',
    'standardThreeWayValves':  'V3_Клапан трехходовой стандартный',
    'standardDampers':  'ZC_Задвижки стандартные',
    'WDOdevices':  'Водоразборный прибор',
    'setPressNodes':  'Узел с заданным напором',
    'refillNodes':  'Узел подпитки',
    'specExpends':  'Удельные расходы',
    'calcTemperatures':  'Расчетные температуры',
    'gvsLoadGraphs':  'График нагрузки ГВС',
    'varCoefficients':  'Коэффициенты вариации',
    'calcSchemes':  'Расчетная схема',
    'heatSystem':  'Система теплоснабжения',
    'throttlesOUT':  'DR_OUT',
    'linesOUT':  'ANY_OUT',
    'reverseValvesOUT':  'OK_OUT',
    'bypassOUT':  'BP_OUT',
    'heatSourcesOUT':  'IST_OUT',
    'pumpsOUT':  'NS_OUT',
    'nodesOUT':  'US_OUT',
    'heatPipeSectionsOUT':  'UT_OUT',
    'commonRegulatorsOUT':  'RS_OUT',
    'dampersOUT':  'ZD_OUT',
    'pumpStationsOUT':  'NST_OUT',
    'commonConsumersOUT':  'PT_OUT',
    'regulArmaturesOUT':  'ZD2_OUT',
    'pressDropRegulatorsOUT':  'RPP_OUT',
    'calcSchemeheatLosesOUT':  'TEPLO_OUT',
    'diaphragmsOUT':  'DRO_OUT',
    'totalsOUT':  'ITOG_OUT',
    'calcSchemesOUT':  'ITOG2_OUT',
    'heatLosesOUT':  'UT_KTP_OUT',
    'sectionHeatLosesOUT':  'UT_TEPLO_OUT',
    'TEPLO_t_OUT':  'TEPLO_t_OUT',
    'organizations':  'Организации владельцы',
    'standardEMs':  'EL_Электродвигатель стандартный',
    'isolMaterials':  '07_Теплоизоляционный материал',
    'hSourceWorkMonthGraphs':  'GO_Месячный график работы источника',
    'airGroundMonthTemperatures':  'GT_Месячные температуры воздуха и грунта',
    'deployedTempGraphs':  'TG_Развернутый температурный график',
    'qualityRegTempGraphs':  'TK_График температур качественного регулирования',
    'normTemperaturesGraphs':  'TN_График нормативных температур',
    'corrosionIndicators':  'Индикатор_коррозии',
    'passports':  'Паспорт объекта теплоснабжения',
    'serviceOrganizations':  'Организации обслуживающие',
    'passportsDocs':  'Паспорт объекта теплоснабжения документы',
    'magistrals':  'Магистрали',
    'localHydroResistances2':  'Местные сопротивления участка трубопровода',
    'texts':  'Текст'
}


#-----------------------------------------------


def str_for_sql(tn: str, prefix: str) -> str:
    s = ''
    tab = tab_list.get(tn, None)

    if tab:
        for i in tab:
            if s != '': s += ','
            s += prefix
            s += '.'
            s += i
    return s
    
if __name__ == "__main__":
    pass

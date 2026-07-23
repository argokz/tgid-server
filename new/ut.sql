CREATE OR REPLACE VIEW ut_view AS 

SELECT 
    l.id,
    'heatPipeSections'::text AS name_object,
    'line'::text AS type_object,
    n1.fileid as "fileid",

    l.externalsignlineid,
    l.displaysign,              -- Флажок подписи под объектом на карте
    l.organizationid,
    hps.magistral,              -- Магистраль 
    hps.distsite AS rs,         -- Участок РС
    hps.magistralsite AS ms,    -- Участок МС
    hps.tubingtypeid,           -- Вид трубы (1,'канальная','К',1),(2,'бесканальная','Б',2),(3,'подвальная','П',3),(4,'надземная','Н',4),(5,'обвязка узлов и насосных станций','О',5);
    hps.diameterinternal,       -- Диаметр внутренний, мм 
    hps.diameterexternal,       -- Диаметр условный, мм   
    hps.diametercondit,         -- Диаметр наружный, мм   
    hps.pipesectlength,         -- Длина участка теплопровода, м
    hps.wallthickness,          -- Толщина стенки, мм
    hps.pipesectstateidflow,    -- Состояние участка подающего теплопровода
    hps.pipesectstateidret,
    hps.id AS hps_id,
    utp.id AS nomgp,
    uto.id AS nomgo,

    utp.ist AS "istP",          -- Источник на подаче
    uto.ist AS "istO",          -- Источник на обратке

    utp.b101 AS pod_b101,       -- Расчетная тепловая нагрузка, Гкал/ч
    utp.b102 AS pod_b102,       -- Расчетная тепловая нагрузка на отопление, Гкал/ч 
    utp.b103 AS pod_b103,       -- Расчетная тепловая нагрузка на вентиляцию, Гкал/ч
    utp.b104 AS pod_b104,       -- Расчетная тепловая нагрузка на ГВС, Гкал/ч       
    uto.b101 AS obr_b101,
    uto.b102 AS obr_b102,
    uto.b103 AS obr_b103,
    uto.b104 AS obr_b104,
    utp.a13 AS pod_q,           -- Расход сет. воды, т/ч
    uto.a13 AS obr_q,
    utp.a9 AS pod_v,            -- Объем воды, м^3
    uto.a9 AS obr_v,
    utp.a10 AS pod_w,           -- Скорость потока, м/c

    l.shape
   FROM linesobj l
     JOIN nodes n1 ON n1.id = l.nodeid1
     JOIN nodes n2 ON n2.id = l.nodeid2
     LEFT JOIN heatpipesections hps ON hps.lineid = l.id
     LEFT JOIN ( SELECT c.fileid,
            max(c.id) AS cid
           FROM calculation c
             LEFT JOIN fragments fr ON fr.id = c.fileid
          GROUP BY c.fileid) calc ON calc.fileid = n1.fileid
     LEFT JOIN ut_out utp ON utp.lineid = l.id AND (utp.externalsignlineid = ANY (ARRAY[2, 4])) AND utp.calculationid = calc.cid
     LEFT JOIN ut_out uto ON uto.lineid = l.id AND (uto.externalsignlineid = ANY (ARRAY[3, 5])) AND uto.calculationid = calc.cid
  WHERE l.removed = 0 AND n1.fileid = n2.fileid


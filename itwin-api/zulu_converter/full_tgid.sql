--===========================--
--        Гидравлика             --
--===========================--
---------------------------------
-- heatsystem - Гидравлика
-- heatsystem - Система теплоснабжения
drop table if exists heatsystem;

create table heatsystem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Наименование системы теплоснабжения
    nasel_point varchar(50) default (NULL),   -- Населенный пункт
    seasonID int default ((1)),               -- Признак отопительного периода
    year varchar(50) default (NULL),          -- Календарный год начала отопительного сезона
    t_or float default ((-32)),               -- Расч.темп.наружного возд.для отопления, °C
    t_vr float default ((-32)),               -- Расч.темп.наружного возд.для ветиляции, °C
    t_vnew float default ((8)),               -- Темп.наружного возд.конца(начала) отоп.сезона, °C
    tx float default ((5)),                   -- Расч.темп.холодной воды в отопит.период, °C
    tx_leto float default ((15)),             -- Расч.темп.холодной воды в летний период, °C
    tip_Qgvs int default ((1)),               -- Нагрузка ГВС
    begin_year date default (NULL),           -- Дата начала отоп.сезона
    end_year date default (NULL),             -- Дата окончания отоп.сезона
    tn_god float default ((0)),               -- Среднесезонная температура наружного воздуха, отопит.период, °C
    tg_god float default ((0)),               -- Среднесезонная температура грунта, отопит.период, °C
    tn_god_leto float default ((0)),          -- Среднесезонная температура наружного воздуха, летний период, °C
    tg_god_leto float default ((0)),          -- Среднесезонная температура грунта, летний период, °C
    a float default ((0.25)),                 -- Нормативная потеря сетевой воды с утечкой, %
    year_audit date default (NULL),           -- Отоп.сезон аудита
    tvn_1 float default ((8)),
    tvn_2 float default ((0)),
    tvn_3 float default ((-15)),
    tvn_4 float default ((-32)),
    tvn_5 float default ((-32)),
    G1n_sys_1 float default ((0)),
    G1n_sys_2 float default ((0)),
    G1n_sys_3 float default ((0)),
    G1n_sys_4 float default ((0)),
    G1n_sys_5 float default ((0)),
    G2n_sys_1 float default ((0)),
    G2n_sys_2 float default ((0)),
    G2n_sys_3 float default ((0)),
    G2n_sys_4 float default ((0)),
    G2n_sys_5 float default ((0)),
    Gnz_sys_1 float default ((0)),
    Gnz_sys_2 float default ((0)),
    Gnz_sys_3 float default ((0)),
    Gnz_sys_4 float default ((0)),
    Gnz_sys_5 float default ((0)),
    Qn_pot_1 float default ((0)),
    Qn_pot_2 float default ((0)),
    Qn_pot_3 float default ((0)),
    Qn_pot_4 float default ((0)),
    Qn_pot_5 float default ((0)),
    Qn_gv_pot_1 float default ((0)),
    Qn_gv_pot_2 float default ((0)),
    Qn_gv_pot_3 float default ((0)),
    Qn_gv_pot_4 float default ((0)),
    Qn_gv_pot_5 float default ((0)),
    Q1n_tp_1 float default ((0)),
    Q1n_tp_2 float default ((0)),
    Q1n_tp_3 float default ((0)),
    Q1n_tp_4 float default ((0)),
    Q1n_tp_5 float default ((0)),
    Q2n_tp_1 float default ((0)),
    Q2n_tp_2 float default ((0)),
    Q2n_tp_3 float default ((0)),
    Q2n_tp_4 float default ((0)),
    Q2n_tp_5 float default ((0)),
    t1n_pot_1 float default ((0)),
    t1n_pot_2 float default ((0)),
    t1n_pot_3 float default ((0)),
    t1n_pot_4 float default ((0)),
    t1n_pot_5 float default ((0)),
    t2n_pot_1 float default ((0)),
    t2n_pot_2 float default ((0)),
    t2n_pot_3 float default ((0)),
    t2n_pot_4 float default ((0)),
    t2n_pot_5 float default ((0)),
    t1n_sys_1 float default ((0)),
    t1n_sys_2 float default ((0)),
    t1n_sys_3 float default ((0)),
    t1n_sys_4 float default ((0)),
    t1n_sys_5 float default ((0)),
    t2n_sys_1 float default ((0)),
    t2n_sys_2 float default ((0)),
    t2n_sys_3 float default ((0)),
    t2n_sys_4 float default ((0)),
    t2n_sys_5 float default ((0)),
    tn_long_1 float default ((0)),
    tn_long_2 float default ((0)),
    tn_long_3 float default ((0)),
    tn_long_4 float default ((0)),
    tn_long_5 float default ((0)),
    tn_long_6 float default ((0)),
    tn_long_7 float default ((0)),
    tn_long_8 float default ((0)),
    tn_long_9 float default ((0)),
    tn_long_10 float default ((0)),
    tn_long_11 float default ((0)),
    tn_long_12 float default ((0)),
    tgr_long_1 float default ((0)),
    tgr_long_2 float default ((0)),
    tgr_long_3 float default ((0)),
    tgr_long_4 float default ((0)),
    tgr_long_5 float default ((0)),
    tgr_long_6 float default ((0)),
    tgr_long_7 float default ((0)),
    tgr_long_8 float default ((0)),
    tgr_long_9 float default ((0)),
    tgr_long_10 float default ((0)),
    tgr_long_11 float default ((0)),
    tgr_long_12 float default ((0)),
    tpod_long_1 float default ((0)),
    tpod_long_2 float default ((0)),
    tpod_long_3 float default ((0)),
    tpod_long_4 float default ((0)),
    tpod_long_5 float default ((0)),
    tpod_long_6 float default ((0)),
    tpod_long_7 float default ((0)),
    tpod_long_8 float default ((0)),
    tpod_long_9 float default ((0)),
    tpod_long_10 float default ((0)),
    tpod_long_11 float default ((0)),
    tpod_long_12 float default ((0)),
    tn_fakt_1 float default ((0)),
    tn_fakt_2 float default ((0)),
    tn_fakt_3 float default ((0)),
    tn_fakt_4 float default ((0)),
    tn_fakt_5 float default ((0)),
    tn_fakt_6 float default ((0)),
    tn_fakt_7 float default ((0)),
    tn_fakt_8 float default ((0)),
    tn_fakt_9 float default ((0)),
    tn_fakt_10 float default ((0)),
    tn_fakt_11 float default ((0)),
    tn_fakt_12 float default ((0)),
    tgr_fakt_1 float default ((0)),
    tgr_fakt_2 float default ((0)),
    tgr_fakt_3 float default ((0)),
    tgr_fakt_4 float default ((0)),
    tgr_fakt_5 float default ((0)),
    tgr_fakt_6 float default ((0)),
    tgr_fakt_7 float default ((0)),
    tgr_fakt_8 float default ((0)),
    tgr_fakt_9 float default ((0)),
    tgr_fakt_10 float default ((0)),
    tgr_fakt_11 float default ((0)),
    tgr_fakt_12 float default ((0)),
    tpod_fakt_1 float default ((0)),
    tpod_fakt_2 float default ((0)),
    tpod_fakt_3 float default ((0)),
    tpod_fakt_4 float default ((0)),
    tpod_fakt_5 float default ((0)),
    tpod_fakt_6 float default ((0)),
    tpod_fakt_7 float default ((0)),
    tpod_fakt_8 float default ((0)),
    tpod_fakt_9 float default ((0)),
    tpod_fakt_10 float default ((0)),
    tpod_fakt_11 float default ((0)),
    tpod_fakt_12 float default ((0)),
    phone_manager varchar(50) default (NULL), -- Телефон/факс руководителя
    removed int default ((0)),
    idRemoved int default (NULL),
    Central_Meridian float default ((0)),     -- Центральный меридиан
    Latitude_Of_Origin float default ((0)),   -- Широта начала координат
    False_Easting int default ((0)),          -- Ложный восток
    False_Northing int default ((0)),         -- Ложный север
    Scale_Factor float default ((1)),         -- Коэффициент масштабирования
    dx float default ((0)),                   -- 
    dy float default ((0)),                   -- 
    Angle float default ((0))                 -- Угол поворота
);

INSERT INTO "heatsystem" ("id","name","nasel_point","seasonid","year","t_or","t_vr","t_vnew","tx","tx_leto","tip_qgvs","begin_year","end_year","tn_god","tg_god","tn_god_leto","tg_god_leto","a","year_audit","tvn_1","tvn_2","tvn_3","tvn_4","tvn_5","g1n_sys_1","g1n_sys_2","g1n_sys_3","g1n_sys_4","g1n_sys_5","g2n_sys_1","g2n_sys_2","g2n_sys_3","g2n_sys_4","g2n_sys_5","gnz_sys_1","gnz_sys_2","gnz_sys_3","gnz_sys_4","gnz_sys_5","qn_pot_1","qn_pot_2","qn_pot_3","qn_pot_4","qn_pot_5","qn_gv_pot_1","qn_gv_pot_2","qn_gv_pot_3","qn_gv_pot_4","qn_gv_pot_5","q1n_tp_1","q1n_tp_2","q1n_tp_3","q1n_tp_4","q1n_tp_5","q2n_tp_1","q2n_tp_2","q2n_tp_3","q2n_tp_4","q2n_tp_5","t1n_pot_1","t1n_pot_2","t1n_pot_3","t1n_pot_4","t1n_pot_5","t2n_pot_1","t2n_pot_2","t2n_pot_3","t2n_pot_4","t2n_pot_5","t1n_sys_1","t1n_sys_2","t1n_sys_3","t1n_sys_4","t1n_sys_5","t2n_sys_1","t2n_sys_2","t2n_sys_3","t2n_sys_4","t2n_sys_5","tn_long_1","tn_long_2","tn_long_3","tn_long_4","tn_long_5","tn_long_6","tn_long_7","tn_long_8","tn_long_9","tn_long_10","tn_long_11","tn_long_12","tgr_long_1","tgr_long_2","tgr_long_3","tgr_long_4","tgr_long_5","tgr_long_6","tgr_long_7","tgr_long_8","tgr_long_9","tgr_long_10","tgr_long_11","tgr_long_12","tpod_long_1","tpod_long_2","tpod_long_3","tpod_long_4","tpod_long_5","tpod_long_6","tpod_long_7","tpod_long_8","tpod_long_9","tpod_long_10","tpod_long_11","tpod_long_12","tn_fakt_1","tn_fakt_2","tn_fakt_3","tn_fakt_4","tn_fakt_5","tn_fakt_6","tn_fakt_7","tn_fakt_8","tn_fakt_9","tn_fakt_10","tn_fakt_11","tn_fakt_12","tgr_fakt_1","tgr_fakt_2","tgr_fakt_3","tgr_fakt_4","tgr_fakt_5","tgr_fakt_6","tgr_fakt_7","tgr_fakt_8","tgr_fakt_9","tgr_fakt_10","tgr_fakt_11","tgr_fakt_12","tpod_fakt_1","tpod_fakt_2","tpod_fakt_3","tpod_fakt_4","tpod_fakt_5","tpod_fakt_6","tpod_fakt_7","tpod_fakt_8","tpod_fakt_9","tpod_fakt_10","tpod_fakt_11","tpod_fakt_12","phone_manager","removed","idremoved","central_meridian","latitude_of_origin","false_easting","false_northing","scale_factor","angle") VALUES
(1,'Система теплоснабжения','Астана',2,NULL,-31.2,-31.2,10.0,5.0,15.0,NULL,NULL,NULL,9.0,1.0,8.0,0.5,0.25,NULL,8.0,0.0,-15.0,-32.0,-32.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,NULL,0,NULL,72.0,0.0,40405,-5671188,1.0,0.0);


-- SELECT setval('"heatsystem_id_seq"', 1);
---------------------------------
-- fragments - Гидравлика
-- fragments - Фрагмент тепловой сети
drop table if exists fragments;

create table fragments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(80) default (NULL),
    name_sys varchar(50) default (NULL),
    nasel_point varchar(50) default (NULL),
    sezon varchar(50) default (NULL),
    year varchar(50) default (NULL),
    t_or float default ((-32)),
    t_vr float default ((-32)),
    t_vnew float default ((8)),
    tx float default ((5)),
    tx_leto float default ((15)),
    tip_Qgvs varchar(50) default (NULL),
    begin_year date default (NULL),
    end_year date default (NULL),
    tn_god float default ((0)),
    tg_god float default ((0)),
    tn_god_leto float default ((0)),
    tg_god_leto float default ((0)),
    a float default ((0.25)),
    year_audit date default (NULL),
    tvn_1 float default ((8)),
    tvn_2 float default ((0)),
    tvn_3 float default ((-15)),
    tvn_4 float default ((-32)),
    tvn_5 float default ((-32)),
    G1n_sys_1 float default ((0)),
    G1n_sys_2 float default ((0)),
    G1n_sys_3 float default ((0)),
    G1n_sys_4 float default ((0)),
    G1n_sys_5 float default ((0)),
    G2n_sys_1 float default ((0)),
    G2n_sys_2 float default ((0)),
    G2n_sys_3 float default ((0)),
    G2n_sys_4 float default ((0)),
    G2n_sys_5 float default ((0)),
    Gnz_sys_1 float default ((0)),
    Gnz_sys_2 float default ((0)),
    Gnz_sys_3 float default ((0)),
    Gnz_sys_4 float default ((0)),
    Gnz_sys_5 float default ((0)),
    Qn_pot_1 float default ((0)),
    Qn_pot_2 float default ((0)),
    Qn_pot_3 float default ((0)),
    Qn_pot_4 float default ((0)),
    Qn_pot_5 float default ((0)),
    Qn_gv_pot_1 float default ((0)),
    Qn_gv_pot_2 float default ((0)),
    Qn_gv_pot_3 float default ((0)),
    Qn_gv_pot_4 float default ((0)),
    Qn_gv_pot_5 float default ((0)),
    Q1n_tp_1 float default ((0)),
    Q1n_tp_2 float default ((0)),
    Q1n_tp_3 float default ((0)),
    Q1n_tp_4 float default ((0)),
    Q1n_tp_5 float default ((0)),
    Q2n_tp_1 float default ((0)),
    Q2n_tp_2 float default ((0)),
    Q2n_tp_3 float default ((0)),
    Q2n_tp_4 float default ((0)),
    Q2n_tp_5 float default ((0)),
    t1n_pot_1 float default ((0)),
    t1n_pot_2 float default ((0)),
    t1n_pot_3 float default ((0)),
    t1n_pot_4 float default ((0)),
    t1n_pot_5 float default ((0)),
    t2n_pot_1 float default ((0)),
    t2n_pot_2 float default ((0)),
    t2n_pot_3 float default ((0)),
    t2n_pot_4 float default ((0)),
    t2n_pot_5 float default ((0)),
    t1n_sys_1 float default ((0)),
    t1n_sys_2 float default ((0)),
    t1n_sys_3 float default ((0)),
    t1n_sys_4 float default ((0)),
    t1n_sys_5 float default ((0)),
    t2n_sys_1 float default ((0)),
    t2n_sys_2 float default ((0)),
    t2n_sys_3 float default ((0)),
    t2n_sys_4 float default ((0)),
    t2n_sys_5 float default ((0)),
    tn_long_1 float default ((0)),
    tn_long_2 float default ((0)),
    tn_long_3 float default ((0)),
    tn_long_4 float default ((0)),
    tn_long_5 float default ((0)),
    tn_long_6 float default ((0)),
    tn_long_7 float default ((0)),
    tn_long_8 float default ((0)),
    tn_long_9 float default ((0)),
    tn_long_10 float default ((0)),
    tn_long_11 float default ((0)),
    tn_long_12 float default ((0)),
    tgr_long_1 float default ((0)),
    tgr_long_2 float default ((0)),
    tgr_long_3 float default ((0)),
    tgr_long_4 float default ((0)),
    tgr_long_5 float default ((0)),
    tgr_long_6 float default ((0)),
    tgr_long_7 float default ((0)),
    tgr_long_8 float default ((0)),
    tgr_long_9 float default ((0)),
    tgr_long_10 float default ((0)),
    tgr_long_11 float default ((0)),
    tgr_long_12 float default ((0)),
    tpod_long_1 float default ((0)),
    tpod_long_2 float default ((0)),
    tpod_long_3 float default ((0)),
    tpod_long_4 float default ((0)),
    tpod_long_5 float default ((0)),
    tpod_long_6 float default ((0)),
    tpod_long_7 float default ((0)),
    tpod_long_8 float default ((0)),
    tpod_long_9 float default ((0)),
    tpod_long_10 float default ((0)),
    tpod_long_11 float default ((0)),
    tpod_long_12 float default ((0)),
    tn_fakt_1 float default ((0)),
    tn_fakt_2 float default ((0)),
    tn_fakt_3 float default ((0)),
    tn_fakt_4 float default ((0)),
    tn_fakt_5 float default ((0)),
    tn_fakt_6 float default ((0)),
    tn_fakt_7 float default ((0)),
    tn_fakt_8 float default ((0)),
    tn_fakt_9 float default ((0)),
    tn_fakt_10 float default ((0)),
    tn_fakt_11 float default ((0)),
    tn_fakt_12 float default ((0)),
    tgr_fakt_1 float default ((0)),
    tgr_fakt_2 float default ((0)),
    tgr_fakt_3 float default ((0)),
    tgr_fakt_4 float default ((0)),
    tgr_fakt_5 float default ((0)),
    tgr_fakt_6 float default ((0)),
    tgr_fakt_7 float default ((0)),
    tgr_fakt_8 float default ((0)),
    tgr_fakt_9 float default ((0)),
    tgr_fakt_10 float default ((0)),
    tgr_fakt_11 float default ((0)),
    tgr_fakt_12 float default ((0)),
    tpod_fakt_1 float default ((0)),
    tpod_fakt_2 float default ((0)),
    tpod_fakt_3 float default ((0)),
    tpod_fakt_4 float default ((0)),
    tpod_fakt_5 float default ((0)),
    tpod_fakt_6 float default ((0)),
    tpod_fakt_7 float default ((0)),
    tpod_fakt_8 float default ((0)),
    tpod_fakt_9 float default ((0)),
    tpod_fakt_10 float default ((0)),
    tpod_fakt_11 float default ((0)),
    tpod_fakt_12 float default ((0)),
    phone_manager varchar(50) default (NULL),
    removed int default ((0)),
    idRemoved int default (NULL),
    id_old int default ((0)) 
);

INSERT INTO "fragments" ("id","name","name_sys","nasel_point","sezon","year","t_or","t_vr","t_vnew","tx","tx_leto","tip_qgvs","begin_year","end_year","tn_god","tg_god","tn_god_leto","tg_god_leto","a","year_audit","tvn_1","tvn_2","tvn_3","tvn_4","tvn_5","g1n_sys_1","g1n_sys_2","g1n_sys_3","g1n_sys_4","g1n_sys_5","g2n_sys_1","g2n_sys_2","g2n_sys_3","g2n_sys_4","g2n_sys_5","gnz_sys_1","gnz_sys_2","gnz_sys_3","gnz_sys_4","gnz_sys_5","qn_pot_1","qn_pot_2","qn_pot_3","qn_pot_4","qn_pot_5","qn_gv_pot_1","qn_gv_pot_2","qn_gv_pot_3","qn_gv_pot_4","qn_gv_pot_5","q1n_tp_1","q1n_tp_2","q1n_tp_3","q1n_tp_4","q1n_tp_5","q2n_tp_1","q2n_tp_2","q2n_tp_3","q2n_tp_4","q2n_tp_5","t1n_pot_1","t1n_pot_2","t1n_pot_3","t1n_pot_4","t1n_pot_5","t2n_pot_1","t2n_pot_2","t2n_pot_3","t2n_pot_4","t2n_pot_5","t1n_sys_1","t1n_sys_2","t1n_sys_3","t1n_sys_4","t1n_sys_5","t2n_sys_1","t2n_sys_2","t2n_sys_3","t2n_sys_4","t2n_sys_5","tn_long_1","tn_long_2","tn_long_3","tn_long_4","tn_long_5","tn_long_6","tn_long_7","tn_long_8","tn_long_9","tn_long_10","tn_long_11","tn_long_12","tgr_long_1","tgr_long_2","tgr_long_3","tgr_long_4","tgr_long_5","tgr_long_6","tgr_long_7","tgr_long_8","tgr_long_9","tgr_long_10","tgr_long_11","tgr_long_12","tpod_long_1","tpod_long_2","tpod_long_3","tpod_long_4","tpod_long_5","tpod_long_6","tpod_long_7","tpod_long_8","tpod_long_9","tpod_long_10","tpod_long_11","tpod_long_12","tn_fakt_1","tn_fakt_2","tn_fakt_3","tn_fakt_4","tn_fakt_5","tn_fakt_6","tn_fakt_7","tn_fakt_8","tn_fakt_9","tn_fakt_10","tn_fakt_11","tn_fakt_12","tgr_fakt_1","tgr_fakt_2","tgr_fakt_3","tgr_fakt_4","tgr_fakt_5","tgr_fakt_6","tgr_fakt_7","tgr_fakt_8","tgr_fakt_9","tgr_fakt_10","tgr_fakt_11","tgr_fakt_12","tpod_fakt_1","tpod_fakt_2","tpod_fakt_3","tpod_fakt_4","tpod_fakt_5","tpod_fakt_6","tpod_fakt_7","tpod_fakt_8","tpod_fakt_9","tpod_fakt_10","tpod_fakt_11","tpod_fakt_12","phone_manager","removed","idremoved","id_old") VALUES
(1,'Магистраль',NULL,NULL,NULL,NULL,-31.2,-31.2,10.0,5.0,15.0,NULL,NULL,NULL,0.0,0.0,0.0,0.0,0.25,NULL,8.0,0.0,-15.0,-32.0,-32.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,NULL,0,NULL,0);


-- SELECT setval('"fragments_id_seq"', 3224);
---------------------------------
-- externalcodes - Гидравлика
-- externalcodes - Расчетная схема
drop table if exists externalcodes;

create table externalcodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    belongMagistral int default (NULL),
    objectID int default ((1)),
    exploitRegionID int default (NULL),
    exploitSite int default (NULL),
    heatSourceID int default (NULL),
    master int default (NULL),
    performer varchar(50) default (NULL),
    displaySign int default ((0)),
    fillDate date default (NULL),
    powerSystem varchar(50) default (NULL),
    region varchar(50) default (NULL),
    passportNum varchar(50) default (NULL),
    networkType varchar(50) default (NULL),
    heatSource varchar(50) default (NULL),
    projectOrganization varchar(50) default (NULL),
    projectNum varchar(50) default (NULL),
    avgWayLength int default (NULL),
    operPressure varchar(50) default (NULL),
    operTemperature varchar(50) default (NULL),
    constructDate varchar(50) default (NULL),
    exploitInitDate varchar(50) default (NULL),
    balanceValue int default (NULL),
    balanceValueYear int default (NULL),
    initChamber varchar(50) default (NULL),
    finalChamber varchar(50) default (NULL),
    lifetime int default (NULL),
    calcLifetime int default (NULL),
    calcStartsNum int default (NULL),
    purpose varchar(50) default (NULL),
    connectNode varchar(50) default (NULL),
    finalNode varchar(50) default (NULL),
    kod2 varchar(50) default (NULL),
    uzel2 varchar(50) default (NULL),
    registNum int default (NULL),
    owner int default (NULL),
    ownerAddress varchar(50) default (NULL),
    workingEnv varchar(50) default (NULL),
    projectDocuments varchar,
    responsiblePerson varchar(50) default (NULL),
    passport varchar,
    fileID int default (NULL),
    removed int default ((0)),
    idRemoved int default (NULL),
    id_old int default ((0)) 
);
CREATE INDEX externalcodes_fileid_idx ON externalcodes (fileid);

INSERT INTO "externalcodes" ("id","name","belongmagistral","objectid","exploitregionid","exploitsite","heatsourceid","master","performer","displaysign","filldate","powersystem","region","passportnum","networktype","heatsource","projectorganization","projectnum","avgwaylength","operpressure","opertemperature","constructdate","exploitinitdate","balancevalue","balancevalueyear","initchamber","finalchamber","lifetime","calclifetime","calcstartsnum","purpose","connectnode","finalnode","kod2","uzel2","registnum","owner","owneraddress","workingenv","projectdocuments","responsibleperson","passport","fileid","removed","idremoved","id_old") VALUES
(1,'М1',NULL,1,NULL,NULL,NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,0,NULL,0);



-- SELECT setval('"externalcodes_id_seq"', 30257);
---------------------------------
-- calctemperatures - Гидравлика
-- calctemperatures - Расчетные температуры
drop table if exists calctemperatures;

create table calctemperatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calcTemperatureID varchar(50) default (NULL), -- Код расчетных температур
    Tx float default ((5)),                   -- Расч.температура холодной водопр.воды, °C
    Tn_r float default ((-35)),               -- Расчетная температура наружного воздуха для отопления, °C
    Tn_r_v float default ((-35)),             -- Расч.температура наружного воздуха для вентиляции и воздушной СО, °C
    tn_isl float default ((2.5)),             -- Температура наружного воздуха излома темп.графика, °C
    T1_isl_2stup float default ((70)),        -- Расч.температура сетевой воды на входе ТП в т.изл.темп. граф., °C

    Tr_co_1_zco float default ((150)),        -- Расч.температура воды в подающем трубопроводе, зав.СО, °C
    Tr_co_2_zco float default ((70)),         -- Расч.температура воды в обратном трубопроводе, зав.СО, °C
    Tr_co_3_zco float default ((95)),         -- Расч.температура воды после узла смешения зав.СО, °C
    
    Tr_to_1_nco float default ((150)),        -- Расчетная температура сетевой воды на входе подогревателя, незав.СО, °C
    Tr_to_2_nco float default ((80)),         -- Расч.температура сетевой воды на выходе подогревателя, незав.СО, °C
    Tr_co_1m_nco float default ((140)),       -- Расч.температура воды в подающем трубопроводе местной СО незав.СО, °C
    Tr_co_2m_nco float default ((70)),        -- Расч.температура воды в обратном трубопроводе местной СО незав.СО, °C
    Tr_co_3m_nco float default ((95)),        -- Расч.температура воды после узла смешения местной СО незав.СО, °C

    Tr_1_cv float default ((150)),            -- Расч.темп. сет.воды на входе вентиляции или воздушной системы отопления, °C
    Tr_2_cv float default ((70)),             -- Расч.темп. сет.воды на выходе вентиляции или воздушной системы отопления, °C

    Tr_co_1_zco_pr float default ((150)),     -- Расч.температура воды в подающем трубопроводе зав.СО, парал.ГВС, °C
    Tr_co_2_zco_pr float default ((70)),      -- Расч.температура воды в обратном трубопроводе зав.СО парал.ГВС, °C
    Tr_co_3_zco_pr float default ((95)),      -- Расч.температура воды после узла смешения зав.СО парал.ГВС, °C
    Tr_to_1_pr float default ((150)),         -- Расч.температура сетевой воды на входе подогревателя, незав.СО парал.ГВС, °C
    Tr_to_2_pr float default ((80)),          -- Расчетная температура сетевой воды на выходе подогревателя, независимой СО парал.ГВС, °C

    Tr_co_1m_nco_pr float default ((140)),    -- Расчетная температура воды в подающем трубопроводе местной СО независимая СО парал.ГВС, °C
    Tr_co_2m_nco_pr float default ((80)),     -- Расч.температура воды в обратном трубопроводе местной СО незав.СО парал.ГВС, °C
    Tr_co_3m_nco_pr float default ((95)),     -- Расч.температура воды после узла смешения местной СО незав.СО парал.ГВС, °C
    T2_isl_2stup_pr float default ((30)),     -- Температура сетевой воды на выходе 2 ступени подогревателя т.изл.темп. граф., парал.ГВС, °C

    Tr_co_1_zco_sm float default ((150)),     -- Расч.температура воды в подающем трубопроводе, зав.СО смеш.ГВС, °C
    Tr_co_2_zco_sm float default ((70)),      -- Расч.температура воды в обратном трубопроводе, зав.СО, смеш.ГВС, °C
    Tr_co_3_zco_sm float default ((95)),      -- Расч.температура воды после узла смешения зав.СО смеш.ГВС, °C
    Tr_to_1_sm float default ((150)),         -- Расч.температура сетевой воды на входе подогревателя, незав.СО смеш.ГВС, °C
    Tr_to_2_sm float default ((70)),          -- Расч.температура сетевой воды на выходе подогревателя незав.СО смеш.ГВС, °C
    Tr_co_1m_nco_sm float default ((140)),    -- Расч.температура воды в подающем трубопроводе местной СО незав.СО смеш.ГВС, °C
    Tr_co_2m_nco_sm float default ((70)),     -- Расч.температура воды в обратном трубопроводе местной СО незав.СО смеш.ГВС, °C
    Tr_co_3m_nco_sm float default ((70)),     -- Расч.температура воды после узла смешения местной СО, незав.СО смеш.ГВС, °C
    T2_isl_2stup_sm float default ((41.7)),   -- Температура сетевой воды на выходе СО в т.изл.темп. граф. смеш.ГВС, °C
    delta_tg_sm float default ((5)),          -- Недогрев водопроводной воды в 1 ступени ГВС до обратной СО в т.изл.темп.граф смеш.ГВС, °C
    
    Tr_co_1_zco_ps float default ((150)),     -- Расч.температура воды в подающем трубопроводе зав.СО посл.ГВС, °C
    Tr_co_2_zco_ps float default ((70)),      -- Расч.температура воды в обратном трубопроводе зав.СО посл.ГВС, °C
    Tr_co_3_zco_ps float default ((95)),      -- Расч.температура воды после узла смешения зав.СО посл.ГВС, °C
    Tr_to_1_ps float default ((150)),         -- Расч.температура сетевой воды на входе подогревателя незав.СО посл.ГВС, °C
    Tr_to_2_ps float default ((80)),          -- Расчетная температура сетевой воды на выходе подогревателя незав.СО посл.ГВС, °C
    Tr_co_1m_nco_ps float default ((140)),    -- Расчетная температура воды в подающем трубопроводе местной СО незав.СО посл.ГВС, °C
    Tr_co_2m_nco_ps float default ((70)),     -- Расчетная температура воды в обратном трубопроводе местной СО незав.СО посл.ГВС, °C
    Tr_co_3m_nco_ps float default ((95)),     -- Расчетная температура воды после узла смешения местной СО незав.СО, посл.ГВС, °C
    T2_isl_2stup_ps float default ((41.7)),   -- Температура сетевой воды на выходе СО в т.изл.темп. граф.посл.ГВС, °C
    delta_tg_ps float default ((5)),          -- Недогрев водопроводной воды в 1 ступени ГВС до обратной СО в т.изл.темп. граф.посл. ГВС, °C
    
    Tr_co_1_zco_pw float default ((150)),     -- Расч.температура воды в подающем трубопроводе зав.СО предвкл.ГВС, °C
    Tr_co_2_zco_pw float default ((70)),      -- Расч.температура воды в обратном трубопроводе зав.СО предвкл.ГВС, °C
    Tr_co_3_zco_pw float default ((95)),      -- Расч.температура воды после узла смешения зав.СО предвкл.ГВС, °C
    Tr_to_1_pw float default ((150)),         -- Расч.температура сетевой воды на входе подогревателя незав.СО предвкл.ГВС, °C
    Tr_to_2_pw float default ((80)),          -- Расчетная температура сетевой воды на выходе подогревателя незав.СО предвкл.ГВС, °C
    Tr_co_1m_nco_pw float default ((140)),    -- Расчетная температура воды в подающем трубопроводе местной СО незав.СО предвкл.ГВС, °C
    Tr_co_2m_nco_pw float default ((70)),     -- Расчетная температура воды в обратном трубопроводе местной СО незав.СО предвкл.ГВС, °C
    Tr_co_3m_nco_pw float default ((95)),     -- Расчетная температура воды после узла смешения местной СО незав.СО, предвкл.ГВС, °C
    T2_isl_2stup_pw float default ((41.7)),   -- Температура сетевой воды на выходе СО в т.изл.темп. граф.предвкл.ГВС, °C
    
    fileID int not null,
    id_old int default ((0)) 
);
CREATE INDEX calctemperatures_fileid_idx ON calctemperatures (fileid);

INSERT INTO "calctemperatures" ("id","calctemperatureid","tx","tn_r","tn_r_v","tn_isl","t1_isl_2stup","tr_co_1_zco","tr_co_2_zco","tr_co_3_zco","tr_to_1_nco","tr_to_2_nco","tr_co_1m_nco","tr_co_2m_nco","tr_co_3m_nco","tr_1_cv","tr_2_cv","tr_co_1_zco_pr","tr_co_2_zco_pr","tr_co_3_zco_pr","tr_to_1_pr","tr_to_2_pr","tr_co_1m_nco_pr","tr_co_2m_nco_pr","tr_co_3m_nco_pr","t2_isl_2stup_pr","tr_co_1_zco_sm","tr_co_2_zco_sm","tr_co_3_zco_sm","tr_to_1_sm","tr_to_2_sm","tr_co_1m_nco_sm","tr_co_2m_nco_sm","tr_co_3m_nco_sm","t2_isl_2stup_sm","delta_tg_sm","tr_co_1_zco_ps","tr_co_2_zco_ps","tr_co_3_zco_ps","tr_to_1_ps","tr_to_2_ps","tr_co_1m_nco_ps","tr_co_2m_nco_ps","tr_co_3m_nco_ps","t2_isl_2stup_ps","delta_tg_ps","tr_co_1_zco_pw","tr_co_2_zco_pw","tr_co_3_zco_pw","tr_to_1_pw","tr_to_2_pw","tr_co_1m_nco_pw","tr_co_2m_nco_pw","tr_co_3m_nco_pw","t2_isl_2stup_pw","fileid","id_old") VALUES
(1,'ТР1',5.0,-35.0,-35.0,2.5,70.0,130.0,70.0,95.0,130.0,70.0,130.0,70.0,95.0,130.0,70.0,130.0,70.0,95.0,130.0,70.0,130.0,70.0,95.0,30.0,130.0,70.0,95.0,130.0,70.0,130.0,70.0,70.0,41.7,5.0,130.0,70.0,95.0,130.0,70.0,130.0,70.0,95.0,41.7,5.0,130.0,70.0,95.0,130.0,70.0,130.0,70.0,95.0,41.7,1,0);



-- SELECT setval('"calctemperatures_id_seq"', 3690);
---------------------------------
-- gvsloadgraphs - Гидравлика
-- gvsloadgraphs - График нагрузки ГВС
drop table if exists gvsloadgraphs;

create table gvsloadgraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gvsLoadGraphID varchar(50) default (NULL),
    gvs_00_01 varchar(50) default (NULL),     -- Нагрузка ГВ с 00 до 01 часов суток в будний день
    gvs_01_02 varchar(50) default (NULL),     -- Нагрузка ГВ с 01 до 02 часов суток в будний день
    gvs_02_03 varchar(50) default (NULL),     -- Нагрузка ГВ с 02 до 03 часов суток в будний день
    gvs_03_04 varchar(50) default (NULL),     -- Нагрузка ГВ с 03 до 04 часов суток в будний день
    gvs_04_05 varchar(50) default (NULL),     -- Нагрузка ГВ с 04 до 05 часов суток в будний день
    gvs_05_06 varchar(50) default (NULL),     -- Нагрузка ГВ с 05 до 06 часов суток в будний день
    gvs_06_07 varchar(50) default (NULL),     -- Нагрузка ГВ с 06 до 07 часов суток в будний день
    gvs_07_08 varchar(50) default (NULL),     -- Нагрузка ГВ с 07 до 08 часов суток в будний день
    gvs_08_09 varchar(50) default (NULL),     -- Нагрузка ГВ с 08 до 09 часов суток в будний день
    gvs_09_10 varchar(50) default (NULL),     -- Нагрузка ГВ с 09 до 10 часов суток в будний день
    gvs_10_11 varchar(50) default (NULL),     -- Нагрузка ГВ с 11 до 12 часов суток в будний день
    gvs_11_12 varchar(50) default (NULL),     -- Нагрузка ГВ с 11 до 12 часов суток в будний день
    gvs_12_13 varchar(50) default (NULL),     -- Нагрузка ГВ с 12 до 13 часов суток в будний день
    gvs_13_14 varchar(50) default (NULL),     -- Нагрузка ГВ с 13 до 14 часов суток в будний день
    gvs_14_15 varchar(50) default (NULL),     -- Нагрузка ГВ с 14 до 15 часов суток в будний день
    gvs_16_17 varchar(50) default (NULL),     -- Нагрузка ГВ с 16 до 17 часов суток в будний день
    gvs_17_18 varchar(50) default (NULL),     -- Нагрузка ГВ с 17 до 18 часов суток в будний день
    gvs_18_19 varchar(50) default (NULL),     -- Нагрузка ГВ с 18 до 19 часов суток в будний день
    gvs_19_20 varchar(50) default (NULL),     -- Нагрузка ГВ с 19 до 20 часов суток в будний день
    gvs_20_21 varchar(50) default (NULL),     -- Нагрузка ГВ с 20 до 21 часов суток в будний день
    gvs_21_22 varchar(50) default (NULL),     -- Нагрузка ГВ с 21 до 22 часов суток в будний день
    gvs_22_23 varchar(50) default (NULL),     -- Нагрузка ГВ с 22 до 23 часов суток в будний день
    gvs_23_24 varchar(50) default (NULL),     -- Нагрузка ГВ с 23 до 24 часов суток в будний день
    gvs_00_01_vix varchar(50) default (NULL), -- Нагрузка ГВ с 00 до 01 часов суток в выходной день
    gvs_01_02_vix varchar(50) default (NULL), -- Нагрузка ГВ с 01 до 02 часов суток в выходной день
    gvs_02_03_vix varchar(50) default (NULL), -- Нагрузка ГВ с 02 до 03 часов суток в выходной день
    gvs_03_04_vix varchar(50) default (NULL), -- Нагрузка ГВ с 03 до 04 часов суток в выходной день
    gvs_04_05_vix varchar(50) default (NULL), -- Нагрузка ГВ с 04 до 05 часов суток в выходной день
    gvs_05_06_vix varchar(50) default (NULL), -- Нагрузка ГВ с 05 до 06 часов суток в выходной день
    gvs_06_07_vix varchar(50) default (NULL), -- Нагрузка ГВ с 06 до 07 часов суток в выходной день
    gvs_07_08_vix varchar(50) default (NULL), -- Нагрузка ГВ с 07 до 08 часов суток в выходной день
    gvs_08_09_vix varchar(50) default (NULL), -- Нагрузка ГВ с 08 до 09 часов суток в выходной день
    gvs_09_10_vix varchar(50) default (NULL), -- Нагрузка ГВ с 09 до 10 часов суток в выходной день
    gvs_10_11_vix varchar(50) default (NULL), -- Нагрузка ГВ с 11 до 12 часов суток в выходной день
    gvs_11_12_vix varchar(50) default (NULL), -- Нагрузка ГВ с 11 до 12 часов суток в выходной день
    gvs_12_13_vix varchar(50) default (NULL), -- Нагрузка ГВ с 12 до 13 часов суток в выходной день
    gvs_13_14_vix varchar(50) default (NULL), -- Нагрузка ГВ с 13 до 14 часов суток в выходной день
    gvs_14_15_vix varchar(50) default (NULL), -- Нагрузка ГВ с 14 до 15 часов суток в выходной день
    gvs_15_16_vix varchar(50) default (NULL), -- Нагрузка ГВ с 15 до 16 часов суток в выходной день
    gvs_16_17_vix varchar(50) default (NULL), -- Нагрузка ГВ с 16 до 17 часов суток в выходной день
    gvs_17_18_vix varchar(50) default (NULL), -- Нагрузка ГВ с 17 до 18 часов суток в выходной день
    gvs_18_19_vix varchar(50) default (NULL), -- Нагрузка ГВ с 18 до 19 часов суток в выходной день
    gvs_19_20_vix varchar(50) default (NULL), -- Нагрузка ГВ с 19 до 20 часов суток в выходной день
    gvs_20_21_vix varchar(50) default (NULL), -- Нагрузка ГВ с 20 до 21 часов суток в выходной день
    gvs_21_22_vix varchar(50) default (NULL), -- Нагрузка ГВ с 21 до 22 часов суток в выходной день
    gvs_22_23_vix varchar(50) default (NULL), -- Нагрузка ГВ с 22 до 23 часов суток в выходной день
    gvs_23_24_vix varchar(50) default (NULL), -- Нагрузка ГВ с 23 до 24 часов суток в выходной день
    fileID int not null,
    id_old int default ((0)) 
);
CREATE INDEX gvsloadgraphs_fileid_idx ON gvsloadgraphs (fileid);
---------------------------------
-- specexpends - Гидравлика
-- specexpends - Удельные расходы
drop table if exists specexpends;

create table specexpends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specExpendID varchar(50) default (NULL),  -- Код УР
    hSourceCode varchar(50) default (NULL),   -- Код ист.тепла
    calcHLdep float default ((12.5)),         -- УР потреб.на отопл., зав.сх., т/Гкал
    calcHLindep float default ((14.3)),       -- УР потреб.на отопл., незав.сх., т/Гкал
    calcHLventil float default ((12.5)),      -- УР потреб.на вент., т/Гкал
    calcHLcond float default ((12.5)),        -- УР потреб.на конд., т/Гкал
    calcHLcloseSys float default ((12.5)),    -- УР потреб.на техн.проц.в закр.ТС, т/Гкал
    calcHLopenSys float default ((18.2)),     -- УР потреб.на техн.проц.в откр.ТС, т/Гкал
    calcExpendHWopen float default ((18.2)),  -- УР на ГВ при откр.ТС, т/Гкал
    circHLosOpen float default ((66.7)),      -- УР на комп.тепл.потерь рецирк.ГВС, т/Гкал
    avgHLGVScloseParall float default ((28.75)),  -- УР на ГВ при парал.ГВС, т/Гкал
    avgHLGVScloseMix float default ((16.6)),  -- УР на ГВ при смеш.ГВС, т/Гкал
    avgHLGVScloseConseq float default ((18.7)),   -- УР на ГВ при послед.ГВС, т/Гкал
    avgHLGVSclosePreON float default ((44.1)),    -- УР на ГВ при предвкл.ГВС, т/Гкал
    avgHLGVScloseSummer float default ((25)), -- УР в закрытой ГВС летний период, т/Гкал
    avgHLGVSopenSummer float default ((15.4)),    -- УР в открытой ГВС летний период, т/Гкал
    fileID int default (NULL),
    id_old int default ((0)) 
);
CREATE INDEX specexpends_fileid_idx ON specexpends (fileid);

INSERT INTO "specexpends" ("id","specexpendid","hsourcecode","calchldep","calchlindep","calchlventil","calchlcond","calchlclosesys","calchlopensys","calcexpendhwopen","circhlosopen","avghlgvscloseparall","avghlgvsclosemix","avghlgvscloseconseq","avghlgvsclosepreon","avghlgvsclosesummer","avghlgvsopensummer","fileid","id_old") VALUES
(1,'УР1',NULL,12.5,14.3,12.5,12.5,12.5,18.2,18.2,66.7,28.75,16.6,18.7,44.1,25.0,15.4,1,0);


-- SELECT setval('"specexpends_id_seq"', 4065);
---------------------------------
-- texts - Гидравлика
-- texts - Тексты
drop table if exists texts;

create table texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internalNodeID int default (NULL),
    label_text varchar default (''),
    font_name varchar default ('Arial'),
    font_size int default ((21)),
    x float default ((0)),
    y float default ((0)),
    fileID int default (NULL),
    removed int default ((0)) 
);
CREATE INDEX texts_fileid_idx ON texts (fileid);
---------------------------------
-- varcoefficients - Гидравлика
-- varcoefficients - Коэффициенты вариации
drop table if exists varcoefficients;

create table varcoefficients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kodkv varchar(50) default (NULL),         -- Код группы коэф.вар.
    kvpot float default ((1)),                -- Коэф.вар.нагрузки по всем видам теплопотребл.
    otoplz float default ((1)),               -- На отопление, зависимая
    otopln float default ((1)),               -- На отопление, независимая
    ventil float default ((1)),               -- Коэф.вар.нагрузки вент.
    kondiz float default ((1)),               -- На кондициоирование
    txz float default ((1)),                  -- Коэф.вар.нагрузки технол., закр.
    txop float default ((1)),                 -- На технологические процессы из подающего трубопровода
    txoo float default ((1)),                 -- На технологические процессы из обратного трубопровода
    gvz float default ((1)),                  -- На ГВ в закрытой схеме
    gvop float default ((1)),                 -- На ГВ из подающего трубопровода
    gvoo float default ((1)),                 -- На ГВ из обратного трубопровода
    ut float default ((1)),                   -- На утечку в узлах расчетной схемы
    cher float default ((0)),                 -- Изменение значений эквивалентной шероховатости участка
    diam float default ((0)),                 -- Изменение значений диаметров труб участка
    fileID int default (NULL),
    id_old int default ((0)) 
);
CREATE INDEX varcoefficients_fileid_idx ON varcoefficients (fileid);
---------------------------------
-- nodes - Гидравлика
-- nodes - ОбщееТочечныеОбъекты
drop table if exists nodes;

create table nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internalNodeID int default (NULL),        -- Идентификатор узла в качестве внутреннего
    externalCodeID int default (NULL),        -- Код расчетной схемы
    externalNodeName varchar(50) default (NULL),  -- Наименование узла присоединения
    externalSignID int default ((1)),         -- Признак теплопровода узла присоединения
    addressID int default (NULL),             -- Адрес
    geoMarkTopTube float default ((0)),       -- Геодезическая отметка оси трубы, м
    geoMarkNodeArea float default ((0)),      -- Геодезическая отметка поверхности земли, м
    calcPressFlow float default ((0)),        -- Измеренное давление по подаче, м.вод.ст
    calcPressRet float default ((0)),         -- Измеренное давление по обратке, м.вод.ст
    PICdate date default (NULL),              -- Дата ввода в эксплуатацию
    lastRepairDate date default (NULL),       -- Дата последнего ремонта
    displaySign int default ((0)),            -- Флажок подписи под объектом на карте
    archiveChangeDate timestamp default (NULL),   -- Дата изменения Архива
    operatorID int default (NULL),            -- Оператор архива
    nodeName varchar(255) default (NULL),     -- Наименование
    scheme varchar,                           -- Схема
    memo varchar,                             -- Дополнительное поле
    gpsCoords varchar(255) default (NULL),    -- GPS-координаты
    belongHN varchar(50) default (NULL),      -- Принадлежность тепловым сетям
    passport varchar,                         -- Паспорт
    inventNumber varchar(50) default (NULL),  -- Инвентарный номер
    pipelineSign varchar(50) default (NULL),  -- Признак трубопровода
    nodeTypeID int default (NULL),            -- Конструкция узла
    isBusy int default ((0)),                 -- Флажок занятости узла
    isLoaded int default (NULL),              -- Флажок нагруженности узла
    belongMagistralSite int default (NULL),   -- Принадлежность участку МС
    belongDistSite int default (NULL),        -- Принадлежность участку РС
    organizationID int default (NULL),        -- Владелец
    magistralSite int default (NULL),         -- Участок МС
    distSite int default (NULL),              -- Участок РС
    registNumber varchar(50) default (NULL),  -- Регистрационный номер
    x float default ((0)),                    -- Координата объекта по х
    y float default ((0)),                    -- Координата объекта по y
    fileID int default (NULL),                -- Фрагмент
    removed int default ((0)),                -- Удаленный узел
    idRemoved int default (NULL),
    shape geometry default (NULL),
    id_old int default ((0)) 
);
CREATE INDEX nodes_fileid_idx ON nodes (fileid);
-- CREATE INDEX nodes_shape_idx ON nodes USING GIST (shape);
---------------------------------
-- linesobj - Гидравлика
-- linesobj - ОбщееЛинейныеОбъекты
drop table if exists linesobj;

create table linesobj (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID1 int default (NULL),
    nodeID2 int default (NULL),
    externalSignLineID int default ((1)),     -- Признак участка трубопровода
    location varchar(50) default (NULL),
    hydroRes float default ((0)),             -- Гидравлическое сопротивление участка
    organizationID int default (NULL),        -- Владелец участка теплопровода
    registNum varchar(50) default (NULL),     -- Регистрационный номер
    firstPICdate date default (NULL),         -- Дата первичного ввода в эксплуатацию
    lastMaintDate date default (NULL),
    displaySign int default ((0)),
    archiveChangeDate timestamp default (NULL),   -- Дата изменения архива
    operatorID int default (NULL),            -- Оператор архивации
    coords varchar,
    typ varchar(50) default (NULL),
    removed int default ((0)),
    idRemoved int default (NULL),
    shape geometry default (NULL),
    id_old int default ((0)) 
);
CREATE INDEX linesobj_nodeid1_idx ON linesobj (nodeid1);
CREATE INDEX linesobj_nodeid2_idx ON linesobj (nodeid2);
-- CREATE INDEX linesobj_shape_idx ON linesobj USING GIST (shape);
---------------------------------
-- setpressnodes - Гидравлика
-- setpressnodes - Узлы с заданным напором
drop table if exists setpressnodes;

create table setpressnodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    pressFlow float default ((0)),            -- Пьезометрический напор в подающем теплопроводе, м.вод.ст
    pressRet float default ((0)),             -- Пьезометрический напор в обратном теплопроводе, м.вод.ст
    fragment_resultID int default (NULL),
    file_result varchar(50) default (NULL),   -- Наименование файла результатов
    kod_m varchar(50) default (NULL),         -- Код расчетной схемы узла обобщенного потребителя
    uzel_m varchar(50) default (NULL),        -- Наименование узла обобщенного потребителя
    fileID int default (NULL) 
);
CREATE INDEX setpressnodes_nodeid_idx ON setpressnodes (nodeid);
CREATE INDEX setpressnodes_fileid_idx ON setpressnodes (fileid);
---------------------------------
-- directions - Гидравлика
-- directions - Направления
drop table if exists directions;

create table directions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar default (NULL),
    fileID int not null,
    id_old int default ((0)) 
);
CREATE INDEX directions_fileid_idx ON directions (fileid);
---------------------------------
-- deployeddirections - Гидравлика
-- deployeddirections - Развернутые направления
drop table if exists deployeddirections;

create table deployeddirections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    directionID int,
    nodeID int default (NULL) 
);
CREATE INDEX deployeddirections_nodeid_idx ON deployeddirections (nodeid);
---------------------------------
-- connectnodes - Гидравлика
-- connectnodes - Соединительные узлы
drop table if exists connectnodes;

create table connectnodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    connectID int default (NULL) 
);
CREATE INDEX connectnodes_nodeid_idx ON connectnodes (nodeid);
---------------------------------
-- wdodevices - Гидравлика
-- wdodevices - Водоразборный прибор
drop table if exists wdodevices;

create table wdodevices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    externalSignID int default (NULL),
    WDO float default ((0)),                  -- Водоразбор, т/ч
    hydroRes float default ((0))              -- Гидр.сопротивление, м*ч^2/т^2
);
CREATE INDEX wdodevices_nodeid_idx ON wdodevices (nodeid);
---------------------------------
-- buildingentries - Гидравлика
-- buildingentries - Ввод в здание5
drop table if exists buildingentries;

create table buildingentries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL) 
);
CREATE INDEX buildingentries_nodeid_idx ON buildingentries (nodeid);
---------------------------------
-- generalizedconsumers - Гидравлика
-- generalizedconsumers - Потребитель обобщенный
drop table if exists generalizedconsumers;

create table generalizedconsumers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    quarter int default ((0)),                -- Квартал
    maxBuildingHeight float default ((0)),    -- Наибольшая высота здания, м
    accumCoeff float default ((32.0)),        -- Коэффициент аккумуляции здания
    hydroModeSignID int default ((3)),        -- Признак расчета гидравл.аварийного потребителя: Ш - через шайбы, Д-через регулятор перепада давления, С - через сопротивления
    specExpendID int default (NULL),          -- Код удельных расходов тепло/вода, для расчетного режима
    calcTemperatureID int default (NULL),     -- Код расчетных температур, °C
    gvsLoadGraphID int default (NULL),        -- Код суточного графика нагрузки ГВ, м*ч^2/т^2
    varCoeffID int default (NULL),            -- Код группы коэффициентов вариации
    normHLosFlow float default ((0)),         -- Норм.тепловые потери в под.теплопр.распр.сети, Гкал/ч
    normHLosRet float default ((0)),          -- Норм.тепловые потери в обр.теплопр.распр.сети, Гкал/ч
    calcHLdep float default ((0)),            -- Расчетная тепловая нагрузка на отопление, зависимая СО, Гкал/ч
    calcInternHDdep float default ((0)),      -- Расчетные внутренние тепловыделения, зависимая СО, Гкал/ч
    adjCalcHLdep float default ((0)),         -- Договорная нагрузка на отопление, зависимая СО, Гкал/ч
    adjCalcHDdep float default ((0)),         -- Договор.внутренние тепловыделения, зависимая СО, Гкал/ч
    perspCalcHLdep float default ((0)),       -- Перспективная нагрузка на отопление, зависимая СО, Гкал/ч
    perspCalcInternHDdep float default ((0)), -- Перспект.внутренние тепловыделения, зависимая СО, Гкал/ч
    calcTempDep float default ((18)),         -- Расчетная температура в отапливаемых помещениях, зависимая СО, °C
    connectionSchemeID int default ((2)),     -- Схема присоединения зависимой СО
    mixFactCoeffDep float default ((2.2)),    -- Фактический коэффициент смешения, зависимая СО
    calcHLindep float default ((0)),          -- Расчетная тепловая нагрузка на отопление, независимая СО, Гкал/ч
    calcInternHDindep float default ((0)),    -- Расчетные внутренние тепловыделения, независимая СО, Гкал/ч
    adjCalcHLindep float default ((0)),       -- Договорная нагрузка на отопление, независимая СО, Гкал/ч
    adjCalcInternHDindep float default ((0)), -- Договорные внутренние тепловыделения, независимая СО, Гкал/ч
    perspCalcHLindep float default ((0)),     -- Перспективная нагрузка на отопление, независимая СО, Гкал/ч
    perspCalcInternHDindep float default ((0)),   -- Перспективные внутренние тепловыделения, независимая СО, Гкал/ч
    calcTempIndep float default ((18)),       -- Расчетная температура в отапливаемых помещениях, независимая СО, °C
    mixFactCoeffIndep float default ((1.8)),  -- Фактический коэффициент смешения, независимая СО
    calcHLventil float default ((0)),         -- Расчетная тепловая нагрузка на вентиляцию, Гкал/ч
    adjCalcHLventil float default ((0)),      -- Договорная тепловая нагрузка на вентиляцию, Гкал/ч
    perspCalcHLventil float default ((0)),    -- Перспективная тепловая нагрузка на вентиляцию, Гкал/ч
    calcHLcond float default ((0)),           -- Расчетная тепловая нагрузка на кондиционирование, Гкал/ч
    adjCalcHLcond float default ((0)),        -- Договорная нагрузка на кондиционирование, Гкал/ч
    perspCalcHLcond float default ((0)),      -- Перспективная нагрузка на кондиционирование, Гкал/ч
    calcHLcloseSys float default ((0)),       -- Расчетная тепловая нагрузка на технологию в закрытой системе, Гкал/ч
    calcHLopenSysFlow float default ((0)),    -- Средняя нагрузка на технологию в открытой системе из подающего теплопровода, Гкал/ч
    calcHLopenSysRet float default ((0)),     -- Средняя нагрузка на технологию в открытой системе из обратного теплопровода, Гкал/ч
    adjCalcHLcloseSys float default ((0)),    -- Договорная нагрузка на технологию в закрытой системе, Гкал/ч
    adjCalcHLopenSysFlow float default ((0)),
    adjCalcHLopenSysRet float default ((0)),
    perspCalcHLcloseSys float default ((0)),  -- Перспективная нагрузка на технологию в закрытой системе, Гкал/ч
    perspCalcHLopenSysFlow float default ((0)),
    perspCalcHLopenSysRet float default ((0)),
    expendHWpart float default ((0)),         -- Доля расхода сетевой воды через КУ от расчётного, при отключеннии её по воздуху
    calcTempHA float default ((0)),           -- Расч.темп. нагретого воздуха в системе вентиляции или возд.отопления, °C
    calcHLparall float default ((0)),         -- Расчетная тепловая нагрузка на отопление парал.ГВС, Гкал/ч
    internHDparall float default ((0)),       -- Внутренние тепловыделения, парал.ГВС, Гкал/ч
    adjCalcHLparall float default ((0)),      -- Договорная нагрузка на отопление парал.ГВС, Гкал/ч
    adjInternHDparall float default ((0)),    -- Договор.внутренние тепловыделения, парал.ГВС, Гкал/ч
    perspCalcHLparall float default ((0)),    -- Перспективная нагрузка на отопление парал.ГВС, Гкал/ч
    perspInternHDparall float default ((0)),  -- Перспект.внутренние тепловыделения, парал.ГВС, Гкал/ч
    schemeParallID int default (NULL),        -- Схема присоединения СО, при парал.ГВС
    calcHLGVSparall float default ((0)),      -- Средняя тепловая нагрузка на ГВС, парал.сх., Гкал/ч
    adjCalcHLGVSparall float default ((0)),
    perspCalcHLGVSparall float default ((0)),
    hourIrregCoeffParall float default ((1.2)),   -- Коэф. часовой неравномерности нагрузки парал.ГВС
    avgHLcompParall float default ((0)),      -- Расчетная тепловая нагрузка на компенсацию тепловых потерь в трубопр. цирк-ой ГВС, парал.сх., %
    tempRecircPipeParall float default ((40)),    -- Температура в рециркуляционном трубопроводе ГВС, °C
    calcTempHRparall float default ((18)),    -- Расчетная температура в отапливаемых помещениях, парал.ГВС, °C
    calcTempHWDOparall float default ((60)),  -- Расчетная температура горячей воды в местах водоразбора, парал.ГВС, °C
    AMRdepParall float default ((2.2)),       -- Фактический коэффициент смешения,зав.СО, парал.ГВС
    calcHLmix float default ((0)),            -- Расчетная тепловая нагрузка на отопление, смеш.ГВС, Гкал/ч
    internHDmix float default ((0)),          -- Внутренние тепловыделения,смеш.ГВС, Гкал/ч
    adjCalcHLmix float default ((0)),         -- Договорная нагрузка на отопление, смеш.ГВС, Гкал/ч
    adjInternHDmix float default ((0)),       -- Договор.внутренние тепловыделения,смеш.ГВС, Гкал/ч
    perspCalcHLmix float default ((0)),       -- Перспективная нагрузка на отопление, смеш.ГВС, Гкал/ч
    perspInternHDmix float default ((0)),     -- Перспект.внутренние тепловыделения,смеш.ГВС, Гкал/ч
    schemeMixID int default (NULL),           -- Схема присоединения СО смеш.ГВС
    calcHLGVSmix float default ((0)),         -- Средняя тепловая нагрузка на ГВС, смеш., Гкал/ч
    adjCalcHLGVSmix float default ((0)),
    perspCalcHLGVSmix float default ((0)),
    hourIrregCoeffMix float default ((1.2)),  -- Коэф. часовой неравномерности нагрузки, смеш.ГВС
    avgHLcompMix float default ((0)),         -- Расчетная тепловая нагрузка на компенсацию тепловых потерь в трубопр. цирк-ой ГВС, смеш.сх., %
    tempRecircPipeMix float default ((40)),   -- Температура в рециркуляционном трубопроводе ГВС, °C
    calcTempHRmix float default ((18)),       -- Расчетная температура в отапливаемых помещениях, смеш.ГВС, °C
    calcTempHWDOmix float default ((60)),     -- Расчетная температура горячей воды в местах водоразбора, смеш.ГВС, °C
    AMRdepMix float default ((2.2)),          -- Фактический коэффициент смешения,зав.СО, смеш.ГВС
    calcHLconseq float default ((0)),         -- Расчетная тепловая нагрузка на отопление, посл.ГВС, Гкал/ч
    internHDconseq float default ((0)),       -- Внутренние тепловыделения,посл.ГВС, Гкал/ч
    adjCalcHLconseq float default ((0)),      -- Договорная нагрузка на отопление, посл.ГВС, Гкал/ч
    adjInternHDconseq float default ((0)),    -- Договор.внутренние тепловыделения,посл.ГВС, Гкал/ч
    perspCalcHLconseq float default ((0)),    -- Перспективная нагрузка на отопление, посл.ГВС, Гкал/ч
    perspInternHDconseq float default ((0)),  -- Перспект.внутренние тепловыделения,посл.ГВС, Гкал/ч
    schemeConseqID int default (NULL),        -- Схема присоединения СО посл.ГВС
    calcHLGVSconseq float default ((0)),      -- Средняя тепловая нагрузка на ГВС,посл. ГВС, Гкал/ч
    adjCalcHLGVSconseq float default ((0)),
    perspCalcHLGVSconseq float default ((0)),
    hourIrregCoeffConseq float default ((1.2)),   -- Коэф. часовой неравномерности, посл.ГВС
    avgHLcompconseq float default ((0)),      -- Расчетная тепловая нагрузка на компенсацию тепловых потерь в трубопр. цирк-ой ГВС, посл.сх., %
    tempRecircPipeConseq float default ((40)),    -- Температура в рециркуляционном трубопроводе ГВС, °C
    calcTempHRconseq float default ((18)),    -- Расчетная температура в отапливаемых помещениях, посл.ГВС, °C
    calcTempHWDOconseq float default ((60)),  -- Расчетная температура горячей воды в местах водоразбора, посл.ГВС, °C
    AMRdepConseq float default ((2.2)),       -- Фактический коэффициент смешения,зав.СО,посл.ГВС
    calcHLpreON float default ((0)),          -- Расчетная тепловая нагрузка на отопление, предвкл.ГВС, Гкал/ч
    internHDpreON float default ((0)),        -- Внутренние тепловыделения, предвкл.ГВС, Гкал/ч
    adjCalcHLpreON float default ((0)),       -- Договорная нагрузка на отопление, предвкл.ГВС, Гкал/ч
    adjInternHDpreON float default ((0)),     -- Договор.внутренние тепловыделения, предвкл.ГВС, Гкал/ч
    perspCalcHLpreON float default ((0)),     -- Перспективная нагрузка на отопление, предвкл.ГВС, Гкал/ч
    perspInternHDpreON float default ((0)),   -- Перспект.внутренние тепловыделения, предвкл.ГВС, Гкал/ч
    schemePreONID int default (NULL),         -- Схема присоединения СО предвкл.ГВС
    calcHLGVSpreON float default ((0)),       -- Средняя тепловая нагрузка на ГВС, предвкл. ГВС, Гкал/ч
    adjCalcHLGVSpreON float default ((0)),
    perspCalcHLGVSpreON float default ((0)),
    hourIrregCoeffPreON float default ((1.2)),    -- Коэф. часовой неравномерности, предвкл.ГВС
    avgHLcompPreON float default ((0)),       -- Расчетная тепловая нагрузка на компенсацию тепловых потерь в трубопр. цирк-ой ГВС, предвкл.сх., %
    tempRecircPipePreON float default ((40)), -- Температура в рециркуляционном трубопроводе ГВС, °C
    calcTempHRpreON float default ((18)),     -- Расчетная температура в отапливаемых помещениях, предвкл.ГВС, °C
    calcTempHWDOpreON float default ((60)),   -- Расчетная температура горячей воды в местах водоразбора, предвкл.ГВС, °C
    AMRdepPreON float default ((2.2)),        -- Фактический коэффициент смешения,зав.СО, предвкл.ГВС
    avgHLGVSopenSysFlow float default ((0)),  -- Средняя тепловая нагрузка на ГВС в открытой системе из подающего трубопровода, Гкал/ч
    avgHLGVSopenSysRet float default ((0)),   -- Средняя тепловая нагрузка на ГВС в открытой системе из обратного трубопровода, Гкал/ч
    adjAvgHLGVSopenSysFlow float default ((0)),
    adjAvgHLGVSopenSysRet float default ((0)),
    perspAvgHLGVSopenSysFlow float default ((0)),
    perspAvgHLGVSopenSysRet float default ((0)),
    hourIrregCoeffOpen float default ((1.2)), -- Коэф. часовой неравномерности, откр.ГВС
    avgHLcompOpen float default ((0)),        -- Расчетные тепловые потери в рециркуляц. контуре ГВС, откр.ГВС, %
    tempRecircPipeOpen float default ((40)),  -- Температура в рециркуляционном трубопроводе ГВС, °C
    calcTempHWDOopen float default ((60)),    -- Расчетная температура горячей воды откр. ГВС, °C
    PDvalveInstallLocID int default (NULL),   -- Место установки клапана перепада давления: П- подача, О- Обратка
    setPDonRegulator float default ((0)),     -- Заданный перепад давления на регуляторе перепада, м.вод.ст
    setLeakageFlow float default ((0)),       -- Заданная утечка из подающего трубопровода, т/ч
    setLeakageRet float default ((0)),        -- Заданная утечка из обратного трубопровода, т/ч
    WEmeteringDeviceID int default (NULL),    -- Признак установки прибора учета
    volWaterHS float default ((13.3)),        -- Удельный объем воды в системе отопления, м^3*ч/Гкал
    volWaterVS float default ((5.5)),         -- Удельный объем воды в системе вентиляции, м^3*ч/Гкал
    minThrustDS float default ((0)),          -- Мин.располагаемый напор в распред.сети, м.вод.ст
    hydroResCloseSys float default ((0)),     -- Гидравлическое сопротивление для закрытой системы, м*ч^2/т^2
    hydroResCloseSysSummer float default ((0)),   -- Гидр.сопротивление закрытых систем в летний период, м*ч^2/т^2
    closeSysCalcSignID int default ((1)),     -- Признак расчета на заданное сопротивление закрытой системы теплопотребления
    hydroResWDOFlow float default ((0)),      -- Гидравлическое сопротивление для водоразбора из подающего трубопровода, м*ч^2/т^2
    calcSignOpenSysFlowID int default ((1)),  -- Признак расчета на заданое сопротивление открытой системы теплопотребления при водоразборе из подающего трубопровода
    hydroResWDORet float default ((0)),       -- Гидравлическое сопротивление для водоразбора из обратного трубопровода, м*ч^2/т^2
    calcSignResWDORetID int default ((1)),    -- Признак расчета на заданое сопротивление теплопотребителя для водоразбора из обратного трубопровода, пробел или символ 'Н'автоматический
    calcSignSetLoadCloseSys int default ((1)),    -- Признак расчета на заданную нагрузку в закрытых системах теплопотребления
    calcSignSetLoadOpenSysFlow int default ((1)), -- Признак расчета на заданную нагрузку из подающего трубопровода в открытых системах теплопотребления
    calcSignSetLoadOpenSysRet int default ((1)),  -- Признак расчета на заданную нагрузку из обратного трубопровода в открытых системах теплопотребления
    hydroThrustIn float default ((0)),        -- Пьезом.напор на входе тепл.пункта, плановый режим, м.вод.ст
    hydroThrustOut float default ((0)),       -- Пьезом.напор на выходе тепл.пункта, плановый режим, м.вод.ст
    calcExpendDep float default ((0)),        -- Расчетный расход на отопление, зав.СО, т/ч
    calcExpendIndep float default ((0)),      -- Расчетный расход на отопление, незав.СО, т/ч
    calcExpendVentil float default ((0)),     -- Расчетный расход на вентиляцию, т/ч
    calcExpendCond float default ((0)),       -- Расчетный расход на кондиционирование, т/ч
    calcExpendHWFlow float default ((0)),     -- Расчетный расход на ГВС, под.трубопров., т/ч
    calcExpendHWRet float default ((0)),      -- Расчетный расход на ГВС, обр.трубопров., т/ч
    calcExpendRecircOpen float default ((0)), -- Расчетный расход на рецирк., откр.ГВС, т/ч
    calcExpendHWparall float default ((0)),   -- Расчетный расход на ГВС, параллельная, т/ч
    calcExpendHWmix float default ((0)),      -- Расчетный расход на ГВС, смешанная, т/ч
    calcExpendHWconseq float default ((0)),   -- Расчетный расход на ГВС, последовательная, т/ч
    calcExpendHWpreON float default ((0)),    -- Расчетный расход на ГВС, предвключенная, т/ч
    calcThrustInWSD int default (NULL),       -- Расчетный напор на входе водоразборных приборов, м.вод.ст
    consumerStateID int default ((1)),        -- Состояние потребителя
    name varchar(255)                         -- Содержательное наименование потребителя
);
CREATE INDEX generalizedconsumers_nodeid_idx ON generalizedconsumers (nodeid);
---------------------------------
-- heatchambers - Гидравлика
-- heatchambers - Тепловая камера5
drop table if exists heatchambers;

create table heatchambers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL),
    slotsCount int default (NULL),
    slotsWeight varchar(50) default (NULL),
    internalHeight float default ((0)),
    internalWidth float default ((0)),
    internalLength float default ((0)),
    wallMaterial varchar(255) default (NULL),
    stairsCount int default (NULL),
    stopArmatureCount int default (NULL),
    ballValvesCount int default (NULL),
    airVentsCount int default (NULL) 
);
CREATE INDEX heatchambers_nodeid_idx ON heatchambers (nodeid);
---------------------------------
-- heatsources - Гидравлика
-- heatsources - Источник тепла2
drop table if exists heatsources;

create table heatsources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sourceName varchar(50) default (NULL),    -- Код теплогенерирующей установки
    nodeID int default (NULL),
    name varchar(50) default (NULL),          -- Наименование источника тепла
    stateID int default ((1)),                -- Состояние
    hSourceTypeID int default ((1)),          -- Тип
    hSourceID int default (NULL),
    hSourcePower float default ((0)),         -- Распол.мощность, Гкал/ч
    hSourcePowerInst float default ((0)),     -- Установл.мощность, Гкал/ч
    hSeasonBeginDate date default (NULL),     -- Дата начала отоп.периода
    hSeasonEndDate date default (NULL),       -- Дата окончания отоп.периода
    hSourceCode varchar(50) default (NULL),
    temperDWflowSummer float default ((0)),   -- Температура воды в подающем трубопроводе в летний период, °C
    temperDWretSummer float default ((0)),    -- Температура воды в обратном трубопроводе в летний период, °C
    specVolHS float default ((0)),            -- Удельный объем воды в системе отопления, м^3*ч/Гкал
    specVolVent float default ((0)),          -- Удельный объем воды в системе вентиляции, м^3*ч/Гкал
    expendDWnorm1 float default ((0)),        -- Норм.расх.сет.воды на выв., 1 тчк, т/ч
    expendDWnorm2 float default ((0)),        -- Норм.расх.сет.воды на выв., 2 тчк, т/ч
    expendDWnorm3 float default ((0)),        -- Норм.расх.сет.воды на выв., 3 тчк, т/ч
    expendDWnorm4 float default ((0)),        -- Норм.расх.сет.воды на выв., 4 тчк, т/ч
    expendDWnorm5 float default ((0)),        -- Норм.расх.сет.воды на выв., 5 тчк, т/ч
    managerPhone int default (NULL),          -- Тел./факс руковод.
    controllerPhone int default (NULL),       -- Тел./факс диспетч.
    powerSet float default ((0)),             -- Тепловая мощность установленная
    powerAvailable float default ((0)),       -- Тепловая мощность располагаемая
    heightTubeMark int default (NULL),
    heightAreaMark int default (NULL),
    repairWorks float default ((0)),          -- Ремонтные работы
    t1_summer float default ((0)),
    t2_summer float default ((0)),
    name_tg varchar(50) default (NULL),       -- Наименование
    heatLosCalcYear varchar(20) default (NULL),   -- Год
    graphTypeID int default ((1)) not null,   -- Тип температурного графика
    tn_1 float default ((8)) not null,        -- Температура наружн.воздуха начала/конца отоп. Сезона, °C
    tn_5 float default ((-32)) not null,      -- Расчетная темп.наружн.воздуха для отопления, °C
    tvn_r float default ((18)) not null,      -- Расчетная темп. воздуха внутри отапл.помещений, °C
    t1_r float default ((150)) not null,      -- Расчетная температура сет.воды в под.теплопр., °C
    t2_r float default ((70)) not null,       -- Расчетная температура сет.воды в обр.теплопр., °C
    t3_r float default ((95)) not null,       -- Расчетная температура сет.воды после узла смешения, °C
    q_r float default ((0)) not null,         -- Расчетная нагрузка на отопление, Гкал/ч
    t1_2r float default ((70)) not null,      -- Температура воды нижней срезки графика, °C
    t1_4r float default ((200)) not null,     -- Температура воды верхней срезки графика, °C
    tvb_tr float default ((18)),              -- Требуемая температура воздуха внутри отапл.помещений, °C
    uf float default ((2.2)) not null,        -- Фактический коэфф.смещения
    t2_2r float default ((0)) not null,       -- Температура воды нижней срезки обрат.воды
    q_gv float default ((0)) not null,        -- Расчетная нагрузка в ГВС, Гкал/ч
    tg_r float default ((60)) not null,       -- Темпер.горячей воды в точках водоразбора, °C
    tx_r float default ((5)) not null,        -- Темпер.холодной воды, °C
    t2_gv float default ((60)) not null,      -- Темпер.воды в обратном трубопр.для переключения водоразбора, °C
    pr int default ((0)) not null,            -- Признак способа водоразбора горячей воды
    g1 float default ((0.6)) not null,        -- Коэфф.гидравл.устойчивости под.теплопровода
    g2 float default ((0.3)) not null,        -- Коэфф.гидравл.устойчивости обр.теплопровода
    t_gv1 float default ((6)) not null,       -- Величина недогрева в первой ступени подогр. ГВС, °C
    deployedTempGraphID int default ((0)),
    v float default ((0)) not null,           -- Скорость ветра, м/c
    date_on float,                            -- Дата иcполнения
    name_exe varchar(50),                     -- Исполнитель
    name_manager varchar(50),
    dt2_co float default ((10)) not null,     -- Разность обрат.воды при зав.СО и нез., °C
    t2pod_parl float default ((30)) not null, -- Темп.на вых.подогр.паралл.ГВ, т.излома, °C
    dt2v_sm_noavm float default ((5)) not null,   -- Недогрев водопр.воды в 1ступ.,смеш.ГВ, част.авт.ТП, °C
    dt2v_sm_avm float default ((10)) not null,    -- Недогрев водопр.воды в 1ступ.,смеш.ГВ, авт.ТП, °C
    t1pod_sm float default ((41.7)) not null, -- Темп.на вых.СО,смеш.ГВ, т.излома, °C
    t1pod_posll float default ((41.7)) not null,  -- Темп.на вых.СО,послед.ГВ, т.излома, °C
    dt2v_posl float default ((5)) not null,   -- Недогрев водопр.воды в 1ступ.,посл.ГВ, °C
    length_1 int default ((31)),
    length_2 int default ((28)),
    length_3 int default ((31)),
    length_4 int default ((30)),
    length_5 int default ((31)),
    length_6 int default ((30)),
    length_7 int default ((31)),
    length_8 int default ((31)),
    length_9 int default ((30)),
    length_10 int default ((31)),
    length_11 int default ((30)),
    length_12 int default ((31)),
    t_1 float default ((5)),
    t_2 float default ((5)),
    t_3 float default ((5)),
    t_4 float default ((5)),
    t_5 float default ((15)),
    t_6 float default ((15)),
    t_7 float default ((15)),
    t_8 float default ((15)),
    t_9 float default ((15)),
    t_10 float default ((5)),
    t_11 float default ((5)),
    t_12 float default ((5)),
    t1_1 float default ((0)),
    t1_2 float default ((0)),
    t1_3 float default ((0)),
    t1_4 float default ((0)),
    t1_5 float default ((0)),
    t1_6 float default ((0)),
    t1_7 float default ((0)),
    t1_8 float default ((0)),
    t1_9 float default ((0)),
    t1_10 float default ((0)),
    t1_11 float default ((0)),
    t1_12 float default ((0)),
    t2_1 float default ((0)),
    t2_2 float default ((0)),
    t2_3 float default ((0)),
    t2_4 float default ((0)),
    t2_5 float default ((0)),
    t2_6 float default ((0)),
    t2_7 float default ((0)),
    t2_8 float default ((0)),
    t2_9 float default ((0)),
    t2_10 float default ((0)),
    t2_11 float default ((0)),
    t2_12 float default ((0)),
    length_1_fakt int default ((31)),
    length_2_fakt int default ((28)),
    length_3_fakt int default ((31)),
    length_4_fakt int default ((30)),
    length_5_fakt int default ((31)),
    length_6_fakt int default ((30)),
    length_7_fakt int default ((31)),
    length_8_fakt int default ((31)),
    length_9_fakt int default ((30)),
    length_10_fakt int default ((31)),
    length_11_fakt int default ((30)),
    length_12_fakt int default ((31)),
    t_1_fakt float default ((0)),
    t_2_fakt float default ((0)),
    t_3_fakt float default ((0)),
    t_4_fakt float default ((0)),
    t_5_fakt float default ((0)),
    t_6_fakt float default ((0)),
    t_7_fakt float default ((0)),
    t_8_fakt float default ((0)),
    t_9_fakt float default ((0)),
    t_10_fakt float default ((0)),
    t_11_fakt float default ((0)),
    t_12_fakt float default ((0)),
    t1_1_fakt float default ((0)),
    t1_2_fakt float default ((0)),
    t1_3_fakt float default ((0)),
    t1_4_fakt float default ((0)),
    t1_5_fakt float default ((0)),
    t1_6_fakt float default ((0)),
    t1_7_fakt float default ((0)),
    t1_8_fakt float default ((0)),
    t1_9_fakt float default ((0)),
    t1_10_fakt float default ((0)),
    t1_11_fakt float default ((0)),
    t1_12_fakt float default ((0)),
    t2_1_fakt float default ((0)),
    t2_2_fakt float default ((0)),
    t2_3_fakt float default ((0)),
    t2_4_fakt float default ((0)),
    t2_5_fakt float default ((0)),
    t2_6_fakt float default ((0)),
    t2_7_fakt float default ((0)),
    t2_8_fakt float default ((0)),
    t2_9_fakt float default ((0)),
    t2_10_fakt float default ((0)),
    t2_11_fakt float default ((0)),
    t2_12_fakt float default ((0)),
    Gpod_1_fakt float default ((0)),
    Gpod_2_fakt float default ((0)),
    Gpod_3_fakt float default ((0)),
    Gpod_4_fakt float default ((0)),
    Gpod_5_fakt float default ((0)),
    Gpod_6_fakt float default ((0)),
    Gpod_7_fakt float default ((0)),
    Gpod_8_fakt float default ((0)),
    Gpod_9_fakt float default ((0)),
    Gpod_10_fakt float default ((0)),
    Gpod_11_fakt float default ((0)),
    Gpod_12_fakt float default ((0)),
    Ggvs_pribor_1_fakt float default ((0)),
    Ggvs_pribor_2_fakt float default ((0)),
    Ggvs_pribor_3_fakt float default ((0)),
    Ggvs_pribor_4_fakt float default ((0)),
    Ggvs_pribor_5_fakt float default ((0)),
    Ggvs_pribor_6_fakt float default ((0)),
    Ggvs_pribor_7_fakt float default ((0)),
    Ggvs_pribor_8_fakt float default ((0)),
    Ggvs_pribor_9_fakt float default ((0)),
    Ggvs_pribor_10_fakt float default ((0)),
    Ggvs_pribor_11_fakt float default ((0)),
    Ggvs_pribor_12_fakt float default ((0)),
    Gakt_tex_1_fakt float default ((0)),
    Gakt_tex_2_fakt float default ((0)),
    Gakt_tex_3_fakt float default ((0)),
    Gakt_tex_4_fakt float default ((0)),
    Gakt_tex_5_fakt float default ((0)),
    Gakt_tex_6_fakt float default ((0)),
    Gakt_tex_7_fakt float default ((0)),
    Gakt_tex_8_fakt float default ((0)),
    Gakt_tex_9_fakt float default ((0)),
    Gakt_tex_10_fakt float default ((0)),
    Gakt_tex_11_fakt float default ((0)),
    Gakt_tex_12_fakt float default ((0)),
    Gakt_avarija_1_fakt float default ((0)),
    Gakt_avarija_2_fakt float default ((0)),
    Gakt_avarija_3_fakt float default ((0)),
    Gakt_avarija_4_fakt float default ((0)),
    Gakt_avarija_5_fakt float default ((0)),
    Gakt_avarija_6_fakt float default ((0)),
    Gakt_avarija_7_fakt float default ((0)),
    Gakt_avarija_8_fakt float default ((0)),
    Gakt_avarija_9_fakt float default ((0)),
    Gakt_avarija_10_fakt float default ((0)),
    Gakt_avarija_11_fakt float default ((0)),
    Gakt_avarija_12_fakt float default ((0)),
    id_old int default ((0)) 
);
CREATE INDEX heatsources_nodeid_idx ON heatsources (nodeid);
---------------------------------
-- realconsumers - Гидравлика
-- realconsumers - Потребитель реальный
drop table if exists realconsumers;

create table realconsumers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL),          -- Содержательное наименование потребителя
    consumerStateID int default ((1)),        -- Состояние
    automDegID int default ((1)),             -- Степень автоматизации: А-автоматизированный, Ч-частично автоматизированный, Н-неавтоматизированная
    sectConsumerCode varchar(50) default (NULL),  -- Код секционированного потребителя
    schemeNum varchar(50) default ('1.1'),    -- Номер расчетной схемы
    buildHeight float default ((0)),          -- Высота здания, м
    accumCoeff float default ((0)),           -- Коэффициент аккумуляции здания
    specExpendID int default (NULL),          -- Код УР
    calcTemperatureID int default (NULL),     -- Код расчетных температур, °C
    gvsLoadGraphID int default (NULL),        -- Код суточного графика нагрузки ГВ
    varCoeffID int default (NULL),            -- Код КВ
    calcHLdep float default ((0)),            -- Расчетная нагрузка на отопление, зав.СО, Гкал/ч
    calcHLindep float default ((0)),          -- Расчетная нагрузка на отопление, незав.СО, Гкал/ч
    relLoadFacade float default ((0)),        -- Отн.нагрузка уличного фасада, %
    calcInternHD float default ((0)),         -- Расчетные внутренние тепловыделения, Гкал/ч
    contCalcHLdep float default ((0)),        -- Договорнаянагрузка на отопление, зав.СО, Гкал/ч
    contcalcHLindep float default ((0)),      -- Договорная нагрузка на отопление, незав.СО, Гкал/ч
    contRelLoadFacade float default ((0)),    -- Договор.отн.нагрузка уличного фасада, %
    contInternHD float default ((0)),         -- Договор ВнутрТепловыделения, Гкал/ч
    perspCalcHLdep float default ((0)),       -- Перспективнаянагрузка на отопление, зав.СО, Гкал/ч
    perspcalcHLindep float default ((0)),     -- Перспективная нагрузка на отопление, незав.СО, Гкал/ч
    perspRelLoadFacade float default ((0)),   -- Перспенкт.отн.нагрузка уличного фасада, %
    perspInternHD float default ((0)),        -- Перспект ВнутрТепловыделения, Гкал/ч
    calcHLventil float default ((0)),         -- Расчетная нагрузка на вентиляцию, Гкал/ч
    expendHWpart float default ((0)),         -- Доля расхода воды через КУ при откл.по возд.
    contCalcHLventil float default ((0)),     -- Договорная нагрузка на вентиляцию, Гкал/ч
    perspCalcHLventil float default ((0)),    -- Перспективная нагрузка на вентиляцию, Гкал/ч
    avgHLcond float default ((0)),            -- Расчетная нагрузка на кондиционирование, Гкал/ч
    contAvgHLcond float default ((0)),        -- Договорная нагрузка на кондиционирование, Гкал/ч
    perspAvgHLcond float default ((0)),       -- Договорная нагрузка на кондиционирование, Гкал/ч
    avgHLcloseSys float default ((0)),        -- Расчетная нагрузка на технологию, закрытая, Гкал/ч
    avgHLopenSysFlow float default ((0)),     -- Средняя тепл.нагрузка на технологию, под.труб., Гкал/ч
    avgHLopenSysRet float default ((0)),      -- Средняя тепл.нагрузка на технологию, обр.труб., Гкал/ч
    contAvgHLcloseSys float default ((0)),    -- Договорная нагрузка на технологию, закрытая, Гкал/ч
    contAvgHLopenSysFlow float default ((0)), -- Договор.СреднНагрузкаТехнологиюПодача, Гкал/ч
    contAvgHLopenSysRet float default ((0)),  -- Договор.СреднНагрузкаТехнологиюОбратка, Гкал/ч
    perspAvgHLclose float default ((0)),      -- Договорная нагрузка на технологию, закрытая, Гкал/ч
    perspAvgHLopenFlow float default ((0)),   -- Договор.СреднНагрузкаТехнологиюПодача, Гкал/ч
    contAvgHLopenRet float default ((0)),     -- Перспект.СреднНагрузкаТехнологиюОбратка, Гкал/ч
    avgHLGVSopenFlow float default ((0)),     -- Средняя тепл.нагрузка на ГВ, подающий теплопровод, Гкал/ч
    avgHLGVSopenRet float default ((0)),      -- Средняя тепл.нагрузка на ГВ, обратный теплопровод, Гкал/ч
    avgHLGVScloseParall float default ((0)),  -- Средняя тепл.нагрузка на ГВ, параллельная сх., Гкал/ч
    avgHLGVScloseMix float default ((0)),     -- Средняя тепл.нагрузка на ГВ, смешанная сх., Гкал/ч
    avgHLGVScloseConseq float default ((0)),  -- Средняя тепл.нагрузка на ГВ последовательная сх., Гкал/ч
    avgHLGVSclosePreON float default ((0)),   -- Средняя тепл.нагрузка на ГВ, предвключ.сх., Гкал/ч
    contAvgHLGVSopenFlow float default ((0)), -- Договор.средняя нагрузка на ГВ, подающий трубопров., Гкал/ч
    contAvgHLGVSopenRet float default ((0)),  -- Договор.средняя нагрузка на ГВ, обратный трубопров., Гкал/ч
    contAvgHLGVScloseParall float default ((0)),  -- Договор.средняя нагрузка на ГВ, параллельная сх., Гкал/ч
    contAvgHLGVScloseMix float default ((0)), -- Договор.средняя нагрузка на ГВ, смешанная сх., Гкал/ч
    contAvgHLGVScloseConseq float default ((0)),  -- Договор.средняя нагрузка на ГВ, последовательная сх., Гкал/ч
    contAvgHLGVSclosePreON float default ((0)),   -- Договор.средняя тепл.нагрузка на ГВ, предвключ.сх., Гкал/ч
    perspAvgHLGVSopenFlow float default ((0)),    -- Перспект.средняя нагрузка на ГВ, подающий трубопров., Гкал/ч
    perspAvgHLGVSopenRet float default ((0)), -- Перспект.средняя нагрузка на ГВ, обратный трубопров., Гкал/ч
    perspAvgHLGVScloseParall float default ((0)), -- Перспект.средняя нагрузка на ГВ, параллельная сх., Гкал/ч
    perspAvgHLGVScloseMix float default ((0)),    -- Перспект.средняя нагрузка на ГВ, смешанная сх., Гкал/ч
    perspAvgHLGVScloseConseq float default ((0)), -- Перспект.средняя нагрузка на ГВ, последовательная сх., Гкал/ч
    perspAvgHLGVSclosePreON float default ((0)),  -- Перспект.средняя тепл.нагрузка на ГВ, предвключ.сх., Гкал/ч
    hydroModeSignID int default ((1)),        -- Признак расчета аварийного режима потребителя
    mixFactCoeff float default ((2.2)),       -- Коэффициент смешения элеватора
    hourIrregCoeff float default ((1.2)),     -- Коэффициент часовой неравномерности нагрузки горячего водоснабжения
    circHLosOpen float default ((0)),         -- Расчетные тепловые потери в рецирк. контуре ГВС, %
    tempRecircPipe float default ((40)),       -- Температура в рециркуляционном трубопроводе ГВС, °C
    setLeakageFlow float default ((0)),       -- Утечка из подающего теплопровода., т/ч
    setLeakageRet float default ((0)),        -- Утечка из обратного теплопровода, т/ч
    WEmeteringDeviceID int default (NULL),    -- Прибор учета расхода воды
    volWaterHS float default ((13.3)),        -- Удельный объем воды в системе отопления, м^3*ч/Гкал
    volWaterVS float default ((5.5)),         -- Удельный объем воды в системе вентиляции, м^3*ч/Гкал
    hydroResCloseSys float default ((0)),     -- Гидр.сопротивл. закр. Систем, м*ч^2/т^2
    hydroResCloseSysSummer float default ((0)),   -- Гидр.сопротивл.потребителя в летний период, м*ч^2/т^2
    closeSysCalcSignID int default ((1)),     -- Признак гид.сопр.закр.ТП
    hydroResWDOFlow float default ((0)),      -- Гидр.сопротивл. откр. ГВС, подающий трубпр., м*ч^2/т^2
    calcSignOpenSysFlowID int default ((1)),  -- Признак гид.сопр.под.труб.
    hydroResWDORet float default ((0)),       -- Гидр.сопротивл. откр. ГВС, обратный трубпр., м*ч^2/т^2
    calcSignResWDORetID int default ((1)),    -- Признак гид.сопр.обр.труб.
    calcSignSetLoadCloseSys int default (NULL),   -- Признак расчета гидр.реж.закрТП
    calcSignSetLoadOpenSysFlow int default (NULL),    -- Признак расчета гидр.реж.откр ГВС под.теплопр.
    calcSignSetLoadOpenSysRet int default (NULL), -- Признак расчета гидр.реж.открГВС обр.теплопр.
    hydroThrustIn float default ((0)),        -- Пьезом.напор на входе тепл.пункта, плановый режим, м.вод.ст
    hydroThrustOut float default ((0)),       -- Пьезом.напор на выходе тепл.пункта, плановый режим, м.вод.ст
    calcExpendDep float default ((0)),        -- Расчетный расход на отопление, зав.СО, т/ч
    calcExpendIndep float default ((0)),      -- Расчетный расход на отопление, незав.СО, т/ч
    calcExpendVentil float default ((0)),     -- Расчетный расход на вентиляцию, т/ч
    calcExpendCond float default ((0)),       -- Расчетный расход на кондиционирование, т/ч
    calcExpendHWFlow float default ((0)),     -- Расчетный расход на ГВС, под.трубопров., т/ч
    calcExpendHWRet float default ((0)),      -- Расчетный расход на ГВС, обр.трубопров., т/ч
    calcExpendRecircOpen float default ((0)), -- Расчетный расход на рецирк., откр.ГВС, т/ч
    calcExpendHWparall float default ((0)),   -- Расчетный расход на ГВС, параллельная, т/ч
    calcExpendHWmix float default ((0)),      -- Расчетный расход на ГВС, смешанная, т/ч
    calcExpendHWconseq float default ((0)),   -- Расчетный расход на ГВС, последовательная, т/ч
    calcExpendHWpreON float default ((0)),    -- Расчетный расход на ГВС, предвключенная, т/ч
    throtStageSignID int default ((1)),       -- Признак ступени дросселирования
    diameterThrotDiaph float default ((3)),   -- Мин.диам.дрос.диафр., мм
    diameterElevNozzle float default ((3)),   -- Мин.диам.сопла элеват., мм
    temperChartSignID int default ((1)),      -- Темп.график
    calcSignRes int default (NULL),           -- Расчет сопротивления факт.режима
    calcSignHL int default (NULL),            -- Расчет теплопотребл. факт.режима
    parallHeatersCount1 int default (NULL),   -- Кол.вкл.подогрев.1 ст.ГВ, штук(и)
    parallHeatersCount2 int default (NULL),   -- Кол.вкл.подогрев.2 ст.ГВ, штук(и)
    parallHeatersCountIndep int default (NULL),   -- Кол.вкл.подогрев.незав.СО, штук(и)
    calcThrustLosHS float default ((1.5)),    -- Расч.потери напора в СО (подогр.), м.вод.ст
    calcThrustLosAH float default ((5)),      -- Расч.потери напора в КУ, м.вод.ст
    calcThrustLosAC float default ((6)),      -- Расч.потери напора на конд., м.вод.ст
    calcThrustLosFlow float default ((3)),    -- Расч.потери напора в под.труб.откр.ГВ, м.вод.ст
    calcThrustLosFlowCirc float default ((4)),    -- Расч.потери напора в цирк.труб.отк.ГВС, м.вод.ст
    calcThrustInWDO float default ((25)),     -- Расч.напор на вх.водоразб.приборов, м.вод.ст
    calcThrustLosHeaters1 float default ((4)),    -- Расч.потери напора на 1 ст.ГВ, м.вод.ст
    calcThrustLosHeaters2 float default ((4)),    -- Расч.потери напора на 2 ст.ГВ, м.вод.ст
    PDvalveInstallLocID int default (NULL),   -- Место установки клапана перепада напора: П- подача, О- Обратка
    setPDonRegulator float default ((0)),     -- Заданный перепад напора на регуляторе, м.вод.ст
    calcFerDiameterSignID int default ((1)), -- Признак шайбы в потребитель Р -разрешить, Н-нельзя записывать
    calcTempHR float default ((18)),          -- Расч.темп. в отапл.помещениях, °C
    calcTempVS float default ((18)),          -- Расч.темп.нагр.возд.после КУ, °C
    calcTempHWDO float default ((60)),        -- Расч.темп.горячей воды, °C
    responsibleID int default (NULL),         -- Техник
    contractNumber varchar(50) default (NULL),    -- Номера договоров с теплоснабжающей организацией
    stopValveTypeID int default (NULL),
    meterDevWorkSign int default (NULL),      -- Признак работы прибора учета
    meterDevSafety int default (NULL),        -- Сохранность пломбы прибора учета
    meterDevStampNum varchar(50) default (NULL),  -- Номер пломбы прибора учета
    isolationType float default ((0)),        -- Изоляция
    buildingTypeID int default ((1)),         -- Тип здания
    heatSourcePTSID int,                      -- Источник тепла
    heatPointID int,                          -- Принадлежность к Тепловому пункту
    countUserGV int default ((0)),            -- Число пользователей горячего водоснабжения, чел
    countBusinessConsumers int default ((0)), -- Количество потребителей-предприятий, шт
    area float default ((0)),                 -- Отапливаемая площадь, м^2
    buildingVolume float default ((0)),       -- Объем отапливаемого здания, м^3
    basementVolume float default ((0)),       -- Объем подвала отапливаемого здания, м^3
    builtInVolume float default ((0)),        -- Объем встроенных помещений отапливаемого здания, м^3
    reduceBuildingVolume float default ((0)),
    countFloors int default ((0)),            -- Количество этажей
    builtYear int default ((0)),              -- Год ввода в эксплуатацию
    streetID int,                             -- Улица
    houseNumber varchar(255),                 -- Номер дома
    note_1 varchar,                           -- Приложение 1
    note_2 varchar,                           -- Приложение 2
    note_pts varchar,                         -- Комментарий ПТС
    note_regime varchar,                       -- Комментарий группы режимов

    elevatornuminst int, -- Номер элеватора
    diameternozzle float, -- Диаметр сопла элеватора

    b23 float default ((0)),   -- Отопление                                         1   
    b28 float default ((0)),   -- Вентиляция (воздушного отопления)                 2   
    b32 float default ((0)),   -- ГВС, закрытая                                     3   
    b20 float default ((0)),   -- Подпорная                                         4   
    b14 float default ((0)),   -- Вход теплового пункта                             5   
    b38 float default ((0)),   -- Ограничительная в циркуляционном контуре ГВС      6   
    b35 float default ((0)),   -- На входе подающего трубопровода открытой ГВС,     37  
    b36 float default ((0)),   -- Подпорно-циркуляционная в открытой ГВС,           45  



    zd7 int default((1)),  -- Вход ТП
    zd8 int default((1)),  -- Выход ТП
    zd27 int default((1)),  -- Вход СО
    zd28 int default((1)),  -- Вх.II ступен.ГВ
    zd36 int default((1)),  -- ОткрГВ подача
    zd38 int default((1)),  -- ОткрГВ обратка
    zd39 int default((2)),  -- Летняя закрГВС
    zd48 int default((1)),  -- Вход СВ
    zd49 int default((2)),  -- Летняя открГВС
    zd50 int default((2)),  -- Летняя открГВС
    zd82 int default((1)),  -- Вх.I ступен.ГВ
    zd83 int default((1)),  -- Вх.II ступен.ГВ
    zd84 int default((1))  -- Вх.I ступен.ГВ


);
CREATE INDEX realconsumers_nodeid_idx ON realconsumers (nodeid);
---------------------------------
-- refillnodes - Гидравлика
-- refillnodes - Узел подпитки
drop table if exists refillnodes;

create table refillnodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    externalSignID int default (NULL),        -- Признак теплопровода узла подпитки
    refillExpend float default ((0)),         -- Расход на подпитку
    WDO float default ((0)),                  -- Расход на водоразбор
    refillLoss float default ((0)),           -- Расход подпитки в % отношении от общей суммы утечки, %
    diameterInternal float default ((0)),     -- Внутренний диаметр бака, мм
    waterVolUp float default ((0)),           -- Верхний допустимый уровень воды в баке, м
    waterVolDown float default ((0)),         -- Нижний допустимый уровень воды в баке, м
    waterVolUpSet float default ((0)),        -- Заданный уровень воды в баке, м
    potsCount int default (NULL),             -- Количество баков, штук(и)
    potsSumVol float default ((0)),           -- Суммарный объём баков-аккумуляторов, м^3
    potWorkingSign varchar(50) default (NULL),    -- Признак режима работы бака
    chargeExpend float default ((0)),         -- Расход на зарядку, т/ч
    dischargeExpend float default ((0)),      -- Расход на разрядку, т/ч
    setPressRet int default (NULL)            -- Заданный напор в обратном теплопроводе, м.вод.ст
);
CREATE INDEX refillnodes_nodeid_idx ON refillnodes (nodeid);
---------------------------------
-- threewayvalves - Гидравлика
-- threewayvalves - Клапан трехходовой
drop table if exists threewayvalves;

create table threewayvalves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    structure varchar,                        -- Структурированное описание
    state varchar(50) default ((1)),          -- Состояние клапана
    purpose varchar(50) default (NULL),       -- Назначение
    calcMixFactCoeff float default ((0)),     -- Расчетный коэффициент смешения
    calcThrustLos float default ((0)),        -- Расчетные потери напора в регулируемом контуре, м.вод.ст
    expendCharStraight varchar(50) default (NULL),    -- Расходная характеристика прямого хода
    expendCharVert varchar(50) default (NULL),    -- Расходная характеристика вертикального хода
    authority float default ((0)),            -- Требуемый авторитет клапана
    calcCapDeviation int default (NULL),      -- Отклонение расчетной пропускной способности от требуемой
    type varchar(50) default (NULL),          -- Марка клапана
    capacity float default ((0)),             -- Расчетная пропускная способность, м^3/ч
    regulator varchar(50) default (NULL),     -- Регулирующий орган
    maxPD float default ((0)),                -- Допустимый перепад давления на клапане, м.вод.ст
    diameterNomin float default ((0)),        -- Диаметр номинальный, мм
    calcExpendNodeMix float default ((0)),    -- Расчетный расход на регулируемом участке, т/ч
    pumpStationName varchar(50) default (NULL)    -- Район местонахождения теплопровода
);
CREATE INDEX threewayvalves_nodeid_idx ON threewayvalves (nodeid);
---------------------------------
-- deployedtempgraphs - Гидравлика
-- deployedtempgraphs - Развернутые температурные графики
drop table if exists deployedtempgraphs;

create table deployedtempgraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hSourceID int default (NULL),
    tn float default ((0)) not null,          -- Темпер. наружн. воздуха, °C
    Q_otn float default ((0)) not null,       -- Относительный расход на отопление
    t1 float default ((0)) not null,          -- Темп.сет.воды в подающем теплопроводе, °C
    t2 float default ((0)) not null,          -- Темп.сет.воды в обратном теплопроводе, °C
    t3 float default ((0)) not null,          -- Темп.сет.воды после узла смешения, °C
    tv float default ((0)) not null,          -- Темп.сет.воды в подающем теплопр.с учетом ветра, °C
    t_bn float default ((0)) not null,        -- Температура внутри отапливаемых помещений
    tg float default ((0)) not null 
);
---------------------------------
-- internalnodes - Гидравлика
-- internalnodes - Внутренний узел
drop table if exists internalnodes;

create table internalnodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL) 
);
CREATE INDEX internalnodes_nodeid_idx ON internalnodes (nodeid);
---------------------------------
-- overgroundnodes - Гидравлика
-- overgroundnodes - Надземный узел5
drop table if exists overgroundnodes;

create table overgroundnodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL),
    stopArmatureDiameter float default ((0)) 
);
CREATE INDEX overgroundnodes_nodeid_idx ON overgroundnodes (nodeid);
---------------------------------
-- pavilions - Гидравлика
-- pavilions - Павильон
drop table if exists pavilions;

create table pavilions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL) 
);
CREATE INDEX pavilions_nodeid_idx ON pavilions (nodeid);
---------------------------------
-- pumpstations - Гидравлика
-- pumpstations - Насосная станция2
drop table if exists pumpstations;

create table pumpstations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),                -- Идентификатор точечного объекта
    name varchar(50) default (NULL),          -- Содержательное наименование насосной станции
    purpose varchar(50) default (NULL),       -- Назначение
    capacity float default ((0)),             -- Производительность
    pumpCountFlow int default (NULL),         -- Количество насосов на подаче
    pumpCountRet int default (NULL),          -- Количество насосов на обратке
    state varchar(50) default (NULL),         -- Состояние насосной станции
    stateID int default ((1)),                -- Ссылка на состояние
    heightTubeMark float default ((0)),       -- Геодезическая отметка оси трубы, м
    heightAreaMark float default ((0))        -- Геодезическая отметка поверхности земли, м
);
CREATE INDEX pumpstations_nodeid_idx ON pumpstations (nodeid);
---------------------------------
-- trps - Гидравлика
-- trps - ТРП
drop table if exists trps;

create table trps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL) 
);
CREATE INDEX trps_nodeid_idx ON trps (nodeid);
---------------------------------
-- undergroundnodes - Гидравлика
-- undergroundnodes - Подземный узел5
drop table if exists undergroundnodes;

create table undergroundnodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL),
    stopArmatureDiameter float default ((0)) 
);
CREATE INDEX undergroundnodes_nodeid_idx ON undergroundnodes (nodeid);
---------------------------------
-- uninstallednodes - Гидравлика
-- uninstallednodes - Неустановленный узел5
drop table if exists uninstallednodes;

create table uninstallednodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int default (NULL),
    name varchar(50) default (NULL) 
);
CREATE INDEX uninstallednodes_nodeid_idx ON uninstallednodes (nodeid);
---------------------------------
-- airheaters - Гидравлика
-- airheaters - Калориферная установка
drop table if exists airheaters;

create table airheaters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    fanInstall varchar(50) default (NULL),    -- Установка вентилятора
    scheme varchar(50) default (NULL),        -- Сх.соединения кал
    airHeatersCount float default ((0)),      -- Кол.калориф.в ряду, штук(и)
    rowsCount float default ((0)),            -- Кол.рядов, штук(и)
    storesCount float default ((0)),          -- Кол.этажей, штук(и)
    airHeaterType varchar(50) default (NULL), -- Тип калорифера
    contaminCoeff float default ((0)),        -- Коэф.загрязнения
    pressCoeff float default ((0)),           -- Коэф.снижения темп.напора
    location varchar(50) default (NULL)       -- Назначение
);
CREATE INDEX airheaters_lineid_idx ON airheaters (lineid);
---------------------------------
-- bypass - Гидравлика
-- bypass - Байпас
drop table if exists bypass;

create table bypass (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    pipelineSignID int not null,              -- Признак теплопр. с регул.напором
    standardID int default ((1)),             -- Стандарт
    standardTubeLink int default (NULL),      -- Ссылка на стандартную трубу
    length int default ((1)),                 -- Длина, м
    diameterInternal float default ((400)),   -- Внутр.диам., мм
    tubeRoughness float default ((0.5)),      -- Экв. шерохов.трубы, мм
    resCoeffsSum float default ((0)),         -- Сумма коэфф местных сопр..
    locInstall varchar(50) default (NULL),    -- Место установки
    h float default ((0)),
    deltaH float default ((0)),
    deltaQ float default ((0)),               -- Допуст.откл.расхода, т/ч
    q float default ((0)),                    -- Регул.расход, т/ч
    regulatorStateID int default ((1))        -- Состояние
);
CREATE INDEX bypass_lineid_idx ON bypass (lineid);
CREATE INDEX bypass_nodeid_idx ON bypass (nodeid);
---------------------------------
-- consumptregulators - Гидравлика
-- consumptregulators - Регулятор расхода
drop table if exists consumptregulators;

create table consumptregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    regConsMean float default ((0)),          -- Значение регулируемого расхода, т/ч
    workAttrID int default (NULL),            -- Период работы
    hydroResOpen float default ((0)),         -- Гидравлическое сопротивление клапана в открытом состоянии, м*ч^2/т^2
    hydroResClose float default ((0)),        -- Гидравлическое сопротивление клапана в закрытом состоянии, м*ч^2/т^2
    regValveCap int default (NULL),           -- Пропускная способность регулирующего клапана, т/ч
    relatLeakage float default ((0)),         -- Относительная протечка в % от KV(негерметичность затвора), %
    plumsConsumption float default ((0)),     -- Расход на слив, м^3/ч
    opc varchar(50) default (NULL),
    deltaH float default ((0)),               -- Допустимое отклонение расхода от заданного значения, т/ч
    regulatorStateID int default ((1))        -- Состояние
);
CREATE INDEX consumptregulators_lineid_idx ON consumptregulators (lineid);
CREATE INDEX consumptregulators_nodeid_idx ON consumptregulators (nodeid);
---------------------------------
-- dampers - Гидравлика
-- dampers - Задвижка
drop table if exists dampers;

create table dampers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    dispatcherSwitch varchar(50) default (NULL),  -- Место установки
    diameterCondit float default ((400)),     -- Диаметр условный, мм
    partDempOpen float default ((0)),         -- Част.откр.задв., % от KV, %
    name varchar(50) default (NULL),          -- Наименование
    standardDampLink int default (NULL),      -- Тип задвижки
    turnCount int default ((0)),              -- Факт.кол.оборот.махов.
    gateControl int default (NULL),           -- Призн.управл.затвор.с земли
    clue int default (NULL),                  -- Возм.закрыт.ключом
    thrustCollar int default (NULL),          -- Налич.упорн.колец
    relatLeakage float default ((0)),         -- Негерм.затвора, % от KV, %
    opc varchar(50) default (NULL),
    damperArmatureStateID int default ((1))   -- Состояние
);
CREATE INDEX dampers_lineid_idx ON dampers (lineid);
---------------------------------
-- diaphragms - Гидравлика
-- diaphragms - Диафрагма
drop table if exists diaphragms;

create table diaphragms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    throtDiaphLoc varchar(50) default (NULL), -- Место установки
    diameterInternal float default ((0)),     -- Внут.диаметр, мм
    consInstDiaphCount int default ((1)),     -- Колич. диафр., штук(и)
    entryMark varchar(50) default (NULL),     -- Признак использования
    stateID int default ((1))                 -- Состояние
);
CREATE INDEX diaphragms_lineid_idx ON diaphragms (lineid);
---------------------------------
-- elevators - Гидравлика
-- elevators - Элеватор
drop table if exists elevators;

create table elevators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    elevatorType int default (NULL),          -- Тип элеватора
    elevatorNumInst int default (NULL),       -- Номер элеватора, установленный
    diameterNozzle float default ((0)),       -- Диаметр сопла элеватора, установленный, мм
    entryMark varchar(50) default (NULL),     -- Признак изпользования рассчитанного элеватора
    diameterChamber float default ((0)),      -- Диаметр камеры смешения (горловины),, мм
    length float default ((0)),               -- Длина корпуса, мм
    diameterInletFlange float default ((0)),  -- Диаметр входного фланца, мм
    diameterOutletFlange float default ((0)), -- Диаметр выходного фланца, мм
    diameterSuctionPipe float default ((0)),  -- Диаметр фланца патрубка подсоса, мм
    material varchar(50) default (NULL),      -- Материал корпуса
    stateID int default ((1)) 
);
CREATE INDEX elevators_lineid_idx ON elevators (lineid);
---------------------------------
-- heatexchangers - Гидравлика
-- heatexchangers - Теплообменник
drop table if exists heatexchangers;

create table heatexchangers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    heatExchType varchar(50) default (NULL),  -- Тип теплообменника
    heatExchCode int default (NULL),          -- Код теплообменника
    location int default (NULL),              -- Функциональное назначение
    stateID int default ((1)) 
);
CREATE INDEX heatexchangers_lineid_idx ON heatexchangers (lineid);
---------------------------------
-- heatpipesections - Гидравлика
-- heatpipesections - Участок теплопровода
drop table if exists heatpipesections;

create table heatpipesections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    pipeSectionID int default (NULL),         -- Принадлежность участку сети ПТС
    pipeSectStateIDflow int default ((1)),    -- Состояние участка подающего теплопровода
    pipeSectStateIDret int default ((1)),     -- Состояние участка обратного теплопровода
    standardID int default ((1)),             -- Стандарт труб на участке
    standardTubeLink int default (NULL),      -- Ссылка на стандартную трубу
    tubesCount int default ((1)),             -- Количество труб на участке
    diameterInternal float default ((1000)),  -- Диаметр внутренний, мм
    diameterCondit float default ((1000)),    -- Диаметр условный, мм
    diameterExternal float default ((1000)),  -- Диаметр наружный, мм
    wallThickness float default ((1)),        -- Толщина стенки, мм
    pipeSectLength float default ((1)),       -- Длина участка теплопровода, м
    tubeRoughness float default ((0.5)),      -- Эквивалентная шероховатость, мм
    localLosesShare float default ((0)),      -- Доля местных потерь
    localResSum float default ((0)),          -- Сумма коэффициентов местных сопротивлений
    varCoeffIDflow int default (NULL),        -- Код коэфф.вариации параметров по подающей трубе
    varCoeffIDret int default (NULL),         -- Код коэфф.вариации параметров по обратной трубе
    calcHeatLosSignID int default ((1)),      -- Метод расчета тепловых потерь
    tubingTypeID int default ((1)),           -- Тип прокладки
    pipeRemontTypeID int default ((3)),       -- Ремонт
    channelID int default (NULL),             -- Код канала
    constrChanWidth float default ((1)),      -- Строительная ширина канала, мм
    constrChanHeight float default ((1)),     -- Строительная высота канала, мм
    heatTestsCoeff float default ((1)),       -- Коэффициент тепловых испытаний
    signNumWork int default ((0)),            -- Признак Числа работы в год <5000часов
    isolMaterialID int default (NULL),        -- Материал тепловой изоляции
    isolThickness float default ((0)),        -- Толщина изоляции, мм
    isolMaterialHCcoeff float default ((1)),  -- Коэффициент поправки теплопроводности изоляционного материала
    pipelineLayingDepth float default ((1)),  -- Глубина заложения до оси теплопровода, м
    isolHTcoeffAbove float default ((7)),     -- Теплоотдача от изоляции трубопровода к окружающему воздуху, Вт/(м*К)
    isolHTcoeffUnder float default ((8)),     -- Коэфф.теплоотдачи от изоляции трубопровода к воздуху канала, Вт/(м*К)
    airGroundHTcoeffUnder float default ((8)),    -- Коэфф.теплоотдачи от воздуха канала к грунту, Вт/(м*К)
    groundHCcoeff float default ((2.56)),     -- Теплопроводность грунта, Вт/(м*К)
    pipelineAxesDist float default ((0)),     -- Расстояние между осями теплопроводов, мм
    damageNum int default ((0)),              -- Количество повреждений (ремонтов) с начала эксплуатации, раз
    lastTransDate date default (NULL),        -- Дата последней перекладки
    lastIsolDate date default (NULL),         -- Дата последней замены изоляционной конструкции
    repairDateCapital date default (NULL),    -- Дата вывода в последний капитальный ремонт
    PICdateCapital date default (NULL),       -- Дата ввода в эксплуатацию после последнего капитального ремонта
    repairDateMaint date default (NULL),      -- Дата вывода в последний текущий ремонт
    PICdateMaint date default (NULL),         -- Дата ввода в эксплуатацию после последнего текущего ремонта
    repairDatePlanTP date default (NULL),     -- Дата планируемого ремонта
    firstPICdateHP date default (NULL),       -- Дата первичного ввода в эксплуатацию
    lastMaintDateHP date default (NULL),
    sectExploitPeriod int default ((0)),      -- Срок эксплуатации участка
    buildingConstrStateID int default (NULL),
    specDamageCoeff float default ((0)),      -- Коэффициент удельной повреждаемости
    specDamageCoeff2 float default ((0)),     -- Коэфф.уд.повреждаемости за последние 2 года
    powCabInstCount10 int default ((0)),      -- Кол.паралл.прокладок силового кабеля, >10м от трубопр., штук(и)
    powCabInstCount5 int default ((0)),       -- Кол.паралл.прокладок силового кабеля, 10-5м от трубопр., штук(и)
    powCabInstCount3 int default ((0)),       -- Кол.паралл.прокладок силового кабеля, 5-3м от трубопр., штук(и)
    powCabInstCount1 int default ((0)),       -- Кол.паралл.прокладок силового кабеля, 3-1м от трубопр., штук(и)
    powCabInstCount0 int default ((0)),       -- Кол.паралл.прокладок силового кабеля, <1м от трубопр., штук(и)
    powCabIntersCount int default ((0)),      -- Количество пересечений силового кабеля трубопровод, штук(и)
    gasECPcount10 int default ((0)),          -- Кол.паралл.прокладок электрохимзащиты газопровода, >10м от трубопр., штук(и)
    gasECPcount5 int default ((0)),           -- Кол.паралл.прокладок электрохимзащиты газопровода, 10-5м от трубопр., штук(и)
    gasECPcount3 int default ((0)),           -- Кол.паралл.прокладок электрохимзащиты газопровода, 5-3м от трубопр., штук(и)
    gasECPcount1 int default ((0)),           -- Кол.паралл.прокладок электрохимзащиты газопровода, 3-1м от трубопр., штук(и)
    gasECPcount0 int default ((0)),           -- Кол.паралл.прокладок электрохимзащиты газопровода, <1м от трубопр., штук(и)
    gasECPIntersCount int default ((0)),      -- Кол.пересечений электрохимзащиты газопровода трубопровода, штук(и)
    elTranspCount10 int default ((0)),        -- Кол.паралл.прокладок элетротранспорта >10м от трубопровода, штук(и)
    elTranspCount5 int default ((0)),         -- Кол.паралл.прокладок элетротранспорта, 10-5м от трубопр., штук(и)
    elTranspCount3 int default ((0)),         -- Кол.паралл.прокладок элетротранспорта, 5-3м от трубопр., штук(и)
    elTranspCount1 int default ((0)),         -- Кол.паралл.прокладок элетротранспорта, 3-1м от трубопр., штук(и)
    elTranspCount0 int default ((0)),         -- Кол.паралл.прокладок элетротранспорта <1м от трубопровода, штук(и)
    elTranspIntersCount int default ((0)),    -- Количество пересечений элетротранспорта, штук(и)
    potentialDiffLevelID int default ((1)),   -- Уровень разности электропотенциалов
    corrosionDegOutID int default ((1)),      -- Степень внешней коррозии
    corrosionDegInID int default ((1)),       -- Степень внутренней коррозии
    floodIntensityGWid int default ((1)),     -- Интенсивность подтопления грунтовыми водами
    floodIntensityFWid int default ((1)),     -- Интенсивность подтопления паводковыми водами
    floodIntensityTWid int default ((1)),     -- Интенсивность подтопления водопроводными водами
    floodIntensityBWid int default ((1)),     -- Интенсивность подтопления фекальными водами
    jointsTightnessInfr int default (NULL),   -- Нарушение герметичности стыков
    chanConstrFract int default (NULL),       -- Излом конструкций перекрытия и стен канала
    projSolDeviation int default (NULL),      -- Отклононение от проекта в процессе эксплуатации
    constrBearReduce int default (NULL),      -- Снижение несущей способности конструкций
    fixedSuppDestr int default (NULL),        -- Разрушение неподвижных опор
    sectWaterDumpID int default ((1)),        -- Водоотведение на участке
    breakComplexityID int default ((1)),      -- Сложность откл.участка для устранения повреждений
    breakConsumVolID int default ((1)),       -- Объем отключаемых потребителей, при повреждении
    ERWdifficultyID int default ((1)),        -- Сложность выполнения аварийно-восстановительных работ
    tubingPedestrianID int default ((1)),     -- Прокладка трубопроводов под пешеходными зонами
    tubingWayID int default ((1)),            -- Прокладка трубопроводов под авто и ж/д дорогами
    populDamageID int default ((1)),          -- Нанесение ущерба населению от подтопления 
    infrastrDamageID int default ((1)),       -- Нанесение ущерба инфраструктуре города от подтопления
    hydraTestsDate date default (NULL),       -- Дата гидравлических испытаний
    sectExpend float default ((0)),           -- Расход на участке при гидравлических испытаниях, т/ч
    sectThrustLoses float default ((0)),      -- Потери напора на участке при гидравлических испытаниях, м.вод.ст
    heatTestsDate date default (NULL),        -- Дата тепловых испытаний
    temperOutAir float default ((0)),         -- Температура наружного воздуха при тепловых испытаниях, °C
    temperGround float default ((0)),         -- Температура грунта при тепловых испытаниях, °C
    expendDWflow float default ((0)),         -- Расход сетевой воды при тепловых испытаниях, подача, т/ч
    expendDWret float default ((0)),          -- Расход сетевой воды при тепловых испытаниях, обратка, т/ч
    temperCoolFlow float default ((0)),       -- Температура остывания при тепловых испытаниях, подача, °C
    temperCoolRet float default ((0)),        -- Температура остывания при тепловых испытаниях, обратка, °C
    temperDWflow float default ((0)),         -- Температура сетевой воды при тепловых испытаниях, подача, °C
    temperDWret float default ((0)),          -- Температура сетевой воды при тепловых испытаниях, обратка, °C
    opc varchar(50) default (NULL),           -- Измеренный расход
    tubeCharactID int default (NULL),         -- Характеристика трубы
    tubeTypeID int default (NULL),            -- Вид трубы
    tubeMaterial varchar(50) default (NULL),  -- Материал трубы
    temperMax float default ((0)),            -- Максимально допустимая температура
    factoryManufID int default (NULL),        -- Завод-изготовитель
    externMaterialID int default (NULL),      -- Материал наружного покрытия
    isolationTypeID int default (NULL),       -- Тип изоляции ППУ
    externCoverThick float default ((0)),     -- Толщина наружного покрытия, мм
    anticorrMaterialID int default (NULL),    -- Материал антикоррозийного покрытия
    magistralSite int default (NULL),         -- Участок МС
    distSite int default (NULL),              -- Участок РС
    exploitReg int default (NULL),            -- Район эксплуатации
    net varchar(50) default (NULL),
    magistral int default (NULL),             -- Магистраль
    exploitSite int default (NULL),           -- Участок эксплуатации
    netType int default (NULL),               -- Вид сети
    crimpingQueSite int default (NULL),       -- Участок очереди опрессовки
    h float default ((0)),
    deltaH float default ((0)),
    deltaQ float default ((0)),
    q float default ((0)),
    primechanie varchar,
    name varchar(50),
    inventNumber varchar(50),
    objectTypeID int,
    Sreda int,
    press float,
    temperature float,
    SpokSluzhbiRash int,
    ressurs int,
    pusk int,
    organizationID int,
    Elektrich int,
    TransportElekricht int,
    Ponezial int,
    Vodootved int,
    SlozhOkluzh int,
    OtkluzhGkal int,
    AvariiVipoln int,
    Pesehod int,
    ZhdDorogi int,
    LudiProklad int,
    UzherbLudi int,
    UzherbSity int,
    VnesniiVid int,
    SostOborudovania int,
    VnesnKorrozia int,
    VnunrenKorrozia int,
    SostKonstrukz int,
    Kategorii int,

    nalichie_vblizi_kommunikacijID int,       -- Наличие вблизи коммуникаций
    harakter_gruntaID int,                    -- Грунт в месте прокладки
    poverhnost_nad_trassojID int,             -- Поверхность над трассой
    podtoplenie_do_truby int,                 -- Подтопление до трубы
    zanos_kanala_gruntomID int,               -- Занос канала грунтом
    stroitelnye_konstrukcii_kanalaID int,     -- Строительные конструкции канала
    sostoyanie_stroitelnyh_konstrukcij_kanalaID int,  -- Состояние строительных конструкций канала
    vnutrennee_sostoyanie_kanalaID int,       -- Внутреннее состояние канала
    konstrukciya_drenazhnogo_ustrojstvaID int,    -- Конструкция дренажного устройства
    sostoyanie_teplovoj_izolyacii_podachaID int,  -- Состояние тепловой изоляции (подача)
    sostoyanie_teplovoj_izolyacii_obratkaID int,  -- Состояние тепловой изоляции (обратка)
    sostoyanie_naruzhnogo_pokrytiya_podachaID int,    -- Состояние наружного покрытия (подача)
    sostoyanie_naruzhnogo_pokrytiya_obratkaID int,    -- Состояние наружного покрытия (обратка)
    sostoyanie_protivokorrozionnogo_pokrytiya_podachaID int,  -- Состоянние противокоррозионного покрытия (подача)
    sostoyanie_protivokorrozionnogo_pokrytiya_obratkaID int,  -- Состоянние противокоррозионного покрытия (обратка)
    nalichie_korrozii_podachaID int,          -- Наличие коррозии (подача)
    nalichie_korrozii_obratkaID int,          -- Наличие коррозии (обратка)
    zashemID int,                             -- Защемления трубопроводов
    sost_podvID int,                          -- Состояние подвесок
    sost_oporID int,                          -- Состояние опор
    nalich_obrKlID int,                       -- Наличие обратных клапанов
    sootv_nadpID int,                         -- Соответствие надписей на арматуре
    nalich_tabl_regID int,                    -- Наличие табличек с регистрационными номерами
    nalich_tabl_parID int,                    -- Наличие таблички с разрешенными параметрами работы
    int_korID int,                            -- Интенсивности процесса внутренней коррозии
    sostoyanie_metalla_truboprovodaID int,    -- Состояние металла трубопровода
    tol1 float,                               -- Первоначальная толщина металла труб
    tol2 float,                               -- Фактическая толщина стенки трубопровода
    glubina_kor float,                        -- Глубина коррозионных повреждений, мм
    razmery_kor float,                        -- Размеры зон коррозионных повреждений, мм
    document_analiz_vlazhnost varchar(255),   -- Анализ проб на влажность
    document_analiz_korrozia varchar(255),    -- Анализ проб на коррозийную активность
    document_potenzial varchar(255),          -- Разность электрических потенциалов «труба-земля»
    document_analiz_vytyazhka varchar(255),   -- Анализ водяной вытяжки
    dokument_analiz_prob_na_vlazhnost varchar(255),   -- Анализ проб на влажность
    dokument_analiz_prob_na_korrozijnuyu_aktivnost varchar(255),  -- Анализ проб на коррозионную активность
    dokument_raznost_elektricheskih_potencialov varchar(255), -- Разность электрических потенциалов
    dokument_analiz_vodyanoj_vytyazhki varchar(255),  -- Анализ водной вытяжки
    dokument_chertezh_objekta_kontrolya varchar(255), -- Чертеж объекта контроля

    len_tube float,                           -- Длина заменённой трубы, м
    len_izol float,                           -- Восстановление тепловой изоляции поверхности труб, м^2
    asfaltirovanie float,                     -- Асфальтирование, ремонт, м^2
    len_channel float,                        -- Длина замененного канала, м
    zamena_kanala_procent float,              -- Замена канала,%
    zamena_kompensatorov int,                 -- Замена компенсаторов
    rekonstrukciya_kamery_nachalnogo_uzla int,    -- Реконструкция камеры начального узда
    rekonstrukciya_kamery_konechnogo_uzla int,    -- Реконструкция камеры конечного узда
    ustanovka_i_zamena_zadvizhek int,         -- Установка и замена задвижек



    mestn varchar default (NULL) 
);
CREATE INDEX heatpipesections_lineid_idx ON heatpipesections (lineid);
---------------------------------
-- localhydroresistances2 - Гидравлика
-- localhydroresistances2 - Местные сопротивления
drop table if exists localhydroresistances2;

create table localhydroresistances2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    name_mest varchar(50) default (NULL),     -- Наименование
    s_mest float default ((0)),               -- Местные сопротивления трубопроводов
    k_mest int default ((0)),                 -- Количество
    sum_mest float default ((0))              -- Сумма местных сопротивлений
);
CREATE INDEX localhydroresistances2_lineid_idx ON localhydroresistances2 (lineid);
---------------------------------
-- opresdeployed - Гидравлика
-- opresdeployed - opresdeployed
drop table if exists opresdeployed;

create table opresdeployed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    directionID int,
    lineID int 
);
CREATE INDEX opresdeployed_lineid_idx ON opresdeployed (lineid);
---------------------------------
-- pressdropregulators - Гидравлика
-- pressdropregulators - Регулятор перепада давления
drop table if exists pressdropregulators;

create table pressdropregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),                -- Наименование узла присоединения импульсной трубки
    pressDropMean float default ((0)),        -- Значение регулируемого перепада давления, м.в.ст.
    regValveHydroRes float default ((0)),     -- Гидравлическое сопротивление клапана регулятора, м*ч^2/т^2
    consThroughRegValve float default ((0)),  -- Расход через клапан регулятора, т/ч
    thrustDropMean float default ((0)),       -- Полученное значение перепада напора, м
    regValveRelCap int default (NULL),        -- Условная пропускная способность регулирующего клапана регулятора, т/ч
    maxLeakageCloseValve float default ((0)), -- Относительная протечка через закрытый клапан
    consDrip float default ((0)),             -- Расход на слив, м^3/ч
    workAttrID int default (NULL),            -- Период работы
    deltaH float default ((0)),               -- Допустимое отклонение перепада давления от заданного значения, м
    regulatorStateID int default ((1))        -- Состояние
);
CREATE INDEX pressdropregulators_lineid_idx ON pressdropregulators (lineid);
CREATE INDEX pressdropregulators_nodeid_idx ON pressdropregulators (nodeid);
---------------------------------
-- pressregulators - Гидравлика
-- pressregulators - Регулятор давления
drop table if exists pressregulators;

create table pressregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),                -- Наименование узла с регулируемым напором
    valveHydroResOpen float default ((0)),    -- Гидравлическое сопротивление клапана в открытом состоянии, м*ч^2/т^2
    valveHydroResClose float default ((0)),   -- Гидравлическое сопротивление клапана в закрытом состоянии, м*ч^2/т^2
    regValveRelCap int default (NULL),        -- Пропускная способность регулирующего клапана, т/ч
    relLeakage float default ((0)),           -- Относительная протечка в % от KV (негерметичность затвора), %
    consDrip float default ((0)),             -- Расход на слив, м^3/ч
    workAttrID int default (NULL),            -- Период работы
    deltaH float default ((0)),               -- Допустимое отклонение напора от заданного значения, м
    regulatorStateID int default ((1)),       -- Состояние
    h float not null,                         -- Значение регулируемого напора, м
    pipelineSignID int not null               -- Признак трубопровода узла с регулируемым напором
);
CREATE INDEX pressregulators_lineid_idx ON pressregulators (lineid);
CREATE INDEX pressregulators_nodeid_idx ON pressregulators (nodeid);
---------------------------------
-- pumps - Гидравлика
-- pumps - Насосный агрегат
drop table if exists pumps;

create table pumps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    offReason int default (NULL),             -- Причина отключения
    pumpStationID varchar(50) default (NULL), -- Район местонахождения теплопровода
    number varchar(50) default (NULL),        -- Номер насосного агрегата
    thrust float default ((0)),               -- Заданный рабочий напор, м.вод.ст
    standardPumpID int default (NULL),        -- Тип насосного агрегата
    parallAgregCount int default ((0)),       -- Количество параллельно включенных агрегатов в группе, штук(и)
    driveTypeID int default ((1)),            -- Привод
    rotorDiameterTypeID int default ((1)),    -- Диаметр рабочего колеса
    standardEMID int default (NULL),          -- Тип установленного электродвигателя
    r0 float default ((0)),                   -- Коэффициент апроксимации R0 характеристики напора H(G)
    r1 float default ((0)),                   -- Коэффициент апроксимации R1 характеристики напора H(G)
    r2 float default ((0)),                   -- Коэффициент апроксимации R2 характеристики напора H(G)
    e0 float default ((0)),                   -- Коэффициент апроксимации E0 характеристики мощности N(G)
    e1 float default ((0)),                   -- Коэффициент апроксимации E1 характеристики мощности N(G)
    e2 float default ((0)),                   -- Коэффициент апроксимации E2 характеристики мощности N(G)
    k0 float default ((0)),                   -- Коэффициент апроксимации K0 характеристики КПД K(G)
    k1 float default ((0)),                   -- Коэффициент апроксимации K1 характеристики КПД K(G)
    k2 float default ((0)),                   -- Коэффициент апроксимации K2 характеристики КПД K(G)
    r0_z float default ((0)),                 -- Коэффициент апроксимации R0 характеристики напора H(G)
    r1_z float default ((0)),                 -- Коэффициент апроксимации R1 характеристики напора H(G)
    r2_z float default ((0)),                 -- Коэффициент апроксимации R2 характеристики напора H(G)
    e0_z float default ((0)),                 -- Коэффициент апроксимации E0 характеристики мощности N(G)
    e1_z float default ((0)),                 -- Коэффициент апроксимации E1 характеристики мощности N(G)
    e2_z float default ((0)),                 -- Коэффициент апроксимации E2 характеристики мощности N(G)
    k0_z float default ((0)),                 -- Коэффициент апроксимации K0 характеристики КПД K(G)
    k1_z float default ((0)),                 -- Коэффициент апроксимации K1 характеристики КПД K(G)
    k2_z float default ((0)),                 -- Коэффициент апроксимации K2 характеристики КПД K(G)
    rotorRotSpeedSet float default ((0)),     -- Частота вращения рабочего колеса заданная, об/мин
    rotorDiameterSet float default ((0)),     -- Диаметр рабочего колеса заданный, мм
    lastPumpReplaceDate date default (NULL),  -- Дата последней замены насоса
    lastEMreplaceDate date default (NULL),    -- Дата последней замены электродвигателя
    lastAgregReplaceDate date default (NULL), -- Дата последней замены насосного агрегата
    repairCountPump int default ((0)),        -- Количество ремонтов насоса с начала эксплуатации
    replaceCountAgreg int default ((0)),      -- Количество замен насосного агрегата
    repairCountEM int default ((0)),          -- Количество ремонтов электродвигателя с начала эксплуатации
    opc varchar(50) default (NULL),
    stateID int default ((1))                 -- Состояние
);
CREATE INDEX pumps_lineid_idx ON pumps (lineid);
---------------------------------
-- regularmatures - Гидравлика
-- regularmatures - Регулирующая арматура
drop table if exists regularmatures;

create table regularmatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    regPDmean float default ((0)),
    diameterCondit float default ((0)),       -- Диаметр условный, мм
    name varchar(50) default (NULL),          -- Наименование
    regArmType varchar(50) default (NULL),    -- Вид арматуры
    regArmSign int default (NULL),            -- Тип арматуры
    damperOpenDeg float default ((0)),        -- Степень открытие арматуры в % от KV, %
    rotationCount int default (NULL),         -- Факт.кол.оборот.махов.
    gateControl int default (NULL),           -- Призн.управл.затвор.с земли
    clue int default (NULL),                  -- Возм.закрыт.ключом
    thrustCollar int default (NULL),          -- Налич.упорн.колец
    relLeakage float default ((0)),           -- Негерм.затвора, % от KV, %
    opc varchar(50) default (NULL),
    h float default ((0)),
    deltaH float default ((0)),
    deltaQ float default ((0)),
    q float default ((0)),
    damperArmatureStateID int default ((1))   -- Состояние
);
CREATE INDEX regularmatures_lineid_idx ON regularmatures (lineid);
CREATE INDEX regularmatures_nodeid_idx ON regularmatures (nodeid);
---------------------------------
-- reversevalves - Гидравлика
-- reversevalves - Обратный клапан
drop table if exists reversevalves;

create table reversevalves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    hydroResOpen float default ((0)),         -- Гидравлическое сопротивление клапана в открытом состоянии, м*ч^2/т^2
    hydroResClose float default ((0)),        -- Гидравлическое сопротивление клапана в закрытом состоянии, м*ч^2/т^2
    locInstall varchar(50) default (NULL),    -- Место установки обратного клапана
    standardRevValveID int default (NULL),    -- Тип обратного клапана
    standardID int default ((1)),             -- Стандарт труб на участке теплопровода
    tubeID int default (NULL),                -- Ссылка на стандартную трубу
    pipelineLength float default ((0)),       -- Длина теплопровода
    diameterInternal float default ((0)),     -- Внутренний диаметр теплопровода
    tubeRoughness float default ((0)),        -- Эквивалентная шероховатость трубы теплопровода, мм
    resCoeffsSum float default ((0)),         -- Сумма коэффициентов местных сопротивлений участка теплопровода
    revValveCap int default (NULL),           -- Пропускная способность обраного клапана, т/ч
    relatLeakage float default ((0)),         -- Относительная протечка в % от KV (негерметичность затвора), %
    stateID int default ((1))                 -- Состояние обратного клапана
);
CREATE INDEX reversevalves_lineid_idx ON reversevalves (lineid);
---------------------------------
-- systemradiators - Гидравлика
-- systemradiators - Радиаторы системы отопления
drop table if exists systemradiators;

create table systemradiators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    name varchar(50) default (NULL),          -- Наименование отопительного прибора конвективно-излучающего типа
    type varchar(50) default (NULL),          -- Тип прибора
    count varchar(50) default (NULL),         -- Количество приборов, штук(и)
    totalEquivSurface varchar(50) default (NULL), -- Суммарная эквивалентная поверхность нагрева приборов, м^2
    stateID int default ((1)) 
);
CREATE INDEX systemradiators_lineid_idx ON systemradiators (lineid);
--- Гидравлика: 46
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- externalcodes objecttypes - lookup Гидравлика
-- objecttypes - Типы объектов
drop table if exists objecttypes;

create table objecttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "objecttypes" ("id","name","code","ord") VALUES
(1,'Магистраль','М',1),
(2,'Распредсеть','Р',2),
(3,'Источник тепла','И',3),
(4,'Насосная станция','Н',4),
(5,'ЦТРП','Ц',5),
(6,'КРП','КРП',6),
(7,'Камера','КАМ',7),
(8,'Котельная','КОТ',8),
(9,'Участок магистрали','УМ',9),
(10,'Районая котельная','РК',3),
(11,'РК сеть отопления','РКО',3),
(12,'РК сеть ГВС','РКГ',3);


-- SELECT setval('"objecttypes_id_seq"', 12);

---------------------------------
-- bypass regulatorstates - lookup Гидравлика
-- regulatorstates - Состояние регулятора
drop table if exists regulatorstates;

create table regulatorstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "regulatorstates" ("id","name","code","ord") VALUES
(1,'открыт','НАДО',1),
(2,'закрыт','НАДО',2),
(3,'неактивен','НАДО',3);


-- SELECT setval('"regulatorstates_id_seq"', 3);

---------------------------------
-- bypass standards - lookup Гидравлика
-- standards - standards
drop table if exists standards;

create table standards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "standards" ("id","name","code","ord") VALUES
(1,'ГОСТ','ГОСТ',1),
(2,'АВВ','АВВ',2),
(3,'ППУ','ППУ',3);


-- SELECT setval('"standards_id_seq"', 3);

---------------------------------
-- bypass pipelinesigns - lookup Гидравлика
-- pipelinesigns - Состояния трубопровода
drop table if exists pipelinesigns;

create table pipelinesigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "pipelinesigns" ("id","name","code","ord") VALUES
(1,'подающий','П',1),
(2,'обратный','О',2);


-- SELECT setval('"pipelinesigns_id_seq"', 2);

---------------------------------
-- reversevalves standardreversevalves - lookup Гидравлика
-- standardreversevalves - KO_Клапан обратный стандартный
drop table if exists standardreversevalves;

create table standardreversevalves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра
    name_ok varchar(50) default (NULL),       -- Наименование обратного клапана
    name_standard varchar(50) default (NULL), -- Обозначение
    material varchar(50) default (NULL),      -- Материал корпуса
    producer varchar(50) default (NULL),      -- Изготовитель
    d_usl float default ((0)),                -- Диаметр условный
    massa float default ((0)),                -- Масса
    p float default ((0)),                    -- Давление, исходная таблица в мм.вод.ст.
    t float default ((0))                     -- Температура рабочей среды максимальная
);

INSERT INTO "standardreversevalves" ("id","name_ok","name_standard","material","producer","d_usl","massa","p","t") VALUES
(1,'Клапан обратный','19с49нж1',NULL,'Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',800.0,645.0,250.0,425.0),
(2,'Клапан обратный','19тн12бк','титан.сплав ВТО-1','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',200.0,18.5,250.0,150.0),
(3,'Клапан обратный','19тн12бк','титан.сплав ВТО-1','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',100.0,4.8,250.0,150.0),
(4,'Клапан обратный','19тн12бк','титан.сплав ВТО-1','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',150.0,9.5,250.0,150.0),
(5,'Клапан обратный','19ч21бр(КА44075.04)','чугун','Душанбинский арматурный з-д',100.0,6.0,160.0,225.0),
(6,'Клапан обратный','19ч21бр(КА44075.04)','чугун','Душанбинский арматурный з-д',150.0,11.6,160.0,225.0),
(7,'Клапан обратный','16кч9нж(Л47007,Л4100','ковкий чугун','Запорожское ПО"ЗАПОРОЖПРОМАРМАТУРА"',50.0,10.9,250.0,300.0),
(8,'Клапан обратный','19кч9нж(Л41007,Л4100','ковкий чугун','Запорожское ПО"ЗАПОРОЖПРОМАРМАТУРА"',80.0,24.7,250.0,300.0),
(9,'Клапан обратный','16кч9нж(Л41007,Л4100','ковкий чугун','Запорожское ПО"ЗАПОРОЖПРОМАРМАТУРА"',65.0,19.8,250.0,300.0),
(10,'Клапан обратный','16ч6р(УЛ41079.02)','чугун','Кролевецкое ПО"КРОЛЕВЕЦПРОМАРМАТУРА"',100.0,35.5,160.0,50.0),
(11,'Клапан обратный','19ч19р(ПФ4403.01)','чугун','Курганское ПО"КУРГАНАРМХИММАШ"',800.0,784.0,100.0,120.0),
(12,'Клапан обратный','19кч9п','ковкий чугун','Запорожское ПО"ЗАПОРОЖПРОМАРМАТУРА"',65.0,18.9,250.0,225.0),
(13,'Клапан обратный','19тн12бк','титан','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',80.0,26.0,250.0,150.0),
(14,'Клапан обратный','19с49нж1','сталь 25-Л-2','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',800.0,645.0,250.0,425.0),
(15,'Клапан обратный','19с49нж1','сталь 25Л-2','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',1000.0,960.0,250.0,425.0),
(16,'Клапан обратный','16кч9п','ковкий чугун','Запорожское ПО"ЗАПОРОЖПРОМАРМАТУРА"',50.0,10.3,250.0,225.0),
(17,'Клапан обратный','16кч9п','ковкий чугун','Запорожское ПО"ЗАПОРОЖПРОМАРМАТУРА"',80.0,24.7,250.0,225.0),
(18,'Клапан обратный','19тн12бк','титан','Пензенское ПО"ПЕНЗТЯЖПРОМАРМАТУРА"',50.0,1.2,250.0,150.0),
(19,'Клапан обратный','19ч21бр(КА44075.04)','чугун','Чуфаровский арматурный з-д',150.0,11.6,250.0,225.0),
(20,'Клапан обратный поворотный',NULL,'сталь','Ивано-Франковский з-д',400.0,NULL,160.0,70.0),
(21,'Клапан обратный поворотный',NULL,'сталь','Ивано-Франковский з-д',600.0,NULL,250.0,150.0),
(22,'Клапан обратный поворотный','19с47нж','сталь','Ивано-Франковский з-д',400.0,136.0,400.0,150.0),
(23,'Клапан обратный поворотный',NULL,'сталь',NULL,300.0,NULL,160.0,150.0),
(24,'Клапан обратный',NULL,'сталь',NULL,250.0,NULL,400.0,70.0),
(25,'Клапан обратный поворотный','19с17нж','сталь',NULL,200.0,153.0,400.0,70.0),
(26,'Клапан обратный поворотный','19с36нж','сталь','Ивано-Франковский з-д',300.0,78.0,400.0,70.0),
(27,'Клапан обратный поворотный',NULL,'сталь',NULL,400.0,NULL,250.0,150.0);


-- SELECT setval('"standardreversevalves_id_seq"', 27);

---------------------------------
-- reversevalves states - lookup Гидравлика
-- states - states
drop table if exists states;

create table states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "states" ("id","name","code","ord") VALUES
(1,'открыт',' ',1),
(2,'закрыт','*',2);


-- SELECT setval('"states_id_seq"', 2);

---------------------------------
-- consumptregulators workattributes - lookup Гидравлика
-- workattributes - workattributes
drop table if exists workattributes;

create table workattributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "workattributes" ("id","name","code","ord") VALUES
(1,'отопительный','О',1),
(2,'летний','Л',2),
(3,'круглогодичный','К',3);


-- SELECT setval('"workattributes_id_seq"', 3);

---------------------------------
-- generalizedconsumers pdvalveinstalllocs - lookup Гидравлика
-- pdvalveinstalllocs - pdvalveinstalllocs
drop table if exists pdvalveinstalllocs;

create table pdvalveinstalllocs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "pdvalveinstalllocs" ("id","name","code","ord") VALUES
(1,'обратка','О',1),
(2,'подача','П',2);


-- SELECT setval('"pdvalveinstalllocs_id_seq"', 2);

---------------------------------
-- generalizedconsumers closesyscalcsigns - lookup Гидравлика
-- closesyscalcsigns - Признаки расчетов закрытой системы
drop table if exists closesyscalcsigns;

create table closesyscalcsigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "closesyscalcsigns" ("id","name","code","ord") VALUES
(1,'рассчитанное',' ',1),
(2,'заданное','Н',NULL);


-- SELECT setval('"closesyscalcsigns_id_seq"', 2);

---------------------------------
-- generalizedconsumers setloadclosesyscalcsigns - lookup Гидравлика
-- setloadclosesyscalcsigns - setloadclosesyscalcsigns
drop table if exists setloadclosesyscalcsigns;

create table setloadclosesyscalcsigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "setloadclosesyscalcsigns" ("id","name","code","ord") VALUES
(1,'сопротивление','С',1),
(2,'нагрузка','Н',2);


-- SELECT setval('"setloadclosesyscalcsigns_id_seq"', 2);

---------------------------------
-- generalizedconsumers hydromodesigns - lookup Гидравлика
-- hydromodesigns - hydromodesigns
drop table if exists hydromodesigns;

create table hydromodesigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "hydromodesigns" ("id","name","code","ord") VALUES
(1,'через шайбы','Ш',1),
(2,'через регулятор перепада давления','Д',2),
(3,'через сопротивления','С',3),
(4,'через нагрузки','Н',4),
(5,'через трехходовой клапан','3',5);


-- SELECT setval('"hydromodesigns_id_seq"', 5);

---------------------------------
-- generalizedconsumers wemeteringdevices - lookup Гидравлика
-- wemeteringdevices - wemeteringdevices
drop table if exists wemeteringdevices;

create table wemeteringdevices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "wemeteringdevices" ("id","name","code","ord") VALUES
(1,'не установлен','НАДО',1),
(2,'установлен','НАДО',2);


-- SELECT setval('"wemeteringdevices_id_seq"', 2);

---------------------------------
-- generalizedconsumers consumerstates - lookup Гидравлика
-- consumerstates - Состояния потребителей
drop table if exists consumerstates;

create table consumerstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "consumerstates" ("id","name","code","ord") VALUES
(1,'открыто',' ',1),
(2,'закрыто','*',2);


-- SELECT setval('"consumerstates_id_seq"', 2);

---------------------------------
-- generalizedconsumers connectionschemes - lookup Гидравлика
-- connectionschemes - Схемы соединений
drop table if exists connectionschemes;

create table connectionschemes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "connectionschemes" ("id","name","code","ord") VALUES
(1,'безэлеваторная зависимая',' ',1),
(2,'элеваторная зависимая','Э',2);


-- SELECT setval('"connectionschemes_id_seq"', 2);

---------------------------------
-- generalizedconsumers schemeconnections - lookup Гидравлика
-- schemeconnections - schemeconnections
drop table if exists schemeconnections;

create table schemeconnections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "schemeconnections" ("id","name","code","ord") VALUES
(1,'элеваторная зависимая','У',1),
(2,'безэлеваторная зависимая',' ',2),
(3,'независимая','Н',3);


-- SELECT setval('"schemeconnections_id_seq"', 3);

---------------------------------
-- heatpipesections calcheatlosessigns - lookup Гидравлика
-- calcheatlosessigns - Признаки расчета тепловых потерь
drop table if exists calcheatlosessigns;

create table calcheatlosessigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "calcheatlosessigns" ("id","name","code","ord") VALUES
(1,'Норма','Н',1),
(2,'Изоляция','И',2);


-- SELECT setval('"calcheatlosessigns_id_seq"', 2);

---------------------------------
-- heatpipesections tubingtypes - lookup Гидравлика
-- tubingtypes - tubingtypes
drop table if exists tubingtypes;

create table tubingtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "tubingtypes" ("id","name","code","ord") VALUES
(1,'канальная','К',1),
(2,'бесканальная','Б',2),
(3,'подвальная','П',3),
(4,'надземная','Н',4),
(5,'обвязка узлов и насосных станций','О',5);


-- SELECT setval('"tubingtypes_id_seq"', 5);

---------------------------------
-- heatpipesections isolmaterials - lookup Гидравлика
-- isolmaterials - isolmaterials
drop table if exists isolmaterials;

create table isolmaterials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Материал
    l float default((0)),                     -- L (Коэф.теплопроводн., Lиз), Вт/(м*К)
    k float default((0))                      -- K (Lиз=L+K*T)
);

INSERT INTO "isolmaterials" ("id","name","l","k") VALUES
(1,'Асбестовый матрац, заполненный совелитом',0.087,0.00012),
(2,'Асбестовый матрац, заполненный стекловолокном',0.058,0.00023),
(3,'Асботкань в несколько слоев',0.13,0.00026),
(4,'Асбестовый шнур',0.12,0.00031),
(5,'Асбестовый шнур (ШАОН)',0.13,0.00026),
(6,'Асбопухшнур (ШАП)',0.093,0.0002),
(7,'Асбовермикулитовые изделия марки 250',0.081,0.00023),
(8,'Асбовермикулитовые изделия марки 300',0.087,0.00023),
(9,'Битумоперлит',0.12,0.00023),
(10,'Битумокерамзит',0.13,0.00023),
(11,'Битумовермикулит',0.13,0.00023),
(12,'Вулканитовые плиты марки 300',0.074,0.00015),
(13,'Диатомовые изделия марки 500',0.116,0.00023),
(14,'Диатомовые изделия марки 600',0.14,0.00023),
(15,'Известково-кремнеземные изделия марки 200',0.069,0.00015),
(16,'Маты минераловатные прошивные марки 100',0.045,0.0002),
(17,'Маты минераловатные прошивные марки 125',0.049,0.0002),
(18,'Маты из минеральной ваты марки 75',0.043,0.00022),
(19,'Маты из непрерывного стекловолокна',0.04,0.00026),
(20,'Маты стекловатные марки 50',0.042,0.00028),
(21,'Пенобетонные изделия',0.11,0.0003),
(22,'Пенопласт ФРП-1 группы 100',0.043,0.00019),
(23,'Пенополимербетон',0.07,0.0),
(24,'Пенополиуретан',0.05,0.0),
(25,'Перлитоцементные изделия марки 300',0.076,0.000185),
(26,'Перлитоцементные изделия марки 350',0.081,0.000185),
(27,'Плиты из минеральной ваты марки 75',0.043,0.00022),
(28,'Плиты стекловатные марки 50',0.042,0.00028),
(29,'Плиты минераловатные полужесткие марки 100',0.044,0.00021),
(30,'Плиты минераловатные полужесткие марки 125',0.047,0.000185),
(31,'Плиты минераловатные марки 250',0.056,0.000185),
(32,'Плиты стекловатные полужесткие марки 75',0.044,0.00023),
(33,'Полуцилиндры минераловатные марки 150',0.049,0.0002),
(34,'Полуцилиндры минераловатные марки 200',0.052,0.000185),
(35,'Полосы из непрерывного стекловолокна',0.04,0.00026),
(36,'Совелитовые изделия марки 350',0.076,0.000185),
(37,'Совелитовые изделия марки 400',0.078,0.000185),
(38,'Скорлупы минераловатные оштукатуренные',0.069,0.00019),
(39,'Фенольный поропласт ФЛ монолит',0.05,0.0),
(40,'Шнур минераловатный марки 200',0.056,0.000185),
(41,'Шнур минераловатный марки 250',0.058,0.000185),
(42,'Шнур минераловатный марки 300',0.061,0.000185),
(43,'Цилиндры минераловатные марки 250',0.056,0.000185),
(44,'Цилиндры минераловатные марки 150',0.049,0.0002),
(45,'Цилиндры минераловатные марки 200',0.052,0.000185),
(46,'Термокраска',0.0,0.0),
(47,'Стекловата фольгированная',0.0,0.0),
(48,'Маты минераловатные',0.0,0.0),
(49,'Минплита',0.0,0.0);


-- SELECT setval('"isolmaterials_id_seq"', 49);

---------------------------------
-- heatpipesections potentialdifflevels - lookup Гидравлика
-- potentialdifflevels - potentialdifflevels
drop table if exists potentialdifflevels;

create table potentialdifflevels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "potentialdifflevels" ("id","name","code","ord") VALUES
(1,'Низкий','Н',1),
(2,'Значительный','З',2),
(3,'Опасный','О',3);


-- SELECT setval('"potentialdifflevels_id_seq"', 3);

---------------------------------
-- heatpipesections corrosiondegreesout - lookup Гидравлика
-- corrosiondegreesout - Степени коррозии снаружи
drop table if exists corrosiondegreesout;

create table corrosiondegreesout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "corrosiondegreesout" ("id","name","code","ord") VALUES
(1,'Допустимая','Д',1),
(2,'Высокая','В',2),
(3,'Аварийная','А',3);


-- SELECT setval('"corrosiondegreesout_id_seq"', 3);

---------------------------------
-- heatpipesections corrosiondegreesin - lookup Гидравлика
-- corrosiondegreesin - Степени коррозии внутри
drop table if exists corrosiondegreesin;

create table corrosiondegreesin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "corrosiondegreesin" ("id","name","code","ord") VALUES
(1,'Слабая, утонение до 10%','НАДО',1),
(2,'Средняя, утонение от 10% до 30%','НАДО',2),
(3,'Сильная, утонение более 30%','НАДО',3);


-- SELECT setval('"corrosiondegreesin_id_seq"', 3);

---------------------------------
-- heatpipesections floodintensitiesgw - lookup Гидравлика
-- floodintensitiesgw - floodintensitiesgw
drop table if exists floodintensitiesgw;

create table floodintensitiesgw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "floodintensitiesgw" ("id","name","code","ord") VALUES
(1,'Отсутствует',' ',1),
(2,'Периодическое','НАДО',2),
(3,'Постоянное','НАДО',3);


-- SELECT setval('"floodintensitiesgw_id_seq"', 3);

---------------------------------
-- heatpipesections floodintensitiesfw - lookup Гидравлика
-- floodintensitiesfw - floodintensitiesfw
drop table if exists floodintensitiesfw;

create table floodintensitiesfw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "floodintensitiesfw" ("id","name","code","ord") VALUES
(1,'Отсутствует',' ',1),
(2,'Периодическое','НАДО',2),
(3,'Постоянное','НАДО',3);


-- SELECT setval('"floodintensitiesfw_id_seq"', 3);

---------------------------------
-- heatpipesections floodintensitiestw - lookup Гидравлика
-- floodintensitiestw - floodintensitiestw
drop table if exists floodintensitiestw;

create table floodintensitiestw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "floodintensitiestw" ("id","name","code","ord") VALUES
(1,'Отсутствует',' ',1),
(2,'Периодическое','НАДО',2),
(3,'Постоянное','НАДО',3);


-- SELECT setval('"floodintensitiestw_id_seq"', 3);

---------------------------------
-- heatpipesections floodintensitiesbw - lookup Гидравлика
-- floodintensitiesbw - floodintensitiesbw
drop table if exists floodintensitiesbw;

create table floodintensitiesbw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "floodintensitiesbw" ("id","name","code","ord") VALUES
(1,'Отсутствует',' ',1),
(2,'Периодическое','НАДО',2),
(3,'Постоянное','НАДО',3);


-- SELECT setval('"floodintensitiesbw_id_seq"', 3);

---------------------------------
-- heatpipesections sectwaterdumps - lookup Гидравлика
-- sectwaterdumps - sectwaterdumps
drop table if exists sectwaterdumps;

create table sectwaterdumps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "sectwaterdumps" ("id","name","code","ord") VALUES
(1,'Интенсивное','НАДО',1),
(2,'Удовлетворительное','НАДО',2),
(3,'Неудовлетворительно','НАДО',3);


-- SELECT setval('"sectwaterdumps_id_seq"', 3);

---------------------------------
-- heatpipesections breakcomplexities - lookup Гидравлика
-- breakcomplexities - Сложности поломок
drop table if exists breakcomplexities;

create table breakcomplexities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "breakcomplexities" ("id","name","code","ord") VALUES
(1,'Низкая (тупиковый участок)','Н',1),
(2,'Средняя (промежуточный участок)','С',2),
(3,'Высокая (головной участок)','В',3);


-- SELECT setval('"breakcomplexities_id_seq"', 3);

---------------------------------
-- heatpipesections breakconsumvols - lookup Гидравлика
-- breakconsumvols - Признаки отключения
drop table if exists breakconsumvols;

create table breakconsumvols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "breakconsumvols" ("id","name","code","ord") VALUES
(1,'Концевой (менее 15Гкал)','К',1),
(2,'Ответвление (от 15 до 50Гкал)','О',2),
(3,'Луч (свыше 50Гкал)','Л',3);


-- SELECT setval('"breakconsumvols_id_seq"', 3);

---------------------------------
-- heatpipesections erwdifficulties - lookup Гидравлика
-- erwdifficulties - erwdifficulties
drop table if exists erwdifficulties;

create table erwdifficulties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "erwdifficulties" ("id","name","code","ord") VALUES
(1,'Удовлетворительная','НАДО',1),
(2,'Средняя (стесненность)','НАДО',2),
(3,'Высокая (отсутствие подъема)','НАДО',3);


-- SELECT setval('"erwdifficulties_id_seq"', 3);

---------------------------------
-- heatpipesections tubingpedestrians - lookup Гидравлика
-- tubingpedestrians - tubingpedestrians
drop table if exists tubingpedestrians;

create table tubingpedestrians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "tubingpedestrians" ("id","name","code","ord") VALUES
(1,'С движением малой интенсивности (до 50 чел/час)','НАДО',1),
(2,'С движением средней  интенсивности (50-200 чел/час','НАДО',2),
(3,'С интенсивным движением пешеходов (свыше 50 чел/ча','НАДО',3);


-- SELECT setval('"tubingpedestrians_id_seq"', 3);

---------------------------------
-- heatpipesections tubingways - lookup Гидравлика
-- tubingways - tubingways
drop table if exists tubingways;

create table tubingways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "tubingways" ("id","name","code","ord") VALUES
(1,'Под квартальными а/дорогами, парковками и стоянкам','',1),
(2,'Под а/дорогами с интенсивным движением','',2),
(3,'Под проспектами и магистралями','',3),
(4,'Под ж/д и трайвай','',3);


-- SELECT setval('"tubingways_id_seq"', 4);

---------------------------------
-- heatpipesections populdamages - lookup Гидравлика
-- populdamages - populdamages
drop table if exists populdamages;

create table populdamages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "populdamages" ("id","name","code","ord") VALUES
(1,'Подвалам домов','НАДО',1),
(2,'Благоустроенным территориям','НАДО',2),
(3,'Организациям в подвалах','НАДО',3),
(4,'Частный сектор','НАДО',4);


-- SELECT setval('"populdamages_id_seq"', 4);

---------------------------------
-- heatpipesections infrastrdamages - lookup Гидравлика
-- infrastrdamages - infrastrdamages
drop table if exists infrastrdamages;

create table infrastrdamages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "infrastrdamages" ("id","name","code","ord") VALUES
(1,'Коммуникации','НАДО',1),
(2,'Фундаменты','НАДО',2),
(3,'Опоры мостов','НАДО',3),
(4,'ЛЭП','НАДО',4);


-- SELECT setval('"infrastrdamages_id_seq"', 4);

---------------------------------
-- heatpipesections tubecharacteristics - lookup Гидравлика
-- tubecharacteristics - tubecharacteristics
drop table if exists tubecharacteristics;

create table tubecharacteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "tubecharacteristics" ("id","name","code","ord") VALUES
(1,'Спиралешовная','С',1),
(2,'Бесшовная','Б',2),
(3,'Прямошовная','П',3);


-- SELECT setval('"tubecharacteristics_id_seq"', 3);

---------------------------------
-- heatpipesections tubetypes - lookup Гидравлика
-- tubetypes - tubetypes
drop table if exists tubetypes;

create table tubetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Наименование
    code varchar(10) default (NULL),          -- Код
    ord int                                   -- Порядок
);

INSERT INTO "tubetypes" ("id","name","code","ord") VALUES
(1,'Стальная','С',1),
(2,'Предизолированная','И',2),
(3,'Полиэтиленовая','Э',3),
(4,'Оцинкованная','Ц',4),
(5,'Усиленная','У',5);


-- SELECT setval('"tubetypes_id_seq"', 5);

---------------------------------
-- heatpipesections isolationtypes - lookup Гидравлика
-- isolationtypes - isolationtypes
drop table if exists isolationtypes;

create table isolationtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "isolationtypes" ("id","name","code","ord") VALUES
(1,'1 тип','НАДО',1),
(2,'2 тип','НАДО',2);


-- SELECT setval('"isolationtypes_id_seq"', 2);

---------------------------------
-- heatpipesections anticorrmaterials - lookup Гидравлика
-- anticorrmaterials - Антикоррозионные материалы
drop table if exists anticorrmaterials;

create table anticorrmaterials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "anticorrmaterials" ("id","name","code","ord") VALUES
(1,'Окраска','О',1),
(2,'Грунтовка ГФ 021',NULL,2),
(3,'Эмаль красная',NULL,3),
(4,'Эмаль синяя',NULL,4),
(5,'Эмаль белая',NULL,5),
(6,'Серебрянка',NULL,6);


-- SELECT setval('"anticorrmaterials_id_seq"', 6);

---------------------------------
-- heatpipesections externalmaterials - lookup Гидравлика
-- externalmaterials - externalmaterials
drop table if exists externalmaterials;

create table externalmaterials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);

INSERT INTO "externalmaterials" ("id","name") VALUES
(1,'Сталь листовая холоднокатанная'),
(2,'Сталь листовая Оцинкованная'),
(3,'ППУ ОЦ'),
(4,'Cтеклоткань'),
(5,'Асбест (хризалит)'),
(6,'Рубероид'),
(7,'Полиэтилен'),
(8,'k-flex'),
(9,'стеклопластик рулоновый РСТ'),
(10,'Сталь листовая оцинкованная вальцованная'),
(11,'Асбесто-цементная'),
(12,'Хризотил');


-- SELECT setval('"externalmaterials_id_seq"', 12);

---------------------------------
-- heatpipesections signnumworks - lookup Гидравлика
-- signnumworks - signnumworks
drop table if exists signnumworks;

create table signnumworks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "signnumworks" ("id","name","code","ord") VALUES
(0,'меньше 5000','1',2),
(1,'больше 5000','0',1);


-- SELECT setval('"signnumworks_id_seq"', 1);

---------------------------------
-- heatpipesections piperemonttypes - lookup Гидравлика
-- piperemonttypes - piperemonttypes
drop table if exists piperemonttypes;

create table piperemonttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "piperemonttypes" ("id","name","code","ord") VALUES
(1,'Новый участок','',1),
(2,'С ремонтом','',2),
(3,'Без ремонта','',3);


-- SELECT setval('"piperemonttypes_id_seq"', 3);

---------------------------------
-- heatpipesections buildingconstrstates - lookup Гидравлика
-- buildingconstrstates - Состояния строительных конструкций
drop table if exists buildingconstrstates;

create table buildingconstrstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "buildingconstrstates" ("id","name","code","ord") VALUES
(1,'Нарушение герметичности стыков','',1),
(2,'Излом конструкций перекрытия и стен канала','',2),
(3,'Отклонения от проектных решений, произошедшие в процессе эксплуатации','',3),
(4,'Снижение несущей способности конструкций','',4),
(5,'Разрушение неподвижных опор','',5);


-- SELECT setval('"buildingconstrstates_id_seq"', 5);

---------------------------------
-- heatpipesections pipesectionsstates - lookup Гидравлика
-- pipesectionsstates - pipesectionsstates
drop table if exists pipesectionsstates;

create table pipesectionsstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "pipesectionsstates" ("id","name","code","ord") VALUES
(1,'открыто',' ',1),
(2,'закрыто','*',2);


-- SELECT setval('"pipesectionsstates_id_seq"', 2);

---------------------------------
-- heatsources heatsourcetypes - lookup Гидравлика
-- heatsourcetypes - heatsourcetypes
drop table if exists heatsourcetypes;

create table heatsourcetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "heatsourcetypes" ("id","name","code","ord") VALUES
(1,'ТЭЦ','ТЭЦ',1),
(2,'Районная котельная','РК',2),
(3,'Местная котельная','МК',3);


-- SELECT setval('"heatsourcetypes_id_seq"', 3);

---------------------------------
-- heatsources graphtypes - lookup Гидравлика
-- graphtypes - graphtypes
drop table if exists graphtypes;

create table graphtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "graphtypes" ("id","name","code","ord") VALUES
(1,'Отопительный(О)','О',1),
(2,'Скорректированный повышенный(СВ)','СВ',2),
(3,'Повышенный(П)','П',3),
(4,'Скорректированный пониженный(СН)','СН',4);


-- SELECT setval('"graphtypes_id_seq"', 4);

---------------------------------
-- heatsources prtable - lookup Гидравлика
-- prtable - prtable
drop table if exists prtable;

create table prtable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "prtable" ("id","name","code","ord") VALUES
(0,'не задано','0',1),
(1,'с переключением','0',2),
(2,'из подающего','1',3),
(3,'из обратного','2',4),
(4,'из обоих','3',5);


-- SELECT setval('"prtable_id_seq"', 4);

---------------------------------
-- linesobj externalsignline - lookup Гидравлика
-- externalsignline - externalsignline
drop table if exists externalsignline;

create table externalsignline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "externalsignline" ("id","name","code","ord") VALUES
(1,'общий',' ',1),
(2,'подающий','П',2),
(3,'обратный','О',3),
(4,'подающий-обратный','ПО',4),
(5,'обратный-подающий','ОП',5);


-- SELECT setval('"externalsignline_id_seq"', 5);

---------------------------------
-- linesobj passwords - lookup Гидравлика
-- passwords - passwords
drop table if exists passwords;

create table passwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name varchar(50) default (NULL),
    user_password varchar(50) default (NULL),
    user_right int default (NULL) 
);

INSERT INTO "passwords" ("id","user_name","user_password","user_right") VALUES
(1,'Администратор','',1088),
(2,'Группа режимов',NULL,15),
(3,'Просмотр',NULL,106),
(4,'Акты раздела',NULL,5);
;

-- SELECT setval('"passwords_id_seq"', 57);

---------------------------------
-- nodes externalsigns - lookup Гидравлика
-- externalsigns - externalsigns
drop table if exists externalsigns;

create table externalsigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "externalsigns" ("id","name","code","ord") VALUES
(1,'общий',' ',1),
(2,'подающий','П',2),
(3,'обратный','О',3);


-- SELECT setval('"externalsigns_id_seq"', 3);

---------------------------------
-- nodes nodetypes - lookup Гидравлика
-- nodetypes - nodetypes
drop table if exists nodetypes;

create table nodetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int,
    visibles varchar 
);

INSERT INTO "nodetypes" ("id","name","code","ord","visibles") VALUES
(7,'Павильон','П',7,'all,generalizedConsumers'),
(8,'ЦТРП','ЦТРП',8,'all'),
(9,'Тепловая камера','КАМ',9,'all,generalizedConsumers'),
(10,'Подземный узел','ПОДЗ',10,'all'),
(11,'Надземный узел','НАДЗ',11,'all'),
(12,'Ввод здание','ВВ',12,'all'),
(13,'Неустановленный узел','?',13,'realConsumers'),
(14,'Насосная станция','НС',14,'all,pumpStations'),
(15,'Источник тепла','ИСТ',15,'all,heatSources'),
(16,'Вертикальный подъем/опуск трубопровода','',16,'all'),
(17,'Границы вертикальных компенсаторов','',17,'all'),
(18,'Камера опуска/подъёма','',18,'all'),
(19,'Переход диаметра','',19,'all'),
(20,'Тепловой пункт','',20,'all,realConsumers,generalizedConsumers'),
(21,'Угол поворота трубопровода','',21,'all'),
(22,'Узел канала','',22,'all');


-- SELECT setval('"nodetypes_id_seq"', 22);

---------------------------------
-- pumps standardpumps - lookup Гидравлика
-- standardpumps - NC_Насос стандартный
drop table if exists standardpumps;

create table standardpumps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Наименование
    tip_nas varchar(50) default (NULL),       -- Тип
    h1 float default ((0)),                   -- H1
    h2 float default ((0)),                   -- H2
    h3 float default ((0)),                   -- H3
    h4 float default ((0)),                   -- H4
    h5 float default ((0)),                   -- H5
    h6 float default ((0)),                   -- H6
    h7 float default ((0)),                   -- H7
    h8 float default ((0)),                   -- H8
    h9 float default ((0)),                   -- H9
    h10 float default ((0)),                  -- H10
    n1 float default ((0)),                   -- N1
    n2 float default ((0)),                   -- N2
    n3 float default ((0)),                   -- N3
    n4 float default ((0)),                   -- N4
    n5 float default ((0)),                   -- N5
    n6 float default ((0)),                   -- N6
    n7 float default ((0)),                   -- N7
    n8 float default ((0)),                   -- N8
    n9 float default ((0)),                   -- N9
    n10 float default ((0)),                  -- N10
    k1 float default ((0)),                   -- КПД1
    k2 float default ((0)),                   -- КПД2
    k3 float default ((0)),                   -- КПД3
    k4 float default ((0)),                   -- КПД4
    k5 float default ((0)),                   -- КПД5
    k6 float default ((0)),                   -- КПД6
    k7 float default ((0)),                   -- КПД7
    k8 float default ((0)),                   -- КПД8
    k9 float default ((0)),                   -- КПД9
    k10 float default ((0)),                  -- КПД10
    q1 float default ((0)),                   -- G1
    q2 float default ((0)),                   -- G2
    q3 float default ((0)),                   -- G3
    q4 float default ((0)),                   -- G4
    q5 float default ((0)),                   -- G5
    q6 float default ((0)),                   -- G6
    q7 float default ((0)),                   -- G7
    q8 float default ((0)),                   -- G8
    q9 float default ((0)),                   -- G9
    q10 float default ((0)),                  -- G10
    q_min float default ((0)),                -- G_min
    h_min float default ((0)),                -- H_min
    q_max float default ((0)),                -- G_max
    h_max float default ((0)),                -- H_max
    q_nomin float default ((0)),              -- Gном
    h_nomin float default ((0)),              -- Hном
    k_nomin float default ((0)),              -- КПДном
    d_nomin float default ((0)),              -- ДиамНом
    rate_nomin float default ((0)),           -- ЧастНом
    kol_d float default ((0)),                -- Колеса
    t_max float default ((0)),                -- Темп
    p_home float default ((0)),               -- ДавлВсаса
    h_home float default ((0)),               -- ВысотаВсаса
    producer varchar(50) default (NULL),      -- Изг
    p_home_max float default ((0)),           -- ДавлМакс
    massa float default ((0))                 -- ДавлМакс
);

INSERT INTO "standardpumps" ("id","name","tip_nas","h1","h2","h3","h4","h5","h6","h7","h8","h9","h10","n1","n2","n3","n4","n5","n6","n7","n8","n9","n10","k1","k2","k3","k4","k5","k6","k7","k8","k9","k10","q1","q2","q3","q4","q5","q6","q7","q8","q9","q10","q_min","h_min","q_max","h_max","q_nomin","h_nomin","k_nomin","d_nomin","rate_nomin","kol_d","t_max","p_home","h_home","producer","p_home_max","massa") VALUES
(1,'насос одноступенчатый двухстор','Д1250-14',18.0,18.0,17.0,16.0,15.0,14.0,13.0,12.0,11.0,8.0,44.0,48.0,52.0,54.0,56.0,58.0,59.0,60.0,59.0,58.0,0.0,20.0,45.0,50.0,60.0,71.0,77.0,80.0,79.0,70.0,0.0,200.0,500.0,600.0,800.0,1000.0,1200.0,1400.0,1500.0,1800.0,1000.0,14.0,1500.0,11.0,1400.0,12.0,NULL,465.0,730.0,1.0,33.0,3.0,5.0,'Сумской насосный з-д',NULL,1630.0),
(2,'насос одноступенчатый двухстор','Д1250-65',75.0,75.0,74.0,73.0,72.0,70.0,68.0,62.0,58.0,35.0,100.0,130.0,160.0,180.0,200.0,220.0,230.0,260.0,290.0,350.0,0.0,26.0,48.0,65.0,78.0,81.0,83.0,88.0,80.0,40.0,0.0,200.0,400.0,600.0,800.0,910.0,1000.0,1200.0,1490.0,2000.0,910.0,70.0,1490.0,58.0,1200.0,62.0,NULL,460.0,1450.0,1.0,85.0,3.0,6.0,'Ливгидромаш',NULL,1153.0),
(3,'насос одноступенчатый двухстор','Д1600-90',107.0,107.0,107.0,105.0,102.0,99.0,93.0,90.0,78.0,70.0,230.0,260.0,310.0,350.0,380.0,410.0,430.0,460.0,500.0,510.0,0.0,24.0,55.0,65.0,75.0,83.0,85.0,85.0,80.0,68.0,0.0,200.0,500.0,600.0,900.0,1260.0,1400.0,1600.0,1860.0,2000.0,1260.0,99.0,1860.0,78.0,1600.0,90.0,NULL,540.0,980.0,1.0,85.0,2.0,4.0,'Болгария',NULL,1506.0),
(4,'насос одноступенчатый двухстор','Д200-36',36.0,38.0,39.0,41.0,40.0,38.0,37.0,36.0,34.0,30.0,14.0,16.0,18.0,21.0,25.0,27.0,29.0,34.0,35.0,38.0,0.0,13.0,25.0,45.0,60.0,67.0,70.0,71.0,70.0,65.0,0.0,20.0,40.0,80.0,120.0,148.0,180.0,200.0,250.0,280.0,148.0,38.0,250.0,34.0,200.0,36.0,NULL,350.0,1450.0,1.0,85.0,3.0,5.0,'Ливгидромаш',NULL,520.0),
(5,'насос одноступенчатый двухстор','Д200-95',102.0,104.0,106.0,108.0,107.0,105.0,102.0,100.0,95.0,72.0,30.0,35.0,40.0,50.0,60.0,65.0,70.0,74.0,80.0,90.0,0.0,15.0,30.0,51.0,64.0,68.0,69.0,63.0,62.0,40.0,0.0,20.0,40.0,80.0,120.0,135.0,160.0,180.0,203.0,240.0,135.0,105.0,240.0,72.0,180.0,100.0,NULL,280.0,2950.0,1.0,85.0,3.0,3.0,'Ливгидромаш',NULL,752.0),
(6,'насос одноступенчатый двухстор','Д2000-100',116.0,116.0,114.0,112.0,110.0,108.0,104.0,100.0,88.0,88.0,200.0,320.0,450.0,550.0,600.0,650.0,700.0,740.0,800.0,800.0,0.0,29.0,50.0,64.0,69.0,72.0,75.0,75.0,68.0,68.0,0.0,400.0,800.0,1200.0,1400.0,1600.0,1800.0,2000.0,2400.0,2400.0,1600.0,108.0,2400.0,88.0,2000.0,100.0,NULL,855.0,980.0,1.0,85.0,2.0,6.0,'Сумской насосный з-д',NULL,2475.0),
(7,'насос одноступенчатый двухстор','Д2000-34',45.0,45.0,44.0,44.0,40.0,39.0,38.0,36.0,26.0,20.0,87.0,113.0,150.0,175.0,195.0,212.0,220.0,225.0,270.0,250.0,0.0,31.0,69.0,71.0,80.0,85.0,87.0,89.0,72.0,52.0,0.0,300.0,750.0,1050.0,1350.0,1600.0,1700.0,1800.0,2400.0,2700.0,1600.0,39.0,2400.0,26.0,1800.0,36.0,NULL,700.0,730.0,1.0,35.0,3.0,5.0,'Сумской насосный з-д',NULL,2870.0),
(8,'насос одноступенчатый двухстор','Д2500-17',26.0,25.0,24.0,23.0,22.0,20.0,16.0,15.0,14.0,9.0,110.0,118.0,120.0,122.0,124.0,130.0,138.0,140.0,145.0,148.0,0.0,21.0,42.0,60.0,70.0,80.0,90.0,89.0,87.0,60.0,0.0,400.0,600.0,1200.0,1400.0,1800.0,2200.0,2400.0,2600.0,3200.0,1800.0,20.0,2600.0,14.0,2400.0,15.0,NULL,550.0,730.0,1.0,35.0,2.0,5.0,'Сумской насосный з-д',NULL,2934.0),
(9,'насос одноступенчатый двухстор','Д2500-45',53.0,53.0,52.0,51.0,50.0,49.0,46.0,45.0,40.0,39.0,150.0,180.0,220.0,2250.0,280.0,320.0,350.0,360.0,380.0,380.0,0.0,30.0,50.0,70.0,80.0,84.0,88.0,89.0,88.0,87.0,0.0,400.0,800.0,1200.0,1600.0,2000.0,2400.0,2600.0,3000.0,3200.0,2000.0,49.0,3000.0,48.0,2600.0,45.0,NULL,755.0,730.0,1.0,35.0,2.0,7.0,'Сумской насосный з-д',NULL,4152.0),
(10,'насос одноступенчатый двухстор','Д2500-62',75.0,75.0,74.0,73.0,71.0,70.0,65.0,60.0,54.0,50.0,200.0,320.0,380.0,400.0,440.0,460.0,480.0,490.0,500.0,500.0,0.0,50.0,67.0,75.0,82.0,84.0,89.0,90.0,86.0,80.0,0.0,750.0,1200.0,1500.0,1800.0,1980.0,2250.0,2400.0,2700.0,3000.0,1980.0,84.0,2700.0,86.0,2400.0,60.0,NULL,700.0,980.0,1.0,85.0,2.0,7.0,'Сумской насосный з-д',NULL,2870.0),
(11,'насос одноступенчатый двухстор','Д320-50',53.0,56.0,58.0,58.0,56.0,56.0,53.0,48.0,40.0,28.0,20.0,25.0,30.0,38.0,40.0,45.0,50.0,60.0,70.0,85.0,0.0,5.0,45.0,58.0,62.0,68.0,74.0,78.0,71.0,55.0,0.0,50.0,100.0,150.0,175.0,200.0,250.0,325.0,420.0,500.0,200.0,56.0,420.0,40.0,325.0,48.0,NULL,405.0,2950.0,1.0,85.0,3.0,3.0,'Ливгидромаш',NULL,886.0),
(12,'насос одноступенчатый двухстор','Д320-70',41.0,42.0,43.0,43.0,44.0,43.0,42.0,41.0,35.0,29.0,30.0,33.0,35.0,45.0,57.0,60.0,66.0,72.0,82.0,90.0,0.0,18.0,35.0,60.0,75.0,78.0,79.0,80.0,71.0,61.0,0.0,50.0,100.0,200.0,300.0,350.0,400.0,450.0,620.0,700.0,350.0,43.0,620.0,35.0,450.0,41.0,NULL,242.0,2950.0,1.0,85.0,3.0,4.0,'Ливгидромаш',NULL,789.0),
(13,'насос одноступенчатый двухстор','Д3200-20',27.0,26.0,25.0,24.0,23.0,22.0,21.0,20.0,18.0,4.0,140.0,150.0,160.0,170.0,180.0,190.0,200.0,205.0,220.0,240.0,0.0,35.0,60.0,74.0,79.0,81.0,82.0,85.0,82.0,55.0,0.0,800.0,1600.0,2000.0,2400.0,2660.0,2940.0,3200.0,3870.0,5600.0,2660.0,22.0,3870.0,18.0,3200.0,20.0,NULL,665.0,585.0,1.0,35.0,2.0,4.0,'Сумской насосный з-д',NULL,5018.0),
(14,'насос одноступенчатый двухстор','Д3200-33',45.0,43.0,41.0,38.0,37.0,35.0,34.0,33.0,29.0,27.0,230.0,245.0,255.0,270.0,290.0,300.0,310.0,315.0,325.0,340.0,0.0,23.0,41.0,60.0,71.0,84.0,85.0,86.0,84.0,80.0,0.0,500.0,1000.0,1500.0,2000.0,2560.0,2920.0,3200.0,3760.0,4000.0,2500.0,35.0,4000.0,27.0,3200.0,33.0,NULL,550.0,980.0,1.0,85.0,2.0,7.0,'Сумской насосный з-д',NULL,2934.0),
(15,'насос одноступенчатый двухстор','Д3200-75',89.0,88.0,87.0,86.0,85.0,80.0,78.0,75.0,68.0,65.0,400.0,400.0,480.0,520.0,560.0,720.0,760.0,800.0,800.0,800.0,0.0,20.0,49.0,64.0,73.0,81.0,85.0,86.0,86.0,86.0,0.0,400.0,1200.0,1600.0,2000.0,2560.0,2800.0,3200.0,3760.0,4000.0,2560.0,88.0,3760.0,68.0,3200.0,75.0,NULL,755.0,980.0,1.0,85.0,2.0,7.0,'Сумской насосный з-д',NULL,4152.0),
(16,'насос одноступенчатый двухстор','Д4000-22',30.0,29.0,28.0,26.0,25.0,24.0,23.0,22.0,20.0,10.0,220.0,225.0,230.0,260.0,280.0,290.0,300.0,310.0,310.0,180.0,0.0,23.0,43.0,63.0,71.0,75.0,78.0,80.0,79.0,70.0,0.0,800.0,1600.0,2400.0,2800.0,3200.0,3600.0,4000.0,4800.0,6400.0,3200.0,24.0,4800.0,20.0,4000.0,22.0,NULL,740.0,585.0,1.0,85.0,2.0,5.0,'Сумской насосный з-д',NULL,NULL),
(17,'насос одноступенчатый двухстор','Д500-36',90.0,92.0,93.0,94.0,93.0,92.0,91.0,90.0,85.0,76.0,100.0,120.0,130.0,150.0,170.0,180.0,195.0,200.0,256.0,320.0,0.0,24.0,44.0,60.0,70.0,78.0,79.0,80.0,75.0,59.0,0.0,100.0,200.0,300.0,400.0,500.0,550.0,600.0,800.0,900.0,500.0,92.0,800.0,85.0,600.0,90.0,NULL,525.0,980.0,1.0,85.0,3.0,4.0,'Ливгидромаш',NULL,725.0),
(18,'насос одноступенчатый двухстор','Д5000-32',44.0,43.0,42.0,40.0,39.0,38.0,36.0,32.0,29.0,24.0,340.0,340.0,380.0,400.0,440.0,480.0,490.0,500.0,490.0,480.0,0.0,25.0,49.0,68.0,80.0,85.0,88.0,90.0,89.0,80.0,0.0,800.0,1600.0,2400.0,3200.0,4000.0,4400.0,5000.0,5600.0,6400.0,4000.0,38.0,5600.0,29.0,5000.0,32.0,NULL,700.0,750.0,1.0,85.0,2.0,8.0,'Сумской насосный з-д',NULL,5018.0),
(19,'насос одноступенчатый двухстор','Д5000-50',60.0,60.0,60.0,59.0,57.0,56.0,55.0,50.0,45.0,40.0,160.0,240.0,320.0,440.0,480.0,520.0,600.0,640.0,720.0,760.0,0.0,30.0,47.0,61.0,78.0,82.0,86.0,90.0,88.0,85.0,0.0,800.0,1600.0,2400.0,3200.0,4000.0,4400.0,5000.0,6140.0,6400.0,4000.0,56.0,6140.0,45.0,5000.0,50.0,NULL,990.0,585.0,1.0,35.0,2.0,5.0,'Сумской насосный з-д',NULL,8698.0),
(20,'насос одноступенчатый двухстор','Д630-90',84.0,83.0,82.0,81.0,80.0,79.0,78.0,72.0,65.0,50.0,34.0,40.0,46.0,52.0,60.0,64.0,68.0,74.0,77.0,60.0,0.0,27.0,43.0,58.0,70.0,73.0,78.0,80.0,64.0,50.0,0.0,50.0,100.0,150.0,200.0,220.0,250.0,280.0,325.0,375.0,220.0,79.0,325.0,65.0,280.0,72.0,NULL,525.0,1450.0,1.0,85.0,3.0,6.0,'Ливгидромаш',NULL,725.0),
(21,'насос одноступенчатый двухстор','Д6300-80',94.0,94.0,93.0,92.0,89.0,85.0,83.0,80.0,54.0,53.0,700.0,800.0,1040.0,1120.0,1300.0,1400.0,1480.0,1560.0,1700.0,1700.0,0.0,24.0,55.0,70.0,80.0,84.0,86.0,87.0,88.0,88.0,0.0,800.0,2400.0,3200.0,4400.0,4930.0,5600.0,6300.0,7200.0,7200.0,4930.0,85.0,7200.0,54.0,6300.0,80.0,NULL,990.0,730.0,1.0,85.0,2.0,7.0,'Сумской насосный з-д',NULL,8698.0),
(22,'насос одноступенчатый двухстор','Д800-28',36.0,35.0,35.0,34.0,34.0,33.0,31.0,29.0,27.0,19.0,33.0,38.0,42.0,48.0,52.0,60.0,68.0,72.0,78.0,92.0,0.0,21.0,41.0,59.0,70.0,80.0,89.0,90.0,84.0,59.0,0.0,100.0,200.0,300.0,400.0,540.0,700.0,800.0,900.0,1200.0,540.0,33.0,900.0,27.0,800.0,29.0,NULL,460.0,980.0,1.0,80.0,3.0,6.0,'Ливгидромаш',NULL,1153.0),
(23,'насос консольный с осевым подв','К160/20',22.0,23.0,24.0,25.0,25.0,24.0,23.0,20.0,16.0,15.0,6.0,7.0,7.0,8.0,8.0,9.0,10.0,10.0,10.0,10.0,0.0,18.0,30.0,45.0,60.0,72.0,80.0,80.0,79.0,71.0,0.0,20.0,40.0,60.0,80.0,110.0,140.0,160.0,190.0,220.0,110.0,24.0,190.0,16.0,160.0,20.0,NULL,264.0,1450.0,1.0,105.0,8.0,4.0,NULL,NULL,NULL),
(24,'насос консольный с осевым подв','К160/30',37.0,39.0,39.0,38.0,37.0,35.0,32.0,30.0,28.0,20.0,9.0,10.0,11.0,11.0,14.0,15.0,16.0,18.0,19.0,21.0,0.0,32.0,35.0,58.0,65.0,70.0,72.0,72.0,70.0,60.0,0.0,40.0,60.0,80.0,100.0,125.0,140.0,160.0,190.0,210.0,125.0,35.0,190.0,28.0,160.0,30.0,NULL,328.0,1450.0,1.0,105.0,8.0,4.0,NULL,NULL,NULL),
(25,'насос консольный с осевым подв','_20/18',20.0,20.0,21.0,21.0,21.0,21.0,20.0,18.0,17.0,15.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,2.0,2.0,2.0,0.0,20.0,30.0,40.0,51.0,52.0,64.0,68.0,68.0,60.0,0.0,3.0,5.0,8.0,10.0,11.0,15.0,20.0,23.0,25.0,11.0,21.0,23.0,17.0,20.0,18.0,NULL,129.0,2900.0,1.0,105.0,1.0,3.0,NULL,NULL,NULL),
(26,'насос консольный с осевым подв','К20/30',33.0,34.0,34.0,34.0,33.0,32.0,32.0,30.0,26.0,23.0,1.0,1.0,1.0,2.0,2.0,2.0,2.0,3.0,3.0,3.0,0.0,20.0,30.0,40.0,45.0,50.0,60.0,63.0,63.0,65.0,0.0,4.0,5.0,7.0,9.0,10.0,15.0,20.0,26.0,30.0,10.0,32.0,26.0,26.0,20.0,30.0,NULL,160.0,2900.0,1.0,105.0,8.0,3.0,NULL,NULL,NULL),
(27,'насос консольный с осевым подв','К290/18',21.0,22.0,22.0,22.0,21.0,20.0,19.0,18.0,16.0,12.0,10.0,12.0,13.0,14.0,15.0,15.0,16.0,16.0,18.0,19.0,0.0,40.0,50.0,65.0,75.0,80.0,85.0,85.0,79.0,70.0,0.0,80.0,120.0,160.0,200.0,220.0,260.0,290.0,330.0,360.0,220.0,20.0,330.0,16.0,290.0,18.0,NULL,268.0,1450.0,1.0,105.0,8.0,4.0,NULL,NULL,NULL),
(28,'насос консольный с осевым подв','К290/30',35.0,36.0,36.0,35.0,35.0,34.0,33.0,30.0,25.0,23.0,18.0,20.0,21.0,21.0,22.0,25.0,26.0,26.0,28.0,30.0,0.0,39.0,50.0,65.0,75.0,80.0,81.0,80.0,75.0,70.0,0.0,80.0,120.0,160.0,200.0,225.0,260.0,290.0,330.0,360.0,225.0,34.0,330.0,25.0,290.0,30.0,NULL,315.0,1450.0,1.0,105.0,8.0,4.0,NULL,NULL,NULL),
(29,'насос консольный с осевым подв','К45/30',34.0,35.0,36.0,36.0,35.0,34.0,33.0,30.0,27.0,25.0,2.0,3.0,3.0,3.0,4.0,4.0,4.0,5.0,5.0,5.0,0.0,28.0,39.0,47.0,54.0,61.0,65.0,70.0,71.0,70.0,0.0,10.0,15.0,20.0,25.0,30.0,35.0,45.0,55.0,60.0,30.0,34.0,55.0,27.0,45.0,30.0,NULL,168.0,2900.0,1.0,105.0,1.0,4.0,NULL,NULL,NULL),
(30,'насос консольный с осевым подв','К45/55',60.0,60.0,60.0,60.0,60.0,59.0,57.0,53.0,45.0,40.0,5.0,6.0,7.0,8.0,9.0,9.0,10.0,10.0,10.0,11.0,0.0,22.0,34.0,42.0,48.0,52.0,60.0,62.0,62.0,60.0,0.0,10.0,15.0,20.0,25.0,30.0,40.0,45.0,62.0,63.0,30.0,59.0,62.0,45.0,45.0,53.0,NULL,218.0,2900.0,1.0,105.0,8.0,4.0,NULL,NULL,NULL),
(31,'насос консольный с осевым подв','К8/18',19.0,19.0,19.0,19.0,19.0,19.0,19.0,18.0,13.0,12.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,15.0,25.0,31.0,36.0,42.0,49.0,50.0,50.0,49.0,0.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,14.0,15.0,6.0,19.0,14.0,13.0,8.0,18.0,NULL,125.0,2900.0,1.0,105.0,8.0,4.0,NULL,NULL,NULL),
(32,'насос консольный с осевым подв','К90/20',26.0,28.0,28.0,28.0,27.0,26.0,24.0,20.0,21.0,17.0,3.0,4.0,5.0,5.0,6.0,6.0,7.0,7.0,7.0,6.0,0.0,39.0,53.0,55.0,70.0,75.0,80.0,80.0,75.0,75.0,0.0,20.0,30.0,40.0,50.0,60.0,70.0,90.0,100.0,110.0,60.0,26.0,100.0,21.0,90.0,20.0,NULL,145.0,2900.0,1.0,105.0,8.0,5.0,NULL,NULL,NULL),
(33,'насос консольный с осевым подв','К90/35',35.0,38.0,39.0,40.0,39.0,38.0,35.0,35.0,20.0,20.0,9.0,9.0,9.0,10.0,11.0,11.0,12.0,13.0,14.0,14.0,0.0,32.0,47.0,55.0,62.0,70.0,75.0,75.0,70.0,58.0,0.0,20.0,30.0,40.0,50.0,65.0,80.0,90.0,113.0,120.0,65.0,38.0,113.0,20.0,90.0,35.0,NULL,174.0,2900.0,1.0,105.0,8.0,5.0,NULL,NULL,NULL),
(34,'насос консольный с осевым подв','К90/55',60.0,60.0,60.0,60.0,60.0,60.0,58.0,55.0,45.0,40.0,12.0,12.0,13.0,14.0,15.0,18.0,19.0,20.0,21.0,22.0,0.0,25.0,35.0,45.0,62.0,65.0,70.0,70.0,62.0,52.0,0.0,20.0,30.0,40.0,60.0,66.0,80.0,90.0,113.0,120.0,66.0,60.0,113.0,45.0,90.0,55.0,NULL,218.0,2900.0,1.0,105.0,8.0,5.0,NULL,NULL,NULL),
(35,'насос консольный с осевым подв','К90/85',97.0,98.0,99.0,99.0,98.0,97.0,95.0,85.0,70.0,62.0,19.0,20.0,21.0,22.0,25.0,28.0,29.0,30.0,36.0,37.0,0.0,25.0,32.0,45.0,58.0,60.0,65.0,66.0,64.0,60.0,0.0,20.0,30.0,40.0,60.0,66.0,80.0,90.0,118.0,130.0,66.0,97.0,118.0,70.0,90.0,85.0,NULL,272.0,2900.0,1.0,105.0,8.0,5.0,NULL,NULL,NULL),
(36,'насос центробежный спиральный','СЭ1250-140',170.0,170.0,168.0,162.0,158.0,155.0,150.0,140.0,135.0,130.0,300.0,330.0,370.0,420.0,450.0,480.0,520.0,560.0,600.0,630.0,0.0,24.0,45.0,61.0,70.0,74.0,79.0,81.0,80.0,80.0,0.0,200.0,400.0,600.0,750.0,850.0,1050.0,1250.0,1330.0,1330.0,850.0,155.0,1330.0,135.0,1250.0,140.0,NULL,470.0,1500.0,1.0,180.0,11.0,7.0,NULL,NULL,4350.0),
(37,'насос центробежный спиральный','СЭ1250-45',62.0,64.0,62.0,60.0,58.0,57.0,55.0,45.0,40.0,38.0,85.0,110.0,122.0,140.0,155.0,160.0,170.0,175.0,200.0,200.0,0.0,45.0,60.0,70.0,78.0,79.0,80.0,80.0,75.0,73.0,0.0,300.0,450.0,600.0,750.0,840.0,900.0,1250.0,1410.0,1500.0,840.0,57.0,1410.0,40.0,1250.0,45.0,NULL,415.0,1500.0,1.0,180.0,11.0,7.0,NULL,NULL,NULL),
(38,'насос центробежный спиральный','СЭ1250-70',88.0,88.0,87.0,85.0,83.0,82.0,73.0,70.0,66.0,63.0,140.0,160.0,179.0,205.0,222.0,240.0,280.0,295.0,308.0,318.0,0.0,35.0,52.0,69.0,75.0,80.0,82.0,82.0,80.0,75.0,0.0,250.0,400.0,600.0,750.0,850.0,1150.0,1250.0,1340.0,1400.0,850.0,82.0,1340.0,66.0,1250.0,70.0,NULL,490.0,1500.0,1.0,180.0,11.0,7.0,'Сумской насосный з-д',NULL,1843.0),
(39,'насос центробежный спиральный','СЭ2500-180',240.0,240.0,240.0,237.0,235.0,218.0,207.0,180.0,155.0,145.0,1000.0,1000.0,1020.0,1050.0,1120.0,1320.0,1410.0,1460.0,1480.0,1480.0,0.0,20.0,33.0,45.0,55.0,76.0,84.0,85.0,84.0,82.0,0.0,250.0,500.0,750.0,1000.0,1700.0,2200.0,2500.0,2850.0,3000.0,1700.0,218.0,2850.0,155.0,2500.0,180.0,NULL,415.0,3000.0,1.0,120.0,10.0,28.0,NULL,NULL,NULL),
(40,'насос центробежный спиральный','СЭ2500-60',82.0,80.0,79.0,75.0,71.0,69.0,65.0,60.0,56.0,45.0,260.0,300.0,320.0,350.0,380.0,400.0,420.0,440.0,450.0,460.0,0.0,37.0,53.0,65.0,74.0,78.0,84.0,86.0,84.0,79.0,0.0,480.0,800.0,1120.0,1440.0,1600.0,2080.0,2500.0,2760.0,3200.0,1600.0,69.0,2760.0,56.0,2500.0,60.0,NULL,470.0,1500.0,1.0,180.0,11.0,12.0,'Сумский насосный з-д',25.0,3675.0),
(41,'насос центробежный спиральный','СЭ500-70',90.0,92.0,90.0,86.0,84.0,81.0,72.0,70.0,66.0,61.0,65.0,82.0,97.0,115.0,122.0,126.0,140.0,142.0,150.0,156.0,0.0,18.0,45.0,66.0,72.0,75.0,81.0,81.0,81.0,76.0,0.0,48.0,151.0,272.0,327.0,360.0,475.0,500.0,550.0,600.0,360.0,81.0,550.0,66.0,500.0,70.0,NULL,250.0,3000.0,1.0,180.0,16.0,10.0,'Ливгидромаш',NULL,2260.0),
(42,'насос центробежный спиральный','СЭ5000-16011',242.0,235.0,220.0,205.0,200.0,188.0,180.0,160.0,140.0,130.0,1650.0,1800.0,2080.0,2100.0,2200.0,2250.0,2400.0,2500.0,2450.0,2420.0,0.0,40.0,70.0,79.0,80.0,85.0,90.0,90.0,85.0,82.0,0.0,1200.0,2400.0,3000.0,3300.0,3600.0,4200.0,5000.0,5550.0,6000.0,3600.0,188.0,5550.0,140.0,5000.0,160.0,NULL,415.0,3000.0,1.0,120.0,10.0,40.0,NULL,NULL,NULL),
(43,'насос центробежный спиральный','СЭ5000-70',108.0,104.0,100.0,98.0,88.0,87.0,85.0,70.0,60.0,60.0,1650.0,1800.0,2080.0,2100.0,2200.0,2250.0,2400.0,2500.0,2450.0,2420.0,0.0,40.0,55.0,70.0,80.0,82.0,84.0,84.0,82.0,82.0,0.0,1000.0,1500.0,2000.0,3000.0,3600.0,4000.0,5000.0,5500.0,5500.0,3600.0,87.0,5500.0,60.0,5000.0,70.0,NULL,550.0,1500.0,1.0,120.0,6.0,15.0,NULL,NULL,NULL),
(44,'насос центробежный спиральный','СЭ800-100',122.0,122.0,121.0,120.0,116.0,114.0,105.0,100.0,96.0,85.0,143.0,148.0,188.0,195.0,220.0,230.0,262.0,278.0,285.0,300.0,0.0,21.0,45.0,60.0,73.0,75.0,80.0,80.0,79.0,75.0,0.0,112.0,250.0,360.0,500.0,550.0,725.0,800.0,850.0,950.0,550.0,114.0,850.0,96.0,800.0,100.0,NULL,415.0,1500.0,1.0,180.0,11.0,5.0,NULL,NULL,5151.0),
(45,'насос центробежный спиральный','СЭ800-55',66.0,65.0,64.0,63.0,62.0,61.0,60.0,55.0,53.0,45.0,95.0,98.0,107.0,113.0,118.0,124.0,135.0,150.0,158.0,167.0,0.0,19.0,58.0,68.0,72.0,76.0,79.0,80.0,76.0,72.0,0.0,100.0,350.0,450.0,500.0,560.0,650.0,800.0,875.0,1000.0,560.0,61.0,875.0,53.0,800.0,55.0,NULL,410.0,1500.0,1.0,180.0,11.0,5.0,'Ливгидромаш',NULL,230.0),
(46,'насос центробежный секционный','ЦН1000-180',239.0,238.0,228.0,220.0,210.0,200.0,190.0,180.0,180.0,165.0,290.0,340.0,400.0,480.0,510.0,550.0,600.0,620.0,620.0,640.0,0.0,40.0,62.0,74.0,78.0,80.0,81.0,81.0,81.0,80.0,0.0,200.0,400.0,600.0,700.0,800.0,900.0,1000.0,1100.0,1100.0,800.0,200.0,1100.0,180.0,1000.0,180.0,NULL,575.0,1480.0,1.0,100.0,2.0,8.0,NULL,NULL,NULL),
(47,'насос центробежный секционный','ЦН400-105',139.0,137.0,135.0,130.0,124.0,122.0,115.0,105.0,93.0,72.0,77.0,85.0,101.0,117.0,130.0,140.0,150.0,160.0,170.0,175.0,0.0,25.0,54.0,62.0,72.0,75.0,78.0,79.0,78.0,68.0,0.0,60.0,150.0,210.0,270.0,300.0,360.0,400.0,500.0,600.0,300.0,122.0,500.0,93.0,400.0,105.0,NULL,445.0,1480.0,1.0,80.0,2.0,6.0,'насосный з-д,г.Сумы',16.0,1922.0),
(48,'насос центробежный секционный','ЦН400-210',275.0,270.0,265.0,255.0,245.0,240.0,228.0,210.0,183.0,150.0,150.0,170.0,200.0,235.0,260.0,270.0,300.0,318.0,328.0,350.0,0.0,28.0,52.0,65.0,71.0,75.0,78.0,79.0,76.0,68.0,0.0,60.0,150.0,210.0,270.0,300.0,360.0,400.0,500.0,600.0,300.0,240.0,500.0,183.0,400.0,210.0,NULL,445.0,1480.0,1.0,100.0,2.0,5.0,NULL,NULL,NULL),
(49,'насос центробежный спиральный','СЭ2500-60',82.0,80.0,79.0,75.0,71.0,69.0,65.0,60.0,56.0,45.0,280.0,300.0,320.0,350.0,380.0,400.0,420.0,440.0,450.0,460.0,0.0,37.0,53.0,65.0,74.0,78.0,84.0,86.0,84.0,79.0,0.0,480.0,800.0,1120.0,1440.0,1600.0,2080.0,2500.0,2760.0,3200.0,1600.0,69.0,2760.0,56.0,2500.0,60.0,NULL,470.0,1500.0,1.0,180.0,11.0,12.0,'Сумский насосный з-д',25.0,3675.0),
(50,'насос центробежный спиральный','СЭ2500-60',82.0,80.0,79.0,75.0,71.0,69.0,65.0,60.0,56.0,45.0,280.0,300.0,320.0,350.0,380.0,400.0,420.0,440.0,450.0,460.0,0.0,37.0,53.0,65.0,74.0,78.0,84.0,86.0,84.0,79.0,0.0,480.0,800.0,1120.0,1440.0,1600.0,2080.0,2500.0,2760.0,3200.0,1600.0,69.0,2760.0,56.0,2500.0,60.0,NULL,470.0,1500.0,1.0,180.0,11.0,12.0,'Сумский насосный з-д',25.0,3675.0),
(51,'насос одноступенчатый двухстор','300Д-70',85.0,93.0,89.0,85.0,75.0,72.0,71.0,70.0,65.0,54.0,10.0,50.0,90.0,130.0,170.0,240.0,245.0,248.0,250.0,260.0,0.0,32.0,48.0,60.0,80.0,85.0,86.0,87.0,87.0,81.0,0.0,144.0,288.0,432.0,720.0,1008.0,1044.0,1080.0,1224.0,1440.0,1008.0,72.0,1440.0,54.0,1080.0,70.0,NULL,472.0,1485.0,1.0,80.0,NULL,3.0,'хоз.комбинат по произв.насосов им.Г.Димитрова',16.0,NULL),
(52,'насос одноступенчатый двухстор','200Д-60',52.0,49.0,46.0,43.0,40.0,39.0,38.0,37.0,36.0,30.0,49.0,52.0,55.0,58.0,61.0,60.0,62.0,68.0,70.0,82.0,0.0,33.0,64.0,78.0,81.0,84.0,85.0,85.0,84.0,67.0,0.0,106.0,216.0,324.0,360.0,396.0,432.0,486.0,504.0,630.0,396.0,39.0,630.0,30.0,486.0,37.0,NULL,525.0,NULL,1.0,80.0,NULL,6.0,'хоз.комбинат по произв.насосов им.Г.Димитрова',16.0,633.0),
(53,'насос одноступенчатый двухстор','300Д-70а',87.0,83.0,70.0,95.0,65.0,62.0,61.0,60.0,55.0,44.0,33.0,37.0,41.0,45.0,110.0,185.0,190.0,200.0,210.0,225.0,0.0,32.0,48.0,62.0,82.0,86.0,86.0,86.0,85.0,79.0,0.0,144.0,288.0,432.0,720.0,1008.0,1044.0,1080.0,1224.0,1440.0,1008.0,86.0,1440.0,79.0,1080.0,86.0,NULL,472.0,1450.0,1.0,80.0,NULL,3.0,'машино-экспорт',16.0,NULL),
(54,'насос одноступенчатый двухстор','200Д-90',119.0,116.0,113.0,110.0,94.0,93.0,92.0,90.0,87.0,83.0,30.0,70.0,110.0,150.0,190.0,200.0,210.0,215.0,225.0,240.0,0.0,36.0,53.0,77.0,79.0,80.0,81.0,81.0,80.0,78.0,0.0,144.0,288.0,576.0,612.0,648.0,684.0,720.0,756.0,792.0,648.0,93.0,792.0,83.0,720.0,90.0,NULL,500.0,1480.0,1.0,80.0,NULL,NULL,'хоз.комбинат по произв.насосов им.Г.Димитрова',NULL,NULL),
(55,'насос одноступенчатый двухстор','300Д-90',100.0,96.0,92.0,86.0,70.0,70.0,70.0,70.0,65.0,55.0,40.0,44.0,48.0,52.0,56.0,240.0,250.0,255.0,270.0,290.0,0.0,43.0,60.0,68.0,83.0,86.0,86.0,87.0,88.0,86.0,0.0,144.0,360.0,576.0,864.0,1044.0,1062.0,1080.0,1168.0,1332.0,1044.0,70.0,1332.0,55.0,1080.0,70.0,NULL,460.0,1450.0,1.0,80.0,NULL,3.0,'хоз.комбинат по произв.насосов им.Г.Димитрова',16.0,2209.0),
(56,'насос консольный с осевым подв','Д2000-21',32.0,31.0,29.0,27.0,26.0,24.0,23.0,21.0,17.0,16.0,92.0,102.0,111.0,120.0,124.0,128.0,132.0,132.0,140.0,141.0,0.0,34.0,68.0,74.0,80.0,84.0,85.0,85.0,78.0,76.0,0.0,400.0,800.0,1200.0,1400.0,1600.0,1800.0,2000.0,2360.0,2400.0,1600.0,24.0,2400.0,16.0,2000.0,21.0,NULL,460.0,980.0,1.0,85.0,2.0,4.0,'Сумской насосный з-д',NULL,1630.0),
(57,'насос центробежный секционный','ЦН400-105',139.0,137.0,135.0,130.0,124.0,122.0,115.0,105.0,93.0,72.0,77.0,85.0,101.0,117.0,130.0,140.0,150.0,160.0,170.0,175.0,0.0,25.0,54.0,62.0,72.0,75.0,78.0,79.0,78.0,68.0,0.0,60.0,150.0,210.0,270.0,300.0,360.0,400.0,500.0,600.0,300.0,122.0,600.0,72.0,290.0,120.0,NULL,445.0,1480.0,1.0,80.0,NULL,NULL,'насосный з-д,г.Сумы',16.0,1922.0),
(58,'насос одноступенчатый двухстор','Д2500-60',75.0,76.0,76.0,74.0,71.0,70.0,66.0,62.0,50.0,50.0,320.0,320.0,330.0,360.0,400.0,410.0,420.0,450.0,500.0,500.0,0.0,33.0,47.0,66.0,80.0,85.0,88.0,89.0,81.0,81.0,0.0,500.0,750.0,1250.0,1750.0,2000.0,2250.0,2500.0,3000.0,3000.0,2000.0,70.0,3000.0,50.0,2500.0,60.0,NULL,700.0,NULL,1.0,85.0,2.0,7.0,'Сумской насосный з-д',16.0,2870.0),
(59,'насос одноступенчатый двухстор','Д500-65',66.0,72.0,73.0,74.0,73.0,72.0,69.0,64.0,60.0,43.0,35.0,50.0,60.0,69.0,85.0,92.0,104.0,120.0,132.0,160.0,0.0,21.0,35.0,48.0,65.0,69.0,75.0,78.0,75.0,52.0,0.0,100.0,150.0,200.0,300.0,340.0,400.0,500.0,550.0,700.0,340.0,69.0,700.0,43.0,500.0,64.0,NULL,465.0,1450.0,1.0,85.0,3.0,4.0,'Ливгидромаш',NULL,610.0),
(60,'насос одноступенчатый двухстор','Д3200-55',62.0,62.0,62.0,61.0,60.0,57.0,56.0,55.0,48.0,37.0,250.0,260.0,320.0,370.0,420.0,470.0,500.0,510.0,560.0,620.0,0.0,30.0,50.0,65.0,76.0,84.0,88.0,90.0,88.0,75.0,0.0,500.0,1000.0,1500.0,2000.0,2550.0,3000.0,3200.0,3900.0,5000.0,2550.0,57.0,5000.0,37.0,3200.0,55.0,NULL,825.0,735.0,1.0,85.0,NULL,5.0,'Сумской насосный з-д',NULL,4959.0),
(61,'насос одноступенчатый двухстор','Д4000-95',107.0,107.0,106.0,104.0,102.0,101.0,98.0,95.0,90.0,71.0,50.0,620.0,760.0,900.0,1010.0,1020.0,1100.0,1180.0,1230.0,1380.0,0.0,25.0,55.0,74.0,81.0,84.0,87.0,89.0,90.0,82.0,0.0,600.0,1500.0,2400.0,3000.0,3200.0,3600.0,4000.0,4500.0,6000.0,3200.0,101.0,6000.0,71.0,4000.0,95.0,NULL,825.0,980.0,1.0,85.0,2.0,8.0,'Сумской насосный з-д',NULL,4959.0),
(62,'насос одноступенчатый двухстор','Д12500-24',37.0,35.0,33.0,31.0,29.0,28.0,26.0,24.0,23.0,18.0,670.0,700.0,740.0,750.0,950.0,970.0,900.0,930.0,970.0,970.0,0.0,28.0,48.0,63.0,75.0,80.0,87.0,87.0,85.0,78.0,0.0,2000.0,4000.0,6000.0,8000.0,9000.0,11000.0,12500.0,12700.0,14000.0,9000.0,28.0,14000.0,18.0,12500.0,24.0,NULL,985.0,500.0,1.0,85.0,1.0,NULL,'Уралгидромаш',NULL,16338.0),
(63,'насос консольный с осевым подв','2К-20/18',20.0,23.0,24.0,23.0,22.0,21.0,18.0,17.0,16.0,15.0,1.0,1.0,1.0,1.0,1.0,2.0,2.0,2.0,2.0,2.0,0.0,39.0,50.0,58.0,60.0,61.0,62.0,64.0,63.0,62.0,0.0,5.0,10.0,13.0,15.0,16.0,20.0,23.0,25.0,28.0,16.0,21.0,28.0,15.0,23.0,17.0,NULL,120.0,2900.0,1.0,85.0,NULL,6.0,'ПО"Армхиммаш',NULL,75.0),
(64,'насос консольный с осевым подв','3К-45/30',32.0,36.0,36.0,35.0,32.0,31.0,29.0,28.0,25.0,20.0,0.0,3.0,4.0,5.0,6.0,6.0,6.0,6.0,6.0,6.0,0.0,30.0,50.0,60.0,70.0,70.0,70.0,70.0,68.0,65.0,0.0,10.0,20.0,30.0,40.0,45.0,50.0,52.0,60.0,70.0,45.0,31.0,70.0,20.0,52.0,28.0,NULL,168.0,2900.0,1.0,85.0,NULL,4.0,'ПО"Армхиммаш',NULL,NULL),
(65,'насос консольный с осевым подв','4К-90/20',26.0,27.0,27.0,27.0,27.0,26.0,25.0,21.0,18.0,13.0,2.0,3.0,4.0,4.0,5.0,6.0,6.0,7.0,7.0,7.0,0.0,20.0,40.0,55.0,65.0,70.0,75.0,80.0,75.0,60.0,0.0,10.0,20.0,30.0,40.0,50.0,60.0,90.0,100.0,120.0,50.0,26.0,120.0,13.0,90.0,20.0,NULL,148.0,2900.0,1.0,85.0,NULL,5.0,'ПО"Армхиммаш',NULL,NULL),
(66,'насос консольный с осевым подв','1.5К-8/19',20.0,21.0,21.0,21.0,22.0,21.0,20.0,19.0,18.0,13.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,12.0,28.0,32.0,40.0,50.0,55.0,58.0,58.0,50.0,0.0,1.0,2.0,3.0,5.0,6.0,8.0,10.0,12.0,16.0,6.0,21.0,16.0,13.0,10.0,19.0,NULL,128.0,2900.0,1.0,85.0,NULL,7.0,'ПО"Армхиммаш',NULL,69.0),
(67,'насос консольный с осевым подв','2К-20/30',34.0,35.0,36.0,34.0,33.0,31.0,29.0,27.0,21.0,16.0,1.0,2.0,2.0,2.0,3.0,3.0,3.0,3.0,3.0,3.0,0.0,30.0,40.0,58.0,64.0,65.0,67.0,68.0,60.0,55.0,0.0,5.0,7.0,15.0,17.0,20.0,24.0,27.0,35.0,40.0,20.0,31.0,40.0,16.0,27.0,27.0,NULL,162.0,2900.0,1.0,85.0,NULL,12.0,'ПО"Армхиммаш',NULL,90.0),
(68,'насос конденсатный турбинный','Кс32-150',18.0,18.0,18.0,18.0,18.0,18.0,17.0,16.0,15.0,10.0,15.0,15.0,15.0,16.0,17.0,18.0,19.0,20.0,22.0,30.0,0.0,15.0,30.0,42.0,48.0,52.0,59.0,62.0,60.0,48.0,0.0,5.0,10.0,15.0,17.0,20.0,25.0,30.0,35.0,50.0,20.0,18.0,50.0,10.0,30.0,16.0,NULL,178.0,2980.0,1.0,150.0,NULL,1.0,'Сумский насосный з-д',NULL,645.0),
(69,'насос конденсатный турбинный','Кс125-55',64.0,65.0,65.0,63.0,62.0,60.0,57.0,51.0,46.0,30.0,12.0,16.0,19.0,23.0,25.0,27.0,29.0,30.0,30.0,30.0,0.0,35.0,49.0,50.0,64.0,66.0,67.0,67.0,65.0,50.0,0.0,30.0,50.0,75.0,90.0,100.0,115.0,130.0,150.0,190.0,100.0,60.0,190.0,30.0,130.0,51.0,NULL,240.0,1450.0,1.0,120.0,NULL,1.0,'Сумский насосный з-д',NULL,1899.0),
(70,'насос конденсатный турбинный д','КсД230-115/3',74.0,74.0,73.0,72.0,68.0,67.0,64.0,61.0,55.0,37.0,25.0,29.0,34.0,37.0,41.0,43.0,47.0,49.0,52.0,56.0,0.0,29.0,49.0,54.0,64.0,68.0,73.0,74.0,73.0,51.0,0.0,40.0,80.0,100.0,140.0,160.0,200.0,220.0,260.0,360.0,160.0,67.0,360.0,37.0,220.0,61.0,NULL,415.0,960.0,1.0,120.0,NULL,1.0,'Сумский насосный з-д',NULL,3636.0),
(71,'насос конденсатный турбинный д','КсД230-115/3',124.0,125.0,126.0,123.0,119.0,112.0,107.0,102.0,94.0,78.0,64.0,75.0,89.0,100.0,110.0,120.0,130.0,134.0,138.0,131.0,0.0,17.0,40.0,51.0,58.0,60.0,63.0,63.0,63.0,60.0,0.0,40.0,100.0,160.0,200.0,240.0,280.0,300.0,340.0,400.0,240.0,112.0,400.0,78.0,300.0,102.0,NULL,550.0,960.0,1.0,120.0,NULL,1.0,'Сумский насосный з-д',NULL,3636.0),
(72,'насос конденсатный турбинный д','КсД230-115/3',94.0,95.0,96.0,93.0,89.0,82.0,77.0,72.0,64.0,48.0,42.0,50.0,60.0,70.0,75.0,84.0,89.0,90.0,89.0,80.0,0.0,17.0,40.0,51.0,58.0,60.0,63.0,63.0,63.0,60.0,0.0,40.0,100.0,160.0,200.0,240.0,280.0,300.0,340.0,400.0,240.0,82.0,400.0,48.0,300.0,72.0,NULL,475.0,960.0,1.0,120.0,NULL,1.0,'Сумский насосный з-д',NULL,3636.0),
(73,'насос турбинный конденсатный','ПЭ65-42-2',465.0,475.0,480.0,485.0,475.0,470.0,462.0,435.0,420.0,400.0,63.0,70.0,78.0,90.0,101.0,103.0,105.0,119.0,123.0,125.0,0.0,25.0,40.0,50.0,58.0,61.0,64.0,68.0,69.0,69.0,0.0,15.0,25.0,35.0,45.0,50.0,55.0,65.0,75.0,80.0,50.0,470.0,80.0,400.0,65.0,435.0,NULL,234.0,2960.0,1.0,160.0,0.0,NULL,'Сумский насосный з-д',NULL,3636.0),
(74,'насос турбинный конденсатный','10НКУ-72',89.0,89.0,89.0,89.0,89.0,89.0,87.0,80.0,72.0,68.0,50.0,60.0,65.0,66.0,70.0,75.0,85.0,120.0,140.0,145.0,0.0,5.0,13.0,20.0,25.0,35.0,57.0,65.0,64.0,60.0,0.0,25.0,50.0,75.0,100.0,150.0,300.0,450.0,550.0,600.0,150.0,89.0,600.0,68.0,450.0,80.0,NULL,500.0,1470.0,1.0,260.0,3.0,20.0,'Южгидромаш',NULL,4692.0),
(75,'насос консольный с осевым подв','2КМ-20/30',34.0,35.0,35.0,34.0,33.0,33.0,31.0,28.0,24.0,14.0,1.0,2.0,2.0,2.0,2.0,3.0,3.0,3.0,3.0,3.0,0.0,30.0,43.0,46.0,57.0,60.0,65.0,66.0,65.0,52.0,0.0,5.0,8.0,10.0,15.0,17.0,20.0,25.0,30.0,40.0,17.0,33.0,40.0,14.0,25.0,28.0,NULL,162.0,2900.0,1.0,85.0,2.0,6.0,'Насосное производство "Армхиммаш',NULL,NULL),
(76,'насос консольный с осевым подв','1.5КМ-8/19',20.0,21.0,22.0,21.0,21.0,20.0,19.0,17.0,15.0,10.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,10.0,39.0,45.0,50.0,54.0,56.0,56.0,52.0,35.0,0.0,2.0,4.0,5.0,6.0,8.0,10.0,12.0,14.0,18.0,8.0,20.0,18.0,10.0,12.0,17.0,NULL,125.0,2900.0,1.0,85.0,2.0,6.0,'Насосное производство "Армхиммаш',NULL,NULL),
(77,'насос одноступенчатый двухстор','1200В-6.3/63',52.0,53.0,54.0,53.0,52.0,51.0,48.0,46.0,40.0,23.0,2750.0,3250.0,3750.0,4550.0,5250.0,5750.0,6500.0,6550.0,7250.0,7400.0,0.0,30.0,50.0,68.0,80.0,85.0,90.0,90.0,85.0,68.0,0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,10.0,5.0,51.0,7.0,46.0,10.0,23.0,NULL,1990.0,375.0,1.0,35.0,NULL,NULL,'Уралгидромаш',NULL,23400.0),
(78,'насос одноступенчатый двухстор','Д1250-125',129.0,132.0,133.0,138.0,135.0,133.0,130.0,125.0,108.0,79.0,200.0,250.0,320.0,380.0,440.0,480.0,500.0,570.0,640.0,28.0,0.0,24.0,40.0,52.0,64.0,70.0,74.0,78.0,72.0,50.0,0.0,200.0,400.0,600.0,800.0,880.0,1000.0,1250.0,1560.0,2000.0,880.0,133.0,2000.0,79.0,1250.0,125.0,NULL,625.0,1450.0,1.0,85.0,3.0,5.0,NULL,NULL,4452.0),
(79,'насос центробежный','KRHA-400/700/64 M-05',153.0,153.0,153.0,152.0,152.0,151.0,149.0,146.0,142.0,122.0,180.0,200.0,230.0,270.0,315.0,360.0,410.0,460.0,490.0,580.0,0.0,28.0,46.0,59.0,67.0,74.0,78.0,80.0,81.0,75.0,0.0,150.0,300.0,450.0,600.0,750.0,900.0,1050.0,1200.0,1500.0,1100.0,145.0,1400.0,141.0,1250.0,140.0,0.0,0.0,0.0,0.0,200.0,0.0,0.0,'VEB KOMBINAT PUMPEN UND VERDICHTER',0.0,0.0),
(80,'насос центробежный','Д1000-40',48.0,48.0,48.0,46.0,45.0,42.0,40.0,35.0,30.0,25.0,85.0,95.0,108.0,118.0,130.0,140.0,155.0,165.0,175.0,180.0,0.0,23.0,43.0,58.0,75.0,80.0,89.0,90.0,85.0,80.0,0.0,200.0,400.0,600.0,800.0,1000.0,1200.0,1400.0,1600.0,1700.0,900.0,44.0,1300.0,38.0,1000.0,40.0,0.0,540.0,0.0,0.0,0.0,0.0,0.0,NULL,0.0,0.0);


-- SELECT setval('"standardpumps_id_seq"', 80);

---------------------------------
-- pumps standardems - lookup Гидравлика
-- standardems - standardems
drop table if exists standardems;

create table standardems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Наим
    tip_el varchar(50) default (NULL),        -- Тип
    ispol varchar(50) default (NULL),         -- Исполнение
    produser varchar(50) default (NULL),      -- Изг
    f float default ((0)),                    -- ЧастотаВращ, об/мин
    n_el_nomin float default ((0)),           -- МощнНом, кВт
    u float default ((0)),                    -- НапряжНом, кВ
    k_el_nomin float default ((0)),           -- КПДном, %
    norma varchar(50) default (NULL),         -- ГОСТ
    uslovie varchar(50) default (NULL),       -- ТехнУсл
    massa float default ((0)),                -- Масса, кг
    cosFi float default ((0))                 -- СosУглаСдвига
);

INSERT INTO "standardems" ("id","name","tip_el","ispol","produser","f","n_el_nomin","u","k_el_nomin","norma","uslovie","massa","cosfi") VALUES
(1,'Электродвигатель асинхронный','4АЗМ-800/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,800.0,6000.0,96.0,NULL,'ТУ 16.528.326-86',2820.0,NULL),
(2,'Электродвигатель асинхронный','4АРМ-800/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,800.0,6000.0,96.0,NULL,'ТУ 16.528.326-86',2680.0,NULL),
(3,'Электродвигатель асинхронный','4АРМ-1000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,1000.0,6000.0,96.1,NULL,'ТУ 16.528.326-86',2890.0,NULL),
(4,'Электродвигатель асинхронный','4А3М-1000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,1000.0,6000.0,96.1,NULL,'ТУ 16.528.326-86',3030.0,NULL),
(5,'Электродвигатель асинхронный','4АЗМ-3150/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,3150.0,6000.0,97.1,NULL,'ТУ 16.528.339-87',7000.0,NULL),
(6,'Электродвигатель асинхронный','4АЗМ-2000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,2000.0,6000.0,96.7,NULL,'ТУ 16.528.339-87',5600.0,NULL),
(7,'Электродвигатель асинхронный','4АРМ-1600/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,1600.0,6000.0,96.6,NULL,'ТУ 16.528.339-87',4100.0,NULL),
(8,'Электродвигатель асинхронный','4АЗМ-1600/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,1600.0,6000.0,96.6,NULL,'ТУ 16.528.339-87',4270.0,NULL),
(9,'Электродвигатель асинхронный','4АРМ-1250/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,1250.0,6000.0,96.4,NULL,'ТУ 16.528.339-87',3970.0,NULL),
(10,'Электродвигатель асинхронный','4АЗМ-1250/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,1250.0,6000.0,96.4,NULL,'ТУ 16.528.339-87',3970.0,NULL),
(11,'Электродвигатель асинхронный','4АЗМ-4000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,4000.0,6000.0,97.3,NULL,'ТУ 16.528.339-87',9200.0,NULL),
(12,'Электродвигатель асинхронный','5АЗМ-8000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,8000.0,6000.0,97.6,NULL,'ТУ 16.528.326-86',14400.0,NULL),
(13,'Электродвигатель асинхронный','4АЗМ-5000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,5000.0,6000.0,97.3,NULL,'ТУ 16.528.326-86',10400.0,NULL),
(14,'Электродвигатель асинхронный','4АЗМ-500/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,500.0,6000.0,95.7,NULL,'ТУ 16.528.326-86',2660.0,0.88),
(15,'Электродвигатель','4АЗМ-500/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,500.0,6000.0,95.7,NULL,NULL,1930.0,NULL),
(16,'Электродвигатель','4АЗМ-500/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',NULL,500.0,6000.0,95.7,NULL,NULL,2660.0,NULL),
(17,'Электродвигатель асинхронный','4АРМ-500/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,500.0,6000.0,95.7,NULL,'ТУ 16.528.326-86',1800.0,NULL),
(18,'Электродвигатель асинхронный','4АРМ-630/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,630.0,6000.0,95.7,NULL,'ТУ 16.528.326-86',2520.0,NULL),
(19,'Электродвигатель','4АЗМ-630/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,630.0,6000.0,95.7,NULL,NULL,2660.0,NULL),
(20,'Электродвигатель','4АЗМ-630/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',NULL,630.0,6000.0,95.7,NULL,NULL,2660.0,NULL),
(21,'Электродвигатель асинхронный','4АЗМ-630/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,630.0,6000.0,95.8,NULL,'ТУ 16.528.326-86',2660.0,NULL),
(22,'Электродвигатель','4АЗМ-4000/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,4000.0,6000.0,97.3,NULL,NULL,9200.0,NULL),
(23,'Электродвигатель асинхронный','АДЗ-15-62-6У3','У','Харьковское ПО"ХЭМЗ"',1000.0,1000.0,10000.0,94.8,NULL,'ТУ 16.528.326-86',5400.0,NULL),
(24,'Электродвигатель асинхронный','АД-15-62-6УХЛ4','УХЛ','Харьковское ПО"ХЭМЗ"',1000.0,1000.0,10000.0,94.8,NULL,'ТУ 16.510.679-78',5400.0,0.85),
(25,'Электродвигатель асинхронный','ВАН 215/41-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,1600.0,6000.0,94.5,'01.03.06-81',NULL,16220.0,0.83),
(26,'Электродвигатель асинхронный','ВАН 173/56-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,1250.0,6000.0,94.2,'01.03.06-81',NULL,12905.0,0.83),
(27,'Электродвигатель асинхронный','ВАН 215/59-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,2500.0,6000.0,94.7,'01.03.06-81',NULL,20240.0,0.83),
(28,'Электродвигатель асинхронный','ВАН 173/46-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,1000.0,6000.0,93.8,'01.03.06-81',NULL,11750.0,0.77),
(29,'Электродвигатель асинхронный','ВАН 173/36-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,800.0,6000.0,93.5,'01.03.06-81',NULL,10700.0,0.76),
(30,'Электродвигатель асинхронный','ВАН 143/46-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,630.0,6000.0,92.9,'01.03.06-81',NULL,8590.0,0.72),
(31,'Электродвигатель асинхронный','ВАН 143/36-16У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',375.0,630.0,6000.0,92.9,'01.03.06-81',NULL,7280.0,0.72),
(32,'Электродвигатель асинхронный','ВАН 173/46-12У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',500.0,1600.0,6000.0,94.5,'01.03.06-81',NULL,12285.0,0.84),
(33,'Электродвигатель асинхронный','ВАН 143/51-12У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',500.0,1000.0,6000.0,94.0,'01.03.06-81',NULL,8900.0,0.81),
(34,'Электродвигатель асинхронный','ВАН 143/41-12У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',500.0,800.0,6000.0,93.7,'01.03.06-81',NULL,8200.0,0.8),
(35,'Электродвигатель асинхронный','ВАН 118/51-12У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',500.0,630.0,6000.0,93.0,'01.03.06-81',NULL,6650.0,0.74),
(36,'Электродвигатель асинхронный','ВАН 118/28-12У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',500.0,315.0,6000.0,91.5,'01.03.06-81',NULL,5250.0,0.73),
(37,'Электродвигатель асинхронный','ВАН 173/39-10У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',600.0,1600.0,6000.0,94.6,'01.03.06-81',NULL,11600.0,0.86),
(38,'Электродвигатель асинхронный','ВАН 143/51-10У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',600.0,1250.0,6000.0,94.4,'01.03.06-81',NULL,8900.0,0.83),
(39,'Электродвигатель асинхронный','ВАН 143/41-10У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',600.0,1000.0,6000.0,94.0,'01.03.06-81',NULL,8270.0,0.84),
(40,'Электродвигатель асинхронный','ВАН 118/51-10У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',600.0,800.0,6000.0,93.7,'01.03.06-81',NULL,6650.0,0.82),
(41,'Электродвигатель асинхронный','ВАН 118/23-10У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',600.0,315.0,6000.0,91.6,'01.03.06-81',NULL,5000.0,0.77),
(42,'Электродвигатель асинхронный','ВАН 118/51-8У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',750.0,1000.0,6000.0,94.3,'01.03.06-81',NULL,6700.0,0.86),
(43,'Электродвигатель асинхронный','ВАН 118/41-8У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',750.0,800.0,6000.0,93.8,'01.03.06-81',NULL,6200.0,0.84),
(44,'Электродвигатель асинхронный','ВАН 118/23-8У3','У','Свердловское ПО"УРАЛЭЛЕКТРОТЯЖМАШ"',750.0,400.0,6000.0,92.3,'01.03.06-81',NULL,5050.0,0.84),
(45,'Электродвигатель асинхронный','ДА 304-560Х-4У1','У1','Лысьвенский турбогенераторный з-д',1500.0,1250.0,6000.0,95.5,NULL,'ТУ 16.528.315-85',4840.0,0.87),
(46,'Электродвигатель асинхронный','ДА 304-560УК-4У1','У1','Лысьвенский турбогенераторный з-д',1500.0,1600.0,6000.0,95.8,NULL,'ТУ 16.528.315-85',5570.0,0.88),
(47,'Электродвигатель асинхронный','ДА 304-560У-4У1','У1','Лысьвенский турбогенераторный з-д',1500.0,2000.0,6000.0,96.0,NULL,'ТУ 16.528.315-85',6040.0,0.88),
(48,'Электродвигатель асинхронный','ДА 304-560Х-6У1','У1','Лысьвенский турбогенераторный з-д',1500.0,1000.0,6000.0,95.5,NULL,'ТУ 16.528.315-85',4930.0,0.85),
(49,'Электродвигатель асинхронный','ДА 304-560УК-6У1','У1','Лысьвенский турбогенераторный з-д',1000.0,1250.0,6000.0,95.8,NULL,'ТУ 16.528.315-85',5620.0,0.86),
(50,'Электродвигатель асинхронный','ДА 304-560У-6У1','У1','Лысьвенский турбогенераторный з-д',1000.0,1600.0,6000.0,96.0,NULL,'ТУ 16.528.315-85',6140.0,0.86),
(51,'Электродвигатель асинхронный','ДА 304-560Х-8У1','У1','Лысьвенский турбогенераторный з-д',750.0,630.0,6000.0,94.7,NULL,'ТУ 16.528.315-85',4640.0,0.79),
(52,'Электродвигатель асинхронный','ДА 304-560УК-8У1','У1','Лысьвенский турбогенераторный з-д',750.0,800.0,6000.0,95.0,NULL,'ТУ 16.528.315-85',5400.0,0.8),
(53,'Электродвигатель асинхронный','ДА 304-560У-8У1','У1','Лысьвенский турбогенераторный з-д',750.0,1000.0,6000.0,95.3,NULL,'ТУ 16.528.315-85',5800.0,0.8),
(54,'Электродвигатель асинхронный','ДА 304-560ХК-10У1','У1','Лысьвенский турбогенераторный з-д',600.0,400.0,6000.0,93.6,NULL,'ТУ 16.528.315-85',4200.0,0.78),
(55,'Электродвигатель асинхронный','ДА 304-560Х-10У1','У1','Лысьвенский турбогенераторный з-д',600.0,500.0,6000.0,94.1,NULL,'ТУ 16.528.315-85',4500.0,0.9),
(56,'Электродвигатель асинхронный','ДА 304-560УК-10У1','У1','Лысьвенский турбогенераторный з-д',600.0,630.0,6000.0,94.6,NULL,'ТУ 16.528.315-85',5260.0,0.79),
(57,'Электродвигатель асинхронный','ДА 304-560У-10У1','У1','Лысьвенский турбогенераторный з-д',600.0,800.0,6000.0,94.9,NULL,'ТУ 16.528.315-85',5620.0,0.8),
(58,'Электродвигатель асинхронный','ДА 304-560ХК-12У1','У1','Лысьвенский турбогенераторный з-д',500.0,315.0,6000.0,92.9,NULL,'ТУ 16.528.315-85',4200.0,0.74),
(59,'Электродвигатель асинхронный','ДА 304-560Х-12У1','У1','Лысьвенский турбогенераторный з-д',500.0,400.0,6000.0,93.4,NULL,'ТУ 16.528.315-85',4500.0,0.75),
(60,'Электродвигатель асинхронный','ДА 304-560УК-12У1','У1','Лысьвенский турбогенераторный з-д',500.0,500.0,6000.0,93.9,NULL,'ТУ 16.528.315-85',5250.0,0.75),
(61,'Электродвигатель асинхронный','ДА 304-560У-12У1','У1','Лысьвенский турбогенераторный з-д',500.0,630.0,6000.0,94.0,NULL,'ТУ 16.528.315-85',5600.0,NULL),
(62,'Электродвигатель асинхронный','4АЗМ-2500/6000 УХЛ4','УХЛ4','Новосибирский з-д"СИБЭЛЕКТРОТЯЖМАШ"',3000.0,2500.0,6000.0,96.7,NULL,'ТУ 16.528.285-84',6200.0,NULL),
(63,'Электродвигатель асинхронный','А 355Х-4','У3','ЗЭМ им. В. Коларова, г. София',1485.0,315.0,6000.0,93.8,NULL,NULL,1360.0,0.85),
(64,'Электродвигатель асинхронный','А4.400Х.4У3','У3','ЗЭМ им. В. Коларова, г. София',1500.0,500.0,6000.0,94.7,'183-74',NULL,2070.0,0.88),
(65,'Электродвигатель асинхронный','А4.400Х.4У1','У1','ЗЭМ им. В. Коларова, г. София',1500.0,500.0,6000.0,94.7,'183-74',NULL,2630.0,0.87),
(66,'Электродвигатель асинхронный','А113-4',NULL,'ЗЭМ им. В. Коларова, г. София',1480.0,250.0,6000.0,NULL,'180-70',NULL,1770.0,NULL),
(67,'Электродвигатель асинхронный','А113-4',NULL,'ЗЭМ им. В. Коларова, г. София',1480.0,250.0,6000.0,NULL,'180-55',NULL,1770.0,NULL),
(68,'Электродвигатель асинхронный','А112-4',NULL,'ЗЭМ им. В. Коларова, г. София',1480.0,250.0,6000.0,NULL,NULL,NULL,NULL,NULL),
(69,'Электродвигатель асинхронный','А3-315S2-4У3','У3',NULL,1470.0,150.0,380.0,94.3,NULL,NULL,753.0,NULL),
(70,'Электродвигатель асинхронный','АО2-81-4',NULL,'Катайский насосный з-д',1470.0,40.0,380.0,NULL,NULL,NULL,335.0,NULL),
(71,'Электродвигатель асинхронный','АЛП-104-4',NULL,'КАРУЭЗ',1485.0,250.0,380.0,NULL,NULL,NULL,NULL,NULL),
(72,'Электродвигатель асинхронный','М315 МК-4',NULL,'ЗЭМ им. В. Коларова, г. София',1480.0,250.0,380.0,94.5,NULL,NULL,1040.0,NULL),
(73,'Электродвигатель асинхронный','М280',NULL,NULL,1480.0,200.0,380.0,NULL,NULL,NULL,NULL,NULL),
(74,'Электродвигатель асинхронный','А4-400',NULL,NULL,1000.0,50.0,6000.0,NULL,NULL,NULL,NULL,NULL);


-- SELECT setval('"standardems_id_seq"', 74);

---------------------------------
-- pumps rotordiametertypes - lookup Гидравлика
-- rotordiametertypes - rotordiametertypes
drop table if exists rotordiametertypes;

create table rotordiametertypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "rotordiametertypes" ("id","name","code","ord") VALUES
(1,'номинальный','НАДО',1),
(2,'срезанный','НАДО',2);


-- SELECT setval('"rotordiametertypes_id_seq"', 2);

---------------------------------
-- pumps drivetypes - lookup Гидравлика
-- drivetypes - Типы приводов
drop table if exists drivetypes;

create table drivetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "drivetypes" ("id","name","code","ord") VALUES
(1,'нерегулируемый','Н',1),
(2,'частотно регулируемый','Ч',2);


-- SELECT setval('"drivetypes_id_seq"', 2);

---------------------------------
-- realconsumers throtstagesigns - lookup Гидравлика
-- throtstagesigns - throtstagesigns
drop table if exists throtstagesigns;

create table throtstagesigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "throtstagesigns" ("id","name","code","ord") VALUES
(1,'1.','1',1),
(2,'2.','2',2),
(3,'3.','3',3),
(4,'4.','4',4),
(5,'5.','5',5),
(6,'6.','6',6);


-- SELECT setval('"throtstagesigns_id_seq"', 6);

---------------------------------
-- realconsumers calcferdiametersigns - lookup Гидравлика
-- calcferdiametersigns - Признаки разрешения для записи
drop table if exists calcferdiametersigns;

create table calcferdiametersigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "calcferdiametersigns" ("id","name","code","ord") VALUES
(1,'разрешить','Р',1),
(2,'нельзя записывать','Н',2);


-- SELECT setval('"calcferdiametersigns_id_seq"', 2);

---------------------------------
-- realconsumers stopvalvetypes - lookup Гидравлика
-- stopvalvetypes - stopvalvetypes
drop table if exists stopvalvetypes;

create table stopvalvetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "stopvalvetypes" ("id","name","code","ord") VALUES
(1,'рабочий','НАДО',1),
(2,'нерабочий','НАДО',2);


-- SELECT setval('"stopvalvetypes_id_seq"', 2);

---------------------------------
-- realconsumers automdegs - lookup Гидравлика
-- automdegs - Автоматические градусы
drop table if exists automdegs;

create table automdegs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "automdegs" ("id","name","code","ord") VALUES
(1,'неавтоматизированный','Н',1),
(2,'автоматизированный','А',2),
(3,'трехходовой клапан','3',3);


-- SELECT setval('"automdegs_id_seq"', 3);

---------------------------------
-- realconsumers temperaturechartsigns - lookup Гидравлика
-- temperaturechartsigns - temperaturechartsigns
drop table if exists temperaturechartsigns;

create table temperaturechartsigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "temperaturechartsigns" ("id","name","code","ord") VALUES
(1,'отопительный','НАДО',1),
(2,'повышенный','НАДО',2);


-- SELECT setval('"temperaturechartsigns_id_seq"', 2);

---------------------------------
-- realconsumers buildingtypes - lookup Гидравлика
-- buildingtypes - Типы зданий
drop table if exists buildingtypes;

create table buildingtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "buildingtypes" ("id","name","code","ord") VALUES
(1,'Жилое','Ж',1),
(2,'Бюджетное','Б',2),
(3,'Промышленное','П',3);


-- SELECT setval('"buildingtypes_id_seq"', 3);

---------------------------------
-- dampers damperarmaturestates - lookup Гидравлика
-- damperarmaturestates - Состояния запорной арматуры
drop table if exists damperarmaturestates;

create table damperarmaturestates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "damperarmaturestates" ("id","name","code","ord") VALUES
(1,'открыта','НАДО',1),
(2,'закрыта','НАДО',2),
(4,'частично открыта','НАДО',4);


-- SELECT setval('"damperarmaturestates_id_seq"', 4);

---------------------------------
-- dampers standarddampers - lookup Гидравлика
-- standarddampers - ZC_Задвижки стандартные
drop table if exists standarddampers;

create table standarddampers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Наименование
    name_zc varchar(50) default (NULL),       -- Обозначение
    d float default ((0)),                    -- Диаметр условный, мм
    p float default ((0)),                    -- Давление условное максимальное, , м.вод.ст
    t float default ((0)),                    -- Температура теплоносителя максимальная, °С
    tris varchar(50) default (NULL),          -- Присоединение к трубопроводу
    kol_bolt int default (NULL),              -- Количество болтов на фланце, шт
    tip_privod varchar(50) default (NULL),    -- Вид и тип привода: ручной привод с маховиком, механический с червячной передачей, механический с конической передачей, электрический
    isp_privod varchar(50) default (NULL),    -- Исполнение электропривода: взрывозащищенное, тропическое
    end_privod varchar(50) default (NULL),    -- Максимальное усилие при закрытии при электрическом приводе
    napr_maxovik varchar(50) default (NULL),  -- Направление вращения маховика при ручном управлении
    obor_maxovik int default (NULL),          -- Количество оборотов маховика для полного закрытия задвижки при ручном управлении
    stok varchar(50) default (NULL),          -- Положение штока
    kolza int default (NULL),                 -- Наличие упорных колец: имеются, не имеются
    material varchar(50) default (NULL),      -- Материал корпуса
    macca float default ((0)),                -- Масса, кг
    producer varchar(50) default (NULL)       -- Изготовитель
);

INSERT INTO "standarddampers" ("id","name","name_zc","d","p","t","tris","kol_bolt","tip_privod","isp_privod","end_privod","napr_maxovik","obor_maxovik","stok","kolza","material","macca","producer") VALUES
(1,NULL,'30ч47бр',50.0,101.93,200.0,'Фланцевое',0,'ручной',NULL,NULL,NULL,0,NULL,0,'серый чугун',NULL,NULL),
(2,NULL,'30ч47бр',80.0,101.93,200.0,'Фланцевое',0,'ручной',NULL,NULL,NULL,0,NULL,0,'серый чугун',NULL,NULL),
(3,NULL,'30ч47бр',100.0,101.93,200.0,'Фланцевое',0,'ручной',NULL,NULL,NULL,0,NULL,0,'серый чугун',NULL,NULL),
(4,NULL,'30ч47бр',125.0,101.93,200.0,'Фланцевое',0,'ручной',NULL,NULL,NULL,0,NULL,0,'серый чугун',NULL,NULL),
(5,NULL,'30ч47бр',150.0,101.93,200.0,'Фланцевое',0,'ручной',NULL,NULL,NULL,0,NULL,0,'серый чугун',NULL,NULL),
(6,NULL,'30ч47бр',200.0,101.93,200.0,'Фланцевое',0,'ручной',NULL,NULL,NULL,0,NULL,0,'серый чугун',NULL,NULL);


-- SELECT setval('"standarddampers_id_seq"', 6);

---------------------------------
-- heatsystem seasons - lookup Гидравлика
-- seasons - seasons
drop table if exists seasons;

create table seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "seasons" ("id","name","code","ord") VALUES
(1,'отопительный','О',1),
(2,'летний','Л',2);


-- SELECT setval('"seasons_id_seq"', 2);

---------------------------------
-- heatsystem capacity_types - lookup Гидравлика
-- capacity_types - Типы мощностей
drop table if exists capacity_types;

create table capacity_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "capacity_types" ("id","name","code","ord") VALUES
(1,'средняя','С',1),
(2,'максимальная','М',2);


-- SELECT setval('"capacity_types_id_seq"', 2);

---------------------------------
-- heatsystem yesorno - lookup Гидравлика
-- yesorno - yesorno
drop table if exists yesorno;

create table yesorno (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "yesorno" ("id","name","code","ord") VALUES
(0,'нет','0',2),
(1,'да','1',1);


-- SELECT setval('"yesorno_id_seq"', 1);
--- Гидравлика lookup: 64
--===========================--
--        Факторы риска             --
--===========================--
---------------------------------
-- pipesections - Факторы риска
-- pipesections - Участок ПТС
drop table if exists pipesections;

create table pipesections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- Наименование
    nodeID1 int default (NULL),
    nodeID2 int default (NULL),
    magistral int default (NULL),             -- Магистраль
    magistralSite int default (NULL),         -- Участок МС
    distSite int default (NULL),              -- Участок РС
    tubingTypeID int default (NULL),          -- Тип прокладки
    firstPICdateHP date default (NULL),       -- Дата первичного ввода в эксплуатацию
    lastTransDate date default (NULL),        -- Дата последней перекладки
    lastIsolDate date default (NULL),         -- Дата последней замены изоляционной конструкции
    DiamUslov int default ((0)),              -- Диаметр условный трубопровод, мм
    pipeLength float default ((0)),           -- Протяженность, м
    standart varchar(50) default (NULL),      -- Стандарт на изготовление трубопровода
    inventNumber varchar(50) default (NULL),  -- Инвентарный номер
    tubeTypeID int default ((1)),             -- Материал трубы
    objectTypeID int default ((1)),           -- Назначение трубопровода
    Sreda int default ((1)),                  -- Рабочая среда
    press float default ((0)),                -- Рабочее давление, м.вод.ст
    temperature float default ((0)),          -- Рабочая температура, Град.C
    SpokSluzhbiRash int default ((25)),       -- Расчетный срок службы, лет
    ressurs int default (NULL),               -- Расчетный ресурс,час
    pusk int default (NULL),                  -- Расчетное число пусков, раз
    organizationID int default (NULL),        -- Балансовая принадлежность участка
    Elektrich int default ((1)),              -- Наличие эл.коммуникаций, электрохимзащиты газопровода
    TransportElekricht int default ((1)),     -- Наличие электрифицированного транспорта на расстоянии
    Ponezial int default (NULL),              -- Уровень разности электропотенциала, В
    floodIntensityGWid int default ((1)),     -- Интенсивность подтопления грунтовыми водами
    floodIntensityFWid int default ((1)),     -- Интенсивность подтопления паводковыми водами
    floodIntensityTWid int default ((1)),     -- Интенсивность подтопления водопроводными водами
    floodIntensityBWid int default ((1)),     -- Интенсивность подтопления фекальными водами
    Vodootved int default ((1)),              -- Водоотведение на участке
    SlozhOkluzh int default (NULL),           -- Сложность отключения участка для устранения повреждения
    OtkluzhGkal int default (NULL),           -- Объем отключаемых потребителей, при повреждении, Гкал/ч
    AvariiVipoln int default (NULL),          -- Сложность выполнения аварийно-восстановительных работ
    Pesehod int default (NULL),               -- Прокладка трубопроводов под пешеходными зонами
    ZhdDorogi int default (NULL),             -- Прокладка трубопроводов под авто и ж/д дорогами
    LudiProklad int default (NULL),           -- Прокладка трубопровода в местах массового скопления жителей города
    UzherbLudi int default (NULL),            -- Нанесение ущерба населению от подтопления при возможном повреждении трубопроводов
    UzherbSity int default (NULL),            -- Нанесение ущерба инфраструктуре города при возможном повреждении трубопроводов
    VnesniiVid int default ((1)),             -- Внешний вид
    SostOborudovania int default ((2)),       -- Состояние оборудования
    VnesnKorrozia int default ((1)),          -- Степень внешней коррозии
    VnunrenKorrozia int default ((1)),        -- Степень внутренней коррозии
    SostKonstrukz int default ((1)),          -- Состояние строительных конструкций
    Kategorii int default ((1)),              -- Категории нарушений
    nalichie_vblizi_kommunikacijID int,       -- Наличие вблизи коммуникаций
    harakter_gruntaID int,                    -- Грунт в месте прокладки
    poverhnost_nad_trassojID int,             -- Поверхность над трассой
    podtoplenie_do_truby int,                 -- Подтопление до трубы
    zanos_kanala_gruntomID int,               -- Занос канала грунтом
    stroitelnye_konstrukcii_kanalaID int,     -- Строительные конструкции канала
    sostoyanie_stroitelnyh_konstrukcij_kanalaID int,  -- Состояние строительных конструкций канала
    vnutrennee_sostoyanie_kanalaID int,       -- Внутреннее состояние канала
    konstrukciya_drenazhnogo_ustrojstvaID int,    -- Конструкция дренажного устройства
    sostoyanie_teplovoj_izolyacii_podachaID int,  -- Состояние тепловой изоляции (подача)
    sostoyanie_teplovoj_izolyacii_obratkaID int,  -- Состояние тепловой изоляции (обратка)
    sostoyanie_naruzhnogo_pokrytiya_podachaID int,    -- Состояние наружного покрытия (подача)
    sostoyanie_naruzhnogo_pokrytiya_obratkaID int,    -- Состояние наружного покрытия (обратка)
    sostoyanie_protivokorrozionnogo_pokrytiya_podachaID int,  -- Состоянние противокоррозионного покрытия (подача)
    sostoyanie_protivokorrozionnogo_pokrytiya_obratkaID int,  -- Состоянние противокоррозионного покрытия (обратка)
    nalichie_korrozii_podachaID int,          -- Наличие коррозии (подача)
    nalichie_korrozii_obratkaID int,          -- Наличие коррозии (обратка)
    zashemID int,                             -- Защемления трубопроводов
    sost_podvID int,                          -- Состояние подвесок
    sost_oporID int,                          -- Состояние опор
    nalich_obrKlID int,                       -- Наличие обратных клапанов
    sootv_nadpID int,                         -- Соответствие надписей на арматуре
    nalich_tabl_regID int,                    -- Наличие табличек с регистрационными номерами
    nalich_tabl_parID int,                    -- Наличие таблички с разрешенными параметрами работы
    int_korID int,                            -- Интенсивности процесса внутренней коррозии
    sostoyanie_metalla_truboprovodaID int,    -- Состояние металла трубопровода
    tol1 float,                               -- Первоначальная толщина металла труб
    tol2 float,                               -- Фактическая толщина стенки трубопровода
    glubina_kor float,                        -- Глубина коррозионных повреждений, мм
    razmery_kor float,                        -- Размеры зон коррозионных повреждений, мм
    document_analiz_vlazhnost varchar(255),   -- Анализ проб на влажность
    document_analiz_korrozia varchar(255),    -- Анализ проб на коррозийную активность
    document_potenzial varchar(255),          -- Разность электрических потенциалов «труба-земля»
    document_analiz_vytyazhka varchar(255),   -- Анализ водяной вытяжки
    dokument_analiz_prob_na_vlazhnost varchar(255),   -- Анализ проб на влажность
    dokument_analiz_prob_na_korrozijnuyu_aktivnost varchar(255),  -- Анализ проб на коррозионную активность
    dokument_raznost_elektricheskih_potencialov varchar(255), -- Разность электрических потенциалов
    dokument_analiz_vodyanoj_vytyazhki varchar(255),  -- Анализ водной вытяжки
    dokument_chertezh_objekta_kontrolya varchar(255), -- Чертеж объекта контроля
    diameterCondit float,                     -- Диаметр условный заменённых труб, мм
    diameterExternal float,                   -- Диаметр внешний заменённых труб, мм
    diameterInternal float,                   -- Диаметр внутренний заменённых труб, мм
    wallThickness float,                      -- Толщина стенки, мм
    pipeSectLength float,
    isolMaterialID int,                       -- Материал изоляции
    isolationTypeID int,                      -- Тип изоляции ППУ
    isolThickness float,                      -- Толщина изоляции, мм
    externMaterialID int,                     -- Материал наружного покрытия
    externCoverThick float,                   -- Толщина наружного покрытия, мм
    anticorrMaterialID int,                   -- Материал антикоррозийного покрытия
    len_tube float,                           -- Длина заменённой трубы, м
    len_izol float,                           -- Восстановление тепловой изоляции поверхности труб, м^2
    asfaltirovanie float,                     -- Асфальтирование, ремонт, м^2
    len_channel float,                        -- Длина замененного канала, м
    zamena_kanala_procent float,              -- Замена канала,%
    zamena_kompensatorov int,                 -- Замена компенсаторов
    rekonstrukciya_kamery_nachalnogo_uzla int,    -- Реконструкция камеры начального узда
    rekonstrukciya_kamery_konechnogo_uzla int,    -- Реконструкция камеры конечного узда
    ustanovka_i_zamena_zadvizhek int,         -- Установка и замена задвижек
    id_old int default ((0)) 
);
CREATE INDEX pipesections_nodeid1_idx ON pipesections (nodeid1);
CREATE INDEX pipesections_nodeid2_idx ON pipesections (nodeid2);
--- Факторы риска: 1
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- pipesections faktriska_4_elekt - lookup Факторы риска
-- faktriska_4_elekt - faktriska_4_elekt
drop table if exists faktriska_4_elekt;

create table faktriska_4_elekt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_4_elekt" ("id","name","ves","value","valueiznos","help") VALUES
(1,'более 10 м от трубопровода',1,0.05,0.05,'Наличие эл.коммуникаций, электрохимзащиты газопровода'),
(2,'10-5 м от трубопровода',2,0.05,0.05,'Наличие эл.коммуникаций, электрохимзащиты газопровода'),
(3,'5-3 м от трубопровода',3,0.05,0.05,'Наличие эл.коммуникаций, электрохимзащиты газопровода'),
(4,'3-1 м от трубопровода',4,0.05,0.05,'Наличие эл.коммуникаций, электрохимзащиты газопровода'),
(5,'менее 1 м от трубопровода',5,0.05,0.05,'Наличие эл.коммуникаций, электрохимзащиты газопровода');


-- SELECT setval('"faktriska_4_elekt_id_seq"', 5);

---------------------------------
-- pipesections faktiznos_2_kat_narush - lookup Факторы риска
-- faktiznos_2_kat_narush - Факторы износа (категория нарушений)
drop table if exists faktiznos_2_kat_narush;

create table faktiznos_2_kat_narush (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktiznos_2_kat_narush" ("id","name","ves","value","valueiznos","help") VALUES
(1,'Незначительные сбои',1,0.1,0.1,'Категория нарушений'),
(2,'Не вызывало аварийных ситуаций',2,0.1,0.1,'Категория нарушений'),
(4,'Вызывало нарушения работы сети',4,0.1,0.1,'Категория нарушений'),
(5,'Оборудование физически нельзя включить в работу',5,0.1,0.1,'Категория нарушений');


-- SELECT setval('"faktiznos_2_kat_narush_id_seq"', 5);

---------------------------------
-- pipesections faktriska_17_skoplenie_zhit - lookup Факторы риска
-- faktriska_17_skoplenie_zhit - Факторы риска скопления жителей
drop table if exists faktriska_17_skoplenie_zhit;

create table faktriska_17_skoplenie_zhit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_17_skoplenie_zhit" ("id","name","ves","value","valueiznos","help") VALUES
(1,'места отдыха, учреждения культуры и спорта',1,0.05,0.05,'Прокладка трубопровода в местах массового скопления жителей города'),
(2,'остановки общественного транспорта, рынки',4,0.05,0.05,'Прокладка трубопровода в местах массового скопления жителей города'),
(3,'территории дошкольных, учебных заведений, больниц, храмов',5,0.05,0.05,'Прокладка трубопровода в местах массового скопления жителей города');


-- SELECT setval('"faktriska_17_skoplenie_zhit_id_seq"', 3);

---------------------------------
-- pipesections objecttypes2 - lookup Факторы риска
-- objecttypes2 - objecttypes2
drop table if exists objecttypes2;

create table objecttypes2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "objecttypes2" ("id","name","code","ord") VALUES
(1,'Магистраль','М',1),
(2,'Распредсеть','Р',2);


-- SELECT setval('"objecttypes2_id_seq"', 2);

---------------------------------
-- pipesections faktriska_13_otkl_potrebiteli - lookup Факторы риска
-- faktriska_13_otkl_potrebiteli - Факторы риска отключения потребителей
drop table if exists faktriska_13_otkl_potrebiteli;

create table faktriska_13_otkl_potrebiteli (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_13_otkl_potrebiteli" ("id","name","ves","value","valueiznos","help") VALUES
(1,'концевой участок (менее 15Гкал)',1,0.04,0.04,'Объем отключения потребителей, при возможном повреждении'),
(2,'ответвление (от15 до 50 Гкал)',3,0.04,0.04,'Объем отключения потребителей, при возможном повреждении'),
(3,'луч (свыше 50Гкал)',5,0.04,0.04,'Объем отключения потребителей, при возможном повреждении');


-- SELECT setval('"faktriska_13_otkl_potrebiteli_id_seq"', 3);

---------------------------------
-- pipesections faktriska_15_peshehod - lookup Факторы риска
-- faktriska_15_peshehod - Факторы риска пешеходов
drop table if exists faktriska_15_peshehod;

create table faktriska_15_peshehod (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_15_peshehod" ("id","name","ves","value","valueiznos","help") VALUES
(1,'с движением малой интенсивности (до 50 чел/час)',1,0.05,0.05,'Прокладка  трубопроводов под пешеходными зонами'),
(2,'с движением средней интенсивности (50-200чел/час)',3,0.05,0.05,'Прокладка  трубопроводов под пешеходными зонами'),
(3,'с интенсивным движением пешеходов (свыше 200 чел/час)',5,0.05,0.05,'Прокладка  трубопроводов под пешеходными зонами');


-- SELECT setval('"faktriska_15_peshehod_id_seq"', 3);

---------------------------------
-- pipesections faktriska_6_potencial - lookup Факторы риска
-- faktriska_6_potencial - faktriska_6_potencial
drop table if exists faktriska_6_potencial;

create table faktriska_6_potencial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_6_potencial" ("id","name","ves","value","valueiznos","help") VALUES
(1,'низкий (0,0 В)',1,0.04,0.04,'Уровень разности электропотенциала, В'),
(2,'значительный (0,04 В и менее)',3,0.04,0.04,'Уровень разности электропотенциала, В'),
(3,'опасный (более 0,04 В)',5,0.04,0.04,'Уровень разности электропотенциала, В');


-- SELECT setval('"faktriska_6_potencial_id_seq"', 3);

---------------------------------
-- pipesections faktriska_12_slozhnost_otkl - lookup Факторы риска
-- faktriska_12_slozhnost_otkl - Факторы риска сложности отключений
drop table if exists faktriska_12_slozhnost_otkl;

create table faktriska_12_slozhnost_otkl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_12_slozhnost_otkl" ("id","name","ves","value","valueiznos","help") VALUES
(1,'низкая (тупиковый  участок)',1,0.05,0.05,'Сложность отключения участка для устранения повреждения '),
(2,'средняя (промежуточный участок)',3,0.05,0.05,'Сложность отключения участка для устранения повреждения '),
(3,'высокая (головной участок)',5,0.05,0.05,'Сложность отключения участка для устранения повреждения ');


-- SELECT setval('"faktriska_12_slozhnost_otkl_id_seq"', 3);

---------------------------------
-- pipesections faktiznos_3_sost_obor - lookup Факторы риска
-- faktiznos_3_sost_obor - Факторы износа (состояние оборудования)
drop table if exists faktiznos_3_sost_obor;

create table faktiznos_3_sost_obor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktiznos_3_sost_obor" ("id","name","ves","value","valueiznos","help") VALUES
(1,'новая, почти новая',1,0.05,0.2,'Состояние оборудования'),
(2,'в работе в неаварийном состоянии',2,0.05,0.2,'Состояние оборудования'),
(3,'в работе в предаварийном состоянии',3,0.05,0.2,'Состояние оборудования'),
(4,'в работе в аварийном состоянии',4,0.05,0.2,'Состояние оборудования'),
(5,'не работает',5,0.05,0.2,'Состояние оборудования');


-- SELECT setval('"faktiznos_3_sost_obor_id_seq"', 5);

---------------------------------
-- pipesections coolanttypes - lookup Факторы риска
-- coolanttypes - Типы охлаждающих жидкостей
drop table if exists coolanttypes;

create table coolanttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "coolanttypes" ("id","name","code","ord") VALUES
(1,'Вода','В',1),
(2,'Пар','П',2);


-- SELECT setval('"coolanttypes_id_seq"', 2);

---------------------------------
-- pipesections faktriska_5_transport - lookup Факторы риска
-- faktriska_5_transport - faktriska_5_transport
drop table if exists faktriska_5_transport;

create table faktriska_5_transport (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_5_transport" ("id","name","ves","value","valueiznos","help") VALUES
(1,'более 10 м от трубопровода',1,0.05,0.05,'Наличие электрифицированного транспорта на расстоянии'),
(2,'10-5 м от трубопровода',2,0.05,0.05,'Наличие электрифицированного транспорта на расстоянии'),
(3,'5-3 м от трубопровода',3,0.05,0.05,'Наличие электрифицированного транспорта на расстоянии'),
(4,'3-1 м от трубопровода',4,0.05,0.05,'Наличие электрифицированного транспорта на расстоянии'),
(5,'менее 1 м от трубопровода',5,0.05,0.05,'Наличие электрифицированного транспорта на расстоянии');


-- SELECT setval('"faktriska_5_transport_id_seq"', 5);

---------------------------------
-- pipesections faktiznos_1_vneshnii_vid - lookup Факторы риска
-- faktiznos_1_vneshnii_vid - Факторы износа (внешний вид)
drop table if exists faktiznos_1_vneshnii_vid;

create table faktiznos_1_vneshnii_vid (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktiznos_1_vneshnii_vid" ("id","name","ves","value","valueiznos","help") VALUES
(1,'Отсутствие поверхностных повреждений',1,0.05,0.05,'Внешний вид'),
(2,'Наличие поверхностных повреждений',5,0.05,0.05,'Внешний вид');


-- SELECT setval('"faktiznos_1_vneshnii_vid_id_seq"', 2);

---------------------------------
-- pipesections faktriska_7_vneshkorroz - lookup Факторы риска
-- faktriska_7_vneshkorroz - faktriska_7_vneshkorroz
drop table if exists faktriska_7_vneshkorroz;

create table faktriska_7_vneshkorroz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_7_vneshkorroz" ("id","name","ves","value","valueiznos","help") VALUES
(1,'слабая, утонение до 10%',1,0.04,0.1,'Степень внешней коррозии (утонение металла трубы)'),
(2,'средняя, утонение от 10% до 30 %',3,0.04,0.1,'Степень внешней коррозии (утонение металла трубы)'),
(3,'сильная, утонение более 30%',5,0.04,0.1,'Степень внешней коррозии (утонение металла трубы)');


-- SELECT setval('"faktriska_7_vneshkorroz_id_seq"', 3);

---------------------------------
-- pipesections faktriska_8_vnutkorroz - lookup Факторы риска
-- faktriska_8_vnutkorroz - faktriska_8_vnutkorroz
drop table if exists faktriska_8_vnutkorroz;

create table faktriska_8_vnutkorroz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);

INSERT INTO "faktriska_8_vnutkorroz" ("id","name","ves","value","valueiznos","help") VALUES
(1,'допустимая',1,0.02,0.1,'Степень внутренней коррозии'),
(2,'высокая',3,0.02,0.1,'Степень внутренней коррозии'),
(3,'аварийная',5,0.02,0.1,'Степень внутренней коррозии');


-- SELECT setval('"faktriska_8_vnutkorroz_id_seq"', 3);

---------------------------------
-- pipesections harakter_grunta_shurf - lookup Факторы риска
-- harakter_grunta_shurf - harakter_grunta_shurf
drop table if exists harakter_grunta_shurf;

create table harakter_grunta_shurf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "harakter_grunta_shurf" ("id","name","ord") VALUES
(1,'супесь',1),
(2,'песок',2),
(3,'суглинок',3),
(4,'глина',4),
(5,'строительный мусор',5);


-- SELECT setval('"harakter_grunta_shurf_id_seq"', 5);

---------------------------------
-- pipesections poverhnost_nad_trassoj - lookup Факторы риска
-- poverhnost_nad_trassoj - poverhnost_nad_trassoj
drop table if exists poverhnost_nad_trassoj;

create table poverhnost_nad_trassoj (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "poverhnost_nad_trassoj" ("id","name","ord") VALUES
(1,'асфальт, бетон',1),
(2,'газон',2),
(3,'граница между 1 и 2',3),
(4,'утрамбованный грунт',4),
(5,'поверхность, защищенная от атмосферных осадков',5);


-- SELECT setval('"poverhnost_nad_trassoj_id_seq"', 5);

---------------------------------
-- pipesections nalichie_vblizi_kommunikacij - lookup Факторы риска
-- nalichie_vblizi_kommunikacij - nalichie_vblizi_kommunikacij
drop table if exists nalichie_vblizi_kommunikacij;

create table nalichie_vblizi_kommunikacij (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "nalichie_vblizi_kommunikacij" ("id","name","ord") VALUES
(1,'кабель',1),
(2,'газопровод',2),
(3,'водопровод',3),
(4,'канализация',4),
(5,'нет информации',5);


-- SELECT setval('"nalichie_vblizi_kommunikacij_id_seq"', 5);

---------------------------------
-- pipesections zanos_kanala_gruntom - lookup Факторы риска
-- zanos_kanala_gruntom - zanos_kanala_gruntom
drop table if exists zanos_kanala_gruntom;

create table zanos_kanala_gruntom (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "zanos_kanala_gruntom" ("id","name","ord") VALUES
(1,'нет',1),
(2,'частично',2),
(3,'до трубы',3);


-- SELECT setval('"zanos_kanala_gruntom_id_seq"', 3);

---------------------------------
-- pipesections stroitelnye_konstrukcii_kanala - lookup Факторы риска
-- stroitelnye_konstrukcii_kanala - stroitelnye_konstrukcii_kanala
drop table if exists stroitelnye_konstrukcii_kanala;

create table stroitelnye_konstrukcii_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "stroitelnye_konstrukcii_kanala" ("id","name","ord") VALUES
(4,'Бетонные плитки',1);


-- SELECT setval('"stroitelnye_konstrukcii_kanala_id_seq"', 4);

---------------------------------
-- pipesections sostoyanie_stroitelnyh_konstrukcij_kanala - lookup Факторы риска
-- sostoyanie_stroitelnyh_konstrukcij_kanala - Состояние строительных конструкций канала
drop table if exists sostoyanie_stroitelnyh_konstrukcij_kanala;

create table sostoyanie_stroitelnyh_konstrukcij_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "sostoyanie_stroitelnyh_konstrukcij_kanala" ("id","name","ord") VALUES
(1,'в хорошем состоянии',1),
(2,'удовлетворительное',2),
(3,'разрушены',3);


-- SELECT setval('"sostoyanie_stroitelnyh_konstrukcij_kanala_id_seq"', 3);

---------------------------------
-- pipesections vnutrennee_sostoyanie_kanala - lookup Факторы риска
-- vnutrennee_sostoyanie_kanala - vnutrennee_sostoyanie_kanala
drop table if exists vnutrennee_sostoyanie_kanala;

create table vnutrennee_sostoyanie_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "vnutrennee_sostoyanie_kanala" ("id","name","ord") VALUES
(1,'сухое',1),
(2,'удовлетворительное',2);


-- SELECT setval('"vnutrennee_sostoyanie_kanala_id_seq"', 2);

---------------------------------
-- pipesections konstrukciya_drenazhnogo_ustrojstva - lookup Факторы риска
-- konstrukciya_drenazhnogo_ustrojstva - konstrukciya_drenazhnogo_ustrojstva
drop table if exists konstrukciya_drenazhnogo_ustrojstva;

create table konstrukciya_drenazhnogo_ustrojstva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "konstrukciya_drenazhnogo_ustrojstva" ("id","name","ord") VALUES
(1,'Трубопровод',1);


-- SELECT setval('"konstrukciya_drenazhnogo_ustrojstva_id_seq"', 1);

---------------------------------
-- pipesections sostoyanie_teplovoj_izolyacii - lookup Факторы риска
-- sostoyanie_teplovoj_izolyacii - Состояние тепловой изоляции
drop table if exists sostoyanie_teplovoj_izolyacii;

create table sostoyanie_teplovoj_izolyacii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "sostoyanie_teplovoj_izolyacii" ("id","name","ord") VALUES
(1,'в хорошем состоянии',1),
(2,'разрушена частично',2),
(3,'разрушена полностью ',3);


-- SELECT setval('"sostoyanie_teplovoj_izolyacii_id_seq"', 3);

---------------------------------
-- pipesections sostoyanie_naruzhnogo_pokrytiya - lookup Факторы риска
-- sostoyanie_naruzhnogo_pokrytiya - sostoyanie_naruzhnogo_pokrytiya
drop table if exists sostoyanie_naruzhnogo_pokrytiya;

create table sostoyanie_naruzhnogo_pokrytiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "sostoyanie_naruzhnogo_pokrytiya" ("id","name","ord") VALUES
(1,'в хорошем состоянии',1),
(2,'отсутствует частично',2),
(3,'отсутствует полностью ',3);


-- SELECT setval('"sostoyanie_naruzhnogo_pokrytiya_id_seq"', 3);

---------------------------------
-- pipesections sostoyanie_protivokorrozionnogo_pokrytiya - lookup Факторы риска
-- sostoyanie_protivokorrozionnogo_pokrytiya - Состояние противокоррозионного покрытия
drop table if exists sostoyanie_protivokorrozionnogo_pokrytiya;

create table sostoyanie_protivokorrozionnogo_pokrytiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "sostoyanie_protivokorrozionnogo_pokrytiya" ("id","znachenie","primechanie") VALUES
(1,'в хорошем состоянии',NULL),
(2,'отсутствует частично',NULL),
(3,'отсутствует полностью',NULL);


-- SELECT setval('"sostoyanie_protivokorrozionnogo_pokrytiya_id_seq"', 3);

---------------------------------
-- pipesections nalichie_korrozii_shurf - lookup Факторы риска
-- nalichie_korrozii_shurf - nalichie_korrozii_shurf
drop table if exists nalichie_korrozii_shurf;

create table nalichie_korrozii_shurf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "nalichie_korrozii_shurf" ("id","name","ord") VALUES
(1,'Следов коррозии нет',1),
(2,'Сплошная наружная коррозия на всем осмотренном участке',2),
(3,'Сплошная наружная коррозия в месте повреждения',3),
(4,'Локальная наружная коррозия (язвы)',4),
(5,'Внутренняя коррозия, отдельные язвы',5),
(6,'Внутренняя коррозия в виде цепочек язв или канавок',6),
(7,'Сплошная внутренняя коррозия',7),
(8,'Максимальная глубина повреждения',8);


-- SELECT setval('"nalichie_korrozii_shurf_id_seq"', 8);

---------------------------------
-- pipesections pr_ots_lookup - lookup Факторы риска
-- pr_ots_lookup - Виды защемлений
drop table if exists pr_ots_lookup;

create table pr_ots_lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "pr_ots_lookup" ("id","name","code","ord") VALUES
(1,'Присутствуют',NULL,1),
(2,'Отсутствуют',NULL,2);


-- SELECT setval('"pr_ots_lookup_id_seq"', 2);

---------------------------------
-- pipesections sost_lookup - lookup Факторы риска
-- sost_lookup - sost_lookup
drop table if exists sost_lookup;

create table sost_lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "sost_lookup" ("id","name","code","ord") VALUES
(1,'Хорошее',NULL,1),
(2,'Удовлетворительное',NULL,2),
(3,'Не удовлетворительное',NULL,3),
(4,'Аварийное',NULL,4);


-- SELECT setval('"sost_lookup_id_seq"', 4);

---------------------------------
-- pipesections sootv_lookup - lookup Факторы риска
-- sootv_lookup - sootv_lookup
drop table if exists sootv_lookup;

create table sootv_lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "sootv_lookup" ("id","name","code","ord") VALUES
(1,'Соответствует',NULL,1),
(2,'Не соответствует',NULL,2);


-- SELECT setval('"sootv_lookup_id_seq"', 2);

---------------------------------
-- pipesections int_kor - lookup Факторы риска
-- int_kor - int_kor
drop table if exists int_kor;

create table int_kor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "int_kor" ("id","name","code","ord") VALUES
(1,'слабая',NULL,1),
(2,'средняя',NULL,2),
(3,'сильная',NULL,3),
(4,'аварийная',NULL,4);


-- SELECT setval('"int_kor_id_seq"', 4);

---------------------------------
-- pipesections sostoyanie_metalla_truboprovoda - lookup Факторы риска
-- sostoyanie_metalla_truboprovoda - sostoyanie_metalla_truboprovoda
drop table if exists sostoyanie_metalla_truboprovoda;

create table sostoyanie_metalla_truboprovoda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) not null,
    ord int 
);

INSERT INTO "sostoyanie_metalla_truboprovoda" ("id","name","ord") VALUES
(1,'механические повреждения основного металла и наплавленного металла сварных соединений',1),
(2,'трещины и других поверхностные дефекты',2),
(3,'коррозионные повреждения поверхности металла трубопроводов и сварных соединений',3),
(4,'деформированных участков трубопровода (коробление, провисание и другие отклонения от первоначальной формы)',4);


-- SELECT setval('"sostoyanie_metalla_truboprovoda_id_seq"', 4);

---------------------------------
-- pipesections obj_type_faktory_riska - lookup Факторы риска
-- obj_type_faktory_riska - obj_type_faktory_riska
drop table if exists obj_type_faktory_riska;

create table obj_type_faktory_riska (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name varchar(100) not null,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "obj_type_faktory_riska" ("id","table_name","name","ord") VALUES
(1,'shurfy','Шурфовка',1),
(2,'osmotr','Осмотр',2),
(3,'remont2','Ремонт',3);


-- SELECT setval('"obj_type_faktory_riska_id_seq"', 3);
--- Факторы риска lookup: 32
--===========================--
--        Выходные данные             --
--===========================--
---------------------------------
-- calculation - Выходные данные
-- calculation - Расчет
drop table if exists calculation;

create  table calculation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fileID int,
    Tn float,
    date1 timestamp,
    name varchar,
    user_gid varchar(255),
    calc_params varchar,
    calc_plan int 
);
CREATE INDEX calculation_fileid_idx ON calculation (fileid);
---------------------------------
-- any_out - Выходные данные
-- any_out - Остальные линейные объекты (результат расчета)
drop table if exists any_out;

create  table any_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    ras float,                                -- Расход, т/ч
    ist int                                   -- Источник
);
CREATE INDEX any_out_lineid_idx ON any_out (lineid);
CREATE INDEX any_out_calculationid_idx ON any_out (calculationid);

---------------------------------
-- bp_out - Выходные данные
-- bp_out - Байпаc (результат расчета)
drop table if exists bp_out;

create  table bp_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(10),                          -- Состояние
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    a4 float,                                 -- Геод.отметка верха трубы узла на входе, м
    a5 float,                                 -- Пьез.напор на входе байпаса
    a9 float,                                 -- Геод.отметка верха трубы узла на выходе, м
    a10 float,                                -- Пьез. напор на выходе байпаса, м.вод.ст
    a11 float,                                -- Диаметр диафрагмы, мм
    a12 float,                                -- Гасимый напор на диафрагме, м.вод.ст
    a13 float,                                -- Расчетный расход через диафрагму, т/ч
    a14 varchar(17),                          -- Место установки байпасного участка
    a15 float,                                -- Внутренний диаметр байпасного участка, мм
    a16 float,                                -- Длина трубопровода байпасного участка, м
    a17 float,                                -- Потери напора на байпасном участке, м.вод.ст
    a18 float,                                -- Суммарный гасимый напор, м.вод.ст
    sopr float,                               -- Гидравлическое сопротивление, м*ч^2/т^2
    ist int                                   -- Источник
);
CREATE INDEX bp_out_lineid_idx ON bp_out (lineid);
CREATE INDEX bp_out_calculationid_idx ON bp_out (calculationid);
---------------------------------
-- dr_out - Выходные данные
-- dr_out - Др внешний
drop table if exists dr_out;

create  table dr_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int,
    nodeID int,
    b3 varchar(50),                           -- 4.Содержательное наименование потребителя
    cxema varchar(16),                        -- Номер расчетной схемы
    otoplz float,                             -- Расчетная нагрузка на отопление, зав.СО, Гкал/ч
    otopln float,                             -- Расчетная нагрузка на отопление, незав.СО, Гкал/ч
    ventil float,                             -- Расчетная нагрузка на вентиляцию, Гкал/ч
    kondiz float,                             -- Расчетная нагрузка на кондиционирование, Гкал/ч
    gvop float,                               -- Сред.тепл.нагрузка на ГВ, подающий теплопровод, Гкал/ч
    gvoo float,                               -- Сред.тепл.нагрузка на ГВ, обратный теплопровод, Гкал/ч
    gvpr float,                               -- Сред.тепл.нагрузка на ГВ, параллельная сх., Гкал/ч
    gvsm float,                               -- Сред.тепл. нагрузка на ГВ, смешанная сх., Гкал/ч
    gvps float,                               -- Сред.тепл.нагрузка на ГВ последовательная сх., Гкал/ч
    gvpw float,                               -- Сред.тепл.нагрузка на ГВ, предвключ.сх., Гкал/ч
    b4 float,                                 -- 5.Напор в подающем трубопроводе на входе в ИТП, м.вод.ст
    b5 float,                                 -- 6.Напор в обратном трубопроводе на входе в ИТП, м.вод.ст
    b6 float,                                 -- 7.Располагаемый напор на входе в ИТП, м.вод.ст
    b7 float,                                 -- 8.Диаметр сопла элеватора, мм
    b8 float,                                 -- 9.Гасимый напор на сопле элеватора, м.вод.ст
    b9 float,                                 -- 10.Расчетный расход через сопло элеватора, т/ч
    b10 float,                                -- 11.Номер элеватора установленный
    b11 float,                                -- 12.Номер элеватора выбранный
    b12 float,                                -- 13.Внутр.диаметр головной дросс. диафр. для ТПП или отопления, мм
    b13 float,                                -- 14.Гасимый напор на головной диаф.для ИТП, м.вод.ст
    b14 float,                                -- 15.Расч.расход через головную диафр.для ИТП, т/ч
    b15 float,                                -- 16.Внутр. диам. голов. дросс. диафр. для вент. и ГВС или отопл. и ГВС, мм
    b16 float,                                -- 17.Гасим. напор на голов. диафр. для вент. и ГВС или отопл. и ГВС, м.вод.ст
    b17 float,                                -- 18.Расч. расход через голов. диафр. для вент. и ГВС или отопл.и ГВС, т/ч
    b18 float,                                -- 19.Внутр. диам. подпорной дросс. диафр. на выходе ИТП, мм
    b19 float,                                -- 20.Гасимый напор на подпорной диафр.на выходе ИТП, м.вод.ст
    b20 float,                                -- 21.Расч.расход через подпорную диафр.на выходе ИТП, т/ч
    b21 float,                                -- 22.Внутр. диам. дросс. диафр. на вх. СО вцелом или уличн. Фасада, мм
    b22 float,                                -- 23.Гасим. нап. на диафр. на вх. СО в целом или ул.фасада, м.вод.ст
    b23 float,                                -- 24.Расчет. расх. через диафр. на вх. СО вцелом или ул.фасада, т/ч
    b24 float,                                -- 25.Внутр. диаметр дросс. диафр. на входе СО двор.фасада, мм
    b25 float,                                -- 26.Гасимый напор на диафр. на входе СО двор. Фасада, м.вод.ст
    b26 float,                                -- 27.Расч.расход через диафр. на входе СО двор. Фасада, т/ч
    b27 float,                                -- 28.Внутр. диам. дросс. диафр. на входе системы вентиляции, мм
    b28 float,                                -- 29.Гасимый напор на диафрагме на входе системы вентиляции, м.вод.ст
    b29 float,                                -- 30.Расч.расход через диафрагму на входе системы вентиляции, т/ч
    b30 float,                                -- 31.Внутр.диам. дросс. диафр. на входе подогр.закр.ГВС, мм
    b31 float,                                -- 32.Гасимый напор на диафр. на входе подогр.закр.ГВС, м.вод.ст
    b32 float,                                -- 33.Расч.расход через диафр. на входе подогр.закр.ГВС, т/ч
    b33 float,                                -- 34.Внутр. диам. дросс. диафр. на входе в под.труб.откр.ГВ, мм
    b34 float,                                -- 35.Гасимый напор на диафр. на входе в под. труб-вод откр., м.вод.ст
    b35 float,                                -- 36.Расч.расход через диафр. на входе в под.труб.откр.ГВ, т/ч
    b36 float,                                -- 37.Внутр. диам. подпорно-цирк. дросс. диафр.в откр.ГВ, мм
    b37 float,                                -- 38.Гасимый напор на подпорно-цирк.диафр.в откр., м.вод.ст
    b38 float,                                -- 39.Расч.расход через подпорно-цирк.диафр. в откр., т/ч
    b39 float,                                -- 40.Внутр. диам. ограничит.-цирк. дросс. диафр. в откр., мм
    b40 float,                                -- 41.Гасимый напор на ограничит.-цирк.диафр. в откр., м.вод.ст
    b41 float,                                -- 42.Расч.расход через ограничит.-цирк.диафр. в откр., т/ч
    b42 float,                                -- 43.Объем воды в СО, м^3
    b43 float,                                -- 44.Объем воды в системе вентиляции, м^3
    diam_P float,                             -- 45.Внутренний диаметр трубопров. на входе потребителя, мм
    diam_O float,                             -- 46.Внутренний диаметр трубопров. на выходе потребителя, мм
    balans varchar(50),                       -- 47.Балансовая принадлежность
    comment varchar,                          -- 46.Комментарий
    b101 float,
    b102 float,
    b103 float,
    b104 float,
    b105 float,
    b106 float,
    b107 float,
    b108 float,
    b109 float,
    b110 float,
    b111 float,
    b112 float,
    b113 float,
    b114 float,
    b115 float,
    ist int                                   -- Источник
);
CREATE INDEX dr_out_calculationid_idx ON dr_out (calculationid);
CREATE INDEX dr_out_nodeid_idx ON dr_out (nodeid);
---------------------------------
-- dro_out - Выходные данные
-- dro_out - Диафрагма (результат расчета)
drop table if exists dro_out;

create  table dro_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),                           -- Состояние
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    a8 varchar(51),                           -- Место установки
    ras float,                                -- Расход сетевой воды через диафрагму, т/ч
    a10 float,                                -- Потери напора, м.вод.ст
    a11 float,                                -- Полное гидравлическое сопротивление, м*ч^2/т^2
    a12 float,                                -- Располагаемый напор в конечном узле, м.вод.ст
    a13 float,                                -- Пьзометрический напор в конечном узле, м.вод.ст
    a14 float,                                -- Геодезические отметки местности в конечном узле, м
    a15 float,                                -- Полный напор в конечном узле, м.вод.ст
    ist int                                   -- Источник
);
CREATE INDEX dro_out_lineid_idx ON dro_out (lineid);
CREATE INDEX dro_out_calculationid_idx ON dro_out (calculationid);
---------------------------------
-- ist_out - Выходные данные
-- ist_out - ist_out
drop table if exists ist_out;

create  table ist_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int,
    nodeID int not null,
    externalSignLineID int,                   -- Признак участка теплопровода
    kod_ist varchar(30),
    t1 float,                                 -- Темп.сет. воды во входном узле
    t2 float,                                 -- Темп.сет. воды во вsходном узле
    ist int                                   -- Источник
);
CREATE INDEX ist_out_calculationid_idx ON ist_out (calculationid);
CREATE INDEX ist_out_nodeid_idx ON ist_out (nodeid);
---------------------------------
-- itog_out - Выходные данные
-- itog_out - itog_out
drop table if exists itog_out;

create  table itog_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kodrs varchar(8),                         -- Код расчетной схемы
    n_otz float,                              -- Тепл.нагрузка на отопление в закр.системе, зав.схема, Гкал/ч
    n_otn float,                              -- Тепл.нагрузка на отопление в закрытой системе, нез.схема, Гкал/ч
    n_vn float,                               -- Тепл.нагрузка на вентиляцию в закр. cистеме, Гкал/ч
    n_kn float,                               -- Тепл.нагрузка на техн.проц.и конд.в закр.системе, Гкал/ч
    n_txz float,                              -- Тепл.нагрузка на технол. процессы и кондиц. в закрытой системе, Гкал/ч
    n_txop float,                             -- Тепл.нагрузка или расход на технол. процессы в откр. системе из обратн. трубопр., Гкал/ч
    n_txoo float,                             -- Тепл.нагрузка или расход на технол. процессы в откр. системе из подающ. трубопр., Гкал/ч
    n_gvop float,                             -- Тепл.нагрузка на ГВ в открытой системе из подающего трубопр., Гкал/ч
    n_gvoo float,                             -- Тепл.нагрузка на ГВ в открытой системе из обратного трубопр., Гкал/ч
    n_rez float,                              -- Тепл.нагрузка в циркуляционных трубопроводах ГВС, Гкал/ч
    n_gvz float,                              -- Тепл.нагрузка на горячее водоснабжение в закр.системе, Гкал/ч
    q_otz float,                              -- Расход на отопление в закр. системе, зав. Схема, т/ч
    q_otn float,                              -- Расход на отопление в закр. системе, незав. схема, т/ч
    q_vn float,                               -- Расход на вентиляцию в закрытой системе, т/ч
    q_kn float,                               -- Тепл.нагрузка на техн.процессы и конд. в закр.системе
    q_txz float,                              -- Расход на технол. процессы и кондиц. в закр.системе, т/ч
    q_txop float,                             -- Расход на технол. процессы в откр. системе из обрат. трубопр., т/ч
    q_txoo float,                             -- Расход на технол. процессы в откр. системе из под. трубопр., т/ч
    q_gvop float,                             -- Расход на ГВ в откр. системе из подающего трубопр., т/ч
    q_gvoo float,                             -- Расход на ГВ в откр. системе из обратного трубопр., т/ч
    q_rez float,                              -- Расход сетевой воды в циркул. трубопр. ГВС, т/ч
    q_gvz float                               -- Расход на ГВ в закрытой системе, т/ч
);
---------------------------------
-- itog2_out - Выходные данные
-- itog2_out - itog2_out
drop table if exists itog2_out;

create  table itog2_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(5),
    uzel varchar(30),
    pr varchar(1),
    kn float,
    txz float,
    txop float,
    txoo float,
    ventil_cv float,
    otopl_zco float,
    otopl_nco float,
    otopl_pr float,
    otopl_sm float,
    otopl_ps float,
    otopl_pw float,
    gv_op float,
    gv_oo float,
    gv_sm float,
    gv_pr float,
    gv_ps float,
    gv_pw float,
    h float,
    rez_op float,
    rez_sm float,
    rez_pr float,
    rez_ps float,
    rez_pw float 
);
---------------------------------
-- main_out - Выходные данные
-- main_out - main_out
drop table if exists main_out;

create  table main_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Tn float,
    raschet varchar(20),
    GWS varchar(20) 
);
---------------------------------
-- ns_out - Выходные данные
-- ns_out - Насосы (результат расчета)
drop table if exists ns_out;

create  table ns_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),                           -- Состояние
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    a4 float,                                 -- 5.Геод.отметка поверхн.земли вх.узла, м
    a8 float,                                 -- 9.Геод.отметкаповерхн. земли вых.узла, м
    a9 float,                                 -- 10.Коорд.раб.зоны: 1-я точка -напор, м.вод.ст
    a10 float,                                -- 11.Коорд.рабочей зоны: 1-я точка -расход, т/ч
    a11 float,                                -- 12.Коорд.рабочей зоны:2-я точка -напор, м.вод.ст
    a12 float,                                -- 13.Коорд.рабочей зоны:2-я точка -расход, т/ч
    a13 float,                                -- 14.Рабочий напор, м.вод.ст
    a14 float,                                -- 15.Расход воды через насос, т/ч
    a15 float,                                -- 16.Пьез.напор в узле на входе, м.вод.ст
    a16 float,                                -- 17.Пьез.напор в узле на выходе, м.вод.ст
    a17 varchar(10),                          -- 18.Загрузка
    a18 int,                                  -- 19.Кол.насосов, штук(и)
    a19 varchar(24),                          -- 20.Тип насосов
    ist int                                   -- Источник
);
CREATE INDEX ns_out_lineid_idx ON ns_out (lineid);
CREATE INDEX ns_out_calculationid_idx ON ns_out (calculationid);
---------------------------------
-- nst_out - Выходные данные
-- nst_out - nst_out
drop table if exists nst_out;

create  table nst_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int default (NULL),
    nodeID int,
    pih1 float,                               -- Пьезом. напор на входе, м.вод.ст
    pih2 float,                               -- Пьезом.напор на выходе, м.вод.ст
    ras float,                                -- Расход воды, т/ч
    dP float,                                 -- Потери напора, м.вод.ст
    ist int                                   -- Источник
);
CREATE INDEX nst_out_calculationid_idx ON nst_out (calculationid);
CREATE INDEX nst_out_nodeid_idx ON nst_out (nodeid);
---------------------------------
-- ok_out - Выходные данные
-- ok_out - Обратный клапан (результат расчета)
drop table if exists ok_out;

create  table ok_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    sost varchar(7),
    ras float,                                -- Расход, т/ч
    ist int                                   -- Источник
);
CREATE INDEX ok_out_lineid_idx ON ok_out (lineid);
CREATE INDEX ok_out_calculationid_idx ON ok_out (calculationid);
---------------------------------
-- pt_out - Выходные данные
-- pt_out - Потребители (результат расчета)
drop table if exists pt_out;

create  table pt_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int,
    calculationID int,
    a3 varchar(50),                           -- 5.Содержательное наим.потреб.
    a4 float,                                 -- 6.Расход на отопл., зав.сх., т/ч
    a5 float,                                 -- 7.Расход на отопл., незав.сх., т/ч
    a6 float,                                 -- 8.Расход на вент., т/ч
    a7 float,                                 -- 9.Расход на конд., т/ч
    a8 float,                                 -- 10.Полученный расход на техн., закр.сист., т/ч
    a9 float,                                 -- 11.Расход на техн.из под.теплопр., т/ч
    a10 float,                                -- 12.Расход на техн.из обр.теплопр. в откр сист., т/ч
    a11 float,                                -- 13.Расход на Г.В. в закрытой сист., т/ч
    a12 float,                                -- 14.Расход на Г.В. из под.трубопр. в откр.сист., т/ч
    a13 float,                                -- 15.Расход на Г.В. из обр.теплопр. в откр.сист., т/ч
    a14 float,                                -- 16.Расход в цирк.теплопр.ГВС, т/ч
    a15 float,                                -- 17.Суммарный расход в закрытой системе, т/ч
    a16 float,                                -- 18.Сумм.расход из под.теплопр. в откр.сист., т/ч
    a17 float,                                -- 19.Сумм.расход из обр.теплопр. в откр.сист., т/ч
    a18 float,                                -- 20.Отн.расход сет.воды в закр.сист.
    a19 float,                                -- 21.Заданная утечка из под.теплопр., т/ч
    a20 float,                                -- 22.Заданная утечка из обр.теплопр., т/ч
    a21 float,                                -- 23.Пьез.напор в под.теплопроводе, м.вод.ст
    a22 float,                                -- 24.Пьез.напор в обр.теплопроводе, м.вод.ст
    a23 float,                                -- 25.Распол.напор в узле присоед.потреб., м.вод.ст
    Gsm float,                                -- 26.Расход воды в СО после узла смеш., т/ч
    Gm float,                                 -- 27.Расход воды на вх.мест.СО, незав.присоед., т/ч
    Gx float,                                 -- 28.Расход водопр.воды в закр.ГВС, т/ч
    Ggws float,                               -- 29.Расход сет.воды на 2 ст.закр.ГВС, т/ч
    t1 float,                                 -- 30.Темпер.сет.воды на вх.ТП, °C
    t2 float,                                 -- 31.Темпер.сет.воды на вых.ТП, °C
    t01 float,                                -- 32.Темпер.в под.теплопр.СО, °C
    t02 float,                                -- 33.Темпер.в обр.теплопр.СО, °C
    t03 float,                                -- 34.Темпер.после узла смеш.в СО, °C
    t2co float,                               -- 35.Темпер.сет.воды на вых.подогр.СО, °C
    t2gws float,                              -- 36.Темпер.сет.воды на вых.подогр. 2 ст.ГВС, °C
    tv float,                                 -- 37.Темпер.внутри отапл.помещ., °C
    tg float,                                 -- 38.Горяч.вода на вых.водоразб.приб.в ГВС, °C
    dop8 float,                               -- 39.Темпер.нагретого возд.в сист.вент., °C
    dop9 float,                               -- 40.Темпер.нагретого возд.в сист.конд., °C
    Qotz float,                               -- 41.Тепл.нагрузка на отопл., зав.сх., Гкал/ч
    Qotn float,                               -- 42.Тепл.нагрузка на отопл., незав.сх., Гкал/ч
    dop12 float,                              -- 43.Тепл.нагрузка на вент., Гкал/ч
    dop13 float,                              -- 44.Полученная тепл.нагрузка на конд., Гкал/ч
    dop14 float,                              -- 45.Тепл.нагрузка на техн., закр.сист., Гкал/ч
    dop15 float,                              -- 46.Тепл.нагрузка на техн. из под.трубопр., Гкал/ч
    dop16 float,                              -- 47.Получ.тепл.нагрузка на техн. из обр.трубопр., Гкал/ч
    dop17 float,                              -- 48.Получ.тепл.нагрузка на ГВ в закр.сист., Гкал/ч
    dop18 float,                              -- 49.Получ.тепл.нагрузка на ГВ из под.теплопр., Гкал/ч
    dop19 float,                              -- 50.Тепл.нагрузка на ГВ из обр.теплопр., Гкал/ч
    dop20 float,                              -- 51.Тепл.нагрузка в цирк.теплопр.ГВС, Гкал/ч
    Qsum_z float,                             -- 52.Сумм.тепл.нагрузка в закр.сист., Гкал/ч
    dop22 float,                              -- 52.Сумм.тепл.нагрузка из обр.теплопр. в откр.сист., Гкал/ч
    dop23 float,                              -- 53.Сумм.тепл.нагрузка из обр.теплопр. в откр.сист., Гкал/ч
    Gneob float,                              -- 54.Необх.располаг.напор, м.вод.ст
    Qras_gv_z float,                          -- 55.Расчетная нагрузка в закрытых ГВС, Гкал/ч
    Qotz_treb float,                          -- 56.Требуемый расход тепла на отопление,зав.схема, Гкал/ч
    Qotn_treb float,                          -- 57.Требуемый расход тепла на отопление,незав.схема, Гкал/ч
    Qvent_treb float,                         -- 58.Требуемый расход тепла на вентиляцию, Гкал/ч
    Qgvz_treb float,                          -- 59.Требуемый расход тепла на горячее водоснабжение в закрытой системе, Гкал/ч
    Qgvop_treb float,                         -- 60.Требуемый расход тепла на горячее водоснабжение в открытой системе, подача, Гкал/ч
    Qgvoo_treb float,                         -- 61.Требуемый расход тепла на горячее водоснабжение в открытой системе, обратка, Гкал/ч
    Qrez_treb float,                          -- 62.Требуемый расход тепла на рециркуляцию в в открытой системе ГВ, Гкал/ч
    Qtreb float,                              -- 63.Суммарный требуемый расход тепла в системах теплопотребления, Гкал/ч
    Qfact float,                              -- 60.Суммарная тепловая нагрузка, Гкал/ч
    Q_obesp_min float,                        -- Суммарная теплообеспеченность, %
    Q_obesp_otopl_min float,                  -- Теплообеспеченность отопительной нагрузки, %
    Q_obesp_gvs_min float,                    -- Теплообеспеченность нагрузки горячего водоснабжения, %
    tzam float,                               -- Время замерзания, час
    Qp float,
    b101 float,                               -- Коэффициент смешения элеватора
    b102 float,
    b103 float,
    b104 float,
    b105 float,
    b106 float,
    b107 float,
    b108 float,
    b109 float,
    b110 float,
    b111 float,
    b112 float,
    b113 float,
    b114 float,
    b115 float,
    ist int                                   -- Источник
);
CREATE INDEX pt_out_calculationid_idx ON pt_out (calculationid);
CREATE INDEX pt_out_nodeid_idx ON pt_out (nodeid);
---------------------------------
-- raspar_out - Выходные данные
-- raspar_out - raspar_out
drop table if exists raspar_out;

create  table raspar_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date date,
    kod_p varchar(5),                         -- Код расчетной схемы узла присоединения
    uzel_p varchar(30),                       -- Наименование узла присоединения
    pr_p varchar(1),                          -- Признак теплопровода узла присоединения
    kod varchar(5),                           -- Код расчетной схемы узла с контролируемыми параметрами
    uzel varchar(30),                         -- Наименование узла с контролируемыми параметрами
    pr varchar(1),                            -- Признак теплопровода узла с контролируемыми параметрами
    kod_ist varchar(6),                       -- Источник тепла
    name_object varchar(50),                  -- Имя объекта
    kod_stroki varchar(50),
    typ varchar(50),                          -- Тип объекта
    name_typ varchar(50),
    name_ist varchar(50),
    G float,                                  -- Расчетный расход воды в подающем теплопр., т/ч
    G_obr float,                              -- Расчетный расход воды в обратном теплопр., т/ч
    Gutech float,                             -- Расчетные непроизодственные утечки, т/ч
    Ggvs float,                               -- Расчетный водоразбор в открытых ГВ, т/ч
    Gpodp float,                              -- Расчетный расход подпиточной воды, т/ч
    pP float,                                 -- Расчетное давление в подающем теплопр.
    pO float,                                 -- Расчетное давление в обратном теплопр.
    tP float,                                 -- Расчетная температура воды в подающем теплопров., °C
    tO_ float,
    Qot float,                                -- Расчетная тепловая нагрузка на отопления, Гкал/ч
    Qgvs float,                               -- Расчетная тепловая нагрузка на закрытое ГВ, Гкал/ч
    Qvent float,                              -- Расчетная тепловая нагрузка на вентиляции, Гкал/ч
    Q float,                                  -- Расчетная тепловая нагрузка, Гкал/ч
    poteri float,                             -- Нормативные тепловые потери, Гкал/ч
    t1ras float,                              -- Температура воды в подающем теплопров. по темп.графику, °C
    t2ras float,                              -- Температура воды в обратном теплопров. по темп.графику, °C
    ispoln varchar(50),                       -- Ответственный за подготовку данных
    data_ date,
    G_pod_fakt float,                         -- Фактический расход воды в подающем теплопр., т/ч
    G_obr_fakt float,                         -- Фактический расход воды в обратном теплопр., т/ч
    Gpodp_fakt float,                         -- Фактическая подпитка воды, т/ч
    G_pod_otkl float,                         -- Отклонение фактического расхода от расчетного в подающем теплопр., т/ч
    G_obr_otkl float,                         -- Отклонение фактического расхода от расчетного в обратном теплопр., т/ч
    Gpodp_otkl float,                         -- Отклонение между фактической и расчетной подпидкой, т/ч
    deltaP float,                             -- Расчетный перепад давления
    pP_fakt float,                            -- Фактическое давление в подающем теплопр.
    pO_fakt float,                            -- Фактическое давление в обратном теплопр.
    deltaP_fakt float,                        -- Фактический перепад давления
    pP_pod_otkl float,                        -- Отклонение фактического давления от расчетного в подающем теплопр.
    pO_obr_otkl float,                        -- Отклонение фактического давления от расчетного в обратном теплопр.
    deltaP_otkl float,                        -- Отклонение фактического перепада давления от расчетного
    tP_fakt float,                            -- Фактическая температура в подающем теплопр., °C
    tO_fakt float,                            -- Фактическая температура в обратном теплопр., °C
    deltaT_fakt float,                        -- ",
    tP_pod_otkl float,                        -- Отклонение фактической температуры от расчетной в подающем теплопр., Гкал/ч
    tO_obr_otkl float,                        -- Отклонение фактической температуры от расчетной в обратном теплопр., °C
    Q_fact_rasch float,                       -- Расчетная тепловая нагрузка, Гкал/ч
    Q_otkl_fact_rasch float,                  -- Отклонение фактической тепловой нагрузки от расчетной, Гкал/ч
    Qot_treb float,                           -- Требуемая тепловая нагрузка на отопление, Гкал/ч
    Qvent_treb float,                         -- Требуемая тепловая нагрузка на вентиляцию, Гкал/ч
    Qgvz_treb float,                          -- Требуемая тепловая нагрузка в закрытой ГВ, Гкал/ч
    Qgvop_treb float,
    Qgvoo_treb float,
    Qrez_treb float,
    Q_treb float,                             -- Требуемая тепловая нагрузка, Гкал/ч
    Q_otkl_treb float,                        -- Отклонение фактической тепловой нагрузки от требуемой, Гкал/ч
    Q_fakt float                              -- Фактическая тепловая нагрузка, Гкал/ч
);
---------------------------------
-- rpp_out - Выходные данные
-- rpp_out - rpp_out
drop table if exists rpp_out;

create  table rpp_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int default (NULL),
    lineID int,
    sopr float,
    polozhenie varchar(8),
    ist int                                   -- Источник
);
CREATE INDEX rpp_out_lineid_idx ON rpp_out (lineid);
CREATE INDEX rpp_out_calculationid_idx ON rpp_out (calculationid);
---------------------------------
-- rs_out - Выходные данные
-- rs_out - Сетевые регуляторы (результат расчета)
drop table if exists rs_out;

create  table rs_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),                           -- Состояние
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    a4 float,                                 -- Геод.отметка верха трубы узла на входе рег., м
    a8 float,                                 -- Геод.отметка верха трубы узла на выходе рег., м
    kod3 varchar(6),                          -- Код расч.сх.узла с рег.напором (импул.трубки)
    uzel3 varchar(31),                        -- Наим.узла с регул.напором (импул.трубки)
    pr3 varchar(1),                           -- Признак теплопр. регулируемого узла (импул.трубки)
    a11 float,                                -- Расход сет.воды, т/ч
    a12 float,                                -- Гидравл.сопрот.клапана, м*ч^2/т^2
    a13 float,                                -- Пьез.напор в узле на вх., м.вод.ст
    a14 float,                                -- Пьез.напор в узле на вых., м.вод.ст
    a15 varchar(8),                           -- Признак
    a16 float,                                -- Зад.значение рег.напора
    a17 float,                                -- Получ.значение рег.напора
    a18 float,                                -- Допуст.отклон.
    dx float,                                 -- Разница заданной/полученой регулируемой величины
    a19 varchar(8),                           -- Положение клапана
    ist int                                   -- Источник
);
CREATE INDEX rs_out_lineid_idx ON rs_out (lineid);
CREATE INDEX rs_out_calculationid_idx ON rs_out (calculationid);
---------------------------------
-- tekpar_out - Выходные данные
-- tekpar_out - tekpar_out
drop table if exists tekpar_out;

create  table tekpar_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod_ist varchar(6),
    name_magistral varchar(50),
    typ varchar(50),
    name_typ varchar(50),
    name_ist varchar(50),
    calculationID int,
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    G_pod float,
    G_obr float,
    Gpodp float,
    G_pod_fakt float,
    G_obr_fakt float,
    Gpodp_fakt float,
    G_pod_otkl float,
    G_obr_otkl float,
    Gpodp_otkl float,
    pP float,
    pO float,
    deltaP float,
    pP_fakt float,
    pO_fakt float,
    deltaP_fakt float,
    pP_pod_otkl float,
    pO_obr_otkl float,
    deltaP_otkl float,
    tP float,
    tO_ float,
    deltaT float,
    tP_fakt float,
    tO_fakt float,
    deltaT_fakt float,
    tP_pod_otkl float,
    tO_obr_otkl float,
    deltaT_otkl float,
    Q float,
    poteri float,
    Q_fakt float,
    Q_otkl float,
    name_tg varchar(50) 
);
CREATE INDEX tekpar_out_lineid_idx ON tekpar_out (lineid);
CREATE INDEX tekpar_out_calculationid_idx ON tekpar_out (calculationid);
---------------------------------
-- teplo_out - Выходные данные
-- teplo_out - teplo_out
drop table if exists teplo_out;

create  table teplo_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(5),
    diametr float,
    diametr_usl float,
    y int,
    kolwork int,
    q_N_P float,
    q_N_O float,
    q_K_P float,
    q_K_O float,
    q_B_P float,
    q_B_O float 
);
---------------------------------
-- teplo_t_out - Выходные данные
-- teplo_t_out - teplo_t_out
drop table if exists teplo_t_out;

create  table teplo_t_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(5),
    t1 float,
    t2 float,
    tn float,
    tgr float,
    diametr float,
    diametr_usl float,
    y int,
    kolwork int,
    q_N_P float,
    q_N_O float,
    q_K_P float,
    q_K_O float,
    q_B_P float,
    q_B_O float 
);
---------------------------------
-- us_out - Выходные данные
-- us_out - Узел (результат расчета)
drop table if exists us_out;

create  table us_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int,
    nodeID int not null,
    externalSign int not null,                -- Признак участка теплопровода
    pih float,                                -- Пьез.напор в Узле, м.вод.ст
    t float,                                  -- Темп.в Узле, °C
    t2 float,                                 -- Температура в узле при расчетной температуре наружного воздуха
    ist int                                   -- Источник
);
CREATE INDEX us_out_calculationid_idx ON us_out (calculationid);
CREATE INDEX us_out_nodeid_idx ON us_out (nodeid);
---------------------------------
-- ut_ktp_out - Выходные данные
-- ut_ktp_out - ut_ktp_out
drop table if exists ut_ktp_out;

create  table ut_ktp_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diam float,
    name_typ varchar(1),
    beta float 
);
---------------------------------
-- ut_out - Выходные данные
-- ut_out - Участок теплопровода (результат расчета)
drop table if exists ut_out;

create  table ut_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculationID int,
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    sos varchar(7),                           -- Состояние
    a7 float,                                 -- Длина участка теплопр, м
    a8 float,                                 -- Вн.диаметр трубы, мм
    a9 float,                                 -- Объем воды, м^3
    a10 float,                                -- Скорость потока, м/c
    a11 float,                                -- Время прохождения потока воды, час
    a12 float,                                -- Полное гидр.сопротивление, м*ч^2/т^2
    a13 float,                                -- Расход сет. воды, т/ч
    a14 float,                                -- Уд.лин.потери напора, мм.вод.ст./м
    a15 float,                                -- Лин.потери напора, м.вод.ст
    a16 float,                                -- Мест.потери напора, м.вод.ст
    a17 float,                                -- Общие потери напора, м.вод.ст
    a18 float,                                -- Распол.напор в кон.узле, м.вод.ст
    a19 float,                                -- Пьзом.напор в кон.узле, м.вод.ст
    a20 float,                                -- Геод.отмет.местности в кон.уз., м
    a21 float,                                -- Полный напор в кон.узле, м.вод.ст
    tpot float,                               -- Тепловые потери, Гкал/ч
    t1 float,                                 -- Темп.сет. воды во входном узле, °C
    t2 float,                                 -- Температура остывания сет. воды, °C
    qq float,                                 -- Нормы тепловых потерь, ккал/(ч*м)
    tzam float,                               -- Время остывания при остановке движения, час
    n_pot int,                                -- ,!!!!
    b101 float,                               -- Расчетная тепловая нагрузка, Гкал/ч
    b102 float,                               -- Расчетная тепловая нагрузка на отопление, Гкал/ч
    b103 float,                               -- Расчетная тепловая нагрузка на вентиляцию, Гкал/ч
    b104 float,                               -- Расчетная тепловая нагрузка на ГВС, Гкал/ч
    b105 float,
    b106 float,
    b107 float,
    b108 float,
    b109 float,
    b110 float,
    b111 float,
    b112 float,
    b113 float,
    b114 float,
    b115 float,
    ist int                                   -- Источник
);
CREATE INDEX ut_out_lineid_idx ON ut_out (lineid);
CREATE INDEX ut_out_calculationid_idx ON ut_out (calculationid);
---------------------------------
-- ut_teplo_out - Выходные данные
-- ut_teplo_out - ut_teplo_out
drop table if exists ut_teplo_out;

create  table ut_teplo_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    truba int,
    diametr float,
    tol float,
    diametr_usl float,
    dlina float,
    name_calctpr varchar(8),
    name_typ varchar(8),
    kti float,
    kolwork int,
    kod_owner int,
    year int,
    q float,
    q01 float,
    q02 float,
    q03 float,
    q04 float,
    q05 float,
    q06 float,
    q07 float,
    q08 float,
    q09 float,
    q10 float,
    q11 float,
    q12 float,
    kod_ist varchar(30) 
);
CREATE INDEX ut_teplo_out_lineid_idx ON ut_teplo_out (lineid);
CREATE INDEX ut_teplo_out_calculationid_idx ON ut_teplo_out (calculationid);
---------------------------------
-- zd_out - Выходные данные
-- zd_out - Задвижка (результат расчета)
drop table if exists zd_out;

create  table zd_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),                           -- Состояние
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    a7 varchar(5),                            -- Состояние, %
    a8 varchar(31),                           -- Сод.наим.
    a9 float,                                 -- Расход сет.воды, т/ч
    a10 float,                                -- Потери напора, м.вод.ст
    a11 float,                                -- Гидр.сопротивление, м*ч^2/т^2
    a12 float,                                -- Распол.напор в кон.узле, м.вод.ст
    a13 float,                                -- Пьзом.напор в кон.узле, м.вод.ст
    a14 float,                                -- Геод.отметки мест.в кон.узле, м
    a15 float,                                -- Полный напор в кон.узле, м.вод.ст
    ist int                                   -- Источник
);
CREATE INDEX zd_out_lineid_idx ON zd_out (lineid);
CREATE INDEX zd_out_calculationid_idx ON zd_out (calculationid);
---------------------------------
-- zd2_out - Выходные данные
-- zd2_out - Регулирующая арматура (результат расчета)
drop table if exists zd2_out;

create  table zd2_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sos varchar(7),
    calculationID int default (NULL),
    lineID int,
    externalSignLineID int,                   -- Признак участка теплопровода
    a7 varchar(5),                            -- Состояние
    a8 varchar(31),                           -- Сод.наим.
    a9 float,                                 -- Расход сет.воды, т/ч
    a10 float,                                -- Потери напора, м.вод.ст
    a11 float,                                -- Гидр.сопротивление, м*ч^2/т^2
    a12 float,                                -- Распол.напор в кон.узле, м.вод.ст
    a13 float,                                -- Пьзом.напор в кон.узле, м.вод.ст
    a14 float,                                -- Геод.отметки мест.в кон.узле, м
    a15 float,                                -- Полный напор в кон.узле, м.вод.ст
    ist int                                   -- Источник
);
CREATE INDEX zd2_out_lineid_idx ON zd2_out (lineid);
CREATE INDEX zd2_out_calculationid_idx ON zd2_out (calculationid);
--- Выходные данные: 25
--===========================--
--         lookup            --
--===========================--
--- Выходные данные lookup: 0
--===========================--
--        Стандартные             --
--===========================--
---------------------------------
-- standardpressregulators - Стандартные
-- standardpressregulators - DC_Регуляторы давления стандартные
drop table if exists standardpressregulators;

create table standardpressregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра
    name_rd varchar(50) default (NULL),       -- Наименование регулятора (копировать)
    typ_rd varchar(50) default (NULL),        -- Наименование регулятора по ГОСТу
    typ varchar(50) default (NULL),           -- Тип регулирующего клапана
    t float default ((0)),                    -- Температура рабочей среды максимальная
    d_usl float default ((0)),                -- Диаметр условный
    kv float default ((0)),                   -- Пропускная способность, условная, т/ч (копировать)
    otn_kv int default (NULL),                -- Негерметичность затвора максимальная, % (копировать)
    producer varchar(50) default (NULL)       -- Изготовитель
);

INSERT INTO "standardpressregulators" ("id","name_rd","typ_rd","typ","t","d_usl","kv","otn_kv","producer") VALUES
(1,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,50.0,25.0,0,NULL),
(2,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,250.0,600.0,0,NULL),
(3,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,300.0,900.0,0,NULL),
(4,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,200.0,400.0,0,NULL),
(5,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,500.0,2500.0,0,NULL),
(6,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,700.0,4900.0,0,NULL),
(7,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,600.0,3600.0,0,NULL),
(8,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,80.0,60.0,0,NULL),
(9,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,150.0,250.0,0,NULL),
(10,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,400.0,1600.0,0,NULL),
(11,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,70.0,50.0,0,NULL),
(12,'Регулятор давления гидравлический','РК-1','РД-3М',70.0,700.0,4900.0,0,NULL),
(13,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,300.0,900.0,0,NULL),
(14,'Регулятор давления гидравлический','РК-1','РД-3М',70.0,600.0,3600.0,0,NULL),
(15,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,700.0,4900.0,0,NULL),
(16,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,400.0,1600.0,0,NULL),
(17,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,250.0,625.0,0,NULL),
(18,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,50.0,25.0,0,NULL),
(19,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,250.0,600.0,0,NULL),
(20,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,300.0,900.0,0,NULL),
(21,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,200.0,400.0,0,NULL),
(22,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,500.0,2500.0,0,NULL),
(23,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,700.0,4900.0,0,NULL),
(24,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,600.0,3600.0,0,NULL),
(25,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,80.0,60.0,0,NULL),
(26,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,150.0,250.0,0,NULL),
(27,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,400.0,1600.0,0,NULL),
(28,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,70.0,50.0,0,NULL),
(29,'Регулятор давления гидравлический','РК-1','РД-3М',70.0,700.0,4900.0,0,NULL),
(30,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,300.0,900.0,0,NULL),
(31,'Регулятор давления гидравлический','РК-1','РД-3М',70.0,600.0,3600.0,0,NULL),
(32,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,700.0,4900.0,0,NULL),
(33,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,400.0,1600.0,0,NULL),
(34,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,250.0,625.0,0,NULL),
(35,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,50.0,25.0,0,NULL),
(36,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,250.0,600.0,0,NULL),
(37,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,300.0,900.0,0,NULL),
(38,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,200.0,400.0,0,NULL),
(39,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,500.0,2500.0,0,NULL),
(40,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,700.0,4900.0,0,NULL),
(41,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,600.0,3600.0,0,NULL),
(42,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,80.0,60.0,0,NULL),
(43,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,150.0,250.0,0,NULL),
(44,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,400.0,1600.0,0,NULL),
(45,'Регулятор давления системы ОРГРЭС','РК-1','РД-3А',200.0,70.0,50.0,0,NULL),
(46,'Регулятор давления гидравлический','РК-1','РД-3М',70.0,700.0,4900.0,0,NULL),
(47,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,300.0,900.0,0,NULL),
(48,'Регулятор давления гидравлический','РК-1','РД-3М',70.0,600.0,3600.0,0,NULL),
(49,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,700.0,4900.0,0,NULL),
(50,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,400.0,1600.0,0,NULL),
(51,'Регулятор давления гидравлический','РК-1','РД-3М',90.0,250.0,625.0,0,NULL);


-- SELECT setval('"standardpressregulators_id_seq"', 51);
---------------------------------
-- standardelevators - Стандартные
-- standardelevators - EV_Элеватор стандартный
drop table if exists standardelevators;

create table standardelevators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Порядковый номер стандартного элеватора
    name_elv varchar(50) default (NULL),      -- Наименование элеватора
    typ_elv varchar(50) default (NULL),       -- Тип элеватора
    a5 int default (NULL),                    -- Номер элеватора
    plan1 varchar(50) default (NULL),         -- Номер рабочего чертежа
    conditions varchar(50) default (NULL),    -- Технические условия
    producer varchar(50) default (NULL),      -- Завод-изготовитель
    material varchar(50) default (NULL),      -- Материал корпуса
    p_usl float default ((0)),                -- Давление условное, 1 м. вод.ст.= 0.1 кгс/cм^2, 1 кгс/cм^2 = 10 м.вод.ст.
    t_max int default (NULL),                 -- Максимальная температура рабочей среды
    d_chamber int default (NULL),             -- Диаметр камеры смешения, мм
    dlina int default (NULL),                 -- Длина элеватора общая, мм
    massa float default ((0)),                -- Масса, кг
    d_entry float default ((0)),              -- Диаметр входного фланца, мм
    d_exit float default ((0)),               -- Диаметр выходного фланца, мм
    d_infiltration float default ((0))        -- Диаметр фланца патрубка подсоса, мм
);

INSERT INTO "standardelevators" ("id","name_elv","typ_elv","a5","plan1","conditions","producer","material","p_usl","t_max","d_chamber","dlina","massa","d_entry","d_exit","d_infiltration") VALUES
(1,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',1,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,15,425,100.0,145.0,160.0,160.0),
(2,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',2,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,20,425,NULL,145.0,160.0,160.0),
(3,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',3,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,25,625,NULL,160.0,195.0,180.0),
(4,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',4,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,30,625,NULL,160.0,195.0,180.0),
(5,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',5,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,35,625,NULL,160.0,195.0,180.0),
(6,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',6,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,47,720,NULL,195.0,215.0,215.0),
(7,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',7,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','сталь',160.0,150,59,720,NULL,195.0,215.0,215.0),
(8,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',1,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,15,425,100.0,145.0,160.0,160.0),
(9,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',2,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,20,425,NULL,145.0,160.0,160.0),
(10,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',3,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,25,625,NULL,160.0,195.0,195.0),
(11,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',4,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,30,625,NULL,160.0,195.0,195.0),
(12,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',5,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,35,625,NULL,160.0,195.0,195.0),
(13,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',6,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,47,720,NULL,195.0,215.0,215.0),
(14,'Элеватор водоструйный фланцевый','ВТИ-Тепл.Мосэнерго',7,NULL,NULL,'Сантехоборудование,Главмонтажспецстрой','чугун',90.0,150,59,720,NULL,195.0,215.0,215.0),
(15,'Элеватор водоструйный фланцевый','ЭЧА',1,NULL,NULL,NULL,'чугун',90.0,150,15,425,NULL,150.0,165.0,165.0),
(16,'Элеватор водоструйный фланцевый','ЭЧА',2,NULL,NULL,NULL,'чугун',90.0,150,15,425,NULL,150.0,165.0,165.0),
(17,'Элеватор водоструйный фланцевый','ЭЧА',3,NULL,NULL,NULL,'чугун',90.0,150,25,625,NULL,165.0,200.0,185.0),
(18,'Элеватор водоструйный фланцевый','ЭЧА',4,NULL,NULL,NULL,'чугун',90.0,150,30,625,NULL,165.0,200.0,185.0),
(19,'Элеватор водоструйный фланцевый','ЭЧА',5,NULL,NULL,NULL,'чугун',90.0,150,47,625,NULL,165.0,200.0,185.0),
(20,'Элеватор водоструйный фланцевый','ЭЧА',6,NULL,NULL,NULL,'чугун',90.0,150,47,720,NULL,200.0,220.0,220.0),
(21,'Элеватор водоструйный фланцевый','ЭЧА',7,NULL,NULL,NULL,'чугун',90.0,150,59,720,NULL,200.0,220.0,220.0),
(22,'Элеватор водоструйный фланцевый','40с10бк-М',1,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,15,425,NULL,145.0,160.0,160.0),
(23,'Элеватор водоструйный фланцевый','40с10бк-М',1,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,20,425,NULL,145.0,160.0,160.0),
(24,'Элеватор водоструйный фланцевый','40с10бк-М',3,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,25,625,NULL,160.0,195.0,195.0),
(25,'Элеватор водоструйный фланцевый','40с10бк-М',4,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,30,625,NULL,160.0,195.0,195.0),
(26,'Элеватор водоструйный фланцевый','40с10бк-М',5,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,35,625,NULL,160.0,195.0,195.0),
(27,'Элеватор водоструйный фланцевый','40с10бк-М',6,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,47,720,NULL,195.0,215.0,215.0),
(28,'Элеватор водоструйный фланцевый','40с10бк-М',7,NULL,NULL,'Котельниковский арматурный з-д','чугун',90.0,150,59,720,NULL,195.0,215.0,215.0),
(29,'Элеватор водоструйный фланцевый','40с10бк',1,'КТ93001','ТУ 26-07-1255-82','Котельниковский арматурный з-д','сталь 3',160.0,150,3,360,8.9,NULL,NULL,NULL),
(30,'Элеватор водоструйный фланцевый','40с10бк',2,'КТ84002','ТУ 26-07-1255-82','Котельниковский арматурный з-д','сталь 3',160.0,150,4,440,12.5,NULL,NULL,NULL),
(31,'Элеватор водоструйный фланцевый','40с10бк',3,'КТ960003','ТУ 26-07-1255-82','Котельниковский арматурный з-д','сталь 3',160.0,150,6,570,18.7999992370605,NULL,NULL,NULL),
(32,'Элеватор водоструйный фланцевый','40с10бк',4,'960004','ТУ 26-07-1255-82','Котельниковский арматурный з-д','сталь 3',160.0,150,7,620,24.0,NULL,NULL,NULL);


-- SELECT setval('"standardelevators_id_seq"', 32);
---------------------------------
-- standardcompensators - Стандартные
-- standardcompensators - KC_Компесаторы стандартные
drop table if exists standardcompensators;

create table standardcompensators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Порядковый номер экземпляра
    d_usl float default ((0)),                -- Диаметр условный, мм
    d_n float default ((0)),                  -- Диаметр наружный, мм
    typ varchar(50) default (NULL),           -- Тип
    name varchar(50) default (NULL),          -- Обозначение
    h float default ((0)),                    -- Вылет компенсатора
    kompens float default ((0)),              -- Расчетная компенсирующая способность, мм (копировать)
    l_kompens float default ((0)),            -- Выпрямленная длина, м (копировать)
    t float default ((0)),                    -- Температура теплоносителя максимальная, °С
    p float default ((0))                     -- Допустимое рабочее давление, м.вод.ст
);

INSERT INTO "standardcompensators" ("id","d_usl","d_n","typ","name","h","kompens","l_kompens","t","p") VALUES
(1,50.0,51.0,'П-образный с гнутыми отводами',NULL,0.6,50.0,2.05,200.0,203.87),
(2,50.0,51.0,'П-образный с гнутыми отводами',NULL,0.8,70.0,2.45,200.0,203.87),
(3,50.0,51.0,'П-образный с гнутыми отводами',NULL,1.0,100.0,2.85,200.0,203.87),
(4,50.0,51.0,'П-образный с гнутыми отводами',NULL,1.2,120.0,3.25,200.0,203.87),
(5,100.0,108.0,'П-образный с гнутыми отводами',NULL,1.2,100.0,4.28,200.0,203.87),
(6,100.0,108.0,'П-образный с гнутыми отводами',NULL,1.6,150.0,5.02,200.0,203.87),
(7,100.0,108.0,'П-образный с гнутыми отводами',NULL,2.0,250.0,5.82,200.0,203.87),
(8,100.0,108.0,'П-образный с гнутыми отводами',NULL,2.4,280.0,6.62,200.0,203.87),
(9,125.0,133.0,'П-образный с гнутыми отводами',NULL,1.5,100.0,5.08,200.0,203.87),
(10,125.0,133.0,'П-образный с гнутыми отводами',NULL,2.0,180.0,6.05,200.0,203.87),
(11,125.0,133.0,'П-образный с гнутыми отводами',NULL,2.5,260.0,7.05,200.0,203.87),
(12,125.0,133.0,'П-образный с гнутыми отводами',NULL,3.0,310.0,8.05,200.0,203.87),
(13,150.0,159.0,'П-образный с гнутыми отводами',NULL,1.8,120.0,6.03,200.0,203.87),
(14,150.0,159.0,'П-образный с гнутыми отводами',NULL,2.4,220.0,7.23,200.0,203.87),
(15,150.0,159.0,'П-образный с гнутыми отводами',NULL,3.0,280.0,8.43,200.0,203.87),
(16,150.0,159.0,'П-образный с гнутыми отводами',NULL,3.6,350.0,9.63,200.0,203.87),
(17,200.0,219.0,'П-образный с гнутыми отводами',NULL,2.4,160.0,7.94,200.0,203.87),
(18,200.0,219.0,'П-образный с гнутыми отводами',NULL,3.2,240.0,9.64,200.0,203.87),
(19,200.0,219.0,'П-образный с гнутыми отводами',NULL,4.0,350.0,11.14,200.0,203.87),
(20,200.0,219.0,'П-образный с гнутыми отводами',NULL,4.8,420.0,12.74,200.0,203.87),
(21,250.0,273.0,'П-образный с гнутыми отводами',NULL,3.0,200.0,9.78,200.0,203.87),
(22,250.0,273.0,'П-образный с гнутыми отводами',NULL,4.0,310.0,11.78,200.0,203.87),
(23,250.0,273.0,'П-образный с гнутыми отводами',NULL,5.0,400.0,13.78,200.0,203.87),
(24,250.0,273.0,'П-образный с гнутыми отводами',NULL,6.0,600.0,15.78,200.0,203.87),
(25,300.0,325.0,'П-образный с гнутыми отводами',NULL,3.6,260.0,11.85,200.0,203.87),
(26,300.0,325.0,'П-образный с гнутыми отводами',NULL,4.8,400.0,14.25,200.0,203.87),
(27,300.0,325.0,'П-образный с гнутыми отводами',NULL,6.0,500.0,16.65,200.0,203.87),
(28,300.0,325.0,'П-образный с гнутыми отводами',NULL,7.2,680.0,19.65,200.0,203.87),
(29,350.0,377.0,'П-образный с гнутыми отводами',NULL,4.2,320.0,13.92,200.0,203.87),
(30,350.0,377.0,'П-образный с гнутыми отводами',NULL,5.6,470.0,16.72,200.0,203.87),
(31,350.0,377.0,'П-образный с гнутыми отводами',NULL,7.0,640.0,16.72,200.0,203.87),
(32,400.0,427.0,'П-образный с гнутыми отводами',NULL,4.8,300.0,16.1,200.0,203.87),
(33,400.0,427.0,'П-образный с гнутыми отводами',NULL,6.4,410.0,19.3,200.0,203.87),
(34,400.0,427.0,'П-образный с гнутыми отводами',NULL,8.0,600.0,22.5,200.0,203.87),
(35,400.0,427.0,'П-образный с гнутыми отводами',NULL,4.8,350.0,19.56,200.0,203.87),
(36,400.0,427.0,'П-образный с гнутыми отводами',NULL,8.0,500.0,23.56,200.0,203.87),
(37,400.0,427.0,'П-образный с гнутыми отводами',NULL,10.0,650.0,27.56,200.0,203.87),
(38,100.0,0.0,'Сальниковый, односторонний',NULL,0.0,250.0,0.0,300.0,254.84),
(39,175.0,0.0,'Сальниковый, односторонний',NULL,0.0,250.0,0.0,300.0,254.84),
(40,200.0,0.0,'Сальниковый, односторонний',NULL,0.0,200.0,0.0,300.0,254.84),
(41,200.0,0.0,'Сальниковый, односторонний',NULL,0.0,200.0,0.0,300.0,254.84),
(42,350.0,0.0,'Сальниковый, односторонний',NULL,0.0,400.0,0.0,300.0,254.84),
(43,350.0,0.0,'Сальниковый, односторонний',NULL,0.0,400.0,0.0,300.0,254.84),
(44,400.0,0.0,'Сальниковый, односторонний',NULL,0.0,300.0,0.0,300.0,254.84),
(45,450.0,0.0,'Сальниковый, односторонний',NULL,0.0,500.0,0.0,300.0,254.84),
(46,500.0,0.0,'Сальниковый, односторонний',NULL,0.0,300.0,0.0,300.0,163.09),
(47,800.0,0.0,'Сальниковый, односторонний',NULL,0.0,500.0,0.0,300.0,163.09),
(48,900.0,0.0,'Сальниковый, односторонний',NULL,0.0,350.0,0.0,300.0,163.09),
(49,1400.0,0.0,'Сальниковый, односторонний',NULL,0.0,600.0,0.0,300.0,163.09),
(50,500.0,0.0,'Сальниковый, односторонний',NULL,0.0,300.0,0.0,300.0,254.84),
(51,800.0,0.0,'Сальниковый, односторонний',NULL,0.0,500.0,0.0,300.0,254.84),
(52,900.0,0.0,'Сальниковый, односторонний',NULL,0.0,350.0,0.0,300.0,254.84),
(53,1400.0,0.0,'Сальниковый, односторонний',NULL,0.0,600.0,0.0,300.0,254.84),
(54,100.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,500.0,0.0,300.0,254.84),
(55,175.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,500.0,0.0,300.0,254.84),
(56,200.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,400.0,0.0,300.0,254.84),
(57,200.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,400.0,0.0,300.0,254.84),
(58,350.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,800.0,0.0,300.0,254.84),
(59,350.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,800.0,0.0,300.0,254.84),
(60,400.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,600.0,0.0,300.0,254.84),
(61,450.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,1000.0,0.0,300.0,254.84),
(62,500.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,600.0,0.0,300.0,163.09),
(63,800.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,1000.0,0.0,300.0,163.09),
(64,900.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,700.0,0.0,300.0,163.09),
(65,1400.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,1200.0,0.0,300.0,163.09),
(66,500.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,600.0,0.0,300.0,254.84),
(67,800.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,1000.0,0.0,300.0,254.84),
(68,900.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,700.0,0.0,300.0,254.84),
(69,1400.0,0.0,'Сальниковый, двухсторонний',NULL,0.0,1200.0,0.0,300.0,254.84);


-- SELECT setval('"standardcompensators_id_seq"', 69);
---------------------------------
-- standardairheaters - Стандартные
-- standardairheaters - KL_Калориферы стандартные
drop table if exists standardairheaters;

create table standardairheaters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Порядковый номер экземпляра
    name_kl varchar(50) default (NULL),       -- Тип (марка) калорифера
    s varchar(50) default (NULL),             -- Площадь поверхности нагрева
    s_vozd varchar(50) default (NULL),        -- Живое сечение по воздуху
    s_tepl varchar(50) default (NULL),        -- Живое сечение по теплоносителю
    a1 varchar(50) default (NULL),            -- Постоянная для расчета коэффициента передачи, при скорости теплоносителя <0.25 м/c
    n1 varchar(50) default (NULL),            -- Численное значение скорости для массовой скорости воздуха при скорости теплоносителя <0.25 м/c
    m1 varchar(50) default (NULL),            -- Численное значение скорости для скорости теплоносителя <0.25 м/c
    a2 varchar(50) default (NULL),            -- Постоянная для расчета коэффициента передачи, при скорости теплоносителя >0.25 м/c
    n2 varchar(50) default (NULL),            -- Численное значение скорости для массовой скорости воздуха при скорости теплоносителя >0.25 м/c
    m2 varchar(50) default (NULL)             -- Численное значение скорости для скорости теплоносителя >0.25 м/c
);

INSERT INTO "standardairheaters" ("id","name_kl","s","s_vozd","s_tepl","a1","n1","m1","a2","n2","m2") VALUES
(1,'КФС-2','9.9','0.115','0.0046','14.1','0.289','0.158','11.1','0.393','0.106'),
(2,'КФС-3','13.2','0.154','0.0061','14.1','0.289','0.158','11.1','0.393','0.106'),
(3,'КФС-4','16.7','0.195','0.0061','14.1','0.289','0.158','11.1','0.393','0.106'),
(4,'КФС-5','20.9','0.244','0.0076','14.1','0.289','0.158','11.1','0.393','0.106'),
(5,'КФС-6','25.3','0.295','0.0076','14.1','0.289','0.158','11.1','0.393','0.106'),
(6,'КФС-7','30.4','0.354','0.0092','14.1','0.289','0.158','11.1','0.393','0.106'),
(7,'КФС-9','41.6','0.486','0.0107','14.1','0.289','0.158','11.1','0.393','0.106'),
(8,'КФС-10','47.8','0.558','0.0107','14.1','0.289','0.158','11.1','0.393','0.106'),
(9,'КФС-11','54.6','0.638','0.0122','14.1','0.289','0.158','11.1','0.393','0.106'),
(10,'КВБ-2','9.9','0.115','0.0046','18.5','0.275','0.192','15.3','0.343','0.149'),
(11,'КВБ-3','13.2','0.154','0.0061','18.5','0.275','0.192','15.3','0.275','0.149'),
(12,'КВБ-4','16.7','0.195','0.0061','18.5','0.275','0.192','15.3','0.343','0.149'),
(13,'КВБ-5','20.9','0.244','0.0076','18.5','0.275','0.192','15.3','0.343','0.149'),
(14,'КВБ-6','25.3','0.295','0.0076','18.5','0.275','0.192','15.3','0.343','0.149'),
(15,'КВБ-7','30.4','0.354','0.0092','18.5','0.275','0.192','15.3','0.343','0.149'),
(16,'КВБ-9','41.6','0.486','0.0107','18.5','0.275','0.192','15.3','0.343','0.149'),
(17,'КВБ-10','47.8','0.558','0.0107','18.5','0.275','0.192','15.3','0.343','0.149'),
(18,'КВБ-11','54.6','0.638','0.0122','18.5','0.275','0.192','15.3','0.343','0.149'),
(19,'К3ПП-2','9.9','0.115','0.0046','14.1','0.289','0.158','11.1','0.393','0.106'),
(20,'К3ПП-3','13.2','0.154','0.0061','14.1','0.289','0.158','11.1','0.393','0.106'),
(21,'К3ПП-4','16.7','0.195','0.0061','14.1','0.289','0.158','11.1','0.393','0.106'),
(22,'К3ПП-5','20.9','0.244','0.0076','14.1','0.289','0.158','11.1','0.393','0.106'),
(23,'К3ПП-6','25.3','0.295','0.0076','14.1','0.289','0.158','11.1','0.393','0.106'),
(24,'К3ПП-7','30.4','0.354','0.0092','14.1','0.289','0.158','11.1','0.393','0.106'),
(25,'К3ПП-9','41.6','0.486','0.0107','14.1','0.289','0.158','11.1','0.393','0.106'),
(26,'К3ПП-10','47.8','0.558','0.0107','14.1','0.289','0.158','11.1','0.393','0.106'),
(27,'К3ПП-11','54.6','0.638','0.0122','14.1','0.289','0.158','11.1','0.393','0.106'),
(28,'К4ПП-2','12.7','0.115','0.0061','12.4','0.331','0.14','9.5','0.446','0.034'),
(29,'К4ПП-3','16.9','0.154','0.0082','12.4','0.331','0.14','9.5','0.446','0.034'),
(30,'К4ПП-4','21.4','0.195','0.0082','12.4','0.331','0.14','9.5','0.446','0.034'),
(31,'К4ПП-5','26.8','0.244','0.0102','12.4','0.331','0.14','9.5','0.446','0.0344'),
(32,'К4ПП-6','32.4','0.295','0.0102','12.4','0.331','0.14','9.5','0.446','0.034'),
(33,'К4ПП-7','38.9','0.354','0.0122','12.4','0.331','0.14','9.5','0.446','0.034'),
(34,'К4ПП-9','53.3','0.486','0.0143','12.4','0.331','0.14','9.5','0.446','0.034'),
(35,'К4ПП-10','61.2','0.558','0.0143','12.4','0.331','0.14','9.5','0.446','0.034'),
(36,'К4ПП-11','69.9','0.638','0.0163','12.4','0.331','0.14','9.5','0.446','0.334'),
(37,'КФБ-2','12.7','0.115','0.0061','12.4','0.331','0.14','9.5','0.446','0.034'),
(38,'КФБ-3','16.9','0.154','0.0082','12.4','0.331','0.14','9.5','0.446','0.034'),
(39,'КФБ-4','24.4','0.195','0.0082','12.4','0.331','0.14','9.5','0.446','0.034'),
(40,'КФБ-5','26.8','0.244','0.0102','12.4','0.331','0.14','9.5','0.446','0.0344'),
(41,'КФБ-6','32.4','0.295','0.0102','12.4','0.331','0.14','9.5','0.446','0.034'),
(42,'КФБ-7','38.9','0.354','0.0122','12.4','0.331','0.14','9.5','0.446','0.034'),
(43,'КФБ-9','53.3','0.486','0.0143','12.4','0.331','0.14','9.5','0.446','0.034'),
(44,'КФБ-10','61.2','0.558','0.0143','12.4','0.331','0.14','9.5','0.446','0.034'),
(45,'КФБ-11','69.9','0.638','0.0163','12.4','0.331','0.14','9.5','0.446','0.034'),
(46,'КФСО-2','9.77','0.0193','0.0061','19.4','0.384','0.201','14.3','0.501','0.122'),
(47,'КФСО-3','13.43','0.12','0.0084','19.4','0.384','0.201','14.3','0.501','0.122'),
(48,'КФСО-4','17.06','0.153','0.0084','19.4','0.484','0.201','14.3','0.501','0.122'),
(49,'КФСО-5','21.71','0.167','0.0107','19.4','0.384','0.201','14.3','0.501','0.122'),
(50,'КФСО-6','26.29','0.227','0.0107','19.4','0.384','0.201','14.3','0.501','0.122'),
(51,'КФСО-7','30.05','0.271','0.0122','19.4','0.384','0.201','14.3','0.501','0.122'),
(52,'КФСО-8','35.28','0.318','0.0122','19.4','0.384','0.201','14.3','0.501','0.122'),
(53,'КФСО-9','41.89','0.375','0.0145','19.4','0.384','0.201','14.3','0.501','0.122'),
(54,'КФСО-10','48.22','0.431','0.0145','19.4','0.384','0.201','14.3','0.501','0.122'),
(55,'КФСО-11','55.84','0.497','0.0168','19.4','0.384','0.201','14.3','0.501','0.122'),
(56,'КФБО-2','13.02','0.0913','0.0081','17.9','0.381','0.178','12.7','0.517','0.133'),
(57,'КФБО-3','16.28','0.112','0.011','17.9','0.381','0.178','12.7','0.517','0.133'),
(58,'КФБО-4','20.68','0.143','0.011','17.9','0.381','0.178','12.7','0.517','0.133'),
(59,'КФБО-5','26.88','0.182','0.0132','17.9','0.381','0.178','12.7','0.517','0.133'),
(60,'КФБО-6','32.55','0.222','0.0132','17.9','0.381','0.178','12.7','0.517','0.133'),
(61,'КФБО-7','40.06','0.271','0.0163','17.9','0.381','0.178','12.7','0.517','0.133'),
(62,'КФБО-8','47.04','0.318','0.0163','17.9','0.381','0.178','12.7','0.517','0.133'),
(63,'КФБО-9','55.86','0.375','0.0193','17.9','0.381','0.178','12.7','0.517','0.133'),
(64,'КФБО-10','64.29','0.431','0.0193','17.9','0.381','0.178','12.7','0.517','0.133'),
(65,'КФБО-11','71.06','0.475','0.0213','17.9','0.381','0.178','12.7','0.517','0.133'),
(66,'КМС-2','9.9','0.115','0.00114','14.1','0.289','0.158','11.1','0.393','0.106'),
(67,'КМС-3','13.2','0.154','0.00102','14.1','0.289','0.158','11.1','0.393','0.106'),
(68,'КМС-4','16.7','0.195','0.00102','14.1','0.289','0.158','11.1','0.393','0.106'),
(69,'КМС-5','20.9','0.244','0.00095','14.1','0.289','0.158','11.1','0.393','0.106'),
(70,'КМС-6','25.3','0.295','0.00095','14.1','0.289','0.158','11.1','0.393','0.106'),
(71,'КМС-7','30.4','0.354','0.00114','14.1','0.289','0.158','11.1','0.393','0.106'),
(72,'КМС-8','35.7','0.416','0.00114','14.1','0.289','0.158','11.1','0.393','0.106'),
(73,'КМС-9','41.6','0.486','0.00113','14.1','0.289','0.158','11.1','0.393','0.106'),
(74,'КМС-10','47.8','0.558','0.00113','14.1','0.289','0.158','11.1','0.393','0.106'),
(75,'КМС-11','54.6','0.638','0.00152','14.1','0.289','0.158','11.1','0.393','0.106'),
(76,'КМБ-2','12.7','0.115','0.00152','12.4','0.331','0.14','9.5','0.446','0.034'),
(77,'КМБ-3','16.9','0.154','0.00135','12.4','0.331','0.14','9.5','0.446','0.034'),
(78,'КМБ-4','21.4','0.195','0.00135','12.4','0.331','0.14','9.5','0.446','0.034'),
(79,'КМБ-5','26.8','0.244','0.00127','12.4','0.331','0.14','9.5','0.446','0.034'),
(80,'КМБ-6','32.4','0.295','0.00127','12.4','0.331','0.14','9.5','0.446','0.034'),
(81,'КМБ-7','38.9','0.354','0.00152','12.4','0.331','0.14','9.5','0.446','0.034'),
(82,'КМБ-8','45.7','0.416','0.00132','12.4','0.331','0.14','9.5','0.446','0.034'),
(83,'КМБ-9','53.3','0.485','0.00178','12.4','0.331','0.14','9.5','0.446','0.034'),
(84,'КМБ-10','61.2','0.558','0.00178','12.4','0.331','0.14','9.5','0.446','0.034'),
(85,'КМБ-11','69.9','0.638','0.00203','12.4','0.331','0.14','9.5','0.446','0.034'),
(86,'К3ВП-2','9.9','0.115','0.00076','14.1','0.289','0.158','11.1','0.393','0.106'),
(87,'К3ВП-3','13.2','0.154','0.00076','14.1','0.289','0.158','11.1','0.393','0.106'),
(88,'К3ВП-4','16.7','0.195','0.00076','14.1','0.289','0.158','11.1','0.393','0.106'),
(89,'К3ВП-5','20.9','0.244','0.00096','14.1','0.289','0.158','11.1','0.393','0.106'),
(90,'К3ВП-6','25.3','0.295','0.00096','14.1','0.289','0.158','11.1','0.393','0.106'),
(91,'К3ВП-7','30.4','0.354','0.00114','14.1','0.289','0.158','11.1','0.393','0.106'),
(92,'К3ВП-8','35.7','0.416','0.00114','14.1','0.289','0.158','11.1','0.393','0.106'),
(93,'К3ВП-9','41.6','0.486','0.00178','14.1','0.289','0.158','11.1','0.393','0.106'),
(94,'К3ВП-10','47.8','0.558','0.00178','14.1','0.289','0.158','11.1','0.393','0.106'),
(95,'К3ВП-11','54.6','0.638','0.00203','14.1','0.289','0.158','11.1','0.393','0.106'),
(96,'К4ВП-2','12.7','0.115','0.00102','12.4','0.331','0.14','9.5','0.446','0.034'),
(97,'К4ВП-3','16.9','0.154','0.00102','12.4','0.331','0.14','9.5','0.446','0.034'),
(98,'К4ВП-4','21.4','0.195','0.00102','12.4','0.331','0.14','9.5','0.446','0.034'),
(99,'К4ВП-5','26.8','0.244','0.00127','12.4','0.331','0.14','9.5','0.446','0.034'),
(100,'К4ВП-6','32.4','0.295','0.00127','12.4','0.331','0.14','9.5','0.446','0.034'),
(101,'К4ВП-7','38.9','0.354','0.00153','12.4','0.331','0.14','9.5','0.446','0.034'),
(102,'К4ВП-8','45.7','0.416','0.00153','12.4','0.331','0.14','9.5','0.446','0.034'),
(103,'К4ВП-9','53.3','0.486','0.00237','12.4','0.331','0.14','9.5','0.446','0.034'),
(104,'К4ВП-10','61.2','0.558','0.00237','12.4','0.331','0.14','9.5','0.446','0.034'),
(105,'К4ВП-11','69.9','0.638','0.00271','12.4','0.331','0.14','9.5','0.446','0.034'),
(106,'СТД3010Г-Б-5','20.4','0.272','0.001','16.3','0.382','0.149','13.2','0.371','0.081'),
(107,'СТД3010Г-Б-7','29.1','0.388','0.0012','16.3','0.382','0.149','13.2','0.371','0.081'),
(108,'СТД3010Г-Б-8','34.3','0.457','0.0016','16.3','0.382','0.149','13.2','0.371','0.081'),
(109,'СТД3010Г-Б-9','40.5','0.533','0.0019','16.3','0.382','0.149','13.2','0.371','0.081'),
(110,'СТД3010Г-Б-14','74.2','0.99','0.0024','16.3','0.382','0.149','13.2','0.371','0.081'),
(111,'КВБ-П-01-1','9.54','0.1248','0.0012','19','0.405','0.13','19','0.405','0.13'),
(112,'КВБ-П-01-2','11.8','0.1538','0.0012','19','0.405','0.13','19','0.405','0.13'),
(113,'КВБ-П-01-3','14.06','0.1827','0.0012','19','0.405','0.13','19','0.405','0.13'),
(114,'КВБ-П-01-4','16.3','0.2118','0.0012','19','0.405','0.13','19','0.405','0.13'),
(115,'КВБ-П-01-5','20.73','0.2697','0.0012','19','0.405','0.13','19','0.405','0.13'),
(116,'КВБ-П-01-6','12.73','0.166','0.0016','19','0.405','0.13','19','0.405','0.13'),
(117,'КВБ-П-01-7','15.73','0.2046','0.0016','19','0.405','0.13','19','0.405','0.13'),
(118,'КВБ-П-01-8','18.75','0.2432','0.0016','19','0.405','0.13','19','0.405','0.13'),
(119,'КВБ-П-01-9','21.74','0.2918','0.0016','19','0.405','0.13','19','0.405','0.13'),
(120,'КВБ-П-01-10','27.7','0.359','0.0016','19','0.405','0.13','19','0.405','0.13'),
(121,'КВБ-П-01-11','79.2','1.0207','0.0032','19','0.405','0.13','19','0.405','0.13'),
(122,'КВБ-П-01-12','118.2','1.5337','0.0048','19','0.405','0.13','19','0.405','0.13'),
(123,'КВМ-П-1','4.91','0.107','0.579','18','0.345','0.152','18','0.345','0.152'),
(124,'КВМ-П-2','6.06','0.132','0.579','18','0.345','0.152','18','0.345','0.152'),
(125,'КВМ-П-3','7.2','0.157','0.579','18','0.345','0.152','18','0.345','0.152'),
(126,'КВМ-П-4','8.35','0.182','0.579','18','0.345','0.152','18','0.345','0.152'),
(127,'КВМ-П-5','10.71','0.232','0.579','18','0.345','0.152','18','0.345','0.152'),
(128,'КВМ-П-6','6.54','0.142','0.772','18','0.345','0.152','18','0.345','0.152'),
(129,'КВМ-П-7','8.07','0.175','0.772','18','0.345','0.152','18','0.345','0.152'),
(130,'КВМ-П-8','9.62','0.209','0.722','18','0.345','0.152','18','0.345','0.152'),
(131,'КВМ-П-9','11.13','0.242','0.722','18','0.345','0.152','18','0.345','0.152'),
(132,'КВМ-П-10','14.3','0.309','0.722','18','0.345','0.152','18','0.345','0.152'),
(133,'КВМ-П-11','41.1','0.883','1.544','18','0.345','0.152','18','0.345','0.152'),
(134,'КВМ-П-12','61.8','1.323','2.316','18','0.345','0.152','18','0.345','0.152'),
(135,'КВС-П-1','8.55','0.105','0.869','17.94','0.32','0.132','17.94','0.32','0.132'),
(136,'КВС-П-2','10.62','0.129','0.869','17.94','0.32','0.132','17.94','0.32','0.132'),
(137,'КВС-П-3','12.7','0.154','0.869','17.94','0.32','0.132','17.94','0.32','0.132'),
(138,'КВС-П-4','14.67','0.179','0.869','17.94','0.32','0.132','17.94','0.32','0.132'),
(139,'КВС-П-5','18.81','0.288','0.869','17.94','0.32','0.132','17.94','0.32','0.132'),
(140,'КВС-П-6','11.4','0.139','1.159','17.94','0.32','0.132','17.94','0.32','0.132'),
(141,'КВС-П-7','14.16','0.172','1.159','17.94','0.32','0.132','17.94','0.32','0.132'),
(142,'КВС-П-8','16.92','0.205','1.159','17.94','0.32','0.132','17.94','0.32','0.132'),
(143,'КВС-П-9','19.56','0.238','0.722','17.94','0.32','0.132','17.94','0.32','0.132'),
(144,'КВС-П-10','25.08','0.303','1.159','17.94','0.32','0.132','17.94','0.32','0.132'),
(145,'КВС-П-11','72','0.867','2.31','17.94','0.32','0.132','17.94','0.32','0.132'),
(146,'КВС-П-12','108','1.299','3.474','17.94','0.32','0.132','17.94','0.32','0.132'),
(147,'КВБ-П-1','11.38','0.105','1.159','17','0.32','0.13','17','0.32','0.13'),
(148,'КВБ-П-2','14.21','0.129','1.159','17','0.32','0.13','17','0.32','0.13'),
(149,'КВБ-П-3','16.86','0.154','1.159','17','0.32','0.13','17','0.32','0.13'),
(150,'КВБ-П-4','19.48','0.179','1.159','17','0.32','0.13','17','0.32','0.13'),
(151,'КВБ-П-5','25','0.228','1.159','17','0.32','0.13','17','0.32','0.13'),
(152,'КВБ-П-6','15.14','0.139','1.544','17','0.32','0.13','17','0.32','0.13'),
(153,'КВБ-П-7','18.81','0.179','1.544','17','0.32','0.13','17','0.32','0.13'),
(154,'КВБ-П-8','22.44','0.205','1.544','17','0.32','0.13','17','0.32','0.13'),
(155,'КВБ-П-9','26','0.235','1.544','17','0.32','0.13','17','0.32','0.13'),
(156,'КВБ-П-10','33.34','0.303','1.544','17','0.32','0.13','17','0.32','0.13'),
(157,'КВБ-П-11','95.63','0.867','3.089','17','0.32','0.13','17','0.32','0.13'),
(158,'КВБ-П-12','143.5','1.299','4.632','17','0.32','0.13','17','0.32','0.13'),
(159,'КСк3-6','10.85','0.111','0.00085','19.27','0.482','0.145','19.27','0.482','0.145'),
(160,'КСк3-7','13.37','0.137','0.00085','19.27','0.482','0.145','19.27','0.482','0.145'),
(161,'КСк3-8','15.89','0.163','0.00085','19.27','0.482','0.145','19.27','0.482','0.145'),
(162,'КСк3-9','18.41','0.189','0.00085','19.27','0.482','0.145','19.27','0.482','0.145'),
(163,'КСк3-10','23.45','0.24','0.00085','19.27','0.482','0.145','19.27','0.482','0.145'),
(164,'КСк3-11','68.01','0.685','0.00129','19.27','0.482','0.145','19.27','0.482','0.145'),
(165,'КСк3-12','102.5','1.027','0.00194','19.27','0.482','0.145','19.27','0.482','0.145'),
(166,'КСк4-6','14.26','0.111','0.00111','16.78','0.546','0.176','16.78','0.546','0.176'),
(167,'КСк4-7','17.57','0.137','0.00111','16.78','0.546','0.176','16.78','0.546','0.176'),
(168,'КСк4-8','20.88','0.163','0.0011','16.78','0.546','0.176','16.78','0.546','0.176'),
(169,'КСк4-9','24.19','0.189','0.0011','16.78','0.546','0.176','16.78','0.546','0.176'),
(170,'КСк4-10','30.82','0.24','0.0011','16.78','0.546','0.176','16.78','0.546','0.176'),
(171,'КСк4-11','90.04','0.685','0.00171','16.78','0.546','0.176','16.78','0.546','0.176'),
(172,'КСк4-12','130','1.027','0.00258','16.78','0.546','0.176','16.78','0.546','0.176'),
(173,'Кд1017К','13.57','0.353','0.00051','11.5','0.5','0.15','11.5','0.5','0.15'),
(174,'Кд1018К','27.14','0.353','0.00102','11.5','0.5','0.15','11.5','0.5','0.15'),
(175,'Кд1019К','40.71','0.353','0.00152','11.5','0.5','0.15','11.5','0.5','0.15'),
(176,'Кд2017К','26.85','0.698','0.00102','11.5','0.5','0.15','11.5','0.5','0.15'),
(177,'Кд2018К','53.7','0.698','0.00204','11.5','0.5','0.15','11.5','0.5','0.15'),
(178,'Кд2019К','80.56','0.698','0.00306','11.5','0.5','0.15','11.5','0.5','0.15'),
(179,'Кд4017К','47.6','1.183','0.00127','11.5','0.5','0.15','11.5','0.5','0.15'),
(180,'Кд4017К','47.6','1.183','0.00152','11.5','0.5','0.15','11.5','0.5','0.15'),
(181,'Кд4018К','95.2','1.183','0.00254','11.5','0.5','0.15','11.5','0.5','0.15'),
(182,'Кд4018К','95.2','1.183','0.00304','11.5','0.5','0.15','11.5','0.5','0.15'),
(183,'Кд4019К','142.7','1.183','0.00381','11.5','0.5','0.15','11.5','0.5','0.15'),
(184,'Кд4019К','142.7','1.183','0.00456','11.5','0.5','0.15','11.5','0.5','0.15'),
(185,'Кд6017К','86.92','2.194','0.00178','11.5','0.5','0.15','11.5','0.5','0.15'),
(186,'Кд6017К','86.92','2.194','0.00203','11.5','0.5','0.15','11.5','0.5','0.15'),
(187,'Кд6017К','86.92','2.194','0.00229','11.5','0.5','0.15','11.5','0.5','0.15'),
(188,'Кд6018К','173.8','2.194','0.00356','11.5','0.5','0.15','11.5','0.5','0.15'),
(189,'Кд6018К','173.8','2.194','0.00406','11.5','0.5','0.15','11.5','0.5','0.15'),
(190,'Кд6018К','173.8','2.194','0.00458','11.5','0.5','0.15','11.5','0.5','0.15'),
(191,'Кд6019К','260.7','2.194','0.00534','11.5','0.5','0.15','11.5','0.5','0.15'),
(192,'Кд6019К','260.7','2.194','0.0061','11.5','0.5','0.15','11.5','0.5','0.15'),
(193,'Кд6019К','260.7','2.194','0.00687','11.5','0.5','0.15','11.5','0.5','0.15'),
(194,'Кд8017К','89.56','2.26','0.00178','11.5','0.5','0.15','11.5','0.5','0.15'),
(195,'Кд8018К','179.1','2.26','0.00356','11.5','0.5','0.15','11.5','0.5','0.15'),
(196,'Кд8019К','268.7','2.26','0.00534','11.5','0.5','0.15','11.5','0.5','0.15'),
(197,'Кд12017К','140.7','3.55','0.00127','11.5','0.5','0.15','11.5','0.5','0.15'),
(198,'Кд12017К','140.7','3.55','0.00152','11.5','0.5','0.15','11.5','0.5','0.15'),
(199,'Кд12018К','281.4','3.55','0.00254','11.5','0.5','0.15','11.5','0.5','0.15'),
(200,'Кд12018К','281.4','3.55','0.00304','11.5','0.5','0.15','11.5','0.5','0.15'),
(201,'Кд12019К','122.2','3.55','0.00381','11.5','0.5','0.15','11.5','0.5','0.15'),
(202,'Кд12019К','122.2','3.55','0.00456','11.5','0.5','0.15','11.5','0.5','0.15'),
(203,'Кд16020','267.1','6.75','0.00127','11.5','0.5','0.15','11.5','0.5','0.15'),
(204,'Кд16020','267.1','6.75','0.00152','11.5','0.5','0.15','11.5','0.5','0.15'),
(205,'Кд16024','534.3','6.75','0.00254','11.5','0.5','0.15','11.5','0.5','0.15'),
(206,'Кд16024','534.3','6.75','0.00304','11.5','0.5','0.15','11.5','0.5','0.15'),
(207,'Кд20023','335.4','8.5','0.00127','11.5','0.5','0.15','11.5','0.5','0.15'),
(208,'Кд20023','335.4','8.5','0.00152','11.5','0.5','0.15','11.5','0.5','0.15'),
(209,'Кд20023','335.4','8.5','0.00178','11.5','0.5','0.15','11.5','0.5','0.15'),
(210,'Кд20024','670.7','8.5','0.00254','11.5','0.5','0.15','11.5','0.5','0.15'),
(211,'Кд20024','670.7','8.5','0.00304','11.5','0.5','0.15','11.5','0.5','0.15'),
(212,'Кд20024','670.7','8.5','0.00356','11.5','0.5','0.15','11.5','0.5','0.15'),
(213,'Кд24023','400.3','10.3','0.00127','11.5','0.5','0.15','11.5','0.5','0.15'),
(214,'Кд24023','400.3','10.3','0.00152','11.5','0.5','0.15','11.5','0.5','0.15'),
(215,'Кд24023','400.3','10.3','0.00178','11.5','0.5','0.15','11.5','0.5','0.15');


-- SELECT setval('"standardairheaters_id_seq"', 215);
---------------------------------
-- standardmanometers - Стандартные
-- standardmanometers - MN_Манометр стандартный
drop table if exists standardmanometers;

create table standardmanometers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер по порядку
    name varchar(50) default (NULL),          -- Наименование
    name_mt varchar(50) default (NULL),       -- Тип, модель (копировать)
    typ_mt varchar(50) default (NULL),        -- ГОСТ
    usl varchar(50) default (NULL),           -- Технические условия
    producer varchar(50) default (NULL),      -- Изготовитель
    toch float default ((0)),                 -- Класс точности
    p_nome float default ((0)),               -- Начальное значение шкалы манометра
    p_end float default ((0)),                -- Конечное значение шкалы манометра
    zena float default ((0)),                 -- Цена деления
    p_max float default ((0)),                -- Давление рабочее максимальное, м.вод.ст.
    t_nome float default ((0)),               -- Нижний предел температуры окружающей среды
    t_end float default ((0)),                -- Верхний предел температуры окружающей среды
    diapz_signl varchar(50) default (NULL),   -- Диапазон выходного сигнала манометра, мА
    diametr varchar(50) default (NULL)        -- Диаметр корпуса или габариты, мм
);

INSERT INTO "standardmanometers" ("id","name","name_mt","typ_mt","usl","producer","toch","p_nome","p_end","zena","p_max","t_nome","t_end","diapz_signl","diametr") VALUES
(1,'Манометр трубчатый показывающий','МТП-100/1-ВУМ',NULL,NULL,NULL,2.5,0.0,100.0,NULL,NULL,10.0,35.0,NULL,NULL),
(2,'Манометр самопишущий','МТС-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(3,'Манометр самопишущий','МТС-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(4,'Манометр показывающий','МТП-160',NULL,NULL,NULL,1.5,0.0,250.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(5,'Манометр самопишущий','МТС-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(6,'Манометр самопишущий','МТС-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(7,'Манометр самопишущий','МЭД 22364','7919-80',NULL,'Московский з-д',1.0,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(8,'Манометр самопишущий','МЭД 22364','7919-80',NULL,'Московский з-д',1.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(9,'Манометр электрический пружинный','МПЭ','7919-80',NULL,'Казанский з-д "Теплоконтроль"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(10,'Манометр электрический бесшкальный','МЭД 22365','7919-80',NULL,'Московский з-д "МАНОМЕТР"',1.0,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(11,'Манометр электрический бесшкальный','МЭД 22365','7919-80',NULL,'Московский з-д "МАНОМЕТР"',1.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(12,'Манометр электрический бесшкальный','МЭД 22365','7919-80',NULL,'Московский з-д "МАНОМЕТР"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(13,'Манометр электрический бесшкальный','МЭД 22365','7919-80',NULL,'Московский з-д "МАНОМЕТР"',1.5,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(14,'Манометр электрический бесшкальный','МЭД 22365','7919-80',NULL,'Московский з-д "МАНОМЕТР"',1.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(15,'Манометр электрический бесшкальный','МЭД 22365','7919-80',NULL,'Московский з-д "МАНОМЕТР"',1.5,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(16,'Манометр пружинный показывающий','ЭКМ-IV','7919-80',NULL,'Томский манометровый з-д',1.5,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(17,'Манометр пружинный показывающий','ЭКМ-IV','7919-80',NULL,'Томский манометровый з-д',1.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(18,'Манометр пружинный показывающий','ЭКМ-IV','7919-80',NULL,'Томский манометровый з-д',1.5,0.0,600.0,NULL,NULL,NULL,NULL,NULL,NULL),
(19,'Манометр электрический бесшкальный','МЭД 22364',NULL,NULL,'Московский з-д "МАНОМЕТР"',1.0,10.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(20,'Манометр электрический бесшкальный','МЭД 22364',NULL,NULL,'Московский з-д "МАНОМЕТР"',1.5,10.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(21,'Манометр электрический бесшкальный','МЭД 22365',NULL,NULL,'Московский з-д "МАНОМЕТР"',1.0,250.0,16000.0,NULL,NULL,NULL,NULL,NULL,NULL),
(22,'Манометр электрический бесшкальный','МЭД 22365',NULL,NULL,'Московский з-д "МАНОМЕТР"',1.5,250.0,16000.0,NULL,NULL,NULL,NULL,NULL,NULL),
(23,'Манометр электрический бесшкальный','МЭД 22364',NULL,NULL,'Московский з-д "МАНОМЕТР"',1.0,6.0,150.0,NULL,NULL,NULL,NULL,NULL,NULL),
(24,'Манометр электрический бесшкальный','МЭД 22364',NULL,NULL,'Московский з-д "МАНОМЕТР"',1.5,6.0,150.0,NULL,NULL,NULL,NULL,NULL,NULL),
(25,'Манометр пружинный электрический','МПЭ',NULL,NULL,'Казанский з-д "Тепроконтроль"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(26,'Манометр показывающий','ДМ 100-1',NULL,'25-7310,0050-87','Чистопольский часовой з-д',1.5,0.0,160.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(27,'Манометр пружинный электрический','МО-11202',NULL,NULL,'Московский з-д "МАНОМЕТР"',0.4,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(28,'Манометр образцовый показывающий','МО-11202',NULL,NULL,'Московский з-д "МАНОМЕТР"',0.4,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(29,'Манометр общего назначения показывающий','МП-5',NULL,NULL,'Томский манометровый з-д',1.5,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(30,'Манометр образцовый показывающий','МО-11202',NULL,NULL,'Московский з-д "МАНОМЕТР"',0.4,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(31,'Манометр образцовый показывающий','МО-11202',NULL,NULL,'Московский з-д "МАНОМЕТР"',0.4,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(32,'Манометр общего назначения показывающий','ОБМ1-160',NULL,NULL,'Томский манометровый з-д',1.5,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(33,'Манометр показывающий','МП-5',NULL,NULL,'Томский манометровый з-д',1.5,0.0,60.0,NULL,NULL,NULL,NULL,NULL,NULL),
(34,'Манометр показывающий','МП-5',NULL,NULL,'Томский манометровый з-д',1.5,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(35,'Манометр образцовый показывающий','М0-11202','7919-80',NULL,'Московский з-д "МАНОМЕТР"',0.4,0.0,600.0,NULL,NULL,NULL,NULL,NULL,NULL),
(36,'Манометр показывающий','ОБМ1-100',NULL,NULL,'Томский манометровый з-д',2.5,0.0,400.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(37,'Манометр показывающий','ОБМ1-160',NULL,NULL,'Томский манометровый з-д',1.5,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(38,'Манометр показывающий','ОБМ1-160',NULL,NULL,'Томский манометровый з-д',1.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(39,'Манометр показывающий','ОБМ1-160','2405-72',NULL,'Томский манометровый з-д',1.5,0.0,250.0,0.05,NULL,NULL,NULL,NULL,NULL),
(40,'Манометр показывающий','ОБМ1-100',NULL,NULL,'Томский манометровый з-д',2.5,0.0,100.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(41,'Манометр показывающий','ОБМ1-100',NULL,NULL,'Томский манометровый з-д',2.5,0.0,250.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(42,'Манометр мембранный электрический','ММЭ',NULL,NULL,'Казанский з-д "Теплоконтроль"',1.0,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(43,'Манометр мембранный электрический','ММЭ',NULL,NULL,'Казанский з-д "Теплоконтроль"',1.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(44,'Манометр мембранный электрический','ММЭ',NULL,NULL,'Казанский з-д "Теплоконтроль"',1.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(45,'Манометр показывающий','МП-VI',NULL,NULL,'Томский манометровый з-д',1.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(46,'Манометр показывающий','МП4-VI',NULL,NULL,'Томский манометровый з-д',1.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(47,'Манометр показывающий','МП4-VI',NULL,NULL,'Томский манометровый з-д',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(48,'Манометр показывающий','МП4-VI',NULL,NULL,'Томский манометровый з-д',1.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(49,'Манометр показывающий','МП4-VI',NULL,NULL,'Томский манометровый з-д',1.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(50,'Манометр показывающий','МП4-VI',NULL,NULL,'Томский манометровый з-д',1.5,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(51,'Манометр самопишущий','МТ2С-711 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(52,'Манометр самопишущий','МТ2С-711 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(53,'Манометр самопишущий','МТ2С-711 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(54,'Манометр самопишущий','МТ2С-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(55,'Манометр самопишущий','МТ2С-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(56,'Манометр самопишущий','МТ2С-712 УХЛ4',NULL,'25-02,101962-79','Казанский з-д "Теплоконтроль"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(57,'Манометр показывающий','МТП-160','2405-80',NULL,NULL,1.5,0.0,250.0,0.2,160.0,NULL,NULL,NULL,NULL),
(58,'Манометр показывающий','М1Д-1',NULL,NULL,NULL,2.5,16.0,2500.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(59,'Манометр показывающий','МП3',NULL,NULL,NULL,1.5,0.0,160.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(60,'Манометр показывающий','М1Д-13',NULL,NULL,NULL,2.5,16.0,2500.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(61,'Манометр показывающий','МП3',NULL,NULL,NULL,1.5,0.0,250.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(62,'Манометр показывающий','ЭКМВ-1У',NULL,NULL,NULL,1.5,-10.0,16000.0,NULL,NULL,NULL,60.0,NULL,NULL),
(63,'Манометр показывающий электрический','МПЭ-МИ',NULL,NULL,'Казанский з-д "Теплоконтроль"',1.5,0.0,600.0,NULL,NULL,NULL,NULL,NULL,NULL),
(64,'Манометр пружинный электрический','МПЭ-МИ',NULL,NULL,'Казанский з-д "Теплоконтроль"',1.5,0.0,600.0,NULL,NULL,NULL,NULL,NULL,NULL),
(65,'Манометр показывающий','ДМ 100-1',NULL,'25-7310,0050-87','Чистопольский часовой з-д',1.5,0.0,250.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(66,'Манометр показывающий','МТП-1',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(67,'Манометр показывающий','МТП-1',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(68,'Манометр показывающий','МТП-2',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,1600.0,NULL,NULL,NULL,NULL,NULL,NULL),
(69,'Манометр показывающий','МТП-2',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(70,'Манометр показывающий','МТП-3',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(71,'Манометр показывающий','МТП-3',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(72,'Манометр показывающий','МТП-4',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',2.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(73,'Манометр показывающий','МТП-4',NULL,'25-02,101293-83','Казанский з-д  "Теплоконтроль"',2.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(74,'Манометр самопишущий','МТ-711Р УХЛ4,2',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',1.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(75,'Манометр самопишущий','МТ-711Р УХЛ4,2',NULL,'25-02,101293-83','Казанский з-д "Теплоконтроль"',1.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(76,'Манометр самопишущий','МТ-712Р УХЛ4,2',NULL,'25-02,101293-77','Казанский з-д "Теплоконтроль"',1.5,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(77,'Манометр самопишущий','МТ-712Р УХЛ4,2',NULL,'25-02,101293-77','Казанский з-д "Теплоконтроль"',1.5,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(78,'Манометр дифференциальный','МДФ1-100',NULL,'25-02,ЭД1,25-76','Томский манометровый з-д',0.0,0.0,100.0,NULL,NULL,NULL,NULL,NULL,NULL),
(79,'Манометр показывающий','МП4-У',NULL,'25-02,180335-84','Томский манометровый з-д',0.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(80,'Манометр показывающий','МП4-У',NULL,'25-02,180335-84','Томский манометровый з-д',0.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(81,'Манометр показывающий','МП4-У',NULL,'25-02,180335-84','Томский манометровый з-д',0.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(82,'Манометр показывающий','М-3ВУ',NULL,'25-7310,041-86','Томский манометровый з-д',0.0,0.0,160.0,NULL,NULL,NULL,NULL,NULL,NULL),
(83,'Манометр показывающий','М-3ВУ',NULL,'25-7310,041-86','Томский манометровый з-д',0.0,0.0,250.0,NULL,NULL,NULL,NULL,NULL,NULL),
(84,'Манометр показывающий','М-3ВУ',NULL,'25-7310,041-86','Томский манометровый з-д',0.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(85,'Манометр показывающий','МТП-100',NULL,'25-02,181071-78',NULL,2.5,6.0,16000.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(86,'Манометр показывающий','ВПТ-160',NULL,NULL,NULL,1.5,-1.0,16000.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(87,'Манометр показывающий','МВПТ-160',NULL,NULL,NULL,1.5,-1.0,1600.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(88,'Манометр показывающий','ЭКМ-1У','13717-74',NULL,NULL,1.5,0.0,250.0,0.2,250.0,NULL,60.0,NULL,NULL),
(89,'Манометр показывающий','ЭКВ-1У',NULL,NULL,NULL,1.5,-10.0,1600.0,NULL,NULL,NULL,60.0,NULL,NULL),
(90,'Манометр показывающий','ЭКМ-2У',NULL,NULL,NULL,1.5,-10.0,1600.0,NULL,NULL,NULL,60.0,NULL,NULL),
(91,'Манометр общего назначения показывающий','ОБМ1-100',NULL,NULL,'Томский манометровый з-д',2.5,0.0,100.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(92,'Манометр общего назначения показывающий','ОБМ1-100Б',NULL,NULL,NULL,2.5,0.0,160.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(93,'Манометр показывающий','МОШ1-100',NULL,NULL,NULL,2.5,160.0,600.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(94,'Манометр показывающий','ОБВ1-100',NULL,NULL,NULL,2.5,0.0,NULL,NULL,NULL,-50.0,60.0,NULL,NULL),
(95,'Манометр показывающий','ОБВ1-100Б',NULL,NULL,NULL,2.5,0.0,NULL,NULL,NULL,-50.0,60.0,NULL,NULL),
(96,'Манометр показывающий','МВОШ1-100',NULL,NULL,NULL,2.5,0.0,240.0,NULL,NULL,-50.0,60.0,NULL,NULL),
(97,'Манометр пружинный электрический','МПЭ',NULL,NULL,'Казанский з-д "Теплоконтроль"',1.0,0.0,400.0,NULL,NULL,NULL,NULL,NULL,NULL),
(98,'Манометр пружинный электрический','МПЭ-МИ',NULL,NULL,NULL,1.5,0.0,NULL,NULL,NULL,5.0,60.0,'0-5',NULL),
(99,'Манометр показывющий','ЭКМ-1У','13717-74',NULL,NULL,1.5,0.0,100.0,0.2,NULL,NULL,NULL,NULL,'160'),
(100,'Манометр показывющий','ЭКМ-1У',NULL,NULL,NULL,1.5,0.0,160.0,0.2,160.0,NULL,NULL,NULL,NULL),
(101,'Манометр показывющий','ЭКМ-1У','13717-84',NULL,NULL,1.5,0.0,250.0,0.2,250.0,NULL,NULL,NULL,NULL),
(102,'Манометр показывющий','ЭКМ-1У','13717-68',NULL,NULL,1.5,0.0,250.0,0.2,250.0,NULL,NULL,NULL,'160'),
(103,'Манометр показывющий','МТП-160','2405-72',NULL,NULL,1.5,0.0,100.0,0.2,250.0,NULL,NULL,NULL,'160'),
(104,'Манометр показывющий',NULL,NULL,NULL,NULL,1.5,0.0,160.0,0.2,250.0,NULL,NULL,NULL,NULL),
(105,'Манометр показывющий','ОБМ1-160','8685-65',NULL,NULL,1.5,0.0,100.0,0.2,250.0,NULL,NULL,NULL,NULL),
(106,'Манометр показывющий','МП4-У','2405-80',NULL,NULL,1.5,0.0,100.0,1.5,250.0,NULL,NULL,NULL,'160'),
(107,'Манометр показывющий','МТП-100','2405-80',NULL,NULL,2.5,0.0,10.0,0.02,160.0,NULL,NULL,NULL,NULL),
(108,'Манометр показывющий','МТП-160','2405-72',NULL,NULL,1.5,0.0,160.0,0.2,160.0,NULL,NULL,NULL,NULL),
(109,'Манометр показывющий','МТП-100','2405-80',NULL,NULL,2.5,0.0,100.0,0.2,160.0,NULL,NULL,NULL,NULL),
(110,'Манометр показывющий','ОБМ1-100','2405-72',NULL,NULL,2.5,0.0,160.0,2.5,160.0,NULL,NULL,NULL,NULL),
(111,'Манометр показывющий','ОБМ1-100','2405-80',NULL,NULL,2.5,0.0,100.0,2.5,160.0,NULL,NULL,NULL,NULL),
(112,'Манометр показывющий','МТП-100','2405-80',NULL,NULL,2.5,0.0,10.0,0.02,160.0,NULL,NULL,NULL,NULL),
(113,'Манометр показывющий','ЭКМ-1У','13717-74',NULL,NULL,1.5,0.0,250.0,0.5,160.0,NULL,NULL,NULL,NULL),
(114,'Манометр показывющий',NULL,NULL,NULL,NULL,NULL,0.0,250.0,0.5,160.0,NULL,NULL,NULL,NULL),
(115,'Манометр показывющий','МТП-160','2405-80',NULL,NULL,1.5,0.0,10.0,0.02,160.0,NULL,NULL,NULL,NULL),
(116,'Манометр показывющий','ЭКМ-1У','13717-84',NULL,NULL,1.5,0.0,160.0,0.2,160.0,NULL,NULL,NULL,NULL),
(117,'Манометр показывющий','МТП-160а','2405-80',NULL,NULL,1.5,0.0,250.0,0.5,160.0,NULL,NULL,NULL,NULL),
(118,'Манометр показывющий','МТП-160','2405-80',NULL,NULL,1.5,0.0,250.0,0.5,160.0,NULL,NULL,NULL,NULL),
(119,'Манометр показывющий','ОБМ1-100','2405-72',NULL,NULL,1.5,0.0,60.0,0.1,160.0,NULL,NULL,NULL,NULL),
(120,'Манометр показывющий','ЭКМ-1У','13717-74',NULL,NULL,1.5,0.0,160.0,0.2,160.0,NULL,NULL,NULL,NULL),
(121,'Манометр показывющий','ОБМ1-160','2405-80',NULL,NULL,1.5,0.0,100.0,0.2,160.0,NULL,NULL,NULL,NULL),
(122,'Манометр показывющий','ОБМ1-160б','2405-72',NULL,NULL,1.5,0.0,100.0,0.2,160.0,NULL,NULL,NULL,NULL),
(123,'Манометр показывющий','МП4-У',NULL,NULL,NULL,1.5,0.0,100.0,0.2,160.0,NULL,NULL,NULL,NULL),
(124,'Манометр показывющий','ЭКМ-1У','13717-68',NULL,NULL,1.5,0.0,100.0,0.2,160.0,NULL,NULL,NULL,NULL),
(125,'Манометр показывющий','ОБМ1-160','2405-72',NULL,NULL,1.5,0.0,20.0,0.05,160.0,NULL,NULL,NULL,NULL),
(126,'Манометр показывющий','МП3-У','2405-80',NULL,NULL,1.5,0.0,250.0,0.5,160.0,NULL,NULL,NULL,NULL),
(127,'Манометр показывющий','МТП-100','2405-80',NULL,NULL,2.5,0.0,10.0,0.02,160.0,NULL,NULL,NULL,NULL),
(128,'Манометр показывющий','ОБМ1-100','2405-80',NULL,NULL,2.5,0.0,160.0,0.4,160.0,NULL,NULL,NULL,NULL),
(129,'Манометр показывющий','МТП-160','2405-75',NULL,NULL,1.5,0.0,60.0,0.1,160.0,NULL,NULL,NULL,NULL);


-- SELECT setval('"standardmanometers_id_seq"', 129);
---------------------------------
-- standardplateheatexchangers - Стандартные
-- standardplateheatexchangers - PL_Теплообменники пластинчатые стандартные
drop table if exists standardplateheatexchangers;

create table standardplateheatexchangers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра пластичатого подогревателя
    name_pl varchar(50) default (NULL),       -- ГОСТ
    razmer_pl varchar(50) default (NULL),     -- Габариты (длинаХширинаХтолщина), мм
    tip_pl varchar(50) default (NULL),        -- Тип пластины
    p_pl float default ((0)),                 -- Поверхность теплообмена одной пластины, м^2
    ves float default ((0)),                  -- Вес
    d_pl float default ((0)),                 -- Эквивалентный диаметр канала, м
    s_pl float default ((0)),                 -- Площадь поперечного сечения канала, м^2
    p float default ((0)),                    -- Смачиваемый периметр в поперечном сечении канала, м
    kal float default ((0)),                  -- Ширина канала, мм
    s_kal float default ((0)),                -- Зазор для прохода рабочей среды в канале,мм
    l_pl float default ((0)),                 -- Приведенная длина канала, м
    s_kol float default ((0)),                -- Площадь поперечного сечения коллектора (угловое отверстие на пластине), м^2
    ds_pl float default ((0)),                -- Наибольший диаметр условного прохода присоединительного штуцера, м
    r varchar(50) default (NULL),             -- Коэффициент общего гидравлического сопротивления
    r_stuz float default ((0)),               -- Коэффициент гидравлического сопротивления штуцера
    dd_pl float default ((0)),                -- Толщина стенки канала, м
    lamda_pl float default ((0)),             -- Телопроводность стенки канала
    A_pl float default ((0)),                 -- Коэффициент А, зависщий от типа пластины, СП 41-101-95, Проектирование тепловых пунктов
    B_pl float default ((0))                  -- Коэффициент В, зависщий от типа пластины
);

INSERT INTO "standardplateheatexchangers" ("id","name_pl","razmer_pl","tip_pl","p_pl","ves","d_pl","s_pl","p","kal","s_kal","l_pl","s_kol","ds_pl","r","r_stuz","dd_pl","lamda_pl","a_pl","b_pl") VALUES
(1,'ГОСТ 15518','1370Х300Х1','0,3р',0.3,3.2,0.008,0.0011,0.66,150.0,4.0,1.12,0.0045,65.0,'19.3/RE**0.25',1.5,0.001,50.0,0.368,4.5),
(2,'ГОСТ 15518','1375Х600Х1','0,6р',0.6,5.8,0.0083,0.00245,1.188,545.0,4.5,1.01,0.0243,200.0,'15/RE**0.25',1.5,0.001,50.0,0.492,3.0),
(3,'ГОСТ 15518','1380Х650Х1','0,5Пр',0.5,6.0,0.009,0.00285,1.27,570.0,5.0,0.8,0.0283,200.0,'15/RE**0.25',1.5,0.001,50.0,0.492,3.0);


-- SELECT setval('"standardplateheatexchangers_id_seq"', 3);
---------------------------------
-- standardtempregulators - Стандартные
-- standardtempregulators - PT_Регулятор температуры стандартные
drop table if exists standardtempregulators;

create table standardtempregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра
    structure varchar,                        -- Структурированное описаниес регулятора расхода
    name_pt varchar(50) default (NULL),       -- Обозначение регулятора
    producer varchar(50) default (NULL),      -- Изготовитель
    Ro float default ((0)),                   -- Сопротивление термопреобразователя при температуре 0 Град.С (Ro)
    W100 float default ((0)),                 -- Отношение сопротивления термопреобразователя при температуре 100 Град.С к его сопротивлению при 0 Град.С (W100)
    U varchar(50) default (NULL),             -- Номинальное напряжение питания
    dU varchar(50) default (NULL),            -- Допустимое отклонение напряжения питания
    N varchar(50) default (NULL),             -- Потребляемая мощность
    t1_t2 varchar(50) default (NULL),         -- Диапазон контроля температуры
    dt varchar(50) default (NULL),            -- Разрешающая способность
    st varchar(50) default (NULL),            -- Предел допустимой основной приведенной погрешности контроля температуры
    tip_t varchar(50) default (NULL),         -- Тип входных термопреобразователей
    kan int default (NULL),                   -- Количество каналов контроля температуры
    v varchar(50) default (NULL),             -- Время цикла опроса датчиков
    ispol varchar(150) default (NULL),        -- Управляемые прибором исполнительные механизмы
    s_ispol varchar(50) default (NULL),       -- Способ управления исполнительными механизмами
    Imax varchar(50) default (NULL),          -- Максимальный ток, коммутируемый контактами реле
    PK varchar(50) default (NULL),            -- Интерфейс связи с компьютером
    L varchar(50) default (NULL),             -- Длина связи прибора с адаптером сети АС2
    M varchar(50) default (NULL)              -- Масса прибора
);

INSERT INTO "standardtempregulators" ("id","structure","name_pt","producer","ro","w100","u","du","n","t1_t2","dt","st","tip_t","kan","v","ispol","s_ispol","imax","pk","l","m") VALUES
(1,NULL,'ТРМ32-Щ.01','ОВЕН',50.0,1.426,'220 В 50 Гц','-15…+10%','не более 6 ВА','-50…+1999.9','0.1','+- 0.5','ТСМ, ТСП',4,'не более 6','запорно-регулирующие клапаны контура отопления и ГВС','контакты э/м реле','1 А при напряжении 220 В 59 Гц (соs >0.4)','RS-232','не более 1000','не более 1.2'),
(2,NULL,'ТРМ32-Щ4.03','ОВЕН',100.0,1.426,'220 В 50 Гц','-15…+10%','не более 6 ВА','-50…+1999.9','0.1','+- 0.5','ТСМ, ТСП',4,'не более 6','запорно-регулирующие клапаны контура отопления и ГВС','контакты э/м реле','1 А при напряжении 220 В 59 Гц (соs >0.4)','RS-232','не более 1000','не более 1.2');


-- SELECT setval('"standardtempregulators_id_seq"', 2);
---------------------------------
-- standardconsregulators - Стандартные
-- standardconsregulators - RC_Регуляторы расхода стандартные
drop table if exists standardconsregulators;

create table standardconsregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра
    name_rr varchar(50) default (NULL),       -- Наименование регулятора (копировать)
    dp_max float default ((0)),               -- Значение перепада давления верхнее
    dp_min float default ((0)),               -- Значение перепада давления нихнее
    producer varchar(50) default (NULL),      -- Изготовитель
    p varchar(50) default (NULL),             -- Давление условное
    tyip_rr varchar(50) default (NULL),       -- Наименование регулятора по ГОСТу
    d float default ((0)),                    -- Диаметр условный, мм
    typ_drive varchar(50) default (NULL),     -- Тип привода
    typ_valve varchar(50) default (NULL),     -- Тип импульсного клапана
    d_valve varchar(50) default (NULL),       -- Диаметр импульсного клапана
    kv float default ((0)),                   -- Пропускная способность, условная (копировать)
    otn_kv float default ((0))                -- Негерметичность затвора максимальная, % (копировать)
);

INSERT INTO "standardconsregulators" ("id","name_rr","dp_max","dp_min","producer","p","tyip_rr","d","typ_drive","typ_valve","d_valve","kv","otn_kv") VALUES
(1,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',600.0,'гидравлический',NULL,NULL,3600.0,0.0),
(2,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',150.0,'гидравлический',NULL,NULL,250.0,0.0),
(3,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-124',400.0,'гидравлический','ИК-25','25',1600.0,0.0),
(4,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',250.0,'гидравлический',NULL,NULL,600.0,0.0),
(5,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',300.0,'гидравлический',NULL,NULL,900.0,0.0),
(6,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',200.0,'гидравлический',NULL,NULL,400.0,0.0),
(7,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',500.0,'гидравлический','ИК-25','25',2500.0,0.0),
(8,'Регулятор расхода системы ОРГРЭС',NULL,NULL,'Полтавский турбомеханический з-д',NULL,'РК-1',700.0,'гидравлический',NULL,NULL,NULL,NULL);


-- SELECT setval('"standardconsregulators_id_seq"', 8);
---------------------------------
-- standardflowmeters - Стандартные
-- standardflowmeters - RD_Расходомер стандартный
drop table if exists standardflowmeters;

create table standardflowmeters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер по порядку
    name varchar(50) default (NULL),          -- Наименование
    name_mt varchar(50) default (NULL),       -- Тип, модель (копировать)
    typ_mt varchar(50) default (NULL),        -- ГОСТ
    usl varchar(50) default (NULL),           -- Технические условия
    producer varchar(50) default (NULL),      -- Изготовитель
    toch float default ((0)),                 -- Класс точности
    p_nome float default ((0)),               -- Начальное значение шкалы манометра
    p_end float default ((0)),                -- Конечное значение шкалы манометра
    zena float default ((0)),                 -- Цена деления
    p_max float default ((0)),                -- Давление рабочее максимальное, м.вод.ст.
    t_nome float default ((0)),               -- Верхний предел температуры окружающей среды
    t_end float default ((0)),                -- Нижний предел температуры окружающей среды
    diapz_signl varchar(50) default (NULL),   -- Диапазон выходного сигнала манометра, мА
    diametr varchar(50) default (NULL)        -- Диаметр корпуса или габариты, мм
);

INSERT INTO "standardflowmeters" ("id","name","name_mt","typ_mt","usl","producer","toch","p_nome","p_end","zena","p_max","t_nome","t_end","diapz_signl","diametr") VALUES
(1,'Пример',NULL,NULL,NULL,NULL,NULL,NULL,NULL,0.0,0.0,0.0,0.0,NULL,NULL);


-- SELECT setval('"standardflowmeters_id_seq"', 1);
---------------------------------
-- standardpressdropregulators - Стандартные
-- standardpressdropregulators - RP_Регулятор перепада стандартные
drop table if exists standardpressdropregulators;

create table standardpressdropregulators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра
    tip varchar(50) default (NULL),           -- Тип регулятора
    Du float default ((0)),                   -- Диаметр условный, мм
    Kv float default ((0)),                   -- Условная пропускная способность, м^3/ч
    Pmin_zad float default ((0)),             -- Заданный перепад давления минимальный, МПа
    Pmax_zad float default ((0)),             -- Заданный перепад давления максимальный, МПа
    Sreda varchar(50) default (NULL),         -- Рабочая среда
    Py float default ((0)),                   -- Условное давление рабочей среды, Мпа
    Tmax_sreda float default ((0)),           -- Максимальная температура рабочей среды, Град.С
    Tmax_okru float default ((0)),            -- Максимальная температура окружающей среды, Град.С
    Pmax_klapan float default ((0)),          -- Максимальный перепад давления на клапане, Мпа
    Protethka float default ((0)),            -- Максимальная протечка через закрытый клапан, %
    K_kavit float default ((0)),              -- Коэффициент кавитации
    Xp float default ((0)),                   -- Пропорциональный диапазон регулирования клапана регулятора, Мпа
    Zena varchar(50) default (NULL),          -- Цена одного комплекта, доллар США
    Pr_ustanovki varchar(50) default (NULL),  -- Признак теплопровода для места установки клапана регулятора на подводящих трубопроводах
    Proizvod varchar(50) default (NULL),      -- Изготовитель регулятора
    Mail varchar(50) default (NULL),          -- Адрес электронной почты изготовителя
    Web varchar(50) default (NULL),           -- Адрес Web-узла изготовителя
    Demo varchar                              -- Внешний вид регулятора
);

INSERT INTO "standardpressdropregulators" ("id","tip","du","kv","pmin_zad","pmax_zad","sreda","py","tmax_sreda","tmax_okru","pmax_klapan","protethka","k_kavit","xp","zena","pr_ustanovki","proizvod","mail","web","demo") VALUES
(1,'AVP 15',15.0,1.6,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(2,'AVP 15',15.0,2.5,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(3,'AVP 20',20.0,4.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(4,'AVP 25',25.0,6.3,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(5,'AVP 32',32.0,10.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(6,'IVF 15',15.0,0.63,0.0,0.0,'Вода',1.3,180.0,0.0,1.0,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(7,'IVF 15',15.0,1.0,0.0,0.0,'Вода',1.3,180.0,0.0,1.0,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(8,'IVF 15',15.0,2.5,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(9,'IVF 15',15.0,4.0,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(10,'IVF 20',20.0,6.3,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(11,'IVF 25',25.0,10.0,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(12,'IVF 32',32.0,16.0,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(13,'IVF 40',40.0,20.0,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(14,'IVF 50',50.0,25.0,0.0,0.0,'Вода',1.3,180.0,0.0,0.8,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(15,'AFP 50',50.0,32.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(16,'AFP 65',60.0,50.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(17,'AFP 80',80.0,80.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(18,'AFP 100',100.0,125.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(19,'AFPQ 32',32.0,12.5,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(20,'AFPQ 40',40.0,20.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(21,'AFPQ 50',50.0,32.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(22,'AFPQ 65',60.0,50.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(23,'AFPQ 80',80.0,80.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(24,'AFPQ 100',100.0,125.0,0.0,0.0,'Вода',2.5,150.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(25,'AVQ 15',15.0,1.6,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(26,'AVQ 15',15.0,2.5,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(27,'AVQ 20',20.0,4.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(28,'AVQ 25',25.0,6.3,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(29,'AVQ 32',32.0,10.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(30,'AVPQ 15',15.0,1.6,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(31,'AVPQ 15',15.0,2.5,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(32,'AVPQ 20',20.0,4.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(33,'AVPQ 25',25.0,6.3,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(34,'AVPQ 32',32.0,10.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Подача и обрат','Danfoss',NULL,NULL,NULL),
(35,'AVPB 15',15.0,1.6,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Обратка','Danfoss',NULL,NULL,NULL),
(36,'AVPB 15',15.0,2.5,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Обратка','Danfoss',NULL,NULL,NULL),
(37,'AVPB 20',20.0,4.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Обратка','Danfoss',NULL,NULL,NULL),
(38,'AVPB 25',25.0,6.3,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Обратка','Danfoss',NULL,NULL,NULL),
(39,'AVPB 32',32.0,10.0,0.0,0.0,'Вода',2.5,140.0,0.0,1.2,0.05,0.6,0.0,NULL,'Обратка','Danfoss',NULL,NULL,NULL),
(40,'42-36',15.0,4.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(41,'42-36',20.0,6.3,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.6,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(42,'42-36',25.0,8.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(43,'42-36',32.0,16.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(44,'42-36',40.0,20.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.45,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(45,'42-36',50.0,32.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.4,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(46,'42-36',65.0,50.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.4,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(47,'42-36',80.0,80.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.35,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(48,'42-36',100.0,125.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(49,'42-36',125.0,190.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(50,'42-36',150.0,280.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.2,0.05,0.35,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(51,'42-36',200.0,420.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(52,'42-36',250.0,500.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(53,'42-37',15.0,4.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(54,'42-37',20.0,6.3,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.6,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(55,'42-37',25.0,8.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(56,'42-37',32.0,16.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(57,'42-37',40.0,20.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.45,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(58,'42-37',50.0,32.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.4,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(59,'42-37',65.0,50.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.4,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(60,'42-37',80.0,80.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.35,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(61,'42-37',100.0,125.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(62,'42-37',125.0,190.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(63,'42-37',150.0,280.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.2,0.05,0.35,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(64,'42-37',200.0,420.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(65,'42-37',250.0,500.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(66,'42-39',15.0,4.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(67,'42-39',20.0,6.3,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(68,'42-39',25.0,8.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(69,'42-39',32.0,16.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(70,'42-39',40.0,20.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.45,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(71,'42-39',50.0,32.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.4,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(72,'42-39',65.0,50.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.4,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(73,'42-39',80.0,80.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.35,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(74,'42-39',100.0,125.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(75,'42-39',125.0,190.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(76,'42-39',150.0,280.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.2,0.05,0.35,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(77,'42-39',200.0,420.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(78,'42-39',250.0,500.0,0.01,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(79,'42-10',15.0,4.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(80,'42-10',20.0,6.3,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.6,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(81,'42-10',25.0,8.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.4,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(82,'42-10',32.0,16.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(83,'42-10',40.0,20.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.45,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(84,'42-10',50.0,32.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,0.4,0.05,0.4,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(85,'42-15',15.0,4.0,0.01,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(86,'42-15',20.0,6.3,0.01,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.6,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(87,'42-15',25.0,8.0,0.01,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,1.4,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(88,'42-15',32.0,16.0,0.01,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(89,'42-15',40.0,20.0,0.01,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.45,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(90,'42-15',50.0,32.0,0.01,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,0.4,0.05,0.4,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(91,'42-14',15.0,4.0,0.005,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(92,'42-14',20.0,6.3,0.005,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.6,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(93,'42-14',25.0,8.0,0.005,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,1.4,0.05,0.55,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(94,'42-14',32.0,16.0,0.005,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.55,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(95,'42-14',40.0,20.0,0.005,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.45,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(96,'42-14',50.0,32.0,0.005,0.15,'Жидкости, парообразные среды',4.0,220.0,80.0,0.4,0.05,0.4,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(97,'42-18',15.0,4.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(98,'42-18',20.0,6.3,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.6,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(99,'42-18',25.0,8.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.4,0.05,0.55,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(100,'42-18',32.0,16.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.55,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(101,'42-18',40.0,20.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,0.6,0.05,0.45,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(102,'42-18',50.0,32.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,0.4,0.05,0.4,0.0,NULL,'Подача и обрат','Samson',NULL,NULL,NULL),
(103,'42-20',15.0,4.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(104,'42-20',20.0,6.3,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.6,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(105,'42-20',25.0,8.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(106,'42-20',32.0,16.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(107,'42-20',40.0,20.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.45,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(108,'42-20',50.0,32.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.4,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(109,'42-20',65.0,50.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.4,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(110,'42-20',80.0,80.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(111,'42-20',100.0,125.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(112,'42-20',125.0,190.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(113,'42-20',150.0,280.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.2,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(114,'42-20',200.0,420.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(115,'42-20',250.0,500.0,0.02,0.05,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(116,'42-25',15.0,4.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.65,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(117,'42-25',20.0,6.3,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.6,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(118,'42-25',25.0,8.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(119,'42-25',32.0,16.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.55,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(120,'42-25',40.0,20.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.45,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(121,'42-25',50.0,32.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.5,0.05,0.4,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(122,'42-25',65.0,50.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.4,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(123,'42-25',80.0,80.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,2.0,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(124,'42-25',100.0,125.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(125,'42-25',125.0,190.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.6,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(126,'42-25',150.0,280.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.2,0.05,0.35,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(127,'42-25',200.0,420.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(128,'42-25',250.0,500.0,0.005,1.0,'Жидкости, парообразные среды',4.0,220.0,80.0,1.0,0.05,0.3,0.0,NULL,'Короткозамкн. или байпас','Samson',NULL,NULL,NULL),
(129,'45-1',15.0,2.5,0.01,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(130,'45-1',20.0,6.3,0.01,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(131,'45-1',25.0,8.0,0.01,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(132,'45-1',32.0,12.5,0.01,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(133,'45-1',40.0,16.0,0.01,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(134,'45-1',50.0,20.0,0.01,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(135,'45-2',15.0,2.5,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(136,'45-2',20.0,6.3,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(137,'45-2',25.0,8.0,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(138,'45-2',32.0,12.5,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(139,'45-2',40.0,16.0,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(140,'45-2',50.0,20.0,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(141,'45-3',15.0,2.5,0.01,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(142,'45-3',20.0,6.3,0.01,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(143,'45-3',25.0,8.0,0.01,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(144,'45-3',32.0,12.5,0.01,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(145,'45-3',40.0,16.0,0.01,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(146,'45-3',50.0,20.0,0.01,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(147,'45-4',15.0,2.5,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(148,'45-4',20.0,6.3,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(149,'45-4',25.0,8.0,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(150,'45-4',32.0,12.5,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(151,'45-4',40.0,16.0,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(152,'45-4',50.0,20.0,0.01,0.4,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(153,'45-9',15.0,4.0,0.001,1.5,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.65,0.0,NULL,'Подача и обратка','Samson',NULL,NULL,NULL),
(154,'45-9',20.0,6.3,0.001,1.5,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача и обратка','Samson',NULL,NULL,NULL),
(155,'45-9',25.0,8.0,0.001,1.5,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача и обратка','Samson',NULL,NULL,NULL),
(156,'45-9',32.0,12.5,0.001,1.5,'Жидкости, парообразные среды',2.5,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача и обратка','Samson',NULL,NULL,NULL),
(157,'45-9',40.0,16.0,0.001,1.5,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Подача и обратка','Samson',NULL,NULL,NULL),
(158,'45-9',50.0,20.0,0.001,1.5,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Подача и обратка','Samson',NULL,NULL,NULL),
(159,'46-5',15.0,0.4,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(160,'46-5',15.0,1.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(161,'46-5',15.0,2.5,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(162,'46-5',15.0,4.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(163,'46-5',20.0,6.3,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(164,'46-5',25.0,8.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(165,'46-5',32.0,12.5,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(166,'46-5',40.0,16.0,0.02,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(167,'46-5',50.0,20.0,0.02,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(168,'46-6',15.0,0.4,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(169,'46-6',15.0,1.0,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(170,'46-6',15.0,2.5,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(171,'46-6',15.0,4.0,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(172,'46-6',20.0,6.3,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(173,'46-6',25.0,8.0,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(174,'46-6',32.0,12.5,0.02,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(175,'46-6',40.0,16.0,0.02,0.2,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(176,'46-6',50.0,20.0,0.02,0.2,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(177,'46-7',15.0,0.4,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(178,'46-7',15.0,1.0,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(179,'46-7',15.0,2.5,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(180,'46-7',15.0,4.0,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(181,'46-7',20.0,6.3,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(182,'46-7',25.0,8.0,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(183,'46-7',32.0,12.5,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(184,'46-7',40.0,16.0,0.01,0.2,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(185,'46-7',50.0,20.0,0.01,0.2,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Обратка','Samson',NULL,NULL,NULL),
(186,'47-1',15.0,0.4,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(187,'47-1',15.0,1.0,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(188,'47-1',15.0,2.5,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,0.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(189,'47-1',15.0,4.0,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(190,'47-1',20.0,6.3,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(191,'47-1',25.0,8.0,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(192,'47-1',32.0,12.5,0.01,0.2,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(193,'47-1',40.0,16.0,0.01,0.2,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(194,'47-1',50.0,20.0,0.01,0.2,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(195,'47-4',15.0,0.4,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(196,'47-4',15.0,1.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(197,'47-4',15.0,2.5,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(198,'47-4',15.0,4.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(199,'47-4',20.0,6.3,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(200,'47-4',25.0,8.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(201,'47-4',32.0,12.5,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(202,'47-4',40.0,16.0,0.02,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(203,'47-4',50.0,20.0,0.02,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Подача','Samson',NULL,NULL,NULL),
(204,'47-5',15.0,0.4,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(205,'47-5',15.0,1.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(206,'47-5',15.0,2.5,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(207,'47-5',15.0,4.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(208,'47-5',20.0,6.3,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.6,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(209,'47-5',25.0,8.0,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(210,'47-5',32.0,12.5,0.02,0.05,'Жидкости, парообразные среды',1.6,120.0,80.0,2.0,0.05,0.55,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(211,'47-5',40.0,16.0,0.02,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.5,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL),
(212,'47-5',50.0,20.0,0.02,0.05,'Жидкости, парообразные среды',2.5,120.0,80.0,1.6,0.05,0.45,0.0,NULL,'Обрат','Samson',NULL,NULL,NULL);


-- SELECT setval('"standardpressdropregulators_id_seq"', 212);
---------------------------------
-- standardtubheatexchangers - Стандартные
-- standardtubheatexchangers - TB_Теплообменники трубчатые стандартные
drop table if exists standardtubheatexchangers;

create table standardtubheatexchangers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра трубчатого подогревателя
    name_tb varchar(50) default (NULL),       -- ГОСТ, обозначение
    dn_tr float default ((0)),                -- Наружний диаметр корпуса секции
    kol float default ((0)),                  -- Количество трубок в секции, шт
    s_m_tr float default ((0)),               -- Площадь проходного сечения межтрубного пространства, м^2
    s_t_tr float default ((0)),               -- Площадь сечения трубок, м^2
    d_m_tr float default ((0)),               -- Эквивалентный диаметр межтрубного пространства, м
    l_tr int default (NULL),                  -- Длина трубок одной секции, м
    p_tr float default ((0)),                 -- Поверхность нагрева одной секции, м^2
    ispol varchar(50) default (NULL),         -- Исполнение системы труб: Гладкие, Профилированные
    Q float default ((0)),                    -- Тепловая производительность
    m1 varchar(50) default (NULL),            -- Масса секции, кг
    m2 varchar(50) default (NULL),            -- Масса калача, кг
    m3 varchar(50) default (NULL),            -- Масса перехода, кг
    d_tr varchar(50) default (NULL),          -- Внутренний диаметр трубок, м
    t_tr float default ((0)),                 -- Толщина стенок трубок, м
    help varchar                              -- Примечание
);

INSERT INTO "standardtubheatexchangers" ("id","name_tb","dn_tr","kol","s_m_tr","s_t_tr","d_m_tr","l_tr","p_tr","ispol","q","m1","m2","m3","d_tr","t_tr","help") VALUES
(1,'ГОСТ 27500',57.0,4.0,0.00116,0.00062,0.0129,2,0.37,'гладкие',6880.0,'23,5','8,6','5,5','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(2,'ГОСТ 27500',57.0,4.0,0.00116,0.00062,0.0129,4,0.75,'гладкие',15480.0,'37,0','8,6','5,5','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(3,'ГОСТ 27500',57.0,4.0,0.00116,0.00062,0.0129,2,0.37,'профилированные',8600.0,'23,5','7,9','3,8','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(4,'ГОСТ 27500',57.0,4.0,0.00116,0.00062,0.0129,4,0.75,'профилированные',19780.0,'37,0','7,9','3,8','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(5,'ГОСТ 27500',76.0,7.0,0.00233,0.00108,0.0164,2,0.65,'гладкие',1720.0,'32,5','10,9','6,8','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).                                                                                                 2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.                                                                                                       3. Масса определена при рабочем давлении 1 Мпа.                                                                                  4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(6,'ГОСТ 27500',76.0,7.0,0.00233,0.00108,0.0164,4,1.32,'гладкие',21500.0,'52,4','10,9','6,8','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(7,'ГОСТ 27500',76.0,7.0,0.00233,0.00108,0.0164,2,0.65,'профилированные',12900.0,'32,5','10,4','4,7','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(8,'ГОСТ 27500',76.0,7.0,0.00233,0.00108,0.0164,4,1.32,'профилированные',30100.0,'52,4','10,4','4,7','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(9,'ГОСТ 27500',89.0,10.0,0.00327,0.00154,0.0172,2,0.93,'гладкие',15480.0,'40','13.2','12','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(10,'ГОСТ 27500',89.0,10.0,0.00327,0.00154,0.0172,4,1.88,'гладкие',34400.0,'64.2','13.2','12','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(11,'ГОСТ 27500',89.0,10.0,0.00327,0.00154,0.0172,2,0.93,'профилированные',17200.0,'40','12','5.4','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(12,'ГОСТ 27500',89.0,10.0,0.00327,0.00154,0.0172,4,1.88,'профилированные',43000.0,'64.2','12','5.4','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(13,'ГОСТ 27500',114.0,19.0,0.005,0.00293,0.0155,2,1.79,'гладкие',13400.0,'58','17.7','10.5','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(14,'ГОСТ 27500',114.0,19.0,0.005,0.00293,0.0155,4,3.58,'гладкие',73100.0,'97.1','17.7','10.5','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(15,'ГОСТ 27500',114.0,19.0,0.005,0.00293,0.0155,2,1.79,'профилированные',43000.0,'58','17.2','7.3','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(16,'ГОСТ 27500',114.0,19.0,0.005,0.00293,0.0155,4,3.58,'профилированные',94600.0,'97.1','17.2','7.3','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(17,'ГОСТ 27500',168.0,37.0,0.0122,0.0057,0.019,2,3.49,'гладкие',60200.0,'113','32.8','17.4','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(18,'ГОСТ 27500',168.0,37.0,0.0122,0.0057,0.019,4,6.98,'гладкие',124700.0,'193.8','32.8','17.4','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(19,'ГОСТ 27500',168.0,37.0,0.0122,0.0057,0.019,2,3.49,'профилированные',77400.0,'113','32.8','13.4','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(20,'ГОСТ 27500',168.0,37.0,0.0122,0.0057,0.019,4,6.98,'профилированные',167700.0,'193.8','32.8','13.4','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(21,'ГОСТ 27500',219.0,61.0,0.02139,0.00939,0.0224,2,5.75,'гладкие',98040.0,'173','54.3','52.7','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(22,'ГОСТ 27500',219.0,61.0,0.02139,0.00939,0.0224,4,11.51,'гладкие',202100.0,'301.3','54.3','52.7','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(23,'ГОСТ 27500',219.0,61.0,0.02139,0.00939,0.0224,2,5.75,'профилированные',129000.0,'173','52.7','19.3','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(24,'ГОСТ 27500',219.0,61.0,0.02139,0.00939,0.0224,4,11.51,'профилированные',270900.0,'301.3','52.7','19.3','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(25,'ГОСТ 27500',273.0,109.0,0.03077,0.01679,0.0191,2,10.28,'гладкие',202100.0,'262','81.4','35','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(26,'ГОСТ 27500',273.0,109.0,0.03077,0.01679,0.0191,4,20.56,'гладкие',408500.0,'461.7','81.4','35','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(27,'ГОСТ 27500',273.0,109.0,0.03077,0.01679,0.0191,2,10.28,'профилированные',270900.0,'262','90.4','26.6','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(28,'ГОСТ 27500',273.0,109.0,0.03077,0.01679,0.0191,4,20.56,'профилированные',546100.0,'461.7','90.4','26.6','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(29,'ГОСТ 27500',325.0,151.0,0.04464,0.02325,0.0208,2,14.24,'гладкие',258000.0,'338','97.3','43','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(30,'ГОСТ 27500',325.0,151.0,0.04464,0.02325,0.0208,4,28.49,'гладкие',541800.0,'594.4','97.3','43','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(31,'ГОСТ 27500',325.0,151.0,0.04464,0.02325,0.0208,2,14.24,'профилированные',344000.0,'338','113','34.5','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.'),
(32,'ГОСТ 27500',325.0,151.0,0.04464,0.02325,0.0208,4,28.49,'профилированные',722400.0,'594.4','113','34.5','14',1.0,'1.Тепловая производительность определена при скорости воды внутри трубок 1 м/с, равенстве расходов теплообменивающих сред и температурном напоре 10 Град.С (температурный перепад по греющей воде 70-15 Град.С, нагреваемой - 5-60 Град.С).  2. Гидравлическое сопротивление в трубках не более 0,004 Мпа для гладкой трубки и 0,008 МПа - для профилированной при длине секции 2 м и соответственно  не более 0,006 Мпа и 0,014 Мпа при длине секции 4м, в межтрубном пространстве гидравлическое сопротивление равно 0,007 Мпа при длине секции 2 м и 0,009 Мпа при длине секции 4м.  3. Масса определена при рабочем давлении 1 Мпа.   4. Тепловая производительность дана для сравнения с подогревателями других типоразмеров или типов.');


-- SELECT setval('"standardtubheatexchangers_id_seq"', 32);
---------------------------------
-- standardthermometers - Стандартные
-- standardthermometers - TO_Термометр стандартный
drop table if exists standardthermometers;

create table standardthermometers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер по порядку
    name varchar(50) default (NULL),          -- Наименование
    execution varchar(50) default (NULL),     -- Исполнение
    name_mt varchar(50) default (NULL),       -- Тип
    nomer varchar(50) default (NULL),         -- Номер термометра
    operation varchar(50) default (NULL),     -- Действие
    typ_mt varchar(50) default (NULL),        -- ГОСТ
    destination varchar(150) default (NULL),  -- Назначение
    producer varchar(50) default (NULL),      -- Изготовитель
    t_min float default ((0)),                -- Нижний предел измерения, Град.С
    t_max float default ((0)),                -- Верхний предел измерения, Град.С
    l_1 float default ((0)),                  -- Длина верхней части, мм
    l_2 float default ((0)),                  -- Длина погружаемой части, мм
    l float default ((0)),                    -- Общая длина, м
    d float default ((0)),                    -- Диаметр оболочки
    delta_t float default ((0)),              -- Цена деления, Град.С
    error float default ((0))                 -- Погрешность показаний
);

INSERT INTO "standardthermometers" ("id","name","execution","name_mt","nomer","operation","typ_mt","destination","producer","t_min","t_max","l_1","l_2","l","d","delta_t","error") VALUES
(1,'Термометр технический','стеклянный ртутный',NULL,'4','Прямой',NULL,'Контроль температурного режима',NULL,0.0,100.0,240.0,66.0,NULL,NULL,1.0,NULL),
(2,'Термометр технический','стеклянный ртутный',NULL,'4','Прямой',NULL,'Контроль температурного режима',NULL,0.0,100.0,160.0,103.0,NULL,NULL,1.0,NULL),
(3,'Термометр технический','стеклянный ртутный',NULL,'4','Угловой',NULL,'Контроль температурного режима',NULL,0.0,100.0,240.0,104.0,NULL,NULL,1.0,NULL),
(4,'Термометр технический','стеклянный ртутный',NULL,'4','Угловой',NULL,'Контроль температурного режима',NULL,0.0,100.0,160.0,141.0,NULL,NULL,1.0,NULL),
(5,'Термометр лабораторный нормальный','стеклянный ртутный','ТЛ-4','2',NULL,NULL,'Измерение температуры при тепловых испытаниях',NULL,0.0,55.0,NULL,NULL,530.0,11.0,0.1,0.2),
(6,'Термометр лабораторный нормальный','стеклянный ртутный','ТЛ-4','2',NULL,NULL,'Измерение температуры при тепловых испытаниях',NULL,50.0,105.0,NULL,NULL,530.0,11.0,0.1,0.2),
(7,'Термометр лабораторный нормальный','стеклянный ртутный','ТЛ-4','2',NULL,NULL,'Измерение температуры при тепловых испытаниях',NULL,100.0,155.0,NULL,NULL,530.0,11.0,0.1,0.4),
(8,'Термометр лабораторный нормальный','стеклянный ртутный','ТЛ-4','2',NULL,NULL,'Измерение температуры при тепловых испытаниях',NULL,150.0,205.0,NULL,NULL,530.0,11.0,0.1,0.4),
(9,'Термометры электроконтактные','стеклянный ртутный','ТЗК','1','Прямой','ГОСТ 9871-75','Поддержание заданной температуры и сигнализация о ее достижении','Клинское НПО Теплоприбор',0.0,50.0,200.0,80.0,NULL,NULL,1.0,NULL),
(10,'Термометры электроконтактные','стеклянный ртутный','ТЗК','1','Прямой','ГОСТ 9871-75','Поддержание заданной температуры и сигнализация о ее достижении','Клинское НПО Теплоприбор',0.0,50.0,200.0,100.0,NULL,NULL,1.0,NULL);


-- SELECT setval('"standardthermometers_id_seq"', 10);
---------------------------------
-- standardtubes - Стандартные
-- standardtubes - TP_Трубы стандартные
drop table if exists standardtubes;

create table standardtubes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер экземпляра
    name varchar(50) default (NULL),          -- Наименование
    stand varchar(50) default (NULL),         -- Стандарт
    izgotov varchar(50) default (NULL),       -- Изготовитель
    material varchar(50) default (NULL),      -- Материал стенки
    diametr_usl float default ((0)),          -- Диаметр условный
    diamVne float default ((0)),              -- Диаметр наружный
    diametr float default ((0)),              -- Диаметр внутренний
    tol float default ((0)),                  -- Толщина стенки
    S_sech float default ((0)),               -- Площадь поперечного сечения в свету
    S_1m float default ((0)),                 -- Площадь поверхности 1м длины трубы
    massa_1m float default ((0)),             -- Масса 1 метра трубы без изоляции
    massa_1m_izol float default ((0))         -- Масса 1 метра трубы с изоляцией
);

INSERT INTO "standardtubes" ("id","name","stand","izgotov","material","diametr_usl","diamvne","diametr","tol","s_sech","s_1m","massa_1m","massa_1m_izol") VALUES
(1,NULL,'Россия',NULL,NULL,25.0,32.0,26.0,3.0,0.000531,0.0,0.0,0.0),
(2,NULL,'Россия',NULL,NULL,25.0,32.0,28.0,2.0,0.000616,0.0,0.0,0.0),
(3,NULL,'Россия',NULL,NULL,32.0,38.0,32.0,3.0,0.000804,0.0,0.0,0.0),
(4,NULL,'Россия',NULL,NULL,32.0,38.0,34.0,2.0,0.000908,0.0,0.0,0.0),
(5,NULL,'Россия',NULL,NULL,40.0,45.0,39.0,3.0,0.001195,0.0,0.0,0.0),
(6,NULL,'Россия',NULL,NULL,40.0,45.0,41.0,2.0,0.00132,0.0,0.0,0.0),
(7,NULL,'Россия',NULL,NULL,50.0,57.0,51.0,3.0,0.002042,0.0,0.0,0.0),
(8,NULL,'Россия',NULL,NULL,65.0,76.0,70.0,3.0,0.003848,0.0,0.0,0.0),
(9,NULL,'Россия',NULL,NULL,80.0,89.0,82.0,3.0,0.005281,0.0,0.0,0.0),
(10,NULL,'Россия',NULL,NULL,100.0,108.0,100.0,4.0,0.007854,0.0,0.0,0.0),
(11,NULL,'Россия',NULL,NULL,125.0,133.0,125.0,4.0,0.001227,0.0,0.0,0.0),
(12,NULL,'Россия',NULL,NULL,150.0,159.0,150.0,4.0,0.001767,0.0,0.0,0.0),
(13,NULL,'Россия',NULL,NULL,175.0,194.0,184.0,5.0,0.002659,0.0,0.0,0.0),
(14,NULL,'Россия',NULL,NULL,200.0,219.0,207.0,6.0,0.003365,0.0,0.0,0.0),
(15,NULL,'Россия',NULL,NULL,200.0,219.0,211.0,4.0,0.003497,0.0,0.0,0.0),
(16,NULL,'Россия',NULL,NULL,250.0,273.0,259.0,7.0,0.005269,0.0,0.0,0.0),
(17,NULL,'Россия',NULL,NULL,250.0,273.0,263.0,5.0,0.005433,0.0,0.0,0.0),
(18,NULL,'Россия',NULL,NULL,300.0,325.0,309.0,8.0,0.007499,0.0,0.0,0.0),
(19,NULL,'Россия',NULL,NULL,300.0,325.0,315.0,5.0,0.007793,0.0,0.0,0.0),
(20,NULL,'Россия',NULL,NULL,350.0,377.0,359.0,9.0,0.1012,0.0,0.0,0.0),
(21,NULL,'Россия',NULL,NULL,350.0,377.0,367.0,5.0,0.1058,0.0,0.0,0.0),
(22,NULL,'Россия',NULL,NULL,400.0,426.0,408.0,9.0,0.1307,0.0,0.0,0.0),
(23,NULL,'Россия',NULL,NULL,400.0,426.0,414.0,6.0,0.1346,0.0,0.0,0.0),
(24,NULL,'Россия',NULL,NULL,500.0,530.0,512.0,9.0,0.2059,0.0,0.0,0.0),
(25,NULL,'Россия',NULL,NULL,500.0,530.0,518.0,6.0,0.2107,0.0,0.0,0.0),
(26,NULL,'Россия',NULL,NULL,600.0,630.0,610.0,10.0,0.2922,0.0,0.0,0.0),
(27,NULL,'Россия',NULL,NULL,600.0,630.0,618.0,6.0,0.3,0.0,0.0,0.0),
(28,NULL,'Россия',NULL,NULL,700.0,720.0,698.0,11.0,0.3826,0.0,0.0,0.0),
(29,NULL,'Россия',NULL,NULL,700.0,720.0,706.0,7.0,0.3915,0.0,0.0,0.0),
(30,NULL,'Россия',NULL,NULL,800.0,820.0,796.0,12.0,0.4976,0.0,0.0,0.0),
(31,NULL,'Россия',NULL,NULL,800.0,820.0,806.0,7.0,0.5102,0.0,0.0,0.0),
(32,NULL,'Россия',NULL,NULL,900.0,920.0,892.0,14.0,0.6249,0.0,0.0,0.0),
(33,NULL,'Россия',NULL,NULL,900.0,920.0,904.0,8.0,0.6418,0.0,0.0,0.0),
(34,NULL,'Россия',NULL,NULL,1000.0,1020.0,990.0,15.0,0.7698,0.0,0.0,0.0),
(35,NULL,'Россия',NULL,NULL,1000.0,1020.0,1004.0,8.0,0.7917,0.0,0.0,0.0),
(36,NULL,'Россия',NULL,NULL,1200.0,1220.0,1188.0,16.0,1.1085,0.0,0.0,0.0),
(37,NULL,'Россия',NULL,NULL,1200.0,1220.0,1204.0,8.0,1.347,0.0,0.0,0.0),
(38,NULL,'Россия',NULL,NULL,1400.0,1420.0,1388.0,16.0,1.5131,0.0,0.0,0.0),
(39,NULL,'Россия',NULL,NULL,1400.0,1420.0,1400.0,10.0,1.5394,0.0,0.0,0.0),
(40,NULL,'АВВ',NULL,NULL,20.0,26.9,21.7,2.6,0.0,0.0,0.0,0.0),
(41,NULL,'АВВ',NULL,NULL,25.0,33.7,21.7,2.6,0.0,0.0,0.0,0.0),
(42,NULL,'АВВ',NULL,NULL,32.0,42.4,21.7,2.6,0.0,0.0,0.0,0.0),
(43,NULL,'АВВ',NULL,NULL,40.0,48.3,21.7,2.6,0.0,0.0,0.0,0.0),
(44,NULL,'АВВ',NULL,NULL,50.0,60.3,54.5,2.9,0.0,0.0,0.0,0.0),
(45,NULL,'АВВ',NULL,NULL,65.0,76.1,70.3,2.9,0.0,0.0,0.0,0.0),
(46,NULL,'АВВ',NULL,NULL,80.0,88.9,82.5,3.2,0.0,0.0,0.0,0.0),
(47,NULL,'АВВ',NULL,NULL,100.0,114.3,107.1,3.6,0.0,0.0,0.0,0.0),
(48,NULL,'АВВ',NULL,NULL,125.0,139.7,132.5,3.6,0.0,0.0,0.0,0.0),
(49,NULL,'АВВ',NULL,NULL,150.0,168.3,160.3,4.0,0.0,0.0,0.0,0.0),
(50,NULL,'АВВ',NULL,NULL,200.0,219.1,210.1,4.5,0.0,0.0,0.0,0.0),
(51,NULL,'АВВ',NULL,NULL,250.0,273.0,263.0,5.0,0.0,0.0,0.0,0.0),
(52,NULL,'АВВ',NULL,NULL,300.0,323.9,312.7,5.6,0.0,0.0,0.0,0.0),
(53,NULL,'АВВ',NULL,NULL,350.0,355.6,344.4,5.6,0.0,0.0,0.0,0.0),
(54,NULL,'АВВ',NULL,NULL,400.0,406.4,393.8,6.3,0.0,0.0,0.0,0.0),
(55,NULL,'АВВ',NULL,NULL,450.0,457.2,444.6,6.3,0.0,0.0,0.0,0.0),
(56,NULL,'АВВ',NULL,NULL,500.0,508.0,495.4,6.3,0.0,0.0,0.0,0.0),
(57,NULL,'АВВ',NULL,NULL,550.0,558.8,546.2,6.3,0.0,0.0,0.0,0.0),
(58,NULL,'АВВ',NULL,NULL,600.0,609.6,593.6,8.0,0.0,0.0,0.0,0.0),
(59,NULL,'АВВ',NULL,NULL,700.0,711.0,695.0,8.0,0.0,0.0,0.0,0.0),
(60,NULL,'АВВ',NULL,NULL,800.0,813.0,795.4,8.8,0.0,0.0,0.0,0.0),
(61,NULL,'АВВ',NULL,NULL,900.0,914.0,894.0,10.0,0.0,0.0,0.0,0.0),
(62,NULL,'АВВ',NULL,NULL,1000.0,1016.0,996.0,10.0,0.0,0.0,0.0,0.0),
(63,NULL,'АВВ',NULL,NULL,1100.0,1118.0,1096.0,11.0,0.0,0.0,0.0,0.0),
(64,NULL,'ППУ',NULL,NULL,25.0,32.0,26.0,3.0,0.000530929158456675,0.0,0.0,0.0),
(65,NULL,'ППУ',NULL,NULL,25.0,32.0,26.0,3.0,0.000530929158456675,0.0,0.0,0.0),
(66,NULL,'ППУ',NULL,NULL,32.0,38.0,32.0,3.0,0.000804247719318987,0.0,0.0,0.0),
(67,NULL,'ППУ',NULL,NULL,40.0,45.0,39.0,3.0,0.001194590606527519,0.0,0.0,0.0),
(68,NULL,'ППУ',NULL,NULL,50.0,57.0,51.0,3.0,0.0020428206229967626,0.0,0.0,0.0),
(69,NULL,'ППУ',NULL,NULL,65.0,76.0,70.0,3.0,0.003848451000647497,0.0,0.0,0.0),
(70,NULL,'ППУ',NULL,NULL,80.0,89.0,81.0,4.0,0.005152997350050658,0.0,0.0,0.0),
(71,NULL,'ППУ',NULL,NULL,100.0,108.0,100.0,4.0,0.007853981633974483,0.0,0.0,0.0),
(72,NULL,'ППУ',NULL,NULL,125.0,133.0,125.0,4.0,0.01227184630308513,0.0,0.0,0.0),
(73,NULL,'ППУ',NULL,NULL,150.0,159.0,150.0,4.5,0.017671458676442587,0.0,0.0,0.0),
(74,NULL,'ППУ',NULL,NULL,200.0,219.0,207.0,6.0,0.03365352590341726,0.0,0.0,0.0),
(75,NULL,'ППУ',NULL,NULL,250.0,273.0,259.0,7.0,0.05268529419886423,0.0,0.0,0.0),
(76,NULL,'ППУ',NULL,NULL,300.0,325.0,311.0,7.0,0.0759644957619646,0.0,0.0,0.0),
(77,NULL,'ППУ',NULL,NULL,400.0,426.0,412.0,7.0,0.13331662584773643,0.0,0.0,0.0),
(78,NULL,'ППУ',NULL,NULL,500.0,530.0,516.0,7.0,0.20911697339355098,0.0,0.0,0.0),
(79,NULL,'ППУ',NULL,NULL,600.0,630.0,614.0,8.0,0.29609196600818444,0.0,0.0,0.0),
(80,NULL,'ППУ',NULL,NULL,700.0,720.0,704.0,8.0,0.3892558961503897,0.0,0.0,0.0),
(81,NULL,'ППУ',NULL,NULL,800.0,820.0,802.0,9.0,0.5051712402898924,0.0,0.0,0.0),
(82,NULL,'ППУ',NULL,NULL,900.0,920.0,902.0,9.0,0.6390030873328175,0.0,0.0,0.0),
(83,NULL,'ППУ',NULL,NULL,1000.0,1020.0,1000.0,10.0,0.7853981633974483,0.0,0.0,0.0);


-- SELECT setval('"standardtubes_id_seq"', 83);
---------------------------------
-- standardthreewayvalves - Стандартные
-- standardthreewayvalves - V3_Клапан трехходовой стандартный
drop table if exists standardthreewayvalves;

create table standardthreewayvalves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip_klap varchar(50) default (NULL),      -- марка
    prois varchar(50) default (NULL),         -- Производитель
    strana varchar(50) default (NULL),        -- Страна
    prz_klan varchar(50) default (NULL),      -- Принцип действия
    organ varchar(50) default (NULL),         -- регулирующий орган
    h_1 varchar(50) default (NULL),           -- Тип расходной характеристики прямого хода 'Линейная', 'Ранопроцентная', 'Параболическая'
    h_2 varchar(50) default (NULL),           -- Тип расходной характеристики прямого хода 'Линейная', 'Ранопроцентная', 'Параболическая'
    regul varchar(50) default (NULL),         -- Регулирование
    t_max int default (NULL),                 -- Максимальная температура для воды
    DN float default ((0)),                   -- Диаметр номинальный, мм
    L int default (NULL),                     -- Присоеденительный размер по оси трубопровода, мм
    h float default ((0)),                    -- Ход штока клапана, мм
    dP float default ((0)),                   -- Допустимый перепад давления на клапане, при смешении м.вод.ст.
    dP_2 float default ((0)),                 -- Допустимый перепад давления на клапане, при разделении м.вод.ст.
    kv_s float default ((0)),                 -- Пропускная способность, м^3/ч
    privod varchar(50) default (NULL)         -- Привод
);

INSERT INTO "standardthreewayvalves" ("id","tip_klap","prois","strana","prz_klan","organ","h_1","h_2","regul","t_max","dn","l","h","dp","dp_2","kv_s","privod") VALUES
(1,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,15.0,80,10.0,40.788,10.197,0.63,'AME 435 / AMV 435'),
(2,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,15.0,80,10.0,40.788,10.197,1.0,'AME 438 SU / AMV 438 SU'),
(3,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,15.0,80,10.0,40.788,10.197,1.6,'AME 25 / AMV 25+адаптер'),
(4,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,15.0,80,10.0,40.788,10.197,2.5,'AME 35 / AMV 35+адаптер'),
(5,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,15.0,80,10.0,40.788,10.197,4.0,NULL),
(6,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,20.0,80,10.0,40.788,10.197,6.3,NULL),
(7,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,25.0,95,10.0,40.788,10.197,10.0,NULL),
(8,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,32.0,112,15.0,40.788,10.197,16.0,NULL),
(9,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,40.0,132,15.0,40.788,10.197,25.0,NULL),
(10,'VRG 3','Danfoss','Дания','смешение/разделение','Односедельный клапан','Линейная','Линейная','Пропорциональное',130,50.0,160,15.0,40.788,10.197,40.0,NULL);


-- SELECT setval('"standardthreewayvalves_id_seq"', 10);
--- Стандартные: 14
--===========================--
--         lookup            --
--===========================--
--- Стандартные lookup: 0
--===========================--
--        Технические условия             --
--===========================--
---------------------------------
-- tehnicheskie_usloviya - Технические условия
-- tehnicheskie_usloviya - Технические условия
drop table if exists tehnicheskie_usloviya;

create table tehnicheskie_usloviya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    sostoyanie_dogovora int default ((1)),    -- Состояние договора
    dogovor text,                             -- Договор
    akt text,                                 -- Акт
    data_annulirovaniya date,                 -- Дата аннулирования
    nomer int,                                -- Номер
    god int,                                  -- Год
    nomer_tu varchar(255),                    -- Номер ТУ
    data_vydachi_tu date,                     -- Дата выдачи ТУ
    naimenovanie_organizatsii__zaprashivayuschey_tu varchar(255), -- Наименование организации, запрашивающей ТУ
    naimenovanie_obekta varchar(255),         -- Наименование объекта
    adres_obekta varchar(255),                -- Адрес объекта
    istochnik varchar(255),                   -- Источник
    rayon_ekspluatatsii varchar(25),          -- Район эксплуатации
    teplovye_potoki__gkal_ch float,           -- Тепловые потоки, Гкал/ч
    v_tom_chisle_otoplenie float,             -- В том числе отопление
    v_tom_chisle_ventilyatsiya float,         -- В том числе вентиляция
    v_tom_chisle_gvs_maks float,              -- В том числе ГВС макс
    prirost_nagruzki float,                   -- Прирост нагрузки
    v_tom_chisle_prirost_otoplenie float,     -- В том числе прирост отопление
    v_tom_chisle_prirost_ventilyatsiya float, -- В том числе прирост вентиляция
    v_tom_chisle_prirost_gvs_maks float,      -- В том числе прирост ГВС макс
    kamera varchar(255),                      -- Камера
    dopolnitelnye_tehnicheskie_meropriyatiya text,    -- Дополнительные технические мероприятия
    srok_deystviya_tu varchar(255),           -- Срок действия ТУ
    izmeneniya_prodleniya_1 text,             -- Изменения продления 1
    data_izmeneniya_prodleniya_1 date,        -- Дата изменения продления 1
    teplovye_potoki__gkal_ch_1 float,         -- Тепловые потоки, Гкал/ч 1
    v_tom_chisle_otoplenie_1 float,           -- В том числе отопление 1
    v_tom_chisle_ventilyatsiya_1 float,       -- В том числе вентиляция 1
    v_tom_chisle_gvs_maks_1 float,            -- В том числе ГВС макс 1
    prirost_nagruzki_1 float,                 -- Прирост нагрузки 1
    v_tom_chisle_prirost_otoplenie_1 float,   -- В том числе прирост отопление 1
    v_tom_chisle_prirost_ventilyatsiya_1 float,   -- В том числе прирост вентиляция 1
    v_tom_chisle_prirost_gvs_maks_1 float,    -- В том числе прирост ГВС макс 1
    dopolnitelnye_tehnicheskie_meropriyatiya_1 text,  -- Дополнительные технические мероприятия 1
    izmeneniya_prodleniya_2 text,             -- Изменения продления 2
    data_izmeneniya_prodleniya_2 date,        -- Дата изменения продления 2
    teplovye_potoki__gkal_ch_2 float,         -- Тепловые потоки, Гкал/ч 2
    v_tom_chisle_otoplenie_2 float,           -- В том числе отопление 2
    v_tom_chisle_ventilyatsiya_2 float,       -- В том числе вентиляция 2
    v_tom_chisle_gvs_maks_2 float,            -- В том числе ГВС макс 2
    prirost_nagruzki_2 float,                 -- Прирост нагрузки 2
    v_tom_chisle_prirost_otoplenie_2 float,   -- В том числе прирост отопление 2
    v_tom_chisle_prirost_ventilyatsiya_2 float,   -- В том числе прирост вентиляция 2
    v_tom_chisle_prirost_gvs_maks_2 float,    -- В том числе прирост ГВС макс 2
    dopolnitelnye_tehnicheskie_meropriyatiya_2 text,  -- Дополнительные технические мероприятия 2
    izmeneniya_prodleniya_3 text,             -- Изменения продления 3
    data_izmeneniya_prodleniya_3 date,        -- Дата изменения продления 3
    teplovye_potoki__gkal_ch_3 float,         -- Тепловые потоки, Гкал/ч 3
    v_tom_chisle_otoplenie_3 float,           -- В том числе отопление 3
    v_tom_chisle_ventilyatsiya_3 float,       -- В том числе вентиляция 3
    v_tom_chisle_gvs_maks_3 float,            -- В том числе ГВС макс 3
    prirost_nagruzki_3 float,                 -- Прирост нагрузки 3
    v_tom_chisle_prirost_otoplenie_3 float,   -- В том числе прирост отопление 3
    v_tom_chisle_prirost_ventilyatsiya_3 float,   -- В том числе прирост вентиляция 3
    v_tom_chisle_prirost_gvs_maks_3 float,    -- В том числе прирост ГВС макс 3
    dopolnitelnye_tehnicheskie_meropriyatiya_3 text,  -- Дополнительные технические мероприятия 3
    izmeneniya_prodleniya_4 text,             -- Изменения продления 4
    data_izmeneniya_prodleniya_4 date,        -- Дата изменения продления 4
    teplovye_potoki__gkal_ch_4 float,         -- Тепловые потоки, Гкал/ч 4
    v_tom_chisle_otoplenie_4 float,           -- В том числе отопление 4
    v_tom_chisle_ventilyatsiya_4 float,       -- В том числе вентиляция 4
    v_tom_chisle_gvs_maks_4 float,            -- В том числе ГВС макс 4
    prirost_nagruzki_4 float,                 -- Прирост нагрузки 4
    v_tom_chisle_prirost_otoplenie_4 float,   -- В том числе прирост отопление 4
    v_tom_chisle_prirost_ventilyatsiya_4 float,   -- В том числе прирост вентиляция 4
    v_tom_chisle_prirost_gvs_maks_4 float,    -- В том числе прирост ГВС макс 4
    dopolnitelnye_tehnicheskie_meropriyatiya_4 text,  -- Дополнительные технические мероприятия 4
    izmeneniya_prodleniya_5 text,             -- Изменения продления 5
    data_izmeneniya_prodleniya_5 date,        -- Дата изменения продления 5
    teplovye_potoki__gkal_ch_5 float,         -- Тепловые потоки, Гкал/ч 5
    v_tom_chisle_otoplenie_5 float,           -- В том числе отопление 5
    v_tom_chisle_ventilyatsiya_5 float,       -- В том числе вентиляция 5
    v_tom_chisle_gvs_maks_5 float,            -- В том числе ГВС макс 5
    prirost_nagruzki_5 float,                 -- Прирост нагрузки 5
    v_tom_chisle_prirost_otoplenie_5 float,   -- В том числе прирост отопление 5
    v_tom_chisle_prirost_ventilyatsiya_5 float,   -- В том числе прирост вентиляция 5
    v_tom_chisle_prirost_gvs_maks_5 float,    -- В том числе прирост ГВС макс 5
    dopolnitelnye_tehnicheskie_meropriyatiya_5 text,  -- Дополнительные технические мероприятия 5
    izmeneniya_prodleniya_6 text,             -- Изменения продления 6
    data_izmeneniya_prodleniya_6 date,        -- Дата изменения продления 6
    teplovye_potoki__gkal_ch_6 float,         -- Тепловые потоки, Гкал/ч 6
    v_tom_chisle_otoplenie_6 float,           -- В том числе отопление 6
    v_tom_chisle_ventilyatsiya_6 float,       -- В том числе вентиляция 6
    v_tom_chisle_gvs_maks_6 float,            -- В том числе ГВС макс 6
    prirost_nagruzki_6 float,                 -- Прирост нагрузки 6
    v_tom_chisle_prirost_otoplenie_6 float,   -- В том числе прирост отопление 6
    v_tom_chisle_prirost_ventilyatsiya_6 float,   -- В том числе прирост вентиляция 6
    v_tom_chisle_prirost_gvs_maks_6 float,    -- В том числе прирост ГВС макс 6
    dopolnitelnye_tehnicheskie_meropriyatiya_6 text,  -- Дополнительные технические мероприятия 6
    izmeneniya_prodleniya_7 text,             -- Изменения продления 7
    data_izmeneniya_prodleniya_7 date,        -- Дата изменения продления 7
    teplovye_potoki__gkal_ch_7 float,         -- Тепловые потоки, Гкал/ч 7
    v_tom_chisle_otoplenie_7 float,           -- В том числе отопление 7
    v_tom_chisle_ventilyatsiya_7 float,       -- В том числе вентиляция 7
    v_tom_chisle_gvs_maks_7 float,            -- В том числе ГВС макс 7
    prirost_nagruzki_7 float,                 -- Прирост нагрузки 7
    v_tom_chisle_prirost_otoplenie_7 float,   -- В том числе прирост отопление 7
    v_tom_chisle_prirost_ventilyatsiya_7 float,   -- В том числе прирост вентиляция 7
    v_tom_chisle_prirost_gvs_maks_7 float,    -- В том числе прирост ГВС макс 7
    dopolnitelnye_tehnicheskie_meropriyatiya_7 text,  -- Дополнительные технические мероприятия 7
    nomer_soglasovaniya_ts varchar(255),      -- Номер согласования ТС
    data_soglasovaniya_ts date,               -- Дата согласования ТС
    nomer_soglasovaniya_ov varchar(255),      -- Номер согласования ОВ
    data_soglasovaniya_ov date,               -- Дата согласования ОВ
    nomer_soglasovaniya_tp varchar(255),      -- Номер согласования ТП
    data_soglasovaniya_tp date,               -- Дата согласования ТП
    ispolnenie_dop_tehn_i_energ_meropriyatiy_v_ramkah_tu varchar(255),    -- Исполнение доп техн и энерг мероприятий в рамках ТУ
    stadiya_stroitelstva_obektov varchar(255),    -- Стадия строительства объектов
    nomer_vydachi_akta_dopuska varchar(255),  -- Номер выдачи акта допуска
    data_vydachi_akta_dopuska date,           -- Дата выдачи акта допуска
    teplovaya_nagruzka_po_aktu_dopuska__proektu__gkal_ch float,   -- Тепловая нагрузка по акту допуска (проекту) Гкал/ч
    v_tom_chisle_otoplenie_po_aktu float,     -- В том числе отопление по акту
    v_tom_chisle_ventilyatsiya_po_aktu float, -- В том числе вентиляция по акту
    v_tom_chisle_gvs_maks_po_aktu float,      -- В том числе ГВС макс по акту
    nomer_dogovora varchar(255),              -- Номер договора
    data_dogovora date,                       -- Дата договора
    zdanie int,                               -- Здание
    truba int,                                -- Труба
    kod1 varchar(10),
    uzel1 varchar(25),
    protsent_nagruzki_1 float,                -- Процент нагрузки 1
    kod2 varchar(10),
    uzel2 varchar(25),
    protsent_nagruzki_2 float,                -- Процент нагрузки 2
    kod3 varchar(10),
    uzel3 varchar(25),
    protsent_nagruzki_3 float,                -- Процент нагрузки 3
    kod4 varchar(10),
    uzel4 varchar(25),
    protsent_nagruzki_4 float,                -- Процент нагрузки 4
    kod5 varchar(10),
    uzel5 varchar(25),
    protsent_nagruzki_5 float,                -- Процент нагрузки 5
    tehnicheskie_usloviya text,               -- Технические условия
    tehnicheskie_usloviya_2 text,             -- Технические условия 2
    tehnicheskie_usloviya_3 text,             -- Технические условия 3
    tehnicheskie_usloviya_4 text,             -- Технические условия 4
    tehnicheskie_usloviya_5 text,             -- Технические условия 5
    tehnicheskie_usloviya_6 text,             -- Технические условия 6
    tehnicheskie_usloviya_7 text,             -- Технические условия 7
    tehnicheskie_usloviya_8 text,             -- Технические условия 8
    tehnicheskie_usloviya_9 text,             -- Технические условия 9
    tehnicheskie_usloviya_10 text,            -- Технические условия 10
    v_tom_chisle_gvs_sredn float,             -- В том числе ГВС средн
    v_tom_chisle_prirost_gvs_sredn float,     -- В том числе прирост ГВС средн
    v_tom_chisle_gvs_sredn_1 float,           -- В том числе ГВС средн 1
    v_tom_chisle_prirost_gvs_sredn_1 float,   -- В том числе прирост ГВС средн 1
    v_tom_chisle_gvs_sredn_2 float,           -- В том числе ГВС средн 2
    v_tom_chisle_prirost_gvs_sredn_2 float,   -- В том числе прирост ГВС средн 2
    v_tom_chisle_gvs_sredn_3 float,           -- В том числе ГВС средн 3
    v_tom_chisle_prirost_gvs_sredn_3 float,   -- В том числе прирост ГВС средн 3
    v_tom_chisle_gvs_sredn_4 float,           -- В том числе ГВС средн 4
    v_tom_chisle_prirost_gvs_sredn_4 float,   -- В том числе прирост ГВС средн 4
    v_tom_chisle_gvs_sredn_5 float,           -- В том числе ГВС средн 5
    v_tom_chisle_prirost_gvs_sredn_5 float,   -- В том числе прирост ГВС средн 5
    v_tom_chisle_gvs_sredn_6 float,           -- В том числе ГВС средн 6
    v_tom_chisle_prirost_gvs_sredn_6 float,   -- В том числе прирост ГВС средн 6
    v_tom_chisle_gvs_sredn_7 float,           -- В том числе ГВС средн 7
    v_tom_chisle_prirost_gvs_sredn_7 float,   -- В том числе прирост ГВС средн 7
    v_tom_chisle_gvs_sredn_po_aktu float      -- В том числе ГВС средн по акту
);
---------------------------------
-- zdaniya_tu - Технические условия
-- zdaniya_tu - Здания ТУ
drop table if exists zdaniya_tu;

create table zdaniya_tu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    gorod varchar(20),                        -- Город
    mikrorayon varchar(20),                   -- Микрорайон
    ulitsa varchar(30),                       -- Улица
    dom varchar(30),                          -- Дом
    kommentariy text,
    istochnik int,                            -- Источник
    rayon_ekspluatatsii int,                  -- Район эксплуатации
    kod_rs_uzla_prisoedineniya varchar(10),   -- Код РС узла присоединения
    uzel_prisoedineniya varchar(255),         -- Узел Присоединения
    shape geometry                            -- SHAPE
);
-- CREATE INDEX zdaniya_tu_shape_idx ON zdaniya_tu USING GIST (shape);
--- Технические условия: 2
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- tehnicheskie_usloviya statetu - lookup Технические условия
-- statetu - statetu
drop table if exists statetu;

create table statetu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "statetu" ("id","name","code","ord") VALUES
(1,'Действующий','Д',1),
(2,'Аннулированный','А',2),
(3,'Аннулированный по мониторингу','М',3),
(4,'Завершенный','З',4);


-- SELECT setval('"statetu_id_seq"', 4);
--- Технические условия lookup: 1
--===========================--
--        ПТС             --
--===========================--
---------------------------------
-- organizations - ПТС
-- organizations - Организации
drop table if exists organizations;

create table organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar default (NULL),              -- Наименование
    organizationTypeID int default ((1)),     -- Тип организации
    ownerOrganizationTypeID int default ((2)),    -- Признак организации
    sign varchar(50) default (NULL),          -- Примечание
    phone varchar(50) default (NULL),         -- Телефон организации
    managerPhone varchar(50) default (NULL),  -- Телефон руководителя
    street varchar(50) default (NULL),        -- Улица
    houseNumber varchar(50) default (NULL),   -- Номер дома
    id_old int default ((0)) 
);
---------------------------------
-- organizatsii_podryadchiki - ПТС
-- organizatsii_podryadchiki - Организации подрядчики
drop table if exists organizatsii_podryadchiki;

create table organizatsii_podryadchiki (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie varchar(50),                 -- Наименование
    priznak_organizatsii varchar(2),          -- Признак организации
    telefon_organizatsii varchar(50),         -- Телефон организации
    telefon_rukovoditelya varchar(50),        -- Телефон руководителя
    ulitsa varchar(50),                       -- Улица
    nomer_doma varchar(50)                    -- Номер дома
);
---------------------------------
-- organizatsii_proektnye - ПТС
-- organizatsii_proektnye - Организации проектные
drop table if exists organizatsii_proektnye;

create table organizatsii_proektnye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie varchar(50),                 -- Наименование
    telefon_organizatsii varchar(50),         -- Телефон организации
    telefon_rukovoditelya varchar(50),        -- Телефон руководителя
    gorod varchar(255),                       -- Город
    ulitsa varchar(50),                       -- Улица
    nomer_doma varchar(50)                    -- Номер дома
);
---------------------------------
-- organizatsii_obsluzhivayuschie - ПТС
-- organizatsii_obsluzhivayuschie - Организации обслуживающие
drop table if exists organizatsii_obsluzhivayuschie;

create table organizatsii_obsluzhivayuschie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizatsiya varchar(255),               -- Владелец
    otvetstvennoe_litso varchar(255),         -- Ответственное лицо
    kontaktnyy_nomer_otvetstvennogo_litsa varchar(255)    -- Контактный номер ответственного лица
);
---------------------------------
-- towns - ПТС
-- towns - towns
----- Нет таблцы towns
---------------------------------
-- districts - ПТС
-- districts - Районы
----- Нет таблцы districts
---------------------------------
-- streets - ПТС
-- streets - streets
drop table if exists streets;

create table streets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) not null,               -- Наменование
    ord int                                   -- Порядок
);
---------------------------------
-- energosistemy - ПТС
-- energosistemy - Энергосистемы
drop table if exists energosistemy;

create table energosistemy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kratkoe_naimenovanie_es varchar(255),     -- Краткое наименование ЭС
    polnoe_naimenovanie_es varchar(255)       -- Полное наименование ЭС
);
---------------------------------
-- istochniki_tepla - ПТС
-- istochniki_tepla - Источники тепла
drop table if exists istochniki_tepla;

create table istochniki_tepla (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod_istochnika varchar(25),               -- Код источника
    tip_istochnika int,                       -- Тип источника
    naimenovanie varchar(255),                -- Наименование
    rayon_ekspluatatsii int,                  -- Район эксплуатации
    god_vvoda_v_ekspluatatsiyu int,           -- Год ввода в эксплуатацию
    ustanovlennaya_moschnost float            -- Установленная мощность
);
---------------------------------
-- rayon_ekspluatatsii - ПТС
-- rayon_ekspluatatsii - Район эксплуатации
drop table if exists rayon_ekspluatatsii;

create table rayon_ekspluatatsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_rayona_ekspluatatsii_istochnika_tepla varchar(255),  -- Наименование района эксплуатации источника тепла
    nomer_po_poryadku int                     -- Номер по порядку
);
---------------------------------
-- nachalniki_uchastkov - ПТС
-- nachalniki_uchastkov - Начальники участков
drop table if exists nachalniki_uchastkov;

create table nachalniki_uchastkov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fio varchar(255),                         -- ФИО
    data_naznacheniya date,                   -- Дата приказа о назначения
    kontaktnyy_telefon varchar(255),          -- Контактный телефон
    dolzhnost int,                            -- Должность
    vid_seti int,                             -- Вид сети
    nomer_prikaza varchar(50)                 -- Номер приказа о назначении
);
---------------------------------
-- responsibles - ПТС
-- responsibles - responsibles
drop table if exists responsibles;

create table responsibles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),          -- ФИО
    statusID int                              -- Должность
);
---------------------------------
-- uchastki_ekspluatatsii - ПТС
-- uchastki_ekspluatatsii - Участки эксплуатации
drop table if exists uchastki_ekspluatatsii;

create table uchastki_ekspluatatsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    istochnik_tepla int,                      -- Источник тепла
    rayon_ekspluatatsii int,                  -- Район эксплуатации
    vid_seti int,                             -- Вид сети
    nomer_uchastka varchar(255),              -- Номер участка
    nachalnik_uchastka int                    -- Начальник участка
);
---------------------------------
-- magistrali - ПТС
-- magistrali - Магистрали
drop table if exists magistrali;

create table magistrali (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer_magistrali varchar(10),             -- Номер магистрали
    naimenovanie_magistrali varchar(10),      -- Наименование магистрали
    magistral_tgid varchar(255),              -- Магистраль ТГИД
    rayon_goroda varchar(255),                -- Район города
    istochnik_tepla int,                      -- Источник тепла
    inventarnyy_nomer varchar(10),            -- Инвентарный номер
    data_prisvoeniya_inventarnogo_nomera date,    -- Дата присвоения инвентарного номера
    inventarnyy_nomer_staryy varchar(10),     -- Инвентарный номер старый
    data_prisvoeniya_inventarnogo_nomera_starogo date,    -- Дата присвоения инвентарного номера старого
    kadastrovyy_nomer varchar(25),            -- Кадастровый номер
    opisanie varchar(255),                    -- Описание
    kontur_istochnika_tepla int               -- Контур источника тепла
);
---------------------------------
-- uchastok_ms - ПТС
-- uchastok_ms - Участок МС
drop table if exists uchastok_ms;

create table uchastok_ms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer_uchastka int,                       -- Номер участка
    kadastrovyy_nomer varchar(25),            -- Кадастровый номер
    inventarnyy_nomer varchar(10),            -- Инвентарный номер
    magistral int,                            -- Магистраль
    opisanie_uchastka_ms varchar(255),        -- Описание участка МС
    data_zapolneniya date,                    -- Дата заполнения
    energosistema varchar(50),                -- Энергосистема
    nomer_pasporta varchar(50),               -- Номер паспорта
    vid_seti varchar(50),                     -- Вид сети
    proektnaya_organizatsiya varchar(50),     -- Проектная организация
    nomer_proekta varchar(50),                -- Номер проекта
    dokumenty_registratsii varchar(255),      -- Документы регистрации
    obschaya_dlina_trassy int,                -- Общая длина трассы
    rabochee_davlenie varchar(50),            -- Рабочее давление
    rabochaya_temperatura varchar(50),        -- Рабочая температура
    god_postroyki varchar(50),                -- Год постройки
    god_vvoda_v_ekspluatatsiyu varchar(50),   -- Год ввода в эксплуатацию
    balansovaya_stoimost int,                 -- Балансовая стоимость
    god_otsenki_balansovoy_stoimosti int,     -- Год оценки балансовой стоимости
    kod1 varchar(10),
    uzel1 varchar(25),                        -- Наименование начальной камеры
    kod2 varchar(10),
    uzel2 varchar(25),                        -- Наименование кончной камеры
    responsibleID int,                        -- Ответственное лицо
    prinadlezhnostID int,                     -- Принадлежность
    nomer_prikaza varchar(255),               -- Номер приказа о назначении
    data_prikaza timestamp,                   -- Дата приказа о назначении
    istochniki_teplosnabzheniya int           -- Источник теплоснабжения
);
---------------------------------
-- uchastok_rs - ПТС
-- uchastok_rs - Участок РС
drop table if exists uchastok_rs;

create table uchastok_rs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer_uchastka int,                       -- Номер участка
    magistral int,                            -- Магистраль
    kadastrovyy_nomer varchar(25),            -- Кадастровый номер
    inventarnyy_nomer varchar(10),            -- Инвентарный номер
    data_prisvoeniya_inventarnogo_nomera date,    -- Дата присвоения инвентарного номера
    naimenovanie_uchastka_rs varchar(255),    -- Наименование участка РС
    uzel_podklyucheniya varchar(255),         -- Узел подключения
    konechnyy_uzel varchar(255),              -- Конечный узел
    data_zapolneniya date,                    -- Дата заполнения
    registratsionnyy_nomer varchar(50),       -- Регистрационный номер
    predpriyatie_vladelets int,               -- Предприятие владелец
    adres_predpriyatiya_vladeltsa varchar(50),    -- Адрес предприятия владельца
    naznachenie_rs varchar(50),               -- Назначение РС
    rabochaya_sreda varchar(255),             -- Рабочая среда
    rabochee_davlenie varchar(50),            -- Рабочее давление
    rabochaya_temperatura varchar(50),        -- Рабочая температура
    raschetnyy_srok_sluzhby_let int,          -- Расчетный срок службы,лет
    raschetnyy_resurs_chasov int,             -- Расчетный ресурс,часов
    raschetnoe_chislo_puskov int,             -- Расчетное число пусков
    proektnye_dokumenty text,                 -- Проектные документы
    kod1 varchar(10),                         -- Код РС1
    uzel1 varchar(25),                        -- Наименование начальной камеры
    kod2 varchar(10),                         -- Код РС2
    uzel2 varchar(25),                        -- Наименование кончной камеры
    responsibleID int,                        -- Ответственное лицо
    prinadlezhnostID int,                     -- Принадлежность
    nomer_prikaza varchar(255),               -- Номер приказа о назначении
    data_prikaza timestamp                    -- Дата приказа о назначении
);
---------------------------------
-- heating_seasons - ПТС
-- heating_seasons - Отопительные сезоны
drop table if exists heating_seasons;

create table heating_seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date1 timestamp,                          -- Дата начала отопительного сезона
    date2 timestamp                           -- Дата окончания отопительного сезона
);
--- ПТС: 17
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- organizations organizationtypes - lookup ПТС
-- organizationtypes - Типы организаций
drop table if exists organizationtypes;

create table organizationtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);

INSERT INTO "organizationtypes" ("id","name") VALUES
(1,'Владелец'),
(2,'Обслуживающая'),
(3,'Подрядчик'),
(4,'Проектная');


-- SELECT setval('"organizationtypes_id_seq"', 4);

---------------------------------
-- uchastok_rs dolzhnosti - lookup ПТС
-- dolzhnosti - Должности
drop table if exists dolzhnosti;

create table dolzhnosti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255)                    -- Должность
);

INSERT INTO "dolzhnosti" ("id","znachenie") VALUES
(9,'Инженер производственной службы'),
(10,'Инженер службы перспективного развития'),
(11,'Инженер службы эксплуатации'),
(12,'Начальник производственной службы'),
(13,'Начальник службы эксплуатации'),
(14,'Начальник участка'),
(15,'Техник'),
(19,'????'),
(20,'Заместитель председателя правления по производству'),
(21,'техник'),
(22,'техник'),
(23,'техник');


-- SELECT setval('"dolzhnosti_id_seq"', 23);

---------------------------------
-- uchastok_rs prinadlezhnost - lookup ПТС
-- prinadlezhnost - prinadlezhnost
drop table if exists prinadlezhnost;

create table prinadlezhnost (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "prinadlezhnost" ("id","name","code","ord") VALUES
(1,'На балансе',NULL,1),
(2,'Потебительсккая сеть',NULL,2),
(3,'Обслуживание',NULL,3);


-- SELECT setval('"prinadlezhnost_id_seq"', 3);
--- ПТС lookup: 3
--===========================--
--        Индикаторы коррозии             --
--===========================--
---------------------------------
-- indikator_korrozii - Индикаторы коррозии
-- indikator_korrozii - Индикатор_коррозии
drop table if exists indikator_korrozii;

create table indikator_korrozii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    sostoyanie int default ((1)),             -- Состояние
    uchastok_ekspluatatsii varchar(255),      -- Участок эксплуатации
    istochnik_tepla varchar(255),             -- Источник тепла
    magistral_raspredset varchar(255),        -- Магистраль/Распредсеть
    nachalnik_uchastka varchar(255),          -- Начальник участка
    god_vvoda_v_ekspluatatsiyu date,          -- Год ввода в эксплуатацию
    vid_prokladki int,                        -- Вид прокладки
    ulitsa varchar(255),                      -- Улица
    nomer_doma varchar(255),                  -- Номер дома
    teplonositel int default ((1)),           -- Теплоноситель
    kod_rs_nachalnoy_kamery varchar(255),     -- Код РС начальной камеры
    nachalnaya_kamera varchar(255),           -- Начальная камера
    kod_rs_konechnoy_kamery varchar(255),     -- Код РС конечной камеры
    konechnaya_kamera varchar(255),           -- Конечная камера
    kod_rs_blizhayshey_kamery varchar(255),   -- Код РС ближайшей камеры
    blizhayshaya_kamera varchar(255),         -- Ближайшая камера
    rasstoyanie_do_kamery__m float,           -- Расстояние до камеры, м
    diametr_truby_podayuschiy__uslovn__mm float,  -- Диаметр трубы подающий, условн, мм
    diametr_truby_obratnyy__uslovn__mm float, -- Диаметр трубы обратный, условн, мм
    nomer_indikatora_korrozii varchar(255),   -- Номер индикатора коррозии
    truboprovod int default ((1)),            -- Трубопровод
    kolichestvo_plastin_v_sborke int default ((3)),   -- Количество пластин в сборке
    sredniy_ves_plastiny_pri_ustanovke__g float,  -- Средний вес пластины при установке, г
    radius_krugloy_plastiny__mm float default ((24)), -- Радиус круглой пластины, мм
    radius_vtulki__mm float default ((7.5)),  -- Радиус втулки, мм
    tolschina_plastiny__mm float default ((3)),   -- Толщина пластины, мм
    data_ustanovki date,                      -- Дата установки
    data_izvlecheniya date,                   -- Дата извлечения
    sredniy_ves_plastiny_posle_ispytaniy__g float,    -- Средний вес пластины после испытаний, г
    poterya_massy_srednyaya_pri_kislotnoy_obraboke__g float,  -- Потеря массы средняя при кислотной обрабоке, г
    srednyaya_skorost_korrozii__mm_god float, -- Средняя скорость коррозии, мм/год
    otsenka_korrozionnogo_protsessa int,      -- Оценка коррозионного процесса
    agressivnost_setevoy_vody int,            -- Агрессивность сетевой воды
    vneshniy_vid_plastin text,                -- Внешний вид пластин
    shape geometry,
    save_r int,
    result int,
    dolzhnostID int,                          -- Должность ответственного (исполнителя)
    responsibleID int,                        -- ФИО ответственного (исполнителя)
    stateIndID int,                           -- Состояние стержня
    data_planirovaniya date,                  -- Дата планирования
    regimID int,
    mesto_ustanovki varchar(255),             -- Место установки
    primechanie varchar,                      -- Примечание
    spisok_plastin_pri_ustanovke varchar,
    spisok_plastin_posle_ispytaniy varchar 
);
CREATE INDEX indikator_korrozii_lineid_idx ON indikator_korrozii (lineid);
CREATE INDEX indikator_korrozii_nodeid_idx ON indikator_korrozii (nodeid);
-- CREATE INDEX indikator_korrozii_shape_idx ON indikator_korrozii USING GIST (shape);
---------------------------------
-- indikator_korrozii_po_godam - Индикаторы коррозии
-- indikator_korrozii_po_godam - Индикатор_коррозии_по_годам
drop table if exists indikator_korrozii_po_godam;

create table indikator_korrozii_po_godam (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_i int,
    tekuschiy_nomer varchar(255),             -- Текущий номер
    nomer_indikatora_korrozii varchar(255),   -- Номер индикатора коррозии
    truboprovod varchar(255),                 -- Трубопровод
    kolichestvo_plastin_v_sborke int,         -- Количество пластин в сборке
    sredniy_ves_plastiny_pri_ustanovke__g float,  -- Средний вес пластины при установке, г
    radius_krugloy_plastiny__mm float,        -- Радиус круглой пластины, мм
    radius_vtulki__mm float,                  -- Радиус втулки, мм
    tolschina_plastiny__mm float,             -- Толщина пластины, мм
    data_ustanovki date,                      -- Дата установки
    data_izvlecheniya date,                   -- Дата извлечения
    kolichestvo_dney_ispytaniy int,           -- Количество дней испытаний
    sredniy_ves_plastiny_posle_ispytaniy__g float,    -- Средний вес пластины после испытаний, г
    poterya_massy_srednyaya_pri_kislotnoy_obraboke__g float,  -- Потеря массы средняя при кислотной обрабоке, г
    srednyaya_skorost_korrozii__mm_god float, -- Средняя скорость коррозии, мм/год
    otsenka_korrozionnogo_protsessa int,      -- Оценка коррозионного процесса
    agressivnost_setevoy_vody int,            -- Агрессивность сетевой воды
    vneshniy_vid_plastin text,                -- Внешний вид пластин
    sostoyanie int,                           -- Состояние
    stateIndID int,                           -- Состояние стержня
    data_planirovaniya date,                  -- Дата планирования
    primechanie varchar,
    spisok_plastin_pri_ustanovke varchar,
    spisok_plastin_posle_ispytaniy varchar 
);
--- Индикаторы коррозии: 2
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- indikator_korrozii dolzhnosti_korrozia - lookup Индикаторы коррозии
-- dolzhnosti_korrozia - Должности коррозия
drop table if exists dolzhnosti_korrozia;

create table dolzhnosti_korrozia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255)                    -- Должность
);

INSERT INTO "dolzhnosti_korrozia" ("id","znachenie") VALUES
(1,'Ведущий инженер'),
(2,'Лаборант');


-- SELECT setval('"dolzhnosti_korrozia_id_seq"', 2);

---------------------------------
-- indikator_korrozii responsibles_korrozia - lookup Индикаторы коррозии
-- responsibles_korrozia - Ответственные по химической службе
drop table if exists responsibles_korrozia;

create table responsibles_korrozia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50),                         -- ФИО
    statusID int                              -- Должность
);

INSERT INTO "responsibles_korrozia" ("id","name","statusid") VALUES
(1,'Есмуханбетова А.К.',NULL),
(2,'Шогалова К.Х.',NULL);


-- SELECT setval('"responsibles_korrozia_id_seq"', 2);

---------------------------------
-- indikator_korrozii stateindicator - lookup Индикаторы коррозии
-- stateindicator - Состояние индикатора коррозии
drop table if exists stateindicator;

create table stateindicator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "stateindicator" ("id","name","code","ord") VALUES
(1,'План','П',1),
(2,'Анализ','А',2),
(3,'После расчета','Р',3),
(4,'Архивный','А',4);


-- SELECT setval('"stateindicator_id_seq"', 4);

---------------------------------
-- indikator_korrozii netwateraggressivenesses - lookup Индикаторы коррозии
-- netwateraggressivenesses - netwateraggressivenesses
drop table if exists netwateraggressivenesses;

create table netwateraggressivenesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "netwateraggressivenesses" ("id","name","code","ord") VALUES
(1,'Низкая','НАДО',1),
(2,'Допустимая','НАДО',2),
(3,'Высокая','НАДО',3),
(4,'Аварийная','НАДО',4);


-- SELECT setval('"netwateraggressivenesses_id_seq"', 4);

---------------------------------
-- indikator_korrozii corrosionprocessmarks - lookup Индикаторы коррозии
-- corrosionprocessmarks - Метки коррозионных процессов
drop table if exists corrosionprocessmarks;

create table corrosionprocessmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "corrosionprocessmarks" ("id","name","code","ord") VALUES
(1,'Незначительный','НАДО',1),
(2,'Слабый','НАДО',2),
(3,'Средний','НАДО',3),
(4,'Сильный ','НАДО',4),
(5,'Аварийный','НАДО',5);


-- SELECT setval('"corrosionprocessmarks_id_seq"', 5);

---------------------------------
-- indikator_korrozii stateinds - lookup Индикаторы коррозии
-- stateinds - stateinds
drop table if exists stateinds;

create table stateinds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null 
);

INSERT INTO "stateinds" ("id","name") VALUES
(1,'Извлечение'),
(2,'Провал стержня');


-- SELECT setval('"stateinds_id_seq"', 2);
--- Индикаторы коррозии lookup: 6
--===========================--
--        ПТС 2             --
--===========================--
---------------------------------
-- perehlesty_setey - ПТС 2
-- perehlesty_setey - Перехлесты сетей
drop table if exists perehlesty_setey;

create table perehlesty_setey (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    vysotnaya_otmetka float,                  -- Высотная отметка,м
    primechanie varchar,                      -- Примечание
    shape geometry 
);
CREATE INDEX perehlesty_setey_lineid_idx ON perehlesty_setey (lineid);
-- CREATE INDEX perehlesty_setey_shape_idx ON perehlesty_setey USING GIST (shape);
---------------------------------
-- ugol_povorota_truboprovoda - ПТС 2
-- ugol_povorota_truboprovoda - Угол поворота трубопровода
drop table if exists ugol_povorota_truboprovoda;

create table ugol_povorota_truboprovoda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    naimenovanie_nachalnogo_uzla_truby varchar(255),  -- Наименование начального узла трубы
    naimenovanie_konechnogo_uzla_truby varchar(255),  -- Наименование конечного узла трубы
    vysotnaya_otmetka float,                  -- Высотная отметка
    diametr_truboprovoda varchar(50),         -- Диаметр трубопровода
    ugol_povorota int,                        -- Угол поворота
    primechanie varchar(255),                 -- Примечание
    id_geopoint int,
    shape geometry 
);
CREATE INDEX ugol_povorota_truboprovoda_lineid_idx ON ugol_povorota_truboprovoda (lineid);
CREATE INDEX ugol_povorota_truboprovoda_nodeid_idx ON ugol_povorota_truboprovoda (nodeid);
-- CREATE INDEX ugol_povorota_truboprovoda_shape_idx ON ugol_povorota_truboprovoda USING GIST (shape);
---------------------------------
-- kamera_opuska_ili_podema - ПТС 2
-- kamera_opuska_ili_podema - Камера опуска или подъема
drop table if exists kamera_opuska_ili_podema;

create table kamera_opuska_ili_podema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    dlina float,                              -- Длина,м
    shirina float,                            -- Ширина,м
    vysota float,                             -- Высота,м
    glubina_zalozheniya float,                -- Глубина заложения,м
    diametr float,                            -- Диамертр,мм
    otmetka_verha float,                      -- Отметка верха,м
    otmetka_niza float,                       -- Отметка низа,м
    yuridicheskoe_litso int,                  -- Юридическое лицо
    primechanie varchar,                      -- Примечание
    material int,                             -- Материал
    shape geometry 
);
CREATE INDEX kamera_opuska_ili_podema_lineid_idx ON kamera_opuska_ili_podema (lineid);
-- CREATE INDEX kamera_opuska_ili_podema_shape_idx ON kamera_opuska_ili_podema USING GIST (shape);
---------------------------------
-- vozdushnik - ПТС 2
-- vozdushnik - Воздушник
drop table if exists vozdushnik;

create table vozdushnik (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    d1 float,                                 -- Диаметр на подаче, м.вод.ст
    d2 float,                                 -- Диаметр на обратке, м.вод.ст
    dav1 float,                               -- Давление на подаче, мм
    dav2 float,                               -- Давление на обратке, мм
    m1 int,                                   -- Материал на подаче
    m2 int,                                   -- Материал на обратке
    arm1 int,                                 -- Тип арматуры на подаче
    arm2 int,                                 -- Тип арматуры на обратке
    dav float,                                -- Рабочее давление
    lineID int,
    nodeID int,
    mestoraspolozhenie int,                   -- Месторасположение
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    tip_spusknoy_armatury int,                -- Тип спускной арматуры
    diametr_old varchar(50),
    material int,                             -- Материал
    rabochee_davlenie varchar(50),            -- Рабочее давление
    god_vvoda varchar(50),                    -- Год ввода
    nomer varchar(255),                       -- Номер
    shema varchar,                            -- Схема
    primechanie varchar(255),                 -- Примечание
    prinadlezhnost varchar(50),               -- Принадлежность
    designTypesID int,                        -- Исполнение
    constructionTypesID int,                  -- Конструкция
    armatureTypesID int,                      -- Тип арматуры
    materialTypesID int,                      -- Материал
    diametr float,                            -- Диаметр, мм
    purposeTypesID int default ((4)),         -- Назначение
    locationTypesID int,                      -- Месторасположение
    shape geometry 
);
CREATE INDEX vozdushnik_lineid_idx ON vozdushnik (lineid);
CREATE INDEX vozdushnik_nodeid_idx ON vozdushnik (nodeid);
-- CREATE INDEX vozdushnik_shape_idx ON vozdushnik USING GIST (shape);
---------------------------------
-- +lyuki - ПТС 2
-- +lyuki - +lyuki
----- Нет таблцы +lyuki
---------------------------------
-- peremychki - ПТС 2
-- peremychki - Перемычки
drop table if exists peremychki;

create table peremychki (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    priznak_truboprovoda int,                 -- Признак трубпровода
    mesto_ustanovki varchar,                  -- Место установки
    diametr_peremychki float,                 -- Диаметр пермычки,мм
    otklyuchayuschaya_armatura int,           -- Отключающая арматура
    diametr_otklyuch_armatury float,          -- Диаметр отключающей арматуры,мм
    spusknaya_armatura int,                   -- Спускная арматура
    diametr_spuskn_armatury float,            -- Диаметр спускной арматуры,мм
    prinadlezhnost varchar,                   -- Принадлежность
    designTypesID int,
    constructionTypesID int,
    armatureTypesID int,
    materialTypesID int,
    shape geometry 
);
CREATE INDEX peremychki_lineid_idx ON peremychki (lineid);
-- CREATE INDEX peremychki_shape_idx ON peremychki USING GIST (shape);
---------------------------------
-- bridge_crossing - ПТС 2
-- bridge_crossing - Мостовой переход
drop table if exists bridge_crossing;

create table bridge_crossing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    length float,                             -- Длина,м
    nomer_chertezha varchar,                  -- Номер чертежа
    primechanie varchar(255),                 -- Примечание
    shape geometry 
);
-- CREATE INDEX bridge_crossing_shape_idx ON bridge_crossing USING GIST (shape);
---------------------------------
-- nasosnye_stantsii - ПТС 2
-- nasosnye_stantsii - Насосная станция
drop table if exists nasosnye_stantsii;

create table nasosnye_stantsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    reg_nomer int,                            -- Регистрационный номер
    god_stroitelstva varchar(50),             -- Год строительства
    proizvoditelnost varchar(50),             -- Производительность
    kolichestvo_nasosov_na_podache int,       -- Количество насосов на подаче
    kolichestvo_nasosov_na_obratke int,       -- Количество насосов на обратке
    primechanie varchar,                      -- Примечание
    shema varchar,                            -- Схема
    shape geometry 
);
CREATE INDEX nasosnye_stantsii_lineid_idx ON nasosnye_stantsii (lineid);
-- CREATE INDEX nasosnye_stantsii_shape_idx ON nasosnye_stantsii USING GIST (shape);
---------------------------------
-- pavilion - ПТС 2
-- pavilion - Павильон
drop table if exists pavilion;

create table pavilion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    razmery_perekrytiya int,                  -- Размеры перекрытия
    kolichestvo_perekrytiy int,               -- Количество перекрытий
    vnutr_vysota_kamery float,                -- Внутренняя высота камеры
    vnutr_shirina_kamery float,               -- Внутренняя ширина камеры
    vnutr_dlina_kamery float,                 -- Внутренняя длина камеры
    zaglublenie_ot_verha_lyuka_do_n float,    -- Заглубление от верха люка до н
    vozvyshenie_verha_plity_perekry float,    -- Возвышение верха плиты перекры
    fakticheskoe_kolichestvo_lyukov int,      -- Фактическое количество люков
    kolichestvo_deystvuyuschiy_lyukov int,    -- Количество действующиы люков
    kolichestvo_chugunnyh_lyukov int,         -- Количество чугунных люков
    kolichestvo_stalnyh_lyukov int,           -- Количество сталных люков
    kolichestvo_zapirayuschih_lyukov int,     -- Количество запирающих люков
    kolichestvo_dren_armatury int,            -- Количество дрен арматуры
    harakteristika_dren_armatury varchar(50), -- Характеристика дрен арматуры
    kolichestvo_dren_liniy int,               -- Количество дрен линий
    harakteristika_dren_liniy varchar(50),    -- Характеристика дрен линий
    kolichestvo_dren_kolodtsev int,           -- Количество дрен колодцев
    harakteristika_dren_kolodtsev varchar(50),    -- Характеристика дрен колодцев
    kolichestvo_tochek_zamera int,            -- Количество точек замера
    harakteristika_tochek_zamera varchar(50), -- Характеристика точек замера
    vid_stroeniya varchar(50),                -- Вид строения
    koordinirovano int,                       -- Координировано
    fizicheskoe_litso int,                    -- Физическое лицо
    yuridicheskoe_litso int,                  -- Юридическое лицо
    primechanie varchar(250),                 -- Примечание
    dno_kamery float,                         -- Дно камеры, м
    steny int,                                -- Стены
    perekrytie int,                           -- Перекрытие
    shema varchar(100),                       -- Схема
    square float,                             -- Площадь, м^2
    oborudovanie_pavilona varchar,            -- Оборудование павильона
    god_poslednego_vvoda_v_jekspluataciju timestamp,  -- Год ввода в эксплуатацию
    god_poslednego_remonta timestamp,         -- Год последнего ремонта
    sredstva_pozharotushenija int,            -- Средства пожаротушения
    signalizacija int,                        -- Сигнализация
    nalichie_osveshhenija int,                -- Наличие освещения
    nalichie_shem_truboprovodov int,          -- Наличие схем трубопроводов
    organizationID int,                       -- Балансовая принадлежность
    constructionTypesID int,                  -- Конструкция
    locationTypesID int,                      -- Месторасположение
    shape geometry 
);
CREATE INDEX pavilion_lineid_idx ON pavilion (lineid);
-- CREATE INDEX pavilion_shape_idx ON pavilion USING GIST (shape);
---------------------------------
-- tstrp - ПТС 2
-- tstrp - ЦТРП
drop table if exists tstrp;

create table tstrp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    name varchar,                             -- Наименование
    shape geometry 
);
CREATE INDEX tstrp_lineid_idx ON tstrp (lineid);
-- CREATE INDEX tstrp_shape_idx ON tstrp USING GIST (shape);
---------------------------------
-- kompensator - ПТС 2
-- kompensator - Компенсатор
drop table if exists kompensator;

create table kompensator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    naimenovanie_nachalnogo_uzla_truby varchar(255),  -- Наименование начального узла трубы
    naimenovanie_konechnogo_uzla_truby varchar(255),  -- Наименование конечного узла трубы
    tip_kompensatora int,                     -- Тип компенсатора
    forma_radialnogo_kompensatora int,        -- Форма радиального компенсатора
    vid_osevogo_kompensatora int,             -- Вид осевого компенсатора
    diametr_truboprovoda int,                 -- Диаметр трубопровода
    spina float,                              -- Спина
    vylet float,                              -- Вылет
    nomer_kompensatora varchar(255),          -- Номер компенсатора
    god_vvoda varchar(50),                    -- Год ввода
    shema text,                               -- Схема
    primechanie varchar(255),                 -- Примечание
    fizicheskoe_litso int,                    -- Физическое лицо
    yuridicheskoe_litso int,                  -- Юридическое лицо
    prinadlezhnost varchar(50),               -- Принадлежность
    shape geometry,
    constructionTypesID int                   -- Конструкция
);
CREATE INDEX kompensator_lineid_idx ON kompensator (lineid);
CREATE INDEX kompensator_nodeid_idx ON kompensator (nodeid);
-- CREATE INDEX kompensator_shape_idx ON kompensator USING GIST (shape);
---------------------------------
-- vvody_v_zdanie - ПТС 2
-- vvody_v_zdanie - Вводы в здание
drop table if exists vvody_v_zdanie;

create table vvody_v_zdanie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    vysotnaya_otmetka float,                  -- Высотная отметка
    primechanie varchar,                      -- Примечание
    sposob_vvoda int,                         -- Способ ввода
    shape geometry 
);
CREATE INDEX vvody_v_zdanie_lineid_idx ON vvody_v_zdanie (lineid);
-- CREATE INDEX vvody_v_zdanie_shape_idx ON vvody_v_zdanie USING GIST (shape);
---------------------------------
-- tkamera - ПТС 2
-- tkamera - Тепловая камера
drop table if exists tkamera;

create table tkamera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    razmery_perekrytiya int,                  -- Размеры перекрытия
    kolichestvo_perekrytiy int,               -- Количество перекрытий
    vnutr_vysota_kamery float,                -- Внутренняя высота камеры, мм
    vnutr_shirina_kamery float,               -- Внутренняя ширина камеры, мм
    vnutr_dlina_kamery float,                 -- Внутренняя длина камеры, м
    zaglublenie_ot_verha_lyuka_do_n float,    -- Заглубление от верха люка до низа
    vozvyshenie_verha_plity_perekry float,    -- Возвышение верха плиты перекры, шт
    fakticheskoe_kolichestvo_lyukov int,      -- Фактическое количество люков, шт
    kolichestvo_deystvuyuschiy_lyukov int,    -- Количество действующиы люков, шт
    kolichestvo_chugunnyh_lyukov int,         -- Количество чугунных люков, шт
    kolichestvo_stalnyh_lyukov int,           -- Количество сталных люков, шт
    kolichestvo_zapirayuschih_lyukov int,     -- Количество запирающих люков, шт
    kolichestvo_dren_armatury int,            -- Количество дрен арматуры, шт
    harakteristika_dren_armatury varchar(50), -- Характеристика дрен арматуры
    kolichestvo_dren_liniy int,               -- Количество дрен линий, шт
    harakteristika_dren_liniy varchar(50),    -- Характеристика дрен линий
    kolichestvo_dren_kolodtsev int,           -- Количество дрен колодцев
    harakteristika_dren_kolodtsev varchar(50),    -- Характеристика дрен колодцев
    kolichestvo_tochek_zamera int,            -- Количество точек замера
    harakteristika_tochek_zamera varchar(50), -- Характеристика точек замера
    vid_stroeniya varchar(50),                -- Вид строения
    koordinirovano int,                       -- Координировано
    fizicheskoe_litso int,                    -- Физическое лицо
    yuridicheskoe_litso int,                  -- Юридическое лицо
    primechanie varchar(250),                 -- Примечание
    dno_kamery float,                         -- Дно камеры, м
    steny int,                                -- Стены
    perekrytie int,                           -- Перекрытие
    shema varchar(100),                       -- Схема
    tip_kamery int,                           -- Тип камеры
    tip_perekrytiya_kamery int,               -- Тип перекрытия камеры
    nalichie_reshetok int,                    -- Наличие решеток
    konstrukcija_kamery varchar(50),          -- Конструкция камеры
    god_vvoda_v_jekspluataciju timestamp,     -- Год ввода в эксплуатацию
    god_poslednego_remonta timestamp,         -- Год последнего ремонта
    organizationID int,                       -- Балансовая принадлежность
    constructionTypesID int,                  -- Конструкция
    constructionOverlapTypesID int,           -- Конструкция перекрытия
    overlapTypesID int,                       -- Тип перекрытия
    shape geometry,
    kolichestvo_zhelezobet_lyukov int,        -- Количество железобетонных люков, шт
    kolichestvo_polymer_lyukov int            -- Количество полимерных люков, шт
);
CREATE INDEX tkamera_lineid_idx ON tkamera (lineid);
-- CREATE INDEX tkamera_shape_idx ON tkamera USING GIST (shape);
---------------------------------
-- kolodtsy - ПТС 2
-- kolodtsy - Колодец
drop table if exists kolodtsy;

create table kolodtsy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    diametr float,                            -- Диаметр, мм
    otmetka_lyuka float,                      -- Отметка люка, м
    otmetka_dna float,                        -- Отметка дна, м
    sostoyanie int,
    material int,
    primechanie varchar(250),                 -- Примечание
    purposeTypesID int,                       -- Назначение
    characteristicTypesID int,                -- Характеристика колодца
    characteristicTypesIDlyuki int,           -- Характеристика люка
    materialTypesIDlyuki int,                 -- Материал люка
    constructionTypesIDlyuki int,             -- Конструкция люка
    diametrLyuki float,                       -- Диаметр люка, мм
    priznak_truboprovoda int,                 -- Признак трубопровода
    shape geometry,
    shema varchar(255)                        -- Схема
);
CREATE INDEX kolodtsy_lineid_idx ON kolodtsy (lineid);
-- CREATE INDEX kolodtsy_shape_idx ON kolodtsy USING GIST (shape);
---------------------------------
-- vvod_v_zdanie - ПТС 2
-- vvod_v_zdanie - Ввод в здание
----- Нет таблцы vvod_v_zdanie
---------------------------------
-- vertikalnyy_podem_opusk_truprovoda - ПТС 2
-- vertikalnyy_podem_opusk_truprovoda - Вертикальный подъем опуск трубопровода
drop table if exists vertikalnyy_podem_opusk_truprovoda;

create table vertikalnyy_podem_opusk_truprovoda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    text varchar(50),                         -- Подпись
    shape geometry 
);
CREATE INDEX vertikalnyy_podem_opusk_truprovoda_lineid_idx ON vertikalnyy_podem_opusk_truprovoda (lineid);
CREATE INDEX vertikalnyy_podem_opusk_truprovoda_nodeid_idx ON vertikalnyy_podem_opusk_truprovoda (nodeid);
-- CREATE INDEX vertikalnyy_podem_opusk_truprovoda_shape_idx ON vertikalnyy_podem_opusk_truprovoda USING GIST (shape);
---------------------------------
-- opora - ПТС 2
-- opora - Опора
drop table if exists opora;

create table opora (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- Номер
    lineID int default (NULL),                -- Номер участка
    nodeID int default (NULL),
    mestoraspolozhenie int,                   -- Месторасположение
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    naimenovanie_nachalnogo_uzla_truby varchar(255),  -- Наименование начального узла трубы
    naimenovanie_konechnogo_uzla_truby varchar(255),  -- Наименование конечного узла трубы
    naimenovanie_uzla_kamery_pavilona varchar(255),   -- Наименование узла камеры/павильона
    vysotnaya_otmetka float,                  -- Высотная отметка
    stroitelnaya_konstruktsiya int,           -- Строительная конструкция
    nomer_opory varchar(50),                  -- Номер опоры
    prinadlezhnost varchar(50),               -- Принадлежность
    vid_opory int,                            -- Вид опоры
    shema text,                               -- Схема
    primechanie varchar(255),                 -- Примечание
    vysota_stroitelnaya_konstruktsi float,    -- Высота строительная конструкци
    nomer_shvellera varchar(10),              -- Номер швеллера
    kolichestvo_uporov int,                   -- Количество упоров
    shape geometry,
    constructionTypesID int                   -- Конструкция
);
CREATE INDEX opora_lineid_idx ON opora (lineid);
CREATE INDEX opora_nodeid_idx ON opora (nodeid);
-- CREATE INDEX opora_shape_idx ON opora USING GIST (shape);
---------------------------------
-- granitsy_vertikalnyh_kompensatorov - ПТС 2
-- granitsy_vertikalnyh_kompensatorov - Границы вертикальных компенсаторов
drop table if exists granitsy_vertikalnyh_kompensatorov;

create table granitsy_vertikalnyh_kompensatorov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    vysotnaya_otmetka_verha float,            -- Высотная отметка верха трубы, м
    vysotnaya_otmetka_niza float,             -- Высотная отметка низа трубы, м
    primechanie varchar,                      -- Примечание
    shape geometry 
);
CREATE INDEX granitsy_vertikalnyh_kompensatorov_lineid_idx ON granitsy_vertikalnyh_kompensatorov (lineid);
-- CREATE INDEX granitsy_vertikalnyh_kompensatorov_shape_idx ON granitsy_vertikalnyh_kompensatorov USING GIST (shape);
---------------------------------
-- duker - ПТС 2
-- duker - Дюкер
drop table if exists duker;

create table duker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    length float,
    nomer_chertezha varchar,                  -- Номер чертежа
    primechanie varchar(255),                 -- Примечание
    shape geometry 
);
-- CREATE INDEX duker_shape_idx ON duker USING GIST (shape);
---------------------------------
-- drenazhnyy_truboprovod - ПТС 2
-- drenazhnyy_truboprovod - Дренажный трубопровод
drop table if exists drenazhnyy_truboprovod;

create table drenazhnyy_truboprovod (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_dop varchar(150),
    amount_tr varchar(50),
    material_u varchar(50),
    diametr_up varchar(50),
    material_d varchar(50),
    diametr_do varchar(50),
    state_dop varchar(50),
    position_ varchar(50),
    id_style varchar(8),
    owner_dop varchar(254),
    planshet_c varchar(50),
    ground_con varchar(50),
    territoryi int,
    note_ varchar(250),
    type_dop varchar(50),
    temp_up varchar(50),
    temp_down varchar(50),
    id_style1 int,
    out_diamet varchar(150),
    data_intro varchar(150),
    ss varchar(254),
    shape_leng float,
    shape geometry,
    priznak_truboprovoda int,
    diameter float 
);
-- CREATE INDEX drenazhnyy_truboprovod_shape_idx ON drenazhnyy_truboprovod USING GIST (shape);
---------------------------------
-- kanal - ПТС 2
-- kanal - Канал
drop table if exists kanal;

create table kanal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    id__truboprovod int,                      -- ID Трубопровод
    nachalnaya_kamera varchar(255),           -- Начальная камера
    konechnaya_kamera varchar(255),           -- Конечная камера
    tip_kanala varchar(255),                  -- Тип канала старый
    konstruktsiya varchar(255),               -- Конструкция старая
    shirina__mm float,                        -- Ширина на входе, мм
    vysota__mm float,                         -- Высота на входе, мм
    dlina__mm float,                          -- Длина, м
    diametr_truby__uslovnyy__mm int,          -- Диаметр трубы, условный, мм
    material int,                             -- Тип перекрытия/Материал
    kolichestvo_drenazhnyh_liniy int,         -- Количество дренажных линий
    nalichie_gidroizolyatsii int,             -- Наличие гидроизоляции
    god_vvoda_v_ekspluatatsiyu date,          -- Год ввода в эксплуатацию
    shema varchar(255),                       -- Схема
    primechanie varchar(255),                 -- Примечание
    kod1 varchar(5),
    uzel1 varchar(25),
    kod2 varchar(5),
    uzel2 varchar(25),
    drenazhnye_linii int,                     -- Дренажные линии
    fizicheskoe_litso int,                    -- Физическое лицо
    yuridicheskoe_litso int,                  -- Юридическое лицо
    name_typ int,                             -- name typ
    shape geometry,
    channelTypeID int,                        -- Тип канала
    constructionTypesID int,                  -- Конструкция
    overlapTypesID int,                       -- Тип перекрытия
    materialTypesID int,                      -- Материал
    shirina__mm__out float,                   -- Ширина на выходе, мм
    vysota__mm__out float                     -- Высота на выходе, мм
);
CREATE INDEX kanal_lineid_idx ON kanal (lineid);
CREATE INDEX kanal_nodeid_idx ON kanal (nodeid);
-- CREATE INDEX kanal_shape_idx ON kanal USING GIST (shape);
---------------------------------
-- drenazhnyy_kran - ПТС 2
-- drenazhnyy_kran - Дренажный кран
drop table if exists drenazhnyy_kran;

create table drenazhnyy_kran (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    d1 float,                                 -- Диаметр на подаче, м.вод.ст
    d2 float,                                 -- Диаметр на обратке, м.вод.ст
    dav1 float,                               -- Давление на подаче, мм
    dav2 float,                               -- Давление на обратке, мм
    m1 int,                                   -- Материал на подаче
    m2 int,                                   -- Материал на обратке
    arm1 int,                                 -- Тип арматуры на подаче
    arm2 int,                                 -- Тип арматуры на обратке
    dav float,                                -- Рабочее давление
    lineID int,
    nodeID int,
    mestoraspolozhenie int,                   -- Месторасположение
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    tip_spusknoy_armatury int,                -- Тип спускной арматуры
    diametr_old varchar(50),
    material int,                             -- Материал
    rabochee_davlenie varchar(50),            -- Рабочее давление
    god_vvoda varchar(50),                    -- Год ввода
    nomer varchar(255),                       -- Номер
    shema varchar,                            -- Схема
    primechanie varchar(255),                 -- Примечание
    prinadlezhnost varchar(50),               -- Принадлежность
    designTypesID int,                        -- Исполнение
    constructionTypesID int,                  -- Конструкция
    armatureTypesID int,                      -- Тип арматуры
    materialTypesID int,                      -- Материал
    diametr float,                            -- Диаметр, мм
    purposeTypesID int default ((3)),         -- Назначение
    locationTypesID int default ((3)),        -- Месторасположение
    shape geometry 
);
CREATE INDEX drenazhnyy_kran_lineid_idx ON drenazhnyy_kran (lineid);
CREATE INDEX drenazhnyy_kran_nodeid_idx ON drenazhnyy_kran (nodeid);
-- CREATE INDEX drenazhnyy_kran_shape_idx ON drenazhnyy_kran USING GIST (shape);
---------------------------------
-- +shield - ПТС 2
-- +shield - +shield
----- Нет таблцы +shield
---------------------------------
-- zapornaya_armatura - ПТС 2
-- zapornaya_armatura - Запорная арматура
drop table if exists zapornaya_armatura;

create table zapornaya_armatura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    d1 float,                                 -- Диаметр на подаче, м.вод.ст
    d2 float,                                 -- Диаметр на обратке, м.вод.ст
    dav1 float,                               -- Давление на подаче, мм
    dav2 float,                               -- Давление на обратке, мм
    m1 int,                                   -- Материал на подаче
    m2 int,                                   -- Материал на обратке
    arm1 int,                                 -- Тип арматуры на подаче
    arm2 int,                                 -- Тип арматуры на обратке
    dav float,                                -- Рабочее давление
    lineID int,
    nodeID int,
    stateID int default ((1)),                -- Состояние задвижки
    mestoraspolozhenie int,                   -- Месторасположение
    tip_prisoedineniya int,                   -- Тип присоединения
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    tip_zapornoy_armatury int,                -- Тип запорной арматуры
    diametr_old varchar(50),
    material int,                             -- Материал
    rabochee_davlenie varchar(50),            -- Рабочее давление
    god_vvoda varchar(50),                    -- Год ввода
    nomer varchar(255),                       -- Номер
    shema varchar,                            -- Схема
    primechanie varchar(255),                 -- Примечание
    prinadlezhnost varchar(50),               -- Принадлежность
    vid_sharovogo_krana int,                  -- Вид шарового крана
    tip_otklyucheniya int,                    -- Тип отключения
    marka varchar(255),                       -- Марка
    naznachenie int,                          -- Назначение
    designTypesID int,                        -- Исполнение
    constructionTypesID int,                  -- Конструкция
    armatureTypesID int,                      -- Тип арматуры
    materialTypesID int,                      -- Материал
    diametr float,                            -- Диаметр условный, мм
    purposeTypesID int,                       -- Назначение
    locationTypesID int,                      -- Месторасположение
    shape geometry,
    nodeID_pts int default (NULL),            -- Наименование узла размещения
    nomer2 varchar(255) default (NULL)        -- Номер задвижки
);
CREATE INDEX zapornaya_armatura_lineid_idx ON zapornaya_armatura (lineid);
CREATE INDEX zapornaya_armatura_nodeid_idx ON zapornaya_armatura (nodeid);
-- CREATE INDEX zapornaya_armatura_shape_idx ON zapornaya_armatura USING GIST (shape);
---------------------------------
-- perehod_diametra - ПТС 2
-- perehod_diametra - Переход диаметра
drop table if exists perehod_diametra;

create table perehod_diametra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    geodezicheskaya_otmetka float,            -- Геодезическая отметка
    priznak_truboprovoda int,                 -- Признак трубопровода
    naimenovanie_nachalnogo_uzla_truby varchar(255),  -- Наименование начального узла трубы
    vysotnaya_otmetka float,                  -- Высотная отметка
    nachalnyy_diametr int,                    -- Начальный диаметр, мм
    konechnyy_diametr int,                    -- Конечный диаметр, мм
    mesto_raspolozheniya varchar(255),        -- Место расположения
    primechanie varchar(255),                 -- Примечание
    kod varchar(5),                           -- Код РС
    uzel varchar(25),                         -- Наименование РС
    id_geopoint int,                          -- #
    prinadlezhnost varchar(50),               -- Принадлежность
    shape geometry 
);
CREATE INDEX perehod_diametra_lineid_idx ON perehod_diametra (lineid);
CREATE INDEX perehod_diametra_nodeid_idx ON perehod_diametra (nodeid);
-- CREATE INDEX perehod_diametra_shape_idx ON perehod_diametra USING GIST (shape);
---------------------------------
-- istochniki_teplosnabzheniya - ПТС 2
-- istochniki_teplosnabzheniya - Источник тепла
drop table if exists istochniki_teplosnabzheniya;

create table istochniki_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    naimenovanie_istochnika varchar(50),      -- Наименование источника
    tip_istochnika varchar(50),               -- Тип источника
    shema varchar,                            -- Схема
    shape geometry 
);
CREATE INDEX istochniki_teplosnabzheniya_lineid_idx ON istochniki_teplosnabzheniya (lineid);
-- CREATE INDEX istochniki_teplosnabzheniya_shape_idx ON istochniki_teplosnabzheniya USING GIST (shape);
---------------------------------
-- heatpoint - ПТС 2
-- heatpoint - Тепловой пункт
drop table if exists heatpoint;

create table heatpoint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255),                        -- Наименование ТП
    heatPointTypeID int,                      -- Тип теплового пункта
    raschetnayaNagruzkaCO float,              -- Расчетная нагрузка на систему отопления, гкал/час
    srednyayaNagruzkaGV float,                -- Средняя нагрузка на горячее водоснабжение, гкал/час
    maxNagruzkaGV float,                      -- Максимальная нагрузка на горячее водоснабжение, гкал/час
    raschetnayaNagruzkaSV float,              -- Расчетная нагрузка на систему вентиляции, гкал/час
    nodeID int,
    nodeName varchar(255),
    countUserGV int default ((0)),
    countBusinessConsumers int default ((0)),
    area float default ((0)),
    buildingVolume float default ((0)),
    basementVolume float default ((0)),
    builtInVolume float default ((0)),
    reduceBuildingVolume float default ((0)),
    shape geometry 
);
CREATE INDEX heatpoint_nodeid_idx ON heatpoint (nodeid);
-- CREATE INDEX heatpoint_shape_idx ON heatpoint USING GIST (shape);
---------------------------------
-- uzel_kanala - ПТС 2
-- uzel_kanala - Узел канала
drop table if exists uzel_kanala;

create table uzel_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    otmetka_verha float,                      -- Отметка верха,м
    otmetka_niza float,                       -- Отметка низа,м
    primechanie varchar,                      -- Примечание
    shape geometry 
);
CREATE INDEX uzel_kanala_lineid_idx ON uzel_kanala (lineid);
-- CREATE INDEX uzel_kanala_shape_idx ON uzel_kanala USING GIST (shape);
--- ПТС 2: 28
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- drenazhnyy_kran material_obektov_setey_teplosnabzheniya - lookup ПТС 2
-- material_obektov_setey_teplosnabzheniya - Материал объектов сетей теплоснабжения
drop table if exists material_obektov_setey_teplosnabzheniya;

create table material_obektov_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);

INSERT INTO "material_obektov_setey_teplosnabzheniya" ("id","id_geom","naimenovanie","primechanie") VALUES
(1,11,'сталь',NULL),
(2,12,'чугун',NULL),
(3,13,'бетон',NULL),
(4,14,'бронза',NULL),
(5,15,'кирпич',NULL),
(6,16,'ж/б блоки',NULL),
(7,17,'ж/б плиты','монолитные, пустотные, сплошные'),
(8,18,'минплита',NULL),
(9,19,'шлакоблоки',NULL),
(10,20,'рубероид',NULL),
(11,21,'асбестоцементная штукатурка',NULL),
(12,22,'пенополиуретан',NULL),
(13,23,'лакостеклоткань',NULL),
(14,24,'фольга',NULL),
(15,25,'асфальт',NULL),
(16,1,'грунт','земля, щебень, песок, дресьва'),
(17,2,'тротуарные блоки',NULL),
(18,3,'ж/б лоток',NULL),
(19,4,'ж/б кольцо монолитное',NULL),
(20,5,'ж/б плиты дорожные',NULL),
(21,6,'дерево',NULL),
(22,7,'шифер',NULL),
(23,8,'металлошифер',NULL),
(24,26,'скорлупы пенополиуретана',NULL),
(25,27,'минплита "URSA"',NULL),
(26,9,'сталь Т1, чугун Т2',NULL),
(27,10,'чугун Т1, сталь Т2',NULL),
(28,28,'металлические',NULL),
(29,29,'электросварные',NULL),
(30,30,'сталь Т1, сталь Т2',NULL),
(31,31,'чугун Т1, чугун Т2',NULL),
(32,32,'сталь Т1',NULL),
(33,33,'сталь Т2',NULL),
(34,34,'ППУ',NULL);


-- SELECT setval('"material_obektov_setey_teplosnabzheniya_id_seq"', 34);

---------------------------------
-- drenazhnyy_kran tip_armatury_setey_teplosnabzheniya - lookup ПТС 2
-- tip_armatury_setey_teplosnabzheniya - Тип арматуры сетей теплоснабжения
drop table if exists tip_armatury_setey_teplosnabzheniya;

create table tip_armatury_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);

INSERT INTO "tip_armatury_setey_teplosnabzheniya" ("id","id_geom","naimenovanie","primechanie") VALUES
(1,1,'вентиль',NULL),
(2,2,'задвижка',NULL),
(3,3,'заглушка',NULL),
(4,4,'фланец',NULL),
(5,5,'Задвижка на Т1',NULL),
(6,6,'Задвижка на Т2',NULL),
(7,7,'Вентиль на Т1',NULL),
(8,8,'Вентиль на Т2',NULL),
(9,9,'Вентиль на Т1, задвижка на Т2',NULL),
(10,10,'Задвижка на Т1, задвижка на Т2',NULL),
(11,11,'Задвижка на Т1, шаровой кран на Т2 ',NULL),
(12,12,'Задвижка на Т1, винтиль на Т2',NULL),
(13,13,'Шаравой кран на Т1, шаравой кран на Т2',NULL),
(14,14,'Фланец на Т1, фланец на Т2',NULL),
(15,15,'Вентиль на Т1, вентиль на Т2',NULL),
(16,16,'Шаравой кран на Т1',NULL),
(17,17,'Шаравой кран на Т2',NULL),
(18,18,'Задвижка  на Т1, фланец на Т2',NULL),
(19,19,'Шаравой кран на Т1, задвижка на Т2',NULL),
(20,20,'Вентиль на Т1, шаравой кран на Т2',NULL),
(21,21,'Фланец на Т1',NULL),
(22,22,'Фланец на Т2',NULL),
(23,23,'ППУ шаравой кран на Т1, ППУ шаравой кран на Т2',NULL),
(24,24,'Шаравой кран на Т1, фланец на Т2',NULL),
(25,25,'Шаравой кран на Т1, вентиль на Т2',NULL),
(26,26,'Фланец на Т1, задвижка на Т2',NULL),
(27,27,'Фланец на Т1, вентиль на Т2',NULL),
(28,28,'Дископоворотный затвор на Т1, дископоворотный затвор на Т2',NULL),
(29,29,'Дископоворотный затвор на Т1',NULL),
(30,30,'Дископоворотный затвор на Т2',NULL),
(31,31,'ППУ шаравой кран на Т1',NULL),
(32,32,'ППУ шаравой кран на Т2',NULL),
(33,33,'Пробка',NULL),
(34,34,'Балансировочный шаровый кран на Т1',NULL),
(35,35,'Шаровый кран под монометр на Т1',NULL),
(36,36,'Шаровый кран под монометр на Т2',NULL),
(37,37,'Сервисный шаровый кран Т1, Т2',NULL),
(38,38,'Дренаж пробки',NULL),
(39,39,'Шаравой кран',NULL),
(40,40,'Т1 редуктор Т2 задвижка',NULL),
(41,41,'С редуктором',NULL),
(42,42,'Шаровый кран под монометр на Т1,Шаровый кран под монометр на Т2',NULL);


-- SELECT setval('"tip_armatury_setey_teplosnabzheniya_id_seq"', 42);

---------------------------------
-- drenazhnyy_kran objectsonlines - lookup ПТС 2
-- objectsonlines - objectsonlines
----- Нет таблцы objectsonlines

---------------------------------
-- drenazhnyy_kran armaturetypes - lookup ПТС 2
-- armaturetypes - Типы арматуры
drop table if exists armaturetypes;

create table armaturetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "armaturetypes" ("id","name","visible") VALUES
(1,'Шаровый кран','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(2,'Задвижка','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(3,'Вентиль','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(4,'Заглушка','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(5,'Фланец','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(6,'Клапан обратный','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(7,'Клапан захлопка','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(8,'Шаровой кран под монометр','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(9,'Пробка','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(10,'Дископоворотный затвор','drenazhnyy_kran,vozdushnik,zapornaya_armatura');


-- SELECT setval('"armaturetypes_id_seq"', 10);

---------------------------------
-- drenazhnyy_kran designtypes - lookup ПТС 2
-- designtypes - Типы проектов
drop table if exists designtypes;

create table designtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "designtypes" ("id","name","visible") VALUES
(1,'Приварное','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(2,'Фланцевое','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(3,'Редуктор','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(4,'Редуктор горизонтальный','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(5,'Воротниковое','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(6,'ППУ','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(7,'ППУ-ПЭ','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(8,'ППУ-ОЦ','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(9,'Глухой','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(10,'Сервисный','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(11,'Поворотный','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(12,'С плавающей пробкой','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(13,'С редуктором','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(14,'Сварное','zapornaya_armatura'),
(15,'Вантузное','zapornaya_armatura'),
(16,'Вантузное с заглушкой','zapornaya_armatura'),
(17,'Вантузное, фланец','zapornaya_armatura'),
(18,'Под развальцовку трубы','zapornaya_armatura'),
(19,'Приварное с одной стороны, с другой фланцевое','zapornaya_armatura'),
(20,'Резьбовое','zapornaya_armatura'),
(21,'Стяжное между фланцами трубопровода','zapornaya_armatura'),
(22,'Балансировочный','drenazhnyy_kran,vozdushnik,zapornaya_armatura');


-- SELECT setval('"designtypes_id_seq"', 22);

---------------------------------
-- drenazhnyy_kran materialtypes - lookup ПТС 2
-- materialtypes - materialtypes
drop table if exists materialtypes;

create table materialtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar(100) 
);

INSERT INTO "materialtypes" ("id","name","visible") VALUES
(1,'Чугун','drenazhnyy_kran,vozdushnik,zapornaya_armatura,lyuki'),
(2,'Сталь','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(3,'Бронза','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(4,'Бетон','kanal'),
(5,'Кирпич','kanal'),
(6,'Дерево','kanal'),
(7,'Грунт','kanal'),
(8,'Полимер','lyuki');


-- SELECT setval('"materialtypes_id_seq"', 8);

---------------------------------
-- drenazhnyy_kran constructiontypes - lookup ПТС 2
-- constructiontypes - Типы конструкций
drop table if exists constructiontypes;

create table constructiontypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,               -- Наименование
    visible varchar 
);

INSERT INTO "constructiontypes" ("id","name","visible") VALUES
(1,'с ручным приводом','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(2,'с механическим приводом','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(3,'с электроприводом','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(4,'с гидроприводом','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(5,'Горизонтальный','kompensator'),
(6,'Вертикальный','kompensator'),
(7,'Сильфонный','kompensator'),
(8,'Стартовый','kompensator'),
(9,'Сальниковый','kompensator'),
(10,'на шарнире','lyuki'),
(11,'с запорным устройством','lyuki'),
(12,'Лоток ж/б','kanal'),
(13,'Плита ж/б','kanal'),
(14,'Блок ж/б','kanal,pavilion'),
(15,'Монолитный ж/б','kanal,tkamera'),
(16,'Земляная','kanal'),
(17,'Кирпичная','kanal,tkamera,pavilion'),
(18,'Блок ФБС','kanal,tkamera'),
(19,'сборные КС','kanal'),
(20,'сборные 2КС','kanal'),
(21,'сборные 3КС','kanal'),
(22,'сборные 4КС','kanal'),
(23,'сборные 5КС','kanal'),
(24,'сборные КЛ','kanal'),
(25,'сборные 2КЛ','kanal'),
(26,'сборные КЛс','kanal'),
(27,'сборные 2КЛс','kanal'),
(28,'ст. 133','kanal'),
(29,'ст. 159','kanal'),
(30,'ст. 219','kanal'),
(31,'ст. 273','kanal'),
(32,'ст. 325','kanal'),
(33,'ст. 377','kanal'),
(34,'ст. 426','kanal'),
(35,'ст. 530','kanal'),
(36,'ст. 630','kanal'),
(37,'ст. 720','kanal'),
(38,'ст. 820','kanal'),
(39,'ст. 1020','kanal'),
(40,'ст. 1220','kanal'),
(41,'ст. 1420','kanal'),
(42,'Ду325','kanal'),
(43,'Ду426','kanal'),
(44,'Ду530','kanal'),
(45,'Ду630','kanal'),
(46,'Ду720','kanal'),
(47,'Ду820','kanal'),
(48,'Ду1020','kanal'),
(49,'Ду1220','kanal'),
(50,'Ду219','kanal'),
(51,'Ду273','kanal'),
(52,'Ду1420','kanal'),
(53,'Кольцо ж/б','tkamera'),
(54,'Сборные блоки','tkamera'),
(55,'Сборные плиты и панели','tkamera'),
(56,'Монолитный бетон','tkamera'),
(57,'Сборные блоки','tkamera'),
(58,'Железобетонная','tkamera,pavilion'),
(59,'Железо-кирпичная','tkamera,pavilion'),
(9999,'Другая','tkamera,pavilion');


-- SELECT setval('"constructiontypes_id_seq"', 9999);

---------------------------------
-- drenazhnyy_kran locations - lookup ПТС 2
-- locations - locations
drop table if exists locations;

create table locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "locations" ("id","name","code","ord") VALUES
(1,'Камера/Павильон','',1),
(2,'Трубопровод','',2);


-- SELECT setval('"locations_id_seq"', 2);

---------------------------------
-- drenazhnyy_kran purposetypes - lookup ПТС 2
-- purposetypes - purposetypes
drop table if exists purposetypes;

create table purposetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "purposetypes" ("id","name","visible") VALUES
(1,'Секционирующая','zapornaya_armatura'),
(2,'Запорная','zapornaya_armatura'),
(3,'Дренаж','drenazhnyy_kran'),
(4,'Воздушник','vozdushnik'),
(5,'Колодец управления','kolodtsy'),
(6,'Дренажный колодец тепловая камера','kolodtsy');


-- SELECT setval('"purposetypes_id_seq"', 6);

---------------------------------
-- drenazhnyy_kran locationtypes - lookup ПТС 2
-- locationtypes - locationtypes
drop table if exists locationtypes;

create table locationtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "locationtypes" ("id","name","visible") VALUES
(1,'Секция','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(2,'Перемычка','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(3,'Дренажный трубопровод','drenazhnyy_kran,vozdushnik,zapornaya_armatura'),
(7,'Трубопровод','zapornaya_armatura');


-- SELECT setval('"locationtypes_id_seq"', 7);

---------------------------------
-- zapornaya_armatura valvepurpose - lookup ПТС 2
-- valvepurpose - valvepurpose
drop table if exists valvepurpose;

create table valvepurpose (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "valvepurpose" ("id","name","code","ord") VALUES
(1,'Секционирующая','С',1),
(2,'Отключающая','О',2);


-- SELECT setval('"valvepurpose_id_seq"', 2);

---------------------------------
-- zapornaya_armatura connectiontypes - lookup ПТС 2
-- connectiontypes - Типы соединений
drop table if exists connectiontypes;

create table connectiontypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "connectiontypes" ("id","name","code","ord") VALUES
(1,'сварное','',1),
(2,'вантузное','',2),
(3,'вантузное с заглушкой','',3),
(4,'вантузное, фланец','',4),
(5,'муфтовое','',5),
(6,'под приварку','',6),
(7,'под развальцовку трубы','',7),
(8,'приварное с одной стороны с другой фланцевое','',8),
(9,'резьбовое','',9),
(10,'стяжное между фланцами трубопровода','',10),
(11,'фланцевое','',11);


-- SELECT setval('"connectiontypes_id_seq"', 11);

---------------------------------
-- zapornaya_armatura ballvalvetypes - lookup ПТС 2
-- ballvalvetypes - Типы шаровых кранов
drop table if exists ballvalvetypes;

create table ballvalvetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "ballvalvetypes" ("id","name","code","ord") VALUES
(1,'Простой','',1),
(2,'Предизолированный','',2);


-- SELECT setval('"ballvalvetypes_id_seq"', 2);

---------------------------------
-- zapornaya_armatura shutdowntypes - lookup ПТС 2
-- shutdowntypes - shutdowntypes
drop table if exists shutdowntypes;

create table shutdowntypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "shutdowntypes" ("id","name","code","ord") VALUES
(1,'С ручным приводом','',1),
(2,'С электроприводом','',2),
(3,'С гидроприводом','',3);


-- SELECT setval('"shutdowntypes_id_seq"', 3);

---------------------------------
-- kanal konstruktsiya_perekrytiya_kanala - lookup ПТС 2
-- konstruktsiya_perekrytiya_kanala - konstruktsiya_perekrytiya_kanala
----- Нет таблцы konstruktsiya_perekrytiya_kanala

---------------------------------
-- kanal channeltype - lookup ПТС 2
-- channeltype - Тип канала
drop table if exists channeltype;

create table channeltype (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "channeltype" ("id","name","visible") VALUES
(1,'Гильза','kanal'),
(2,'Блочный','kanal'),
(3,'Монолитный','kanal'),
(4,'Лотковый','kanal'),
(5,'Полнопроходной','kanal'),
(6,'Полупроходной','kanal'),
(7,'Непроходной','kanal'),
(8,'Футляр','kanal');


-- SELECT setval('"channeltype_id_seq"', 8);

---------------------------------
-- kanal overlaptypes - lookup ПТС 2
-- overlaptypes - overlaptypes
drop table if exists overlaptypes;

create table overlaptypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "overlaptypes" ("id","name","visible") VALUES
(1,'П1-5','kanal'),
(2,'П2-15','kanal'),
(3,'П3-8','kanal'),
(4,'П4-15','kanal'),
(5,'П5-8','kanal'),
(6,'П5д-8','kanal'),
(7,'П6-15','kanal'),
(8,'П6д-15','kanal'),
(9,'П7-5','kanal'),
(10,'П7д-5','kanal'),
(11,'П8-8','kanal'),
(12,'П8д-8','kanal'),
(13,'П9-15','kanal'),
(14,'П9д-15','kanal'),
(15,'П10-5','kanal'),
(16,'П10д-5','kanal'),
(17,'П11-8','kanal'),
(18,'П11д-8','kanal'),
(19,'П12-15','kanal'),
(20,'П12д-15','kanal'),
(21,'П13-11б','kanal'),
(22,'П13д-11б','kanal'),
(23,'П14-3','kanal'),
(24,'П14д-3','kanal'),
(25,'П15-8','kanal'),
(26,'П15д-8','kanal'),
(27,'П16-15','kanal'),
(28,'П16д-15','kanal'),
(29,'П17-3','kanal'),
(30,'П17д-3','kanal'),
(31,'П18-8','kanal'),
(32,'П18д-8','kanal'),
(33,'П19-15','kanal'),
(34,'П19д-15','kanal'),
(35,'П20-3','kanal'),
(36,'П20д-3','kanal'),
(37,'П21-8','kanal'),
(38,'П21д-8','kanal'),
(39,'П22-15','kanal'),
(40,'П22д-15','kanal'),
(41,'П23д-3','kanal'),
(42,'П24д-8','kanal'),
(43,'П25д-15','kanal'),
(44,'П26д-5','kanal'),
(45,'П27д-8','kanal'),
(46,'П28д-15','kanal'),
(47,'ПТ 75.30.6-15','kanal'),
(48,'ПТ 75.60.8-15','kanal'),
(49,'ПТ 75.90.10-15','kanal'),
(50,'ПТ 75.120.12-15','kanal'),
(51,'ПТ 75.150.12-6','kanal'),
(52,'ПТ 75.150.14-15','kanal'),
(53,'ПТ 75.180.16-12','kanal'),
(54,'ПТ 75.210.16-9','kanal'),
(55,'ПТ 75.240.20-9','kanal'),
(56,'ПТ 300.90.10-9','kanal'),
(57,'ПТ 300.120.12-15','kanal'),
(58,'ПТ 300.150.12-6','kanal'),
(59,'ПТ 300.150.14-15','kanal'),
(60,'ПТ 300.180.16-12','kanal'),
(61,'ПТ 300.210.16-9','kanal'),
(62,'ПТ 300.240.20-9','kanal'),
(63,'ПО-1','kanal,tkamera'),
(64,'ПО-2','kanal,tkamera'),
(65,'ПО-3','kanal,tkamera'),
(66,'ПО-4','kanal,tkamera'),
(67,'ПО-5','kanal,tkamera'),
(68,'ПТ-7и-1','tkamera'),
(69,'ПТ-7и','tkamera'),
(70,'ПТ-6и-1','tkamera'),
(71,'ПТ-6и','tkamera'),
(72,'ПТ-5и-1','tkamera'),
(73,'ПТ-5и','tkamera'),
(74,'ПТ-4и-1','tkamera'),
(75,'ПТ-4и','tkamera'),
(76,'ПТ 4520-5','tkamera'),
(77,'ПТ-45-20-10','tkamera'),
(78,'ПТ-30-20-5','tkamera'),
(79,'ПТ-30-20-10','tkamera'),
(80,'ПТ-30-15-10','tkamera'),
(81,'ПТ-30-12-10','tkamera'),
(82,'ПТ-29-20-5','tkamera'),
(83,'ПТ-30-20-10','tkamera'),
(84,'ВП-16-6','tkamera'),
(85,'ВП-16-12','tkamera'),
(86,'ВП-16-18','tkamera'),
(87,'ВП-16-18 с отв.','tkamera'),
(88,'ВП-19-6','tkamera'),
(89,'ВП-19-12','tkamera'),
(90,'ВП-19-18','tkamera'),
(91,'ВП-19-18 с отв.','tkamera'),
(92,'ВП-22-6','tkamera'),
(93,'ВП-22-12','tkamera'),
(94,'ВП-22-18','tkamera'),
(95,'ВП-22-18 с отв.','tkamera'),
(96,'ВП-22-30','tkamera'),
(97,'ВП-24-12','tkamera'),
(98,'ВП-24-18','tkamera'),
(99,'ВП-24-18 с отв.','tkamera'),
(100,'ВП-24-24','tkamera'),
(101,'ВП-25-12','tkamera'),
(102,'ВП-25-18','tkamera'),
(103,'ВП-25-18 с отв.','tkamera'),
(104,'ВП-28-12','tkamera'),
(105,'ВП-28-18','tkamera'),
(106,'ВП-28-18 с отв.','tkamera'),
(107,'ВП-31-12','tkamera'),
(108,'ВП-31-18','tkamera'),
(109,'ВП-31-18 с отв.','tkamera'),
(110,'ВП-34-12','tkamera'),
(111,'ВП-34-18','tkamera'),
(112,'ВП-34-18 с отв.','tkamera'),
(113,'ВП-37-12','tkamera'),
(114,'ВП-37-18','tkamera'),
(115,'ВП-37-18 с отв.','tkamera'),
(116,'ВП-38-12','tkamera'),
(117,'ВП-38-18 с отв.','tkamera'),
(118,'ВП-40-12','tkamera'),
(119,'ВП-40-18','tkamera'),
(120,'ВП-40-18 с отв.','tkamera'),
(121,'ВП-43-6','tkamera'),
(122,'ВП-43-12','tkamera'),
(123,'ВП-43-18','tkamera'),
(124,'ВП-43-18 с отв.','tkamera'),
(125,'ВП-46-12','tkamera'),
(126,'ВП-46-18','tkamera'),
(127,'ВП-46-18 с отв.','tkamera'),
(128,'ВП-49-6','tkamera'),
(129,'ВП-49-12','tkamera'),
(130,'ВП-49-18','tkamera'),
(131,'ВП-49-18 С отв.','tkamera'),
(132,'ВП-55-6','tkamera'),
(133,'ВП-55-12','tkamera'),
(134,'ВП-55-18','tkamera'),
(135,'ВП-55-18 с отв.','tkamera');


-- SELECT setval('"overlaptypes_id_seq"', 135);

---------------------------------
-- opora buildingconstructions - lookup ПТС 2
-- buildingconstructions - Строительные конструкции
drop table if exists buildingconstructions;

create table buildingconstructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "buildingconstructions" ("id","name","code","ord") VALUES
(1,'Неподвижная','',1),
(2,'Лобовая','',2),
(3,'Щитовая','',3),
(4,'Хомутовая','',4),
(5,'Бугельная','',5),
(6,'Боковая','',6);


-- SELECT setval('"buildingconstructions_id_seq"', 6);

---------------------------------
-- opora tip_opory - lookup ПТС 2
-- tip_opory - tip_opory
drop table if exists tip_opory;

create table tip_opory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "tip_opory" ("id","name","visible") VALUES
(1,'Неподвижная','opora'),
(2,'Лобовая','opora'),
(3,'Хомутовая','opora'),
(4,'Щитовая','opora'),
(5,'Бугельная','opora'),
(6,'Боковая','opora'),
(7,'На ППУ трубопроводе','opora');


-- SELECT setval('"tip_opory_id_seq"', 7);

---------------------------------
-- kolodtsy characteristictypes - lookup ПТС 2
-- characteristictypes - Типы характеристик
drop table if exists characteristictypes;

create table characteristictypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar(100) 
);

INSERT INTO "characteristictypes" ("id","name","visible") VALUES
(1,'с решеткой','kolodtsy'),
(2,'сведенный','kolodtsy'),
(3,'двойной','lyuki'),
(4,'тяжелый','lyuki');


-- SELECT setval('"characteristictypes_id_seq"', 4);

---------------------------------
-- kompensator compensatortypes - lookup ПТС 2
-- compensatortypes - Типы компенсаторов
drop table if exists compensatortypes;

create table compensatortypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "compensatortypes" ("id","name","code","ord") VALUES
(1,'Горизонтальный','',1),
(2,'Вертикальный','',2),
(3,'Сальниковый','',3),
(4,'Сильфонный','',4),
(5,'Сильфонный на Т1','',5),
(6,'Сильфонный на Т2','',6),
(7,'Стартовый','',7);


-- SELECT setval('"compensatortypes_id_seq"', 7);

---------------------------------
-- kompensator radialcompensatorforms - lookup ПТС 2
-- radialcompensatorforms - radialcompensatorforms
drop table if exists radialcompensatorforms;

create table radialcompensatorforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "radialcompensatorforms" ("id","name","code","ord") VALUES
(1,'Волнистый','',1),
(2,'Z-образный','',2),
(3,'П-образный','',3),
(4,'S-образный','',4),
(5,'Омегообразный ','',5),
(6,'Лирообразный','',6),
(7,'Несимметричный','',7);


-- SELECT setval('"radialcompensatorforms_id_seq"', 7);

---------------------------------
-- kompensator axialcompensatortypes - lookup ПТС 2
-- axialcompensatortypes - Типы осевых компенсаторов
drop table if exists axialcompensatortypes;

create table axialcompensatortypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "axialcompensatortypes" ("id","name","code","ord") VALUES
(1,'Сальниковый','',1),
(2,'Упругий','',2),
(3,'Линзовый','',3);


-- SELECT setval('"axialcompensatortypes_id_seq"', 3);

---------------------------------
-- tkamera tip_kamery - lookup ПТС 2
-- tip_kamery - tip_kamery
drop table if exists tip_kamery;

create table tip_kamery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

---------------------------------
-- tkamera tip_perekrytiya_kamery - lookup ПТС 2
-- tip_perekrytiya_kamery - tip_perekrytiya_kamery
drop table if exists tip_perekrytiya_kamery;

create table tip_perekrytiya_kamery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

---------------------------------
-- tkamera constructionoverlaptypes - lookup ПТС 2
-- constructionoverlaptypes - Типы перекрытий конструкций
drop table if exists constructionoverlaptypes;

create table constructionoverlaptypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "constructionoverlaptypes" ("id","name","visible") VALUES
(1,'Монолитная плита','tkamera'),
(2,'Сборные железобетонные плиты','tkamera'),
(3,'Железобетонная','tkamera'),
(4,'Железо-кирпичная','tkamera'),
(5,'Кирпичная','tkamera'),
(9999,'Другая','tkamera');


-- SELECT setval('"constructionoverlaptypes_id_seq"', 9999);

---------------------------------
-- vvody_v_zdanie sposob_vvoda_v_zdanie - lookup ПТС 2
-- sposob_vvoda_v_zdanie - Способ ввода в здание
drop table if exists sposob_vvoda_v_zdanie;

create table sposob_vvoda_v_zdanie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sposob_vvoda varchar(255)                 -- Способ ввода
);

INSERT INTO "sposob_vvoda_v_zdanie" ("id","sposob_vvoda") VALUES
(1,'Тройник'),
(2,'Сварка'),
(3,'Седелка');


-- SELECT setval('"sposob_vvoda_v_zdanie_id_seq"', 3);

---------------------------------
-- vvody_v_zdanie prinadlezhnosttypes - lookup ПТС 2
-- prinadlezhnosttypes - prinadlezhnosttypes
----- Нет таблцы prinadlezhnosttypes

---------------------------------
-- heatpoint heatpointtypes - lookup ПТС 2
-- heatpointtypes - heatpointtypes
drop table if exists heatpointtypes;

create table heatpointtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) not null,
    ord int 
);

INSERT INTO "heatpointtypes" ("id","name","ord") VALUES
(1,'ИТП',NULL),
(2,'ЦРТП',NULL),
(3,'ЦТП',NULL);


-- SELECT setval('"heatpointtypes_id_seq"', 3);
--- ПТС 2 lookup: 29
--===========================--
--        Электрические сети             --
--===========================--
---------------------------------
-- priemnik_elektrosnabzheniya - Электрические сети
-- priemnik_elektrosnabzheniya - Приемник электроснабжения
drop table if exists priemnik_elektrosnabzheniya;

create table priemnik_elektrosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_lep int,                     -- Местоположение/Описание ЛЭП
    tip_priemnika_es varchar(255),            -- Тип приемника ЭС
    naimenovanie_priemnika_es varchar(255),   -- Наименование приемника ЭС
    vladelets_priemnika_es varchar(255),      -- Владелец приемника ЭС
    nomer_akta_razdela_es varchar(255),       -- Номер Акта раздела ЭС
    data_vydachi_akta_razdela_es date,        -- Дата выдачи Акта раздела ЭС
    marka_transformatora_rp int,              -- Марка трансформатора РП
    maksimalno_dopustimaya_nagruzka_vneshnego_vvoda_rp__kvt float,    -- Максимально-допустимая нагрузка внешнего ввода, кВт
    shape geometry,
    nomer_akta_razdela varchar(50),
    documents varchar,                        -- Документы
    data_akta_razdela timestamp,
    trans_pro_kol int,                        -- Трансформаторы производственные, кол-во
    trans_sob_kol int,                        -- Трансформаторы, собственные нужды, кол-во
    edv_pod_kol int,                          -- Электродвигатели по подаче, кол-во
    edv_obr_kol int,                          -- Электродвигатели по обратке, кол-во
    edv_dren_kol int,                         -- Электродвигатели дренажные, кол-во
    edv_opr_kol int,                          -- Электродвигатели опрессовочные, кол-во
    diz_kol int,                              -- Дизель-генераторная установка, кол-во
    chast_reg_reg int,                        -- Частотно-регулируемый привод
    gr_pod int,                               -- Грузоподъёмное оборудование
    primechanie varchar,                      -- Примечание
    typID int,                                -- Тип приемника
    vladeltsy_es_ID int                       -- Владелец приемника
);
-- CREATE INDEX priemnik_elektrosnabzheniya_shape_idx ON priemnik_elektrosnabzheniya USING GIST (shape);
---------------------------------
-- kabelnyy_kanal_es - Электрические сети
-- kabelnyy_kanal_es - Кабельный канал ЭС
drop table if exists kabelnyy_kanal_es;

create table kabelnyy_kanal_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_lep int,                     -- Местоположение/Описание ЛЭП
    nomer_kanala_es varchar(255),             -- Номер канала ЭС
    tip__marka__harakteristika_ varchar(255), -- Тип (марка, характеристика)
    shema_kanala_v_razreze varchar(255),      -- Схема канала в разрезе
    data_ustanovki date,                      -- Дата установки
    dolzhnost int,
    fio_otvetstvennogo__ispolnitelya_ varchar(255),   -- ФИО ответственного (исполнителя)
    kontaktnye_dannye__telefon__el_pochta_ varchar(255),  -- Контактные данные (телефон, эл почта)
    shape geometry,
    naimenovanie_lep2 varchar(255),
    dlina_kanala float,                       -- Длина канала, м
    primechanie varchar                       -- Примечание
);
-- CREATE INDEX kabelnyy_kanal_es_shape_idx ON kabelnyy_kanal_es USING GIST (shape);
---------------------------------
-- gilza_es - Электрические сети
-- gilza_es - Гильза ЭС
drop table if exists gilza_es;

create table gilza_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_lep int,                     -- Местоположение/Описание ЛЭП
    nomer_gilzy_es varchar(255),              -- Номер гильзы ЭС
    tip__marka__harakteristika_ varchar(255), -- Тип (марка, характеристика)
    shema_gilzy_v_razreze varchar(255),       -- Схема гильзы в разрезе
    data_ustanovki date,                      -- Дата установки
    dolzhnost_otvetstvennogo__ispolnitelya_ varchar(255), -- Должность ответственного (исполнителя)
    fio_otvetstvennogo__ispolnitelya_ varchar(255),   -- ФИО ответственного (исполнителя)
    shape geometry,
    naimenovanie_lep2 varchar(255),
    dlina_gilzy float,                        -- Длина гильзы, м
    primechanie varchar                       -- Примечание
);
-- CREATE INDEX gilza_es_shape_idx ON gilza_es USING GIST (shape);
---------------------------------
-- edv - Электрические сети
-- edv - ЕДВ
drop table if exists edv;

create table edv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    purposeID int,                            -- Назначение
    edvTypeID int,                            -- Тип электродвигателя
    description varchar,                      -- Описание
    pow float,                                -- Мощность, кВт
    freq float,                               -- Частота вращения, об/мин
    seria varchar(255),                       -- Частотно-регулируемый привод: серия
    diap float,                               -- Частотно-регулируемый привод: Диапазон скорости, об/мин
    prec float,                               -- Точность регулировки скорости
    primechanie varchar,                      -- Примечание
    marka_edv varchar(255)                    -- Марка электродвигателя
);
---------------------------------
-- istochnik_elektrosnabzheniya - Электрические сети
-- istochnik_elektrosnabzheniya - Источник электроснабжения
drop table if exists istochnik_elektrosnabzheniya;

create table istochnik_elektrosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_lep int,                     -- Местоположение/Описание ЛЭП
    tip_istochnika_es varchar(255),           -- Тип источника ЭС
    naimenovanie_istochnika_es varchar(255),  -- Наименование источника ЭС
    vladelets_istochnika_es varchar(255),     -- Владелец источника ЭС
    nomer_akta_razdela_es varchar(255),       -- Номер Акта раздела ЭС
    data_vydachi_akta_razdela_es date,        -- Дата выдачи Акта раздела ЭС
    marka_transformatora_rp int,              -- Марка трансформатора РП
    maksimalno_dopustimaya_nagruzka_vneshnego_vvoda_rp__kvt varchar(255), -- Максимально-допустимая нагрузка внешнего ввода РП, кВт
    shape geometry,
    typID int,                                -- Тип источника
    primechanie varchar,                      -- Примечание
    vladeltsy_es_ID int                       -- Владелец источника
);
-- CREATE INDEX istochnik_elektrosnabzheniya_shape_idx ON istochnik_elektrosnabzheniya USING GIST (shape);
---------------------------------
-- dgu - Электрические сети
-- dgu - Дгу
drop table if exists dgu;

create table dgu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    purposeID int,                            -- Назначение
    description varchar,                      -- Тип/Описание
    pow float,                                -- Мощность, кВт
    primechanie varchar                       -- Примечание
);
---------------------------------
-- mufta - Электрические сети
-- mufta - Муфта ЭС
drop table if exists mufta;

create table mufta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_lep int,                     -- Местоположение/Описание ЛЭП
    nomer_mufty_es varchar(255),              -- Номер муфты ЭС
    tip__marka__harakteristika_ varchar(255), -- Тип (марка, характеристика)
    rasstoyanie_do_priemnika__m float,        -- Расстояние до приемника, м
    data_ustanovki date,                      -- Дата установки
    dolzhnost_otvetstvennogo__ispolnitelya_ varchar(255), -- Должность ответственного (исполнителя)
    fio_otvetstvennogo__ispolnitelya_ varchar(255),   -- ФИО ответственного (исполнителя)
    kontaktnye_dannye__telefon__el_pochta_ varchar(255),  -- Контактные данные (телефон, эл почта)
    shape geometry,
    naimenovanie_lep2 varchar(255),
    dolzhnostID int,                          -- Должность ответственного (исполнителя)
    responsibleID int,                        -- ФИО ответственного (исполнителя)
    primechanie varchar                       -- Примечание
);
-- CREATE INDEX mufta_shape_idx ON mufta USING GIST (shape);
---------------------------------
-- transf - Электрические сети
-- transf - transf
drop table if exists transf;

create table transf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    transfTypeID int,                         -- Тип трансформатора
    description varchar,                      -- Тип трансформатора
    purposeID int,                            -- Назначение
    pow float,                                -- Суммарная мощность, кВА
    voltageHi float,                          -- Напряжение высокое, кВ
    voltageLo float,                          -- Напряжение низкое, кВ
    Ukz float,                                -- Напряжение короткого замыкания, %
    Ixx float,                                -- Ток холостого хода, %
    kol int,                                  -- Количество, шт
    god int,                                  -- Год ввода в эксплуатацию
    primechanie varchar                       -- Примечание
);
---------------------------------
-- gruzob - Электрические сети
-- gruzob - gruzob
drop table if exists gruzob;

create table gruzob (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    typeID int,                               -- Тип
    description varchar,                      -- Тип/Описание
    kol int,                                  -- Количество, шт
    primechanie varchar                       -- Примечание
);
---------------------------------
-- opora_es - Электрические сети
-- opora_es - Опора ЭС
drop table if exists opora_es;

create table opora_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie_lep int,                     -- Местоположение/Описание ЛЭП
    nomer_opory_es varchar(255),              -- Номер опоры ЭС
    tip__marka__harakteristika_ varchar(255), -- Тип/Описание 
    data_ustanovki date,                      -- Дата установки
    dolzhnost int,
    fio_otvetstvennogo__ispolnitelya_ varchar(255),   -- ФИО ответственного (исполнителя)
    kontaktnye_dannye_telefon__el_pochta_ varchar(255),   -- Контактные данные(телефон, эл почта)
    shape geometry,
    naimenovanie_lep2 varchar(255),
    primechanie varchar                       -- Примечание
);
-- CREATE INDEX opora_es_shape_idx ON opora_es USING GIST (shape);
---------------------------------
-- liniya_elektroperedach - Электрические сети
-- liniya_elektroperedach - Линия электропередач
drop table if exists liniya_elektroperedach;

create table liniya_elektroperedach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip_istochnika varchar(255),              -- Тип источника
    naimenovanie_istochnika int,              -- Наименование источника
    tip_priemnika varchar(255),               -- Тип приемника
    naimenovanie_priemnika int,               -- Наименование приемника
    naimenovanie_lep varchar(255),            -- Местоположение/Описание ЛЭП
    vladelets_lep int,                        -- Владелец ЛЭП
    napryazhenie__kv float,                   -- Напряжение, кВ
    fidera varchar(255),                      -- Рабочие фидера
    tip_prokladki_lep int,                    -- Тип прокладки кабеля
    marka_kabelya_linii int,                  -- Марка кабеля линии
    protyazhennost__m float,                  -- Протяженность кабеля, м
    data_vvoda_v_ekspluatatsiyu date,         -- Дата ввода в эксплуатацию
    primechanie text,                         -- Примечание
    shape geometry,
    protyazhennost__linii_m float,            -- Протяженность линии, м
    fidera_rez varchar(255),                  -- Резервные фидера
    isp_s int,                                -- Наличие исп.съемки
    mestopolozhenie varchar,                  -- Местоположение/Описание
    count_lep int                             -- Количество линий ЛЭП, шт
);
-- CREATE INDEX liniya_elektroperedach_shape_idx ON liniya_elektroperedach USING GIST (shape);
--- Электрические сети: 11
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- liniya_elektroperedach marki_kabeley_es - lookup Электрические сети
-- marki_kabeley_es - Марки кабелей ЭС
drop table if exists marki_kabeley_es;

create table marki_kabeley_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kratkoe_naimenovanie_marki_tipa__kabelya varchar(255),    -- Краткое наименование марки(типа) кабеля
    polnoe_naimenovanie_marki_tipa__kabelya varchar(255)  -- Полное наименование марки(типа) кабеля
);

INSERT INTO "marki_kabeley_es" ("id","kratkoe_naimenovanie_marki_tipa__kabelya","polnoe_naimenovanie_marki_tipa__kabelya") VALUES
(1,'ВПВнг 1*630мм2','ВПВнг 1*630мм2'),
(2,'ВЛ (АС-150) мм2','ВЛ (АС-150) мм2'),
(3,'ААБЛ 3*240 мм2','ААБЛ 3*240 мм2'),
(4,'АПвЭасПуг 1*120 мм2','АПвЭасПуг 1*120 мм2'),
(5,'ААБЛ 3*120 мм2','ААБЛ 3*120 мм2'),
(6,'ВЛ (АС-50) мм2','ВЛ (АС-50) мм2'),
(7,'ВЛ СИП 4*16 мм2','ВЛ СИП 4*16 мм2'),
(8,'АПВПу 1*630/70 мм2','АПВПу 1*630/70 мм2'),
(9,'ВПВнг 1*500 мм2','ВПВнг 1*500 мм2'),
(10,'АСБ 3*240 мм2','АСБ 3*240 мм2'),
(11,'АВБбшв 3*120+1*70 мм2','АВБбшв 3*120+1*70 мм2'),
(12,'ААБЛу 3*150+1*70 мм2','ААБЛу 3*150+1*70 мм2'),
(13,'ААБЛу 3*120 мм2','ААБЛу 3*120 мм2'),
(14,'АВБбШВ 3*120+1*70 мм2 ','АВБбШВ 3*120+1*70 мм2 '),
(15,'АпвП (А) –LS 1*240/95 мм2','АпвП (А) –LS 1*240/95 мм2'),
(16,'АпвП 1*120/95 мм2','АпвП 1*120/95 мм2');


-- SELECT setval('"marki_kabeley_es_id_seq"', 16);

---------------------------------
-- liniya_elektroperedach tipy_lep - lookup Электрические сети
-- tipy_lep - Типы ЛЭП
drop table if exists tipy_lep;

create table tipy_lep (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(3),                           -- Код
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "tipy_lep" ("id","kod","znachenie","primechanie") VALUES
(1,'ВЛ','воздушная линия',NULL),
(2,'КЛ','подземная линия',NULL);


-- SELECT setval('"tipy_lep_id_seq"', 2);

---------------------------------
-- istochnik_elektrosnabzheniya transftypes - lookup Электрические сети
-- transftypes - transftypes
drop table if exists transftypes;

create table transftypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),         -- Наименование
    code varchar(10) default (NULL),          -- Код
    ord int                                   -- Порядок
);

INSERT INTO "transftypes" ("id","name","code","ord") VALUES
(1,'ТС',NULL,1),
(2,'ТСЗ',NULL,2),
(3,'ТСЗН',NULL,3),
(4,'ТСЛ',NULL,4),
(5,'ТСЗЛ',NULL,5),
(6,'ТСГЛ',NULL,6),
(7,'ТМ',NULL,7),
(8,'ТМГ',NULL,8),
(9,'ТМЗ',NULL,9),
(10,'ТМФ',NULL,10),
(11,'ТМГФ',NULL,11),
(12,'ТМН',NULL,12);


-- SELECT setval('"transftypes_id_seq"', 12);

---------------------------------
-- istochnik_elektrosnabzheniya tipy_istochnikov_elektricheskih_setey - lookup Электрические сети
-- tipy_istochnikov_elektricheskih_setey - Типы источников электрических сетей
drop table if exists tipy_istochnikov_elektricheskih_setey;

create table tipy_istochnikov_elektricheskih_setey (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(20),                          -- Код
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "tipy_istochnikov_elektricheskih_setey" ("id","kod","znachenie","primechanie") VALUES
(2,'ПС','Подстанция',NULL),
(3,'РП','Распределительный пункт',NULL),
(4,'ТП','Трансформаторная подстанция',NULL),
(5,'БКТП','Блочная комплектная трансформаторная подстанция',NULL);


-- SELECT setval('"tipy_istochnikov_elektricheskih_setey_id_seq"', 5);

---------------------------------
-- priemnik_elektrosnabzheniya marki_transformatorov_es - lookup Электрические сети
-- marki_transformatorov_es - Марки трансформаторов ЭС
drop table if exists marki_transformatorov_es;

create table marki_transformatorov_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marka_transformatora varchar(255),        -- Марка трансформатора
    moschnost_transformatora__kvt float       -- Мощность трансформатора, кВА
);

INSERT INTO "marki_transformatorov_es" ("id","marka_transformatora","moschnost_transformatora__kvt") VALUES
(1,'Первая марка транфосматоров',1.0),
(2,'Вторая марка транфосматоров',2.0);


-- SELECT setval('"marki_transformatorov_es_id_seq"', 2);

---------------------------------
-- priemnik_elektrosnabzheniya tipy_priemnikov_elektricheskih_setey - lookup Электрические сети
-- tipy_priemnikov_elektricheskih_setey - Типы приемников электрических сетей
drop table if exists tipy_priemnikov_elektricheskih_setey;

create table tipy_priemnikov_elektricheskih_setey (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(3),                           -- Код
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "tipy_priemnikov_elektricheskih_setey" ("id","kod","znachenie","primechanie") VALUES
(1,'ТП','Тепловой пункт тепловой сети',NULL),
(2,'НС','Насосная станция тепловой сети',NULL),
(3,'ТРП','Тепловой распределительный пункт',NULL),
(4,'ПАВ','Павильон тепловой сети',NULL),
(5,'РП','Распределительный пункт ЭС',NULL),
(6,NULL,'ТП-3352 НС-16',NULL);


-- SELECT setval('"tipy_priemnikov_elektricheskih_setey_id_seq"', 6);

---------------------------------
-- mufta dolzhnosti_es - lookup Электрические сети
-- dolzhnosti_es - Должности ЭС
drop table if exists dolzhnosti_es;

create table dolzhnosti_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255)                    -- Должность
);

---------------------------------
-- mufta responsibles_es - lookup Электрические сети
-- responsibles_es - Ответственные по электрическим сетям
drop table if exists responsibles_es;

create table responsibles_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50),                         -- ФИО
    statusID int                              -- Должность
);

---------------------------------
-- transf transfpurpos - lookup Электрические сети
-- transfpurpos - transfpurpos
drop table if exists transfpurpos;

create table transfpurpos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "transfpurpos" ("id","name","code","ord") VALUES
(1,'Производственные',NULL,1),
(2,'Собственные нужды',NULL,2);


-- SELECT setval('"transfpurpos_id_seq"', 2);

---------------------------------
-- edv edvpurpos - lookup Электрические сети
-- edvpurpos - Назначение ЕДВ
drop table if exists edvpurpos;

create table edvpurpos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null 
);

INSERT INTO "edvpurpos" ("id","name") VALUES
(1,'По подаче'),
(2,'По обратке'),
(3,'Дренажный'),
(4,'Опресовочный');


-- SELECT setval('"edvpurpos_id_seq"', 4);

---------------------------------
-- edv typeedv - lookup Электрические сети
-- typeedv - typeedv
drop table if exists typeedv;

create table typeedv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null 
);

INSERT INTO "typeedv" ("id","name") VALUES
(1,'Асинхронный'),
(2,'Синхронный'),
(3,'Постоянного тока');


-- SELECT setval('"typeedv_id_seq"', 3);

---------------------------------
-- dgu dgupurpose - lookup Электрические сети
-- dgupurpose - Назначение дгу
drop table if exists dgupurpose;

create table dgupurpose (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null 
);

INSERT INTO "dgupurpose" ("id","name") VALUES
(1,'Аварийного электроснабжения'),
(2,'Постоянного электроснабжения');


-- SELECT setval('"dgupurpose_id_seq"', 2);

---------------------------------
-- gruzob grupurpose - lookup Электрические сети
-- grupurpose - grupurpose
drop table if exists grupurpose;

create table grupurpose (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null 
);

INSERT INTO "grupurpose" ("id","name") VALUES
(1,'ручные тали с кошками'),
(2,'ручные тали без кошек'),
(3,'электротельфер'),
(4,'мостовой кран-балка'),
(5,'мостовой кран');


-- SELECT setval('"grupurpose_id_seq"', 5);
--- Электрические сети lookup: 13
--===========================--
--        Ремонт             --
--===========================--
---------------------------------
-- opres - Ремонт
-- opres - opres
drop table if exists opres;

create table opres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255),                        -- Наименование контура
    istochnik_tepla int,                      -- Источник тепла
    opisaniye_kontura varchar,                -- Описание контура
    defects varchar,                          -- Повреждения выявленные при испытании
    granitsa_razdela varchar,                 -- Границы раздела
    vid_ispytaniID int,                       -- Вид испытаний по контуру
    date_opres timestamp,                     -- Дата проведения опрессовки
    nodeOprID1 int,                           -- Начальный узел
    nodeOprID2 int,                           -- Конечный узел
    otchet varchar,                           -- Результат испытаний (отчет)
    subdivisionID int,                        -- Подразделение
    responsibleID int,                        -- Руководитель испытаний
    primechanie varchar,                      -- Примечание
    objekt_opressovochnogo_nasosaID int,      -- Объект опрессовочного насоса
    data_nachala_plan date,                   -- Дата начала работ по опрессовке, план
    data_okonchaniya_plan date,               -- Дата окончания работ по опрессовке, план
    data_utverzhdeniya_plana date,            -- Дата утверждения плана опрессовки
    vremya_provedeniya_opressovki varchar(5), -- Время проведения опрессовки
    prodolzhitelnost_opressovki int,          -- Продолжительность опрессовки,мин
    davlenie_opressovki_1_etap float default ((12)),  -- Давление опрессовки 1 этапа, кгс/см2
    davlenie_opressovki_2_etap float default ((16)),  -- Давление опрессовки 2 этапа, кгс/см2
    temperatura_raskholazhivaniya_kontura float default ((45)),   -- Температура расхолаживания контура, °С
    kolichestvo_zvenjev_obhodchikov int,      -- Количество звеньев опрессовки
    fio_utverzhdaemogo varchar(255),          -- Утверждающий
    dolzhnost_utverzhdaemogoID int,           -- Должность
    podrazdelenie_utverzhdaemogoID int,       -- Подразделение
    fio_rukovoditel_ispytanij varchar(255),   -- Руководитель испытаний
    dolzhnost_rukovoditel_ispytanijID int,    -- Должность
    podrazdelenie_rukovoditel_ispytanijID int,    -- Подразделение
    fio_otvetstvennyj_za_obespechenie_rezhimov varchar(255),  -- Ответственный за обеспечение режимов
    dolzhnost_otvetstvennyj_za_obespechenie_rezhimovID int,   -- Должность
    podrazdelenie_otvetstvennyj_za_obespechenie_rezhimovID int,   -- Подразделение
    fio_otvetstvennyj_za_blank_pereklyuchenij varchar(255),   -- Ответственный за бланк переключений
    dolzhnost_otvetstvennyj_za_blank_pereklyuchenijID int,    -- Должность
    podrazdelenie_otvetstvennyj_za_blank_pereklyuchenijID int,    -- Подразделение
    fio_otvetstvennyj_za_ustanovku_manometrov_i_raskhodomerov varchar(255),   -- Ответственный за установку манометров и расходомеров
    dolzhnost_otvetstvennyj_za_ustanovku_manometrov_i_raskhodomerovID int,    -- Должность
    podrazdelenie_otvetstvennyj_za_ustanovku_manometrov_i_raskhodomerovID int,    -- Подразделение
    fio_otvetstvennyj_za_obespechenie_avtotransportom varchar(255),   -- Отвественный за обеспечение автотранспортом
    dolzhnost_otvetstvennyj_za_obespechenie_avtotransportomID int,    -- Должность
    podrazdelenie_otvetstvennyj_za_obespechenie_avtotransportomID int,    -- Подразделение
    fio_otvetstvennyj_za_priem_zayavok_ot_potrebitelej_na_uchastie_v_sovmestnoj_opressovke varchar(255),  -- Отвественный за Прием заявок от потребителей на участие в совместной опрессовке
    dolzhnost_otvetstvennyj_za_priem_zayavok_ot_potrebitelej_na_uchastie_v_sovmestnoj_opressovkeID int,   -- Должность
    podrazdelenie_otvetstvennyj_za_priem_zayavok_ot_potrebitelej_na_uchastie_v_sovmestnoj_opressovkeID int,   -- Подразделение
    fio_otvetstvennyj_za_obespechenie_raboty_elektrooborudovaniya varchar(255),   -- Ответственный за обеспечение работы электрооборудования
    dolzhnost_otvetstvennyj_za_obespechenie_raboty_elektrooborudovaniyaID int,    -- Должность
    podrazdelenie_otvetstvennyj_za_obespechenie_raboty_elektrooborudovaniyaID int,    -- Подразделение
    fio_otvetstvennyj_po_snip_kontura_istochnika_tepla varchar(255),  -- Ответственный по СНиП контура источника тепла
    dolzhnost_otvetstvennyj_po_snip_kontura_istochnika_teplaID int,   -- Должность
    podrazdelenie_otvetstvennyj_po_snip_kontura_istochnika_teplaID int,   -- Подразделение
    fio_otvetstvennyj_za_opoveshchenie_naseleniya_o_ispytaniyah varchar(255), -- Ответственный за оповещение населения о испытаниях
    dolzhnost_otvetstvennyj_za_opoveshchenie_naseleniya_o_ispytaniyahID int,  -- Должность
    podrazdelenie_otvetstvennyj_za_opoveshchenie_naseleniya_o_ispytaniyahID int,  -- Подразделение
    data_utverzhdeniya_akta_ispytanij date,   -- Дата утверждения акта испытания
    reshenie_komissii varchar,                -- Решение комиссии
    akt_ispytanij varchar(255),               -- Акт испытаний
    opres_typeID int,                         -- Тип опрессовки
    sostoyanie_opresID int,                   -- Состояние
    utverdit int default ((0)),               -- Утверждение
    ne_preduprezhdennye_potrebiteli varchar,  -- Список не предупрежденных потребителей
    spisok_trub_ne_uchav varchar,             -- Список трубопроводов, не участвующих в опрессовке
    spisok_potrev_ne_predupr varchar 
);
---------------------------------
-- osmotr - Ремонт
-- osmotr - osmotr
drop table if exists osmotr;

create table osmotr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255),                        -- Наименование
    data_osmotra date,                        -- Дата осмотра
    nomer_akta varchar(30),                   -- Номер акта
    predpolagaemye_prichiny_razrusheniya_izolyacii_korrozii varchar,  -- Предполагаемые причины разрушения изоляции коррозии
    rezultaty_osmotra varchar,                -- Результаты осмотра (отчет)
    namechennye_meropriyatiya varchar,        -- Намеченные мероприятия
    meropriyatiya_po_vosstanovleniyu_prokladki varchar,   -- Мероприятия по восстановлению прокладки
    primechanie varchar,                      -- Примечание
    otvetstvennoe_lico_ID int,                -- Ответственное лицо
    fio_utverzhdaemogo varchar(255),          -- ФИО утверждающего
    dolzhnost_utverzhdaemogoID int,           -- Должность утверждающего
    sluzhba_utverzhdaemogoID int,             -- Служба утверждающего
    fio_1 varchar(255),                       -- ФИО 1 члена
    dolzhnost_1 int,                          -- Должность 1 члена
    fio_2 varchar(255),                       -- ФИО 2 члена
    dolzhnost_2 int,                          -- Должность 2 члена
    podrazdelenie_provodivshee_raboty int,    -- Подразделение проводившее работу
    spisok_trub_ne_uchav varchar,
    spisok_potrev_ne_predupr varchar 
);
---------------------------------
-- remont2 - Ремонт
-- remont2 - Ремонты
drop table if exists remont2;

create table remont2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stateID int,                              -- Состояние
    data_osmotra timestamp,                   -- Дата осмотра
    vremya_osmotra varchar(6),                -- Время осмотра
    otchet_po_defektu varchar,                -- Наименование/Адрес
    len_tube_cur float,                       -- Длина заменённых труб, м
    len_channel_cur float,                    -- Длина участка канала, м
    len_izol_cur float,                       -- Восстановление тепловой изоляции поверхности труб, м^2
    len_tube_inv float,
    len_channel_inv float,
    len_izol_inv float,
    len_tube_cap float,
    len_channel_cap float,
    len_izol_cap float,
    data_nachala_remonta date,                -- Дата начала ремонтных работ
    data_zaversheniya_remonta date,           -- Дата завершения ремонтных работ
    remontTypeID int,                         -- Вид ремонта
    remontCatID int,                          -- Категории нарушений
    subdivisionID int,                        -- Подразделение производившее ремонт
    responsibleID int,                        -- Ответственный за ремонт
    primechanie varchar,                      -- Примечание
    debug int,
    teplovaya_setID int,                      -- Тепловая сеть
    data_utverzhdeniya_plana date,            -- Дата утверждения плана ремонта
    data_nachala_plan date,                   -- Дата начала ремонта плановая
    data_okonchaniya_plan date,               -- Дата окончания ремонта плановая
    len_tube_plan float,                      -- Длина заменённых труб, план, м
    len_izol_plan float,                      -- Восстановление тепловой изоляции поверхности труб, план, м^2
    len_channel_plan float,                   -- Восстановление канальной прокладки, план, м
    asfaltirovanie_plan float,                -- Асфальтирование, план, м^2
    vydelennye_sredstva_plan float,           -- Объем выделенных средств и затрат, тыс.тг. с НДС план
    remontnyj_personal_plan int,              -- Ремонтный персонал, план, чел.
    asfaltirovanie float,                     -- Асфальтирование, ремонт, м^2
    vydelennye_sredstva float,                -- Объем выделенных средств и затрат, тыс.тг. с НДС
    remontnyj_personal int,                   -- Ремонтный персонал, использовано, чел.
    rezultaty_remonta varchar,                -- Результаты ремонта (отчёт)
    kolichestvo_nedootpushchennoj_teplovoj_energii float, -- Количество недоотпущенной тепловой энергии, ГКал
    kolichestvo_otklyuchennyh_potrebitelej int,   -- Количество отключенных потребителей
    nomer_prikaza varchar(200),               -- Номер приказа на ввод в эксплуатацию
    data_prikaza_vvoda_v_ekspluataciyu date,  -- Дата приказа ввода в эксплуацию
    prikaz_vvoda_v_ekspluataciyu varchar(255),    -- Приказ ввода в эксплуацию
    diametr_trub_plan float,                  -- Диаметр условный заменённых труб, план, мм
    utverdit int,                             -- Утверждение
    harakteristika_rabot varchar,             -- Характеристика работ
    harakteristika_uchastkov_remontiruemoj_teplovoj_seti varchar, -- Характеристика участков ремонтируемой тепловой сети
    opisanie_rabot varchar,                   -- Описание ремонтных работ
    plan_flag int,
    transfer_flag int 
);
--- Ремонт: 3
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- remont2 remonttypes - lookup Ремонт
-- remonttypes - remonttypes
drop table if exists remonttypes;

create table remonttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "remonttypes" ("id","name","code","ord") VALUES
(1,'Инвестиционный','И',1),
(2,'Капитальный','К',2),
(3,'Текущий','Т',3);


-- SELECT setval('"remonttypes_id_seq"', 3);

---------------------------------
-- remont2 stateremont2 - lookup Ремонт
-- stateremont2 - stateremont2
drop table if exists stateremont2;

create table stateremont2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255),
    code varchar(10),
    ord int 
);

INSERT INTO "stateremont2" ("id","name","code","ord") VALUES
(1,'План','П',1),
(2,'В процессе','ПР',2),
(3,'Выполнено','В',3);


-- SELECT setval('"stateremont2_id_seq"', 3);

---------------------------------
-- remont2 subdivisions - lookup Ремонт
-- subdivisions - subdivisions
drop table if exists subdivisions;

create table subdivisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),         -- Наменование
    code varchar(10) default (NULL),          -- Код
    ord int                                   -- Порядок
);

INSERT INTO "subdivisions" ("id","name","code","ord") VALUES
(1,'Производственная служба','',1),
(2,'Производственно-ремонтная служба','',2),
(3,'Служба капитального строительства','',3),
(4,'Служба наладки','',4),
(5,'Служба режимов и реализации','',5),
(6,'Служба технического надзора','',6),
(7,'Служба эксплуатации тепловых сетей','',7),
(8,'Служба эксплуатации теплотехнического оборудования','',8),
(9,'Служба информационных технологий','',9),
(10,'Служба материально-технического снабжения и гос.закупок','',10),
(11,'Техническая служба','',11),
(12,'Транспортная служба','',12),
(13,'Оперативно-диспетчерская служба','',13),
(14,'Химическая лаборатория ','',14),
(15,'Энергослужба','',15);


-- SELECT setval('"subdivisions_id_seq"', 15);

---------------------------------
-- remont2 remontcat - lookup Ремонт
-- remontcat - remontcat
drop table if exists remontcat;

create table remontcat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "remontcat" ("id","name","code","ord") VALUES
(1,'Незначительные сбои','',1),
(2,'Не вызывало аварийных ситуаций','',2),
(3,'Нарушение работы сетей','',2),
(4,'Оборудование физически невозможно включить в работу','',4),
(5,'Износ',NULL,5),
(6,'Порыв',NULL,NULL),
(7,'Реконструкция т/тр',NULL,NULL);


-- SELECT setval('"remontcat_id_seq"', 7);

---------------------------------
-- opres vid_ispytani - lookup Ремонт
-- vid_ispytani - vid_ispytani
drop table if exists vid_ispytani;

create table vid_ispytani (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "vid_ispytani" ("id","name","code","ord") VALUES
(1,'гидравлические',NULL,1),
(2,'тепловые',NULL,2);


-- SELECT setval('"vid_ispytani_id_seq"', 2);

---------------------------------
-- opres sostoyanie_opres - lookup Ремонт
-- sostoyanie_opres - sostoyanie_opres
drop table if exists sostoyanie_opres;

create table sostoyanie_opres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "sostoyanie_opres" ("id","name","ord") VALUES
(1,'План',1),
(2,'В процессе',2),
(3,'Выполнено',3);


-- SELECT setval('"sostoyanie_opres_id_seq"', 3);

---------------------------------
-- opres opres_types - lookup Ремонт
-- opres_types - Тип опрессовки
drop table if exists opres_types;

create table opres_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "opres_types" ("id","name","ord") VALUES
(1,'после капитального ремонта',1),
(2,'после инвестиционного ремонта',2),
(3,'после текущего ремонта',3),
(4,'гидравлические испытания',4);


-- SELECT setval('"opres_types_id_seq"', 4);

---------------------------------
-- osmotr naznachenie_vskr - lookup Ремонт
-- naznachenie_vskr - naznachenie_vskr
drop table if exists naznachenie_vskr;

create table naznachenie_vskr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    code varchar(100),
    ord int 
);

INSERT INTO "naznachenie_vskr" ("id","name","code","ord") VALUES
(1,'План',NULL,1),
(2,'Предписание',NULL,2),
(3,'Нарушение',NULL,3);


-- SELECT setval('"naznachenie_vskr_id_seq"', 3);

---------------------------------
-- osmotr materialy_i_mekhanizmy - lookup Ремонт
-- materialy_i_mekhanizmy - materialy_i_mekhanizmy
drop table if exists materialy_i_mekhanizmy;

create table materialy_i_mekhanizmy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "materialy_i_mekhanizmy" ("id","name","ord") VALUES
(1,'манипулятор',1),
(2,'экскаватор',2),
(3,'АС машина',3);


-- SELECT setval('"materialy_i_mekhanizmy_id_seq"', 3);
--- Ремонт lookup: 9
--===========================--
--        Ремонт 2             --
--===========================--
---------------------------------
-- remont - Ремонт 2
-- remont - Ремонты (устарело)
drop table if exists remont;

create table remont (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    stateID int,                              -- Состояние
    data_osmotra timestamp,                   -- Дата осмотра
    vremya_osmotra varchar(6),                -- Время осмотра
    otchet_po_defektu varchar,                -- Отчет по повреждению
    len_tube_cur float,                       -- Длина заменённой трубы, м
    len_channel_cur float,                    -- Длина участка ремонта канала, м
    len_izol_cur float,                       -- Длина заменённой изоляции, м
    len_tube_inv float,                       -- Длина заменённой трубы, м
    len_channel_inv float,                    -- Длина участка ремонта канала, м
    len_izol_inv float,                       -- Длина заменённой изоляции, м
    len_tube_cap float,                       -- Длина заменённой трубы, м
    len_channel_cap float,                    -- Длина участка ремонта канала, м
    len_izol_cap float,                       -- Длина заменённой изоляции, м
    data_nachala_remonta date,                -- Дата начала ремонтных работ
    data_zaversheniya_remonta date,           -- Дата завершения ремонтных работ
    remontTypeID int,                         -- Вид работ (ремонта)
    remontCatID int,                          -- Категории нарушений
    subdivisionID int,                        -- Подразделение производившее ремонт
    responsibleID int,                        -- Ответственный за ремонт
    primechanie varchar,                      -- Примечание
    shape geometry 
);
CREATE INDEX remont_lineid_idx ON remont (lineid);
-- CREATE INDEX remont_shape_idx ON remont USING GIST (shape);
---------------------------------
-- shurfy - Ремонт 2
-- shurfy - Шурф
drop table if exists shurfy;

create table shurfy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    data_utverzhdeniya_plana_shurfovok date,  -- Дата утверждения плана шурфовок
    naznachenie_vskrID int,                   -- Назначение вскрытия
    ulicaID int,                              -- Улица
    nomer_doma varchar(15),                   -- Номер дома
    sostoyanie_shurfaID int,                  -- Состояние
    data_nachala_plan date,                   -- Дата начала шурфовки плановая
    data_okonchaniya_plan date,               -- Дата окончания шурфовки плановая
    data_nachala date,                        -- Дата начала шурфовки
    data_okonchaniya date,                    -- Дата окончания шурфовки
    rasstoyanie_do_blizhajshej_kamery float,  -- Расстояние до ближайшей камеры, м
    dlina_osmotra float,                      -- Длина осмотра, м
    glubina_zalozheniya float,                -- Глубина заложения прокладки, м
    harakter_gruntaID int,
    podtoplenie_do_truby int,
    ustrojstva_vodootvedeniyaID int,          -- Устройства водоотведения
    poverhnost_nad_trassojID int,
    nalichie_vblizi_elektrificirovannogo_transporta int,  -- Наличие вблизи электрифицированного транспорта
    rasstoyanie_do_relsov float,              -- Расстояние до рельсов, м
    nalichie_vblizi_kommunikacijID int,
    nalichie_vblizi_rabotayushchih_elektrozashchitnyh_ustanovokID int,    -- Наличие вблизи работающих электрозащитных установок
    nomer_akta varchar(30),                   -- Номер Акта
    osmotreny_elementyID int,                 -- Осмотрены элементы
    gidroizolyacionnaya_konstrukciya_podachaID int,   -- Гидроизоляционная конструкция (подача)
    gidroizolyacionnaya_konstrukciya_obratkaID int,   -- Гидроизоляционная конструкция (обратка)
    sostoyanie_protivokorrozionnogo_pokrytiya_podachaID int,  -- Состояние противокоррозионного покрытия (подача)
    sostoyanie_protivokorrozionnogo_pokrytiya_obratkaID int,  -- Состояние противокоррозионного покрытия (обратка)
    nalichie_korrozii_podachaID int,          -- Наличие коррозии (подача)
    nalichie_korrozii_obratkaID int,          -- Наличие коррозии (обратка)
    mesto_kontrolnoj_vyrezki_truboprovoda varchar,    -- Место контрольной вырезки трубопровода
    rezultaty_vyrezki varchar,                -- Результаты вырезки
    rezultaty_osmotra varchar,                -- Результаты осмотра (шурф)
    namechennye_meropriyatiya varchar,        -- Намеченные мероприятия
    meropriyatiya_po_vosstanovleniyu_prokladki varchar,   -- Мероприятия по восстановлению прокладки
    primechanie varchar,                      -- Примечание
    materialy_i_mekhanizmyID int,             -- Материалы и механизмы
    fio_utverzhdaemogo varchar(255),          -- ФИО утверждающего
    dolzhnost_utverzhdaemogoID int,           -- Должность утверждающего
    sluzhba_utverzhdaemogoID int,             -- Служба утверждающего
    fio_1 varchar(255),                       -- ФИО 1 члена
    dolzhnost_1 int,                          -- Должность 1 члена
    fio_2 varchar(255),                       -- ФИО 2 члена
    dolzhnost_2 int,                          -- Должность 2 члена
    fio_viziruemogo_1 varchar(255),           -- ФИО визирующего
    dolzhnost_viziruemogoID_1 int,            -- Должность визирующего
    shape geometry,
    utverdit int default ((0)),               -- Утверждение
    stroitelnye_konstrukcii_kanalaID int,
    sostoyanie_stroitelnyh_konstrukcij_kanalaID int,
    vnutrennee_sostoyanie_kanalaID int,
    konstrukciya_drenazhnogo_ustrojstvaID int,
    sostoyanie_teplovoj_izolyacii_podachaID int,
    sostoyanie_teplovoj_izolyacii_obratkaID int,
    sostoyanie_naruzhnogo_pokrytiya_podachaID int,
    sostoyanie_naruzhnogo_pokrytiya_obratkaID int,
    predpolagaemye_prichiny_razrusheniya_izolyacii varchar(255),
    zanos_kanala_gruntomID int,
    nodeID_bizhajshej_kamery int,             -- Ближайшая камера
    naznachenie varchar(255),                 -- Наименование Плана шурфовок
    document_analiz_vlazhnost varchar(255),
    document_analiz_korrozia varchar(255),
    document_potenzial varchar(255),
    document_analiz_vytyazhka varchar(255),
    data_utverzhdenija_akta date              -- Дата акта
);
CREATE INDEX shurfy_lineid_idx ON shurfy (lineid);
-- CREATE INDEX shurfy_shape_idx ON shurfy USING GIST (shape);
---------------------------------
-- defect - Ремонт 2
-- defect - Нарушение
drop table if exists defect;

create table defect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    stateID int,                              -- Состояние
    name varchar(255),                        -- Наименование объекта
    data_osmotra timestamp,                   -- Дата обнаружения нарушения
    vremya_osmotra varchar(6),                -- Время обнаружения нарушения
    otchet_po_defektu varchar,                -- Примечание по дефекту
    len_tube_cur float,                       -- Длина заменённой трубы, м
    len_izol_cur float,                       -- Длина заменённой изоляции, м
    len_channel_cur float,                    -- Длина участка ремонта канала, м
    data_nachala_remonta date,                -- Дата начала ремонтных работ
    data_zaversheniya_remonta date,           -- Дата завершения ремонтных работ
    defectDescription varchar,                -- Описание нарушения
    remontTypeID int,                         -- Режим
    remontCatID int,                          -- Категории нарушений
    subdivisionID int,                        -- Подразделение производившее ремонт
    responsibleID int,                        -- Ответственный за ремонт
    primechanie varchar,                      -- Примечание
    opresID int,                              -- Наименование контура опрессовки
    shape geometry,
    defectsForDiagID int,
    priznak_truboprovoda int,                 -- Поврежденный трубопровод
    mestoPovrezhdenijaID int,                 -- Место нарушения
    tipPoverhnostiID int,                     -- Поверхность в месте раскопки
    povrezhdennyiElementID int,               -- Поврежденный элемент 
    tipPovrezhdeniaID int,                    -- Характер повреждения
    prichinyPovrezhdeniaID int,
    soputstvuiushchiePrichinyID int,
    sostKonstruktsiiKanalaID int,
    sostKonstruktsiiKameryID int,
    sostTeploizolID int,                      -- Состояние теплоизоляции
    sostNaruzhnoiPoverkhnostiID int,          -- Состояние наружной поверхности поврежденной трубы
    sostVnutrenneiPoverkhnostiID int,         -- Состояние внутренней поверхности поврежденной трубы
    tsentrPovrezhdenia varchar(100),          -- Место расположения центра повреждения на трубопроводе, ч
    vysotaPovrezhdenia float default ('0.00'),    -- Высота повреждения, мм
    shirinaPovrezhdenia float default ('0.00'),   -- Ширина повреждения, мм
    ploshchadPovrezhdenia float default ('0.00'), -- Площадь повреждения, мм^2
    stoimostRemonta money,                    -- Стоимость ремонтных работ, тг
    shirinaZaplatki float,                    -- Ширина заплатки, мм
    vysotaZaplatki float,                     -- Высота заплатки, мм
    remontIzolKonstruktsiiID int,             -- Ремонт теплоизоляционной конструкции
    rasstoyanieDoPovrezhdeniyaNachKamery float,   -- Расстояние до нарушения от ближайшей камеры, м
    brigadesID int,                           -- Ремонтная бригада
    vremiaNachalaRemonta varchar(5),          -- Время начала ремонтных работ
    vremiaZaversheniaRemonta varchar(5),      -- Время завершения ремонтных работ
    meropriyatiya varchar,                    -- Способ ликвидации нарушения
    trudozatratyNaRemont float,               -- Трудозатраты на ремонт, чел х час
    osmotrID int,                             -- Наименование контура осмотра
    ulicaID int,                              -- Улица
    nomer_doma varchar(15),                   -- Номер дома
    vid_narusheniyaID int,                    -- Вид нарушения
    prichiny_narusheniya_organizacionnyeID int,
    sostoyanie_teploizolyacii_teploprovodaID int,
    kolichestvo_otklyuchennyh_potrebitelej int,   -- Количество отключенных потребителей
    zatraty_na_vosstanovlenie money,          -- Затраты на восстановление, тг
    inye_socialnye_posledstviya varchar,      -- Иные социальные последствия
    nodeID1 int,                              -- Начальная камера отключения от сети
    nodeID2 int,                              -- Конечная камера отключения от сети
    nomer_akta varchar(30),                   -- Номер акта расследования
    nomer_prikaza varchar(30),                -- Номер приказа на ввод в эксплуатацию
    vid_rabotID int,                          -- Вид работ ремонта
    dreniruemyj_truboprovodID int,            -- Дренируемый трубопровод
    kamery_otkrytiya_drenazhejID int,
    komissiya_rassledovaniyaID int,
    data_shurfovki date,                      -- Дата шурфовки
    data_sostavleniya_akta timestamp,         -- Дата акта расследования
    prikaz_vvoda_v_ekspluataciyu varchar,     -- Приказ ввода в эксплуацию
    kolichestvo_nedootpushchennoj_teplovoj_energii float, -- Количество недоотпущенной тепловой энергии, ГКал
    predsedatel varchar,                      -- Председатель комиссии
    dolzhnost_predsedatelya int,              -- Должность председателя
    chlen_tn_1 varchar,                       -- Член комиссии 1
    dolzhnost_tn_1 int,                       -- Должность
    chlen_tn_2 varchar,                       -- Член комиссии 2
    dolzhnost_tn_2 int,                       -- Должность
    chlen_tn_3 varchar,                       -- Член комиссии 3
    dolzhnost_tn_3 int,                       -- Должность
    remont_kameryID int,                      -- Ремонт камеры
    remont_kanalaID int,                      -- Ремонт канала
    materialy_i_mekhanizmyID int,
    show_map int default ((1)),
    data_prikaza_vvoda_v_ekspluataciyu date,  -- Дата приказа ввода в эксплуацию
    nodeID_bizhajshej_kamery int,             -- Ближайшая камера
    transfer_flag int default ((0)),
    remontID int,
    remontNodeID int 
);
CREATE INDEX defect_lineid_idx ON defect (lineid);
CREATE INDEX defect_nodeid1_idx ON defect (nodeid1);
CREATE INDEX defect_nodeid2_idx ON defect (nodeid2);
-- CREATE INDEX defect_shape_idx ON defect USING GIST (shape);
---------------------------------
-- opressovka_sektsioniruyuschaya_zadvizhka - Ремонт 2
-- opressovka_sektsioniruyuschaya_zadvizhka - Опрессовка секционирующая задвижка
drop table if exists opressovka_sektsioniruyuschaya_zadvizhka;

create table opressovka_sektsioniruyuschaya_zadvizhka (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    nomer varchar(50),                        -- Номер
    shape geometry 
);
CREATE INDEX opressovka_sektsioniruyuschaya_zadvizhka_lineid_idx ON opressovka_sektsioniruyuschaya_zadvizhka (lineid);
CREATE INDEX opressovka_sektsioniruyuschaya_zadvizhka_nodeid_idx ON opressovka_sektsioniruyuschaya_zadvizhka (nodeid);
-- CREATE INDEX opressovka_sektsioniruyuschaya_zadvizhka_shape_idx ON opressovka_sektsioniruyuschaya_zadvizhka USING GIST (shape);
---------------------------------
-- diag - Ремонт 2
-- diag - Диагностика (устарело)
drop table if exists diag;

create table diag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    sredstvoDiagID int,                       -- Средства диагностики
    diam_usl float,                           -- Диаметр условный, мм
    priznak_truboprovoda int,                 -- Признак участка трубопровода
    data_prov timestamp,                      -- Дата проведения
    mesto_vskr varchar(255),                  -- Место проведения (адрес) вскрытия
    naznachenie_vskrID int,                   -- Назначение вскрытия
    nomer_akta_vskr varchar(50),              -- Номер акта вскрытия
    otchet_vskr varchar,                      -- Результаты осмотра (отчет) вскрытия
    mesto_vyr varchar(255),                   -- Место проведения (адрес) вырезки
    naznachenie_vyrID int,                    -- Назначение вырезки
    nomer_akta_vyr varchar(50),               -- Номер акта вырезки
    otchet_vyr varchar,                       -- Результаты осмотра (отчет) вырезки
    vneshny_vidID int,                        -- Внешний вид
    sost_oborudID int,                        -- Состояние оборудования
    sost_konstrID int,                        -- Состояние строительных конструкций
    otchet_osv varchar,                       -- Результаты осмотра (отчет)
    vc1 int,                                  -- наличие воды в канале
    vc2 int,                                  -- занос канала грунтом, когда вода или грунт достигают изоляционного слоя
    vc3 int,                                  -- увлажнение теплоизоляционной конструкции капельной влагой с перекрытия канала или влагой, стекающей по щитовой опоре
    vc4 int,                                  -- наличие на поверхности труб следов коррозии в виде язв или пятен
    vc5 int,                                  -- с продуктами коррозии на отдельных участках поверхности металла труб.
    vt1 int,                                  -- механические повреждения основного металла и наплавленного металла сварных соединений
    vt2 int,                                  -- трещины и других поверхностные дефекты
    vt3 int,                                  -- коррозионные повреждения поверхности металла трубопроводов и сварных соединений
    vt4 int,                                  -- деформированных участков трубопровода (коробление, провисание и другие отклонения от первоначальной формы)
    tol1 float,                               -- Первоначальная толщина металла труб
    tol2 float,                               -- Фактическая толщина стенки трубопровода
    glubina_kor float,                        -- Глубина коррозионных повреждений, мм
    int_korID int,                            -- Интенсивности процесса внутренней коррозии
    razmery_kor float,                        -- Размеры зон коррозионных повреждений, мм
    sost_pokrID int,                          -- Состояние покровного слоя изоляции
    antikorpokrID int,                        -- Антикоррозионное покрытие труб
    zashemID int,                             -- Защемления трубопроводов
    sost_podvID int,                          -- Состояние подвесок
    sost_oporID int,                          -- Состояние опор
    nalich_obrKlID int,                       -- Наличие обратных клапанов
    sootv_nadpID int,                         -- Соответствие надписей на арматуре
    nalich_tabl_regID int,                    -- Наличие табличек с регистрационными номерами
    nalich_tabl_parID int,                    -- Наличие таблички с разрешенными параметрами работы
    subdivisionID int,                        -- Подразделение производившего работы
    responsibleID int,                        -- Ответственное лицо
    primechanie varchar,                      -- Примечание
    shape geometry,
    statusTypesID int                         -- Состояние
);
CREATE INDEX diag_lineid_idx ON diag (lineid);
-- CREATE INDEX diag_shape_idx ON diag USING GIST (shape);
--- Ремонт 2: 5
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- defect mestopovrezhdenija - lookup Ремонт 2
-- mestopovrezhdenija - mestopovrezhdenija
drop table if exists mestopovrezhdenija;

create table mestopovrezhdenija (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "mestopovrezhdenija" ("id","name","ord") VALUES
(1,'Камера',1),
(2,'Непроходной канал',2),
(3,'Полупроходной канал',3),
(4,'В гильзе',4),
(5,'По подвалу',5),
(6,'Надземная',6),
(7,'В пределах ПНС',7);


-- SELECT setval('"mestopovrezhdenija_id_seq"', 7);

---------------------------------
-- defect tippoverhnosti - lookup Ремонт 2
-- tippoverhnosti - tippoverhnosti
drop table if exists tippoverhnosti;

create table tippoverhnosti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "tippoverhnosti" ("id","name","ord") VALUES
(1,'Без раскопки',1),
(2,'Грунт',2),
(3,'Тротуар',3),
(4,'Проезжая часть дороги',4);


-- SELECT setval('"tippoverhnosti_id_seq"', 4);

---------------------------------
-- defect sostteploizol - lookup Ремонт 2
-- sostteploizol - sostteploizol
drop table if exists sostteploizol;

create table sostteploizol (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "sostteploizol" ("id","name","ord") VALUES
(1,'Хорошее',1),
(2,'Разрушено частично',2),
(3,'Разрушено полностью',3);


-- SELECT setval('"sostteploizol_id_seq"', 3);

---------------------------------
-- defect povrezhdennyielement - lookup Ремонт 2
-- povrezhdennyielement - povrezhdennyielement
drop table if exists povrezhdennyielement;

create table povrezhdennyielement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int not null 
);

INSERT INTO "povrezhdennyielement" ("id","name","ord") VALUES
(1,'Прямой участок',1),
(2,'Прямой участок встене или Н.О.',2),
(3,'Прямой участок в скользящей опоре',3),
(4,'Отвод',4),
(5,'Байпас',5),
(6,'Переход(конус)',6),
(7,'Задвижка',7),
(8,'СК',7),
(9,'СКУ',7),
(10,'Дренаж (спускник)',7),
(11,'Воздушник',7);


-- SELECT setval('"povrezhdennyielement_id_seq"', 11);

---------------------------------
-- defect sostvnutrenneipoverkhnosti - lookup Ремонт 2
-- sostvnutrenneipoverkhnosti - Состояние внутренней прверхности
drop table if exists sostvnutrenneipoverkhnosti;

create table sostvnutrenneipoverkhnosti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "sostvnutrenneipoverkhnosti" ("id","name","ord") VALUES
(1,'Следов внутренней коррозии нет',1),
(2,'Отложения, бугры, глубина язв незначительна',2),
(3,'Значительные поражения стенки трубы',3);


-- SELECT setval('"sostvnutrenneipoverkhnosti_id_seq"', 3);

---------------------------------
-- defect sostnaruzhnoipoverkhnosti - lookup Ремонт 2
-- sostnaruzhnoipoverkhnosti - sostnaruzhnoipoverkhnosti
drop table if exists sostnaruzhnoipoverkhnosti;

create table sostnaruzhnoipoverkhnosti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "sostnaruzhnoipoverkhnosti" ("id","name","ord") VALUES
(1,'Антикоррозионное покрытие не нарушено',1),
(2,'Локальная коррозия',2),
(3,'Сплошная коррозия',3);


-- SELECT setval('"sostnaruzhnoipoverkhnosti_id_seq"', 3);

---------------------------------
-- defect remontizolkonstruktsii - lookup Ремонт 2
-- remontizolkonstruktsii - remontizolkonstruktsii
drop table if exists remontizolkonstruktsii;

create table remontizolkonstruktsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);

INSERT INTO "remontizolkonstruktsii" ("id","name","ord") VALUES
(1,'Восстановлена полностью',1),
(2,'Выполнена только противокоррозионная покраска',2),
(3,'Работы не проводились',3);


-- SELECT setval('"remontizolkonstruktsii_id_seq"', 3);

---------------------------------
-- defect tippovrezhdenia - lookup Ремонт 2
-- tippovrezhdenia - tippovrezhdenia
drop table if exists tippovrezhdenia;

create table tippovrezhdenia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int not null 
);

INSERT INTO "tippovrezhdenia" ("id","name","ord") VALUES
(1,'Разрыв',1),
(2,'Свищ',2),
(3,'Разгерметизация СК',3),
(4,'Механическая деформация трубы',4),
(5,'Дефект задвижки',5);


-- SELECT setval('"tippovrezhdenia_id_seq"', 5);

---------------------------------
-- defect defecttypes - lookup Ремонт 2
-- defecttypes - Типы дефектов
drop table if exists defecttypes;

create table defecttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "defecttypes" ("id","name","code","ord") VALUES
(1,'Эксплуатация','Д',1),
(2,'Опресовка','И',2),
(3,'Шурфовка','Ш',3),
(4,'Плановое освидетельствование','О',4),
(5,'Плановая вырезка','В',5),
(6,'Осмотр','В',6),
(7,'Ремонт',NULL,7);


-- SELECT setval('"defecttypes_id_seq"', 7);

---------------------------------
-- defect defectstates - lookup Ремонт 2
-- defectstates - Состояния дефектов
drop table if exists defectstates;

create table defectstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "defectstates" ("id","name","code","ord") VALUES
(1,'Повреждение','Д',1),
(2,'Ремонт','Р',2),
(3,'После ремонта','ПР',3);


-- SELECT setval('"defectstates_id_seq"', 3);

---------------------------------
-- defect brigades - lookup Ремонт 2
-- brigades - Бригады
drop table if exists brigades;

create table brigades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    responsiblesID int not null,
    subdivisionsID int not null,
    kolichestvoСhelovek int not null 
);

---------------------------------
-- defect vid_narusheniya - lookup Ремонт 2
-- vid_narusheniya - vid_narusheniya
drop table if exists vid_narusheniya;

create table vid_narusheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    code varchar(10) not null,
    ord int 
);

INSERT INTO "vid_narusheniya" ("id","name","code","ord") VALUES
(1,'Авария','А',1),
(2,'Технологический отказ','ТО',2),
(3,'функциональный отказ','ФО',3);


-- SELECT setval('"vid_narusheniya_id_seq"', 3);

---------------------------------
-- defect dreniruemyj_truboprovod - lookup Ремонт 2
-- dreniruemyj_truboprovod - Дренируемый трубопровод
drop table if exists dreniruemyj_truboprovod;

create table dreniruemyj_truboprovod (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    code varchar(10) not null,
    ord int 
);

INSERT INTO "dreniruemyj_truboprovod" ("id","name","code","ord") VALUES
(1,'подающий','П',1),
(2,'обратный','О',2),
(3,'оба трубопровода','ОБ',3);


-- SELECT setval('"dreniruemyj_truboprovod_id_seq"', 3);

---------------------------------
-- defect vid_rabot - lookup Ремонт 2
-- vid_rabot - vid_rabot
drop table if exists vid_rabot;

create table vid_rabot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    code varchar(10) not null,
    ord int 
);

INSERT INTO "vid_rabot" ("id","name","code","ord") VALUES
(2,'Текущий ремонт','ТР',2),
(3,'Капитальный ремонт','КР',3),
(4,'Инвестиционный ремонт','ИР',4),
(6,'Опресовка','О',5);


-- SELECT setval('"vid_rabot_id_seq"', 6);

---------------------------------
-- defect remont_kanala - lookup Ремонт 2
-- remont_kanala - remont_kanala
drop table if exists remont_kanala;

create table remont_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    code varchar(10),
    ord int 
);

INSERT INTO "remont_kanala" ("id","name","code","ord") VALUES
(1,'восстановлен старыми элементами',NULL,1),
(2,'плиты перекрытия заменены на новые',NULL,2),
(3,'конструкции канала заменены полностью',NULL,3);


-- SELECT setval('"remont_kanala_id_seq"', 3);

---------------------------------
-- defect remont_kamery - lookup Ремонт 2
-- remont_kamery - remont_kamery
drop table if exists remont_kamery;

create table remont_kamery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    code varchar(10),
    ord int 
);

INSERT INTO "remont_kamery" ("id","name","code","ord") VALUES
(1,'восстановлен старыми элементами',NULL,1),
(2,'плиты перекрытия заменены на новые',NULL,2),
(3,'конструкции канала заменены полностью',NULL,3);


-- SELECT setval('"remont_kamery_id_seq"', 3);

---------------------------------
-- shurfy sostoyanie_shurfa - lookup Ремонт 2
-- sostoyanie_shurfa - Состояние шурфа
drop table if exists sostoyanie_shurfa;

create table sostoyanie_shurfa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "sostoyanie_shurfa" ("id","name","ord") VALUES
(1,'План',1),
(2,'В процессе',2),
(3,'Выполнено',3);


-- SELECT setval('"sostoyanie_shurfa_id_seq"', 3);

---------------------------------
-- shurfy ustrojstva_vodootvedeniya - lookup Ремонт 2
-- ustrojstva_vodootvedeniya - ustrojstva_vodootvedeniya
drop table if exists ustrojstva_vodootvedeniya;

create table ustrojstva_vodootvedeniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "ustrojstva_vodootvedeniya" ("id","name","ord") VALUES
(1,'не имеется',1),
(2,'работоспособно',2),
(3,'неработоспособно',3);


-- SELECT setval('"ustrojstva_vodootvedeniya_id_seq"', 3);

---------------------------------
-- shurfy da_net_informacii - lookup Ремонт 2
-- da_net_informacii - Да нет информации
drop table if exists da_net_informacii;

create table da_net_informacii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "da_net_informacii" ("id","name","ord") VALUES
(1,'да',1),
(2,'нет',2),
(3,'нет информации',3);


-- SELECT setval('"da_net_informacii_id_seq"', 3);

---------------------------------
-- shurfy gidroizolyacionnaya_konstrukciya - lookup Ремонт 2
-- gidroizolyacionnaya_konstrukciya - Гидроизоляционные конструкции
drop table if exists gidroizolyacionnaya_konstrukciya;

create table gidroizolyacionnaya_konstrukciya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "gidroizolyacionnaya_konstrukciya" ("id","name","ord") VALUES
(1,'в хорошем состоянии',1),
(2,'разрушена частично',2),
(3,'разрушена полностью ',3);


-- SELECT setval('"gidroizolyacionnaya_konstrukciya_id_seq"', 3);

---------------------------------
-- shurfy sostoyanie_protivokorrozionnogo_pokrytiya_shurf - lookup Ремонт 2
-- sostoyanie_protivokorrozionnogo_pokrytiya_shurf - Состояние противокоррозионног покрытия
drop table if exists sostoyanie_protivokorrozionnogo_pokrytiya_shurf;

create table sostoyanie_protivokorrozionnogo_pokrytiya_shurf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);

INSERT INTO "sostoyanie_protivokorrozionnogo_pokrytiya_shurf" ("id","name","ord") VALUES
(1,'в хорошем состоянии',1),
(2,'отсутствует частично',2),
(3,'отсутствует полностью',3);


-- SELECT setval('"sostoyanie_protivokorrozionnogo_pokrytiya_shurf_id_seq"', 3);

---------------------------------
-- remont statedefect - lookup Ремонт 2
-- statedefect - Состояние
drop table if exists statedefect;

create table statedefect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "statedefect" ("id","name","code","ord") VALUES
(1,'Нарушение','Д',1),
(2,'Ремонт','Р',2),
(3,'После ремонта','П',3);


-- SELECT setval('"statedefect_id_seq"', 3);

---------------------------------
-- diag statustypes - lookup Ремонт 2
-- statustypes - statustypes
drop table if exists statustypes;

create table statustypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    visible varchar 
);

INSERT INTO "statustypes" ("id","name","visible") VALUES
(1,'Удовлетворительное','diag'),
(2,'Залита','diag'),
(3,'Засыпана','diag'),
(4,'Заилена','diag'),
(5,'Разрушена','diag'),
(6,'Не открыли','diag'),
(7,'Нет доступа','diag'),
(8,'Другое','diag');


-- SELECT setval('"statustypes_id_seq"', 8);

---------------------------------
-- diag sredstvodiag - lookup Ремонт 2
-- sredstvodiag - Средства диагностики
drop table if exists sredstvodiag;

create table sredstvodiag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "sredstvodiag" ("id","name","code","ord") VALUES
(1,'Шурф',NULL,1),
(2,'Вырезка',NULL,2),
(3,'Освидетельствование',NULL,3);


-- SELECT setval('"sredstvodiag_id_seq"', 3);

---------------------------------
-- diag vneshny_vid - lookup Ремонт 2
-- vneshny_vid - vneshny_vid
drop table if exists vneshny_vid;

create table vneshny_vid (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "vneshny_vid" ("id","name","code","ord") VALUES
(1,'Наличие поверхностных повреждений',NULL,1),
(2,'Отсутствие поверхностных повреждений',NULL,2);


-- SELECT setval('"vneshny_vid_id_seq"', 2);

---------------------------------
-- diag sost_oborud - lookup Ремонт 2
-- sost_oborud - sost_oborud
drop table if exists sost_oborud;

create table sost_oborud (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "sost_oborud" ("id","name","code","ord") VALUES
(1,'новое',NULL,1),
(2,'почти новое',NULL,2),
(3,'в работе в не аварийном состоянии',NULL,3),
(4,'в работе в предаварийном состоянии',NULL,4),
(5,'в работе в аварийном состоянии',NULL,5),
(6,'не работает по причине невозможности эксплуатации',NULL,6);


-- SELECT setval('"sost_oborud_id_seq"', 6);

---------------------------------
-- diag sost_konstr - lookup Ремонт 2
-- sost_konstr - sost_konstr
drop table if exists sost_konstr;

create table sost_konstr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "sost_konstr" ("id","name","code","ord") VALUES
(1,'Нарушение герметичности стыков (3 балла); ',NULL,1),
(2,'Излом конструкций перекрытия и стен канала (5 балла); ',NULL,2),
(3,'Отклонение от проектных решений, произошедшие в процессе эксплуатации (1 балла); ',NULL,3),
(4,'Снижение несущей способности конструкций (3 балла); ',NULL,4),
(5,'Разрушение неподвижных опор (5 балла);)  ',NULL,5);


-- SELECT setval('"sost_konstr_id_seq"', 5);
--- Ремонт 2 lookup: 27
--===========================--
--        Документы             --
--===========================--
---------------------------------
-- defectdocuments - Документы
-- defectdocuments - Документы дефектов
drop table if exists defectdocuments;

create table defectdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,                 -- Наименование документа
    date_doc date,                            -- Дата
    path varchar(256)                         -- Документ
);
---------------------------------
-- docdiagosv - Документы
-- docdiagosv - Документы диагностики осв
drop table if exists docdiagosv;

create table docdiagosv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- docdiagvskr - Документы
-- docdiagvskr - Документы диагностики вскрытия
drop table if exists docdiagvskr;

create table docdiagvskr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- docdiagvyr - Документы
-- docdiagvyr - Документы диагностики вырубки
drop table if exists docdiagvyr;

create table docdiagvyr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- electrodocuments - Документы
-- electrodocuments - Электрические документы
drop table if exists electrodocuments;

create table electrodocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- electrodocumentsist - Документы
-- electrodocumentsist - Электрические документы ист
drop table if exists electrodocumentsist;

create table electrodocumentsist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- electrodocumentspr - Документы
-- electrodocumentspr - Электрические документы пр
drop table if exists electrodocumentspr;

create table electrodocumentspr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- gilza_esdocuments - Документы
-- gilza_esdocuments - Гильза документы
drop table if exists gilza_esdocuments;

create table gilza_esdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- kabelnyy_kanal_esdocuments - Документы
-- kabelnyy_kanal_esdocuments - kabelnyy_kanal_esdocuments
drop table if exists kabelnyy_kanal_esdocuments;

create table kabelnyy_kanal_esdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- muftadocuments - Документы
-- muftadocuments - muftadocuments
drop table if exists muftadocuments;

create table muftadocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- opora_esdocuments - Документы
-- opora_esdocuments - opora_esdocuments
drop table if exists opora_esdocuments;

create table opora_esdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- opresacts - Документы
-- opresacts - opresacts
drop table if exists opresacts;

create table opresacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- opresdocuments - Документы
-- opresdocuments - opresdocuments
drop table if exists opresdocuments;

create table opresdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- osmotrdocuments - Документы
-- osmotrdocuments - osmotrdocuments
drop table if exists osmotrdocuments;

create table osmotrdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- realconsumerdocuments1 - Документы
-- realconsumerdocuments1 - realconsumerdocuments1
drop table if exists realconsumerdocuments1;

create table realconsumerdocuments1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- realconsumerdocuments2 - Документы
-- realconsumerdocuments2 - realconsumerdocuments2
drop table if exists realconsumerdocuments2;

create table realconsumerdocuments2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- realconsumerdocuments3 - Документы
-- realconsumerdocuments3 - realconsumerdocuments3
drop table if exists realconsumerdocuments3;

create table realconsumerdocuments3 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- remontdocumenttypes - Документы
-- remontdocumenttypes - remontdocumenttypes
drop table if exists remontdocumenttypes;

create table remontdocumenttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- remontdocuments - Документы
-- remontdocuments - remontdocuments
drop table if exists remontdocuments;

create table remontdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- shurfdocuments - Документы
-- shurfdocuments - shurfdocuments
drop table if exists shurfdocuments;

create table shurfdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- tkameradocuments - Документы
-- tkameradocuments - tkameradocuments
drop table if exists tkameradocuments;

create table tkameradocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- vidy_dokumentov_osmotra - Документы
-- vidy_dokumentov_osmotra - vidy_dokumentov_osmotra
drop table if exists vidy_dokumentov_osmotra;

create table vidy_dokumentov_osmotra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);
---------------------------------
-- vidy_dokumentov_shurfa - Документы
-- vidy_dokumentov_shurfa - vidy_dokumentov_shurfa
drop table if exists vidy_dokumentov_shurfa;

create table vidy_dokumentov_shurfa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);
---------------------------------
-- defectchannel - Документы
-- defectchannel - Дефект канала
drop table if exists defectchannel;

create table defectchannel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- defectkamera - Документы
-- defectkamera - Дефект камера
drop table if exists defectkamera;

create table defectkamera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- defecttube - Документы
-- defecttube - Дефект трубы
drop table if exists defecttube;

create table defecttube (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int,
    elementID int 
);
---------------------------------
-- nalichie_vblizi_kommunikacij_for_shurfy - Документы
-- nalichie_vblizi_kommunikacij_for_shurfy - nalichie_vblizi_kommunikacij_for_shurfy
drop table if exists nalichie_vblizi_kommunikacij_for_shurfy;

create table nalichie_vblizi_kommunikacij_for_shurfy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- povrezhdennyielementfordefect - Документы
-- povrezhdennyielementfordefect - Поврежденные элементы
drop table if exists povrezhdennyielementfordefect;

create table povrezhdennyielementfordefect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- prichinypovrezhdenia - Документы
-- prichinypovrezhdenia - prichinypovrezhdenia
drop table if exists prichinypovrezhdenia;

create table prichinypovrezhdenia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);
---------------------------------
-- prichinypovrezhdeniafordefect - Документы
-- prichinypovrezhdeniafordefect - prichinypovrezhdeniafordefect
drop table if exists prichinypovrezhdeniafordefect;

create table prichinypovrezhdeniafordefect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- prichiny_narusheniya_organizacionnye - Документы
-- prichiny_narusheniya_organizacionnye - prichiny_narusheniya_organizacionnye
drop table if exists prichiny_narusheniya_organizacionnye;

create table prichiny_narusheniya_organizacionnye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- prichiny_narusheniya_organizacionnye_for_defect - Документы
-- prichiny_narusheniya_organizacionnye_for_defect - Причины нарушения организационные для дефектов
drop table if exists prichiny_narusheniya_organizacionnye_for_defect;

create table prichiny_narusheniya_organizacionnye_for_defect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- remonttruboprovodaspisok - Документы
-- remonttruboprovodaspisok - remonttruboprovodaspisok
drop table if exists remonttruboprovodaspisok;

create table remonttruboprovodaspisok (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);
---------------------------------
-- remonttubetypes - Документы
-- remonttubetypes - remonttubetypes
drop table if exists remonttubetypes;

create table remonttubetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(500) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- soputstvuiushchieprichiny - Документы
-- soputstvuiushchieprichiny - soputstvuiushchieprichiny
drop table if exists soputstvuiushchieprichiny;

create table soputstvuiushchieprichiny (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);
---------------------------------
-- soputstvuiushchieprichinyfordefect - Документы
-- soputstvuiushchieprichinyfordefect - soputstvuiushchieprichinyfordefect
drop table if exists soputstvuiushchieprichinyfordefect;

create table soputstvuiushchieprichinyfordefect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- sostkonstruktsiikamery - Документы
-- sostkonstruktsiikamery - sostkonstruktsiikamery
drop table if exists sostkonstruktsiikamery;

create table sostkonstruktsiikamery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);
---------------------------------
-- sostkonstruktsiikameryfordefect - Документы
-- sostkonstruktsiikameryfordefect - sostkonstruktsiikameryfordefect
drop table if exists sostkonstruktsiikameryfordefect;

create table sostkonstruktsiikameryfordefect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- sostkonstruktsiikanala - Документы
-- sostkonstruktsiikanala - sostkonstruktsiikanala
drop table if exists sostkonstruktsiikanala;

create table sostkonstruktsiikanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);
---------------------------------
-- sostkonstruktsiikanalafordefect - Документы
-- sostkonstruktsiikanalafordefect - Состояние конструкции канала
drop table if exists sostkonstruktsiikanalafordefect;

create table sostkonstruktsiikanalafordefect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- spisokelementov - Документы
-- spisokelementov - spisokelementov
drop table if exists spisokelementov;

create table spisokelementov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- vidy_elementov_for_shurfy - Документы
-- vidy_elementov_for_shurfy - vidy_elementov_for_shurfy
drop table if exists vidy_elementov_for_shurfy;

create table vidy_elementov_for_shurfy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activityID int not null,
    objID int not null 
);
---------------------------------
-- vidy_elementov_shurf - Документы
-- vidy_elementov_shurf - vidy_elementov_shurf
drop table if exists vidy_elementov_shurf;

create table vidy_elementov_shurf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);
--- Документы: 43
--===========================--
--         lookup            --
--===========================--
--- Документы lookup: 0
--===========================--
--        Мероприятия             --
--===========================--
---------------------------------
-- defectmeropr - Мероприятия
-- defectmeropr - Дефект меропр
drop table if exists defectmeropr;

create table defectmeropr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- defectmeroprtype - Мероприятия
-- defectmeroprtype - Тип мероприятий по дефектам
drop table if exists defectmeroprtype;

create table defectmeroprtype (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- opresmeropr - Мероприятия
-- opresmeropr - opresmeropr
drop table if exists opresmeropr;

create table opresmeropr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontcapitalchannel - Мероприятия
-- remontcapitalchannel - remontcapitalchannel
drop table if exists remontcapitalchannel;

create table remontcapitalchannel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontcapitalchanneltypes - Мероприятия
-- remontcapitalchanneltypes - remontcapitalchanneltypes
drop table if exists remontcapitalchanneltypes;

create table remontcapitalchanneltypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- remontcapitalkamera - Мероприятия
-- remontcapitalkamera - remontcapitalkamera
drop table if exists remontcapitalkamera;

create table remontcapitalkamera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontcapitaltube - Мероприятия
-- remontcapitaltube - remontcapitaltube
drop table if exists remontcapitaltube;

create table remontcapitaltube (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontcapitaltubetypes - Мероприятия
-- remontcapitaltubetypes - remontcapitaltubetypes
drop table if exists remontcapitaltubetypes;

create table remontcapitaltubetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(500) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- remontchannel - Мероприятия
-- remontchannel - remontchannel
drop table if exists remontchannel;

create table remontchannel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontchanneltypes - Мероприятия
-- remontchanneltypes - remontchanneltypes
drop table if exists remontchanneltypes;

create table remontchanneltypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- remontinvestchannel - Мероприятия
-- remontinvestchannel - remontinvestchannel
drop table if exists remontinvestchannel;

create table remontinvestchannel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontinvestchanneltypes - Мероприятия
-- remontinvestchanneltypes - remontinvestchanneltypes
drop table if exists remontinvestchanneltypes;

create table remontinvestchanneltypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- remontinvestkamera - Мероприятия
-- remontinvestkamera - remontinvestkamera
drop table if exists remontinvestkamera;

create table remontinvestkamera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontinvesttube - Мероприятия
-- remontinvesttube - remontinvesttube
drop table if exists remontinvesttube;

create table remontinvesttube (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remontinvesttubetypes - Мероприятия
-- remontinvesttubetypes - remontinvesttubetypes
drop table if exists remontinvesttubetypes;

create table remontinvesttubetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(500) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- remontkamera - Мероприятия
-- remontkamera - remontkamera
drop table if exists remontkamera;

create table remontkamera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- remonttube - Мероприятия
-- remonttube - remonttube
drop table if exists remonttube;

create table remonttube (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
--- Мероприятия: 17
--===========================--
--         lookup            --
--===========================--
--- Мероприятия lookup: 0
--===========================--
--        Геобаза             --
--===========================--
---------------------------------
-- defekt - Геобаза
-- defekt - Нарушение
drop table if exists defekt;

create table defekt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    sostoyanie int default ((1)),             -- Состояние
    prichina_defekta varchar(255) default (NULL), -- Причина повреждения
    uchastok_ekspluatatsii varchar(255) default (NULL),   -- Участок эксплуатации
    istochnik_tepla int default (NULL),       -- Источник тепла
    magistral_raspredset varchar(255) default (NULL), -- Магистраль/Распредсеть
    nachalnik_uchastka varchar(255) default (NULL),   -- Начальник участка
    chleny_komissii__nachalnik_sluzhby_ekspluatatsii varchar(255) default (NULL), -- Члены комиссии: Начальник службы эксплуатации
    chleny_komissii__inzhener_ps varchar(255) default (NULL), -- Члены комиссии: Инженер ПС
    god_vvoda_v_ekspluatatsiyu date default (NULL),   -- Год ввода в эксплуатацию
    dlitelnost_ekspluatatsii int default (NULL),  -- Длительность эксплуатации
    vid_prokladki int default (NULL),         -- Вид прокладки
    izolyatsiya_truby int default (NULL),     -- Изоляция трубы
    tip_truby int default (NULL),             -- Тип трубы
    harakteristika_truby int default (NULL),  -- Характеристика трубы
    data_osmotra date default (NULL),         -- Дата обнаружения повреждения
    vremya_osmotra varchar(6) default (NULL), -- Время обнаружения повреждения
    ulitsa int default (NULL),                -- Улица
    nomer_doma varchar(255) default (NULL),   -- Номер дома
    teplonositel int default (NULL),          -- Теплоноситель
    kod_rs_nachalnoy_kamery int default (NULL),   -- Код РС начальной камеры
    nachalnaya_kamera varchar(255) default (NULL),    -- Начальная камера
    kod_rs_konechnoy_kamery int default (NULL),   -- Код РС конечной камеры
    konechnaya_kamera varchar(255) default (NULL),    -- Конечная камера
    kod_rs_blizhayshey_kamery varchar(255) default (NULL),    -- Код РС ближайшей камеры
    blizhayshaya_kamera varchar(255) default (NULL),  -- Ближайшая камера
    rasstoyanie_do_kamery__m int default (NULL),  -- Расстояние до камеры, м
    opisanie_defekta text default (NULL),     -- Описание повреждения
    diametr_truby_podayuschiy__uslovn__mm int default (NULL), -- Диаметр трубы подающий, условн, мм
    diametr_truby_obratnyy__uslovn__mm int default (NULL),    -- Диаметр трубы обратный, условн, мм
    dlina_uchastka_truboprovoda__podayuschiy__m int default (NULL),   -- Длина участка трубопровода, подающий, м
    dlina_uchastka_truboprovoda__obratnyy__m int default (NULL),  -- Длина участка трубопровода, обратный, м
    uchastok_osmotren_na_dline__m int default (NULL), -- Участок осмотрен на длине, м
    glubina_zalozheniya_truboprovodov float default (NULL),   -- Глубина заложения трубопроводов
    rasstoyanie_mezhdu_osyami_teploprovodov float default (NULL), -- Расстояние между осями теплопроводов
    harakter_grunta int default (NULL),       -- Характер грунта
    poverhnost_zemli_nad_trassoy int default (NULL),  -- Поверхность земли над трассой
    nalichie_vblizi_elektrifitsirovannogo_transporta int default (NULL),  -- Наличие вблизи электрифицированного транспорта
    rasstoyanie_do_relsov__m int default (NULL),  -- Расстояние до рельсов, м
    nalichie_vblizi_trassy_elektrokabeley int default (NULL), -- Наличие вблизи трассы электрокабелей
    nalichie_vblizi_trassy_gazoprovodov int default (NULL),   -- Наличие вблизи трассы газопроводов
    nalichie_vblizi_trassy_vodoprovoda int default (NULL),    -- Наличие вблизи трассы водопровода
    nalichie_vblizi_trassy_kanalizatsii int default (NULL),   -- Наличие вблизи трассы канализации
    nalichie_rabotayuschih_elektrozaschitnyh_ustanovok int default (NULL),    -- Наличие работающих электрозащитных установок
    podtoplenie_do_truby int default (NULL),  -- Подтопление до трубы
    konstruktsiya_drenazhnogo_ustroystva int default (NULL),  -- Конструкция дренажного устройства
    rabotosposobnost_drenazhnogo_ustroystva int default (NULL),   -- Работоспособность дренажного устройства
    elementy_osmotra_podayuschego_teploprovoda int default (NULL),    -- Элементы осмотра подающего теплопровода
    elementy_osmotra_obratnogo_teploprovoda int default (NULL),   -- Элементы осмотра обратного теплопровода
    pokrovnyy_sloy_material__podayuschiy int default (NULL),  -- Покровный слой материал, подающий
    pokrovnyy_sloy_material__obratnyy int default (NULL), -- Покровный слой материал, обратный
    konstruktsiya_pokrovnogo_sloya__podayuschiy int default (NULL),   -- Конструкция покровного слоя, подающий
    konstruktsiya_pokrovnogo_sloya__obratnyy int default (NULL),  -- Конструкция покровного слоя, обратный
    kolichestvo_sloev_pokrovnogo_materiala__podayuschiy int default (NULL),   -- Количество слоев покровного материала, подающий
    kolichestvo_sloev_pokrovnogo_materiala__obratnyy int default (NULL),  -- Количество слоев покровного материала, обратный
    sostoyanie_pokrovnogo_sloya_izolyatsii__podayuschiy int default (NULL),   -- Состояние покровного слоя изоляции, подающий
    sostoyanie_pokrovnogo_sloya_izolyatsii__obratnyy int default (NULL),  -- Состояние покровного слоя изоляции, обратный
    teplovaya_izolyatsiya_material__podayuschiy int default (NULL),   -- Тепловая изоляция материал, подающий
    teplovaya_izolyatsiya_material__obratnyy int default (NULL),  -- Тепловая изоляция материал, обратный
    tolschina_izolyatsii__mm__podayuschiy float default (NULL),   -- Толщина изоляции, мм, подающий
    tolschina_izolyatsii__mm__obratnyy float default (NULL),  -- Толщина изоляции, мм, обратный
    konstruktsiya_izolyatsii__podayuschiy int default (NULL), -- Конструкция изоляции, подающий
    konstruktsiya_izolyatsii__obratnyy int default (NULL),    -- Конструкция изоляции, обратный
    izdelie_izolyatsii__podayuschiy int default (NULL),   -- Изделие изоляции, подающий
    izdelie_izolyatsii__obratnyy int default (NULL),  -- Изделие изоляции, обратный
    sostoyanie_teplovoy_izolyatsii__podayuschiy int default (NULL),   -- Состояние тепловой изоляции, подающий
    sostoyanie_teplovoy_izolyatsii__obratnyy int default (NULL),  -- Состояние тепловой изоляции, обратный
    tolschina_naruzhnogo_pokrytiya__mm__podayuschiy float default (NULL), -- Толщина наружного покрытия, мм, подающий
    tolschina_naruzhnogo_pokrytiya__mm__obratnyy float default (NULL),    -- Толщина наружного покрытия, мм, обратный
    sostoyanie_gidroizolyatsionnoy_konstruktsii__podayuschiy int default (NULL),  -- Состояние гидроизоляционной конструкции, подающий
    sostoyanie_gidroizolyatsionnoy_konstruktsii__obratnyy int default (NULL), -- Состояние гидроизоляционной конструкции, обратный
    sostoyanie_protivokorrozionnogo_pokrytiya__podayuschiy int default (NULL),    -- Состояние противокоррозионного покрытия, подающий
    sostoyanie_protivokorrozionnogo_pokrytiya__obratnyy int default (NULL),   -- Состояние противокоррозионного покрытия, обратный
    nalichie_korrozii__podayuschiy int default (NULL),    -- Наличие коррозии, подающий
    nalichie_korrozii__obratnyy int default (NULL),   -- Наличие коррозии, обратный
    maksimalnaya_glubina_korrozii__podayuschiy__mm int default (NULL),    -- Максимальная глубина коррозии, подающий, мм
    maksimalnaya_glubina_korrozii__obratnyy__mm int default (NULL),   -- Максимальная глубина коррозии, обратный, мм
    diametr_kavern__podayuschiy__mm int default (NULL),   -- Диаметр каверн, подающий, мм
    diametr_kavern__obratnyy__mm int default (NULL),  -- Диаметр каверн, обратный, мм
    mesto_raspolozheniya_povrezhdeniya_po_perimetru_truby__podayusch int default (NULL),  -- Место расположения повреждения по периметру трубы, подающий
    mesto_raspolozheniya_povrezhdeniya_po_perimetru_truby__obratnyy int default (NULL),   -- Место расположения повреждения по периметру трубы, обратный
    nalichie_razryva_stenki_truby__prichiny__podayuschiy int default (NULL),  -- Наличие разрыва стенки трубы, причины, подающий
    nalichie_razryva_stenki_truby__prichiny__obratnyy int default (NULL), -- Наличие разрыва стенки трубы, причины, обратный
    nalichie_razryva_svarnogo_shva_truby__prichiny__podayuschiy int default (NULL),   -- Наличие разрыва сварного шва трубы, причины, подающий
    nalichie_razryva_svarnogo_shva_truby__prichiny__obratnyy int default (NULL),  -- Наличие разрыва сварного шва трубы, причины, обратный
    shema_privyazki varchar(255) default (NULL),  -- Схема привязки
    nalichie_svischa_truby__prichiny__podayuschiy int default (NULL), -- Наличие свища трубы, причины, подающий
    nalichie_svischa_truby__prichiny__obratnyy int default (NULL),    -- Наличие свища трубы, причины, обратный
    nalichie_povrezhdeniy_elementov_truboprovoda int default (NULL),  -- Наличие повреждений элементов трубопровода
    predpolagaemye_prichiny_korrozionnogo_povrezhdeniya_metalla_trub int default (NULL),  -- Предполагаемые причины коррозионного повреждения металла трубы
    foto_korroziynogo_povrezhdeniya_truby text default (NULL),    -- Фото коррозийного повреждения трубы
    foto_mesta_avarii text default (NULL),    -- Фото места аварии
    shurf int default (NULL),                 -- Шурф
    akt_osmotra_v_shurfe int default (NULL),  -- Акт осмотра в шурфе
    nomer_akta_osmotra_v_shurfe varchar(255) default (NULL),  -- Номер акта осмотра в шурфе
    data_sozdaniya_akta_osmotra_v_shurfe date default (NULL), -- Дата создания акта осмотра в шурфе
    nomer_akta_osmotra_uchastka_truboprovoda int default (NULL),  -- Номер акта осмотра участка трубопровода
    data_sozdaniya_akta_osmotra_uchastka_truboprovoda date default (NULL),    -- Дата создания акта осмотра участка трубопровода
    vlazhnost_grunta int default (NULL),      -- Влажность грунта
    uroven_gruntovyh_vod_po_dannym_ekspluatatsii int default (NULL),  -- Уровень грунтовых вод по данным эксплуатации
    uroven_gruntovyh_vod_v_moment_osmotra_shurfa int default (NULL),  -- Уровень грунтовых вод в момент осмотра шурфа
    prichiny_nalichiya_gruntovyh_vod int default (NULL),  -- Причины наличия грунтовых вод
    tip_teploizolyatsionnoy_konstruktsii int default (NULL),  -- Тип теплоизоляционной конструкции
    konstruktsiyu_pokrovnogo_sloya int default (NULL),    -- Конструкцию покровного слоя
    tip_teploizolyatsionnogo_materiala int default (NULL),    -- Тип теплоизоляционного материала
    sostoyanie_kanala int default (NULL),     -- Состояние канала
    sostoyanie_konstruktsii_kanala int default (NULL),    -- Состояние конструкции канала
    nalichie_gidroizolyatsii_kanala int default (NULL),   -- Наличие гидроизоляции канала
    vysota_stoyaniya_vody_pri_zatoplenii_kanala__mm int default (NULL),   -- Высота стояния воды при затоплении канала, мм
    tolschina_sloya_ilistyh_otlozheniy_v_kanale__mm int default (NULL),   -- Толщина слоя илистых отложений в канале, мм
    pervonachalnaya_tolschina_metalla_trub__mm int default (NULL),    -- Первоначальная толщина металла труб, мм
    ostatochnaya_tolschina_metalla_trub__mm int default (NULL),   -- Остаточная толщина металла труб, мм
    namechennye_meropriyatiya_po_kanalu int default (NULL),
    namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii__podayu int default (NULL),  -- Намеченные мероприятия по изоляционной конструкции, подающий
    namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii__obratn int default (NULL),  -- Намеченные мероприятия по изоляционной конструкции, обратный
    namechennye_meropriyatiya_po_vosstanovleniyu_kanala varchar(255) default (NULL),  -- Намеченные мероприятия по восстановлению канала
    namechennye_meropriyatiya_po_truboprovodu__podayuschiy varchar(255) default (NULL),   -- Намеченные мероприятия по трубопроводу, подающий
    namechennye_meropriyatiya_po_truboprovodu__obratnyy varchar(255) default (NULL),  -- Намеченные мероприятия по трубопроводу, обратный
    namechennye_meropriyatiya_po_elementam_truboprovoda__podayuschiy varchar(255) default (NULL), -- Намеченные мероприятия по элементам трубопровода, подающий
    namechennye_meropriyatiya_po_elementam_truboprovoda__obratnyy varchar(255) default (NULL),    -- Намеченные мероприятия по элементам трубопровода, обратный
    vosstanovitelnye_raboty_shurfa text default (NULL),   -- Восстановительные работы шурфа
    data_vosstanovleniya_shurfa date default (NULL),  -- Дата восстановления шурфа
    shema_remontiruemogo_uchastka text default (NULL),    -- Схема ремонтируемого участка
    data_nachala_remonta date default (NULL), -- Дата начала ремонта
    data_zaversheniya_remonta date default (NULL),    -- Дата завершения ремонта
    remont_izolyatsionnoy_konstruktsii__podayuschiy int default (NULL),   -- Ремонт изоляционной конструкции, подающий
    remont_izolyatsionnoy_konstruktsii__obratnyy varchar(255) default (NULL), -- Ремонт изоляционной конструкции, обратный
    foto_remonta_izolyatsionnoy_konstruktsii text default (NULL), -- Фото ремонта изоляционной конструкции
    remont_po_vosstanovleniyu_kanala int default (NULL),  -- Ремонт по восстановлению канала
    foto_remonta_kanala text default (NULL),  -- Фото ремонта канала
    remont_po_truboprovodu__podayuschiy varchar(255) default (NULL),  -- Ремонт по трубопроводу, подающий
    remont_po_truboprovodu__obratnyy varchar(255) default (NULL), -- Ремонт по трубопроводу, обратный
    remont_po_elementam_truboprovoda__podayuschiy varchar(255) default (NULL),    -- Ремонт по элементам трубопровода, подающий
    remont_po_elementam_truboprovoda__obratnyy varchar(255) default (NULL),   -- Ремонт по элементам трубопровода, обратный
    rezervnye_linii text default (NULL),      -- Резервные линии
    litso__vnesshee_izmenenie__dolzhnost int default (NULL),  -- Лицо, внесшее изменение, должность
    litso__vnesshee_izmenenie__fio varchar(255) default (NULL),   -- Лицо, внесшее изменение, ФИО
    akt_shurfa text default (NULL),           -- Акт шурфа
    akt_osmotra text default (NULL),          -- Акт осмотра
    otklyuchennye_ot_tepla_potrebiteli text default (NULL),   -- Отключенные от тепла потребители
    otchet_po_remontu text default (NULL),    -- Отчет по ремонту
    otchet_osmotra text default (NULL),       -- Отчет осмотра
    shape geometry default (NULL) 
);
CREATE INDEX defekt_lineid_idx ON defekt (lineid);
-- CREATE INDEX defekt_shape_idx ON defekt USING GIST (shape);
---------------------------------
-- corrosionindicators - Геобаза
-- corrosionindicators - Индикаторы коррозии 2
drop table if exists corrosionindicators;

create table corrosionindicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicatorStateID int default ((1)),
    address varchar(250) default (NULL),
    coolantTypeID int default ((1)),
    lineID int default (NULL),
    nodeID int default (NULL),
    chambDistance float default ((0)),
    corrosionIndicatorNum varchar(255) default (NULL),
    pipelineSignID int default (NULL),
    plateCount int default ((3)),
    plateAvgWeightInstall float default ((0)),
    circPlateRad float default ((24)),
    bushRad float default ((7.5)),
    plateThickness float default ((3)),
    installDate timestamp default (NULL),
    extractDate timestamp default (NULL),
    plateAvgWeightAfterExp float default ((0)),
    massAvgLosAcidTreat float default ((0)),
    corrosionAvgRate float default ((0)),
    corrosionProcessMarkID int default (NULL),
    netWaterAggressivenessID int default (NULL),
    plateExternalView varchar,
    shape geometry default (NULL) 
);
CREATE INDEX corrosionindicators_lineid_idx ON corrosionindicators (lineid);
CREATE INDEX corrosionindicators_nodeid_idx ON corrosionindicators (nodeid);
-- CREATE INDEX corrosionindicators_shape_idx ON corrosionindicators USING GIST (shape);
---------------------------------
-- shurf2 - Геобаза
-- shurf2 - Шурф
drop table if exists shurf2;

create table shurf2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    stateID int default ((1)),                -- Назначение вскрытия
    data_osmotra timestamp default (now()),   -- Дата вскрытия
    vremya_osmotra varchar(6) default (NULL), -- Время осмотра
    rayon_ekspluatatsii varchar(255) default (NULL),  -- Район эксплуатации
    uchastok_ekspluatatsii varchar(255) default (NULL),   -- Участок эксплуатации
    magistral int default (NULL),             -- Магистраль
    uchastok_ms int default (NULL),           -- Участок МС
    uchastok_rs int default (NULL),           -- Участок РС
    kod_rs_nachalnoy_kamery varchar(255) default (NULL),  -- Код РС начальной камеры
    nachalnaya_kamera varchar(255) default (NULL),    -- Начальная камера
    kod_rs_konechnoy_kamery varchar(255) default (NULL),  -- Код РС конечной камеры
    konechnaya_kamera varchar(255) default (NULL),    -- Конечная камера
    otchet_po_defektu text default (NULL),    -- Результаты осмотра
    data_nachala_remonta date default (NULL), -- Дата начала ремонта
    data_zaversheniya_remonta date default (NULL),    -- Дата завершения ремонта
    shape geometry default (NULL) 
);
CREATE INDEX shurf2_lineid_idx ON shurf2 (lineid);
-- CREATE INDEX shurf2_shape_idx ON shurf2 USING GIST (shape);
---------------------------------
-- truby_rekonstruiruemye - Геобаза
-- truby_rekonstruiruemye - Трубы реконструируемые
drop table if exists truby_rekonstruiruemye;

create table truby_rekonstruiruemye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sostoyanie_stroitelstva varchar(1),
    gorod varchar(20),
    mikrorayon varchar(20),
    ulitsa varchar(30),
    dom varchar(30),
    kommentariy text,
    nachalnaya_kamera varchar(255),
    konechnaya_kamera varchar(255),
    nomer_tu varchar(50),
    data_vydachi_tu date,
    sostoyanie_dogovora varchar(1),
    naimenovanie_organizatsii__zaprashivayuschey_tu varchar(255),
    naimenovanie_obekta varchar(255),
    rayon_ekspluatatsii varchar(255),
    istochnik varchar(255),
    dlina float,
    diametr_uslovnyy float,
    diametr_vnutrenniy float,
    tolschina_stenki float,
    tip_truby varchar(1),
    vid_prokladki varchar(1),
    harakteristika_truby varchar(1),
    shape geometry 
);
-- CREATE INDEX truby_rekonstruiruemye_shape_idx ON truby_rekonstruiruemye USING GIST (shape);
---------------------------------
-- zdaniya_potrebiteley - Геобаза
-- zdaniya_potrebiteley - Здания потребителей
drop table if exists zdaniya_potrebiteley;

create table zdaniya_potrebiteley (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    gorod varchar(20),                        -- Город
    mikrorayon varchar(20),                   -- Микрорайон
    ulitsa varchar(30),                       -- Улица
    dom varchar(30),                          -- Дом
    kod_rs_uzla_prisoedineniya varchar(10),   -- Код РС узла присоединения
    uzel_prisoedineniya varchar(25),          -- Узел Присоединения
    shape geometry                            -- SHAPE
);
-- CREATE INDEX zdaniya_potrebiteley_shape_idx ON zdaniya_potrebiteley USING GIST (shape);
---------------------------------
-- shield - Геобаза
-- shield - Щит
drop table if exists shield;

create table shield (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    length float,
    nomer_chertezha varchar,
    primechanie varchar(255),
    shape geometry 
);
-- CREATE INDEX shield_shape_idx ON shield USING GIST (shape);
---------------------------------
-- drenazhnyy_kran_old - Геобаза
-- drenazhnyy_kran_old - Дренажный кран старый
drop table if exists drenazhnyy_kran_old;

create table drenazhnyy_kran_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    mestoraspolozhenie int,
    geodezicheskaya_otmetka float,
    priznak_truboprovoda int,
    naimenovanie_nachalnogo_uzla_truby varchar(255),
    naimenovanie_konechnogo_uzla_truby varchar(255),
    naimenovanie_uzla_kamery_pavilona varchar(255),
    tip_spusknoy_armatury int,
    diametr varchar(50),
    material int,
    rabochee_davlenie varchar(50),
    god_vvoda varchar(50),
    nomer varchar(255),
    shema text,
    primechanie varchar(255),
    prinadlezhnost varchar(50),
    shape geometry 
);
CREATE INDEX drenazhnyy_kran_old_lineid_idx ON drenazhnyy_kran_old (lineid);
CREATE INDEX drenazhnyy_kran_old_nodeid_idx ON drenazhnyy_kran_old (nodeid);
-- CREATE INDEX drenazhnyy_kran_old_shape_idx ON drenazhnyy_kran_old USING GIST (shape);
---------------------------------
-- defekt2 - Геобаза
-- defekt2 - Повреждение2
drop table if exists defekt2;

create table defekt2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    stateID int default ((1)),
    data_osmotra timestamp default (now()),   -- Дата обнаружения повреждения
    vremya_osmotra varchar(6) default (NULL), -- Время обнаружения повреждения
    rayon_ekspluatatsii int default (NULL),   -- Район эксплуатации
    uchastok_ekspluatatsii int default (NULL),    -- Участок эксплуатации
    magistral int default (NULL),             -- Магистраль
    uchastok_ms int default (NULL),           -- Участок МС
    uchastok_rs int default (NULL),           -- Участок РС
    kod_rs_nachalnoy_kamery varchar(255) default (NULL),  -- Код РС начальной камеры
    nachalnaya_kamera varchar(255) default (NULL),    -- Начальная камера
    kod_rs_konechnoy_kamery varchar(255) default (NULL),  -- Код РС конечной камеры
    konechnaya_kamera varchar(255) default (NULL),    -- Конечная камера
    otchet_po_defektu text default (NULL),    -- Отчет по повреждению
    dlina_zamenennoy_truby float default (NULL),  -- Длина замененной трубы, м
    data_nachala_remonta date default (NULL), -- Дата начала ремонта
    data_zaversheniya_remonta date default (NULL),    -- Дата завершения ремонта
    shape geometry default (NULL) 
);
CREATE INDEX defekt2_lineid_idx ON defekt2 (lineid);
-- CREATE INDEX defekt2_shape_idx ON defekt2 USING GIST (shape);
---------------------------------
-- vozdushnik_old - Геобаза
-- vozdushnik_old - vozdushnik_old
drop table if exists vozdushnik_old;

create table vozdushnik_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    mestoraspolozhenie int,
    geodezicheskaya_otmetka float,
    priznak_truboprovoda int,
    naimenovanie_nachalnogo_uzla_truby varchar(255),
    naimenovanie_konechnogo_uzla_truby varchar(255),
    naimenovanie_uzla_kamery_pavilona varchar(255),
    tip_spusknoy_armatury varchar(30),
    diametr varchar(50),
    material varchar(50),
    rabochee_davlenie varchar(50),
    god_vvoda varchar(50),
    nomer varchar(255),
    shema text,
    primechanie varchar(255),
    prinadlezhnost varchar(50),
    shape geometry 
);
CREATE INDEX vozdushnik_old_lineid_idx ON vozdushnik_old (lineid);
CREATE INDEX vozdushnik_old_nodeid_idx ON vozdushnik_old (nodeid);
-- CREATE INDEX vozdushnik_old_shape_idx ON vozdushnik_old USING GIST (shape);
---------------------------------
-- zapornaya_armatura_old - Геобаза
-- zapornaya_armatura_old - zapornaya_armatura_old
drop table if exists zapornaya_armatura_old;

create table zapornaya_armatura_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    mestoraspolozhenie int,
    geodezicheskaya_otmetka float,
    priznak_truboprovoda int,
    naimenovanie_nachalnogo_uzla_truby varchar(255),
    naimenovanie_konechnogo_uzla_truby varchar(255),
    naimenovanie_uzla_kamery_pavilona varchar(255),
    tip_zapornoy_armatury varchar(20),
    naznachenie varchar(255),
    diametr varchar(50),
    material int,
    rabochee_davlenie varchar(50),
    tip_prisoedineniya int,
    vid_sharovogo_krana int,
    tip_otklyucheniya int,
    god_vvoda varchar(50),
    nomer varchar(255),
    shema text,
    primechanie varchar(255),
    marka varchar(50),
    zakrytaya varchar(3),
    prinadlezhnost varchar(50),
    sposob_prisoedineniya varchar(150),
    shape geometry 
);
CREATE INDEX zapornaya_armatura_old_lineid_idx ON zapornaya_armatura_old (lineid);
CREATE INDEX zapornaya_armatura_old_nodeid_idx ON zapornaya_armatura_old (nodeid);
-- CREATE INDEX zapornaya_armatura_old_shape_idx ON zapornaya_armatura_old USING GIST (shape);
---------------------------------
-- visualmetriccontrol - Геобаза
-- visualmetriccontrol - Диагностика (устарело)
drop table if exists visualmetriccontrol;

create table visualmetriccontrol (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    controlDate timestamp default (NULL),
    controlOrganizationID int default (NULL),
    controlServiceID int default (NULL),
    controlConditionID int default (NULL),
    controlStageID int default (NULL),
    techCardNumber text default (NULL),
    pipeSectVisControlParamID int default (NULL),
    pipeSectVisControlMetalParamID int default (NULL),
    pipeSectMetricControlMetalParamID int default (NULL),
    pipeSectMetricControlPlasticParamID int default (NULL),
    defectsOrientation float default (NULL),
    defectLocation float default (NULL),
    passportConformity text default (NULL),
    serviceAvailability int default (NULL),
    serviceAvailabilityReasonID int default (NULL),
    coverageID int default (NULL),
    isolationID int default (NULL),
    jamAbsence int default (NULL),
    hangerAttachSpringState int default (NULL),
    reverseValve int default (NULL),
    armatureInscriptionConformity int default (NULL),
    regNumTablesExist int default (NULL),
    nextInspectTableExist int default (NULL),
    defectsImage text default (NULL),
    techDocNumber varchar(255) default (NULL),
    visControlResult varchar(255) default (NULL),
    metricControlMetalResult varchar(255) default (NULL),
    metricControlPlasticResult varchar(255) default (NULL),
    inspectActNumber varchar(255) default (NULL),
    exploitStopSolution varchar(255) default (NULL),
    shape geometry default (NULL) 
);
CREATE INDEX visualmetriccontrol_lineid_idx ON visualmetriccontrol (lineid);
-- CREATE INDEX visualmetriccontrol_shape_idx ON visualmetriccontrol USING GIST (shape);
---------------------------------
-- tankbatteries - Геобаза
-- tankbatteries - Бак-Аккумулятор
drop table if exists tankbatteries;

create table tankbatteries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    designCapacity float default ((0)),       -- Проектная емкость,м^3
    quantity int default ((1)),               -- Количество,шт
    height float default ((1)),               -- Высота,мм
    diameter float default ((400)),           -- Диаметр,мм
    nodeID int default (NULL),
    shape geometry not null 
);
CREATE INDEX tankbatteries_nodeid_idx ON tankbatteries (nodeid);
-- CREATE INDEX tankbatteries_shape_idx ON tankbatteries USING GIST (shape);
---------------------------------
-- kapremont_uchastki_remonta - Геобаза
-- kapremont_uchastki_remonta - Капремонт_участки_ремонта
drop table if exists kapremont_uchastki_remonta;

create table kapremont_uchastki_remonta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    id_remont int,                            -- ID ремонт
    idp1 int,
    ido1 int,
    idp2 int,
    ido2 int,
    shape geometry 
);
CREATE INDEX kapremont_uchastki_remonta_lineid_idx ON kapremont_uchastki_remonta (lineid);
CREATE INDEX kapremont_uchastki_remonta_nodeid_idx ON kapremont_uchastki_remonta (nodeid);
-- CREATE INDEX kapremont_uchastki_remonta_shape_idx ON kapremont_uchastki_remonta USING GIST (shape);
---------------------------------
-- opressovka_uchastki_remonta - Геобаза
-- opressovka_uchastki_remonta - Опрессовка_участки_ремонта
drop table if exists opressovka_uchastki_remonta;

create table opressovka_uchastki_remonta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    id_remont int,                            -- ID ремонт
    idp1 int,
    ido1 int,
    idp2 int,
    ido2 int,
    shape geometry 
);
CREATE INDEX opressovka_uchastki_remonta_lineid_idx ON opressovka_uchastki_remonta (lineid);
CREATE INDEX opressovka_uchastki_remonta_nodeid_idx ON opressovka_uchastki_remonta (nodeid);
-- CREATE INDEX opressovka_uchastki_remonta_shape_idx ON opressovka_uchastki_remonta USING GIST (shape);
---------------------------------
-- opora_skolzyaschaya - Геобаза
-- opora_skolzyaschaya - Опора скользящая
drop table if exists opora_skolzyaschaya;

create table opora_skolzyaschaya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    text varchar(50),
    shape geometry 
);
CREATE INDEX opora_skolzyaschaya_lineid_idx ON opora_skolzyaschaya (lineid);
CREATE INDEX opora_skolzyaschaya_nodeid_idx ON opora_skolzyaschaya (nodeid);
-- CREATE INDEX opora_skolzyaschaya_shape_idx ON opora_skolzyaschaya USING GIST (shape);
---------------------------------
-- podpis - Геобаза
-- podpis - Подпись
drop table if exists podpis;

create table podpis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    text varchar(50),
    shape geometry 
);
CREATE INDEX podpis_lineid_idx ON podpis (lineid);
CREATE INDEX podpis_nodeid_idx ON podpis (nodeid);
-- CREATE INDEX podpis_shape_idx ON podpis USING GIST (shape);
---------------------------------
-- shurf - Геобаза
-- shurf - Шурф
drop table if exists shurf;

create table shurf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    sostoyanie int default ((1)),             -- Состояние
    prichina_defekta varchar(255) default (NULL), -- Причина повреждения
    uchastok_ekspluatatsii varchar(255) default (NULL),   -- Участок эксплуатации
    istochnik_tepla int default (NULL),       -- Источник тепла
    magistral_raspredset varchar(255) default (NULL), -- Магистраль/Распредсеть
    nachalnik_uchastka varchar(255) default (NULL),   -- Начальник участка
    chleny_komissii__nachalnik_sluzhby_ekspluatatsii varchar(255) default (NULL), -- Члены комиссии: Начальник службы эксплуатации
    chleny_komissii__inzhener_ps varchar(255) default (NULL), -- Члены комиссии: Инженер ПС
    god_vvoda_v_ekspluatatsiyu date default (NULL),   -- Год ввода в эксплуатацию
    dlitelnost_ekspluatatsii int default (NULL),  -- Длительность эксплуатации
    vid_prokladki int default (NULL),         -- Вид прокладки
    izolyatsiya_truby int default (NULL),     -- Изоляция трубы
    tip_truby int default (NULL),             -- Тип трубы
    harakteristika_truby int default (NULL),  -- Характеристика трубы
    data_osmotra date default (NULL),         -- Дата осмотра
    vremya_osmotra varchar(6) default (NULL), -- Время осмотра
    ulitsa varchar(255) default (NULL),       -- Улица
    nomer_doma varchar(255) default (NULL),   -- Номер дома
    teplonositel int default (NULL),          -- Теплоноситель
    kod_rs_nachalnoy_kamery int default (NULL),   -- Код РС начальной камеры
    nachalnaya_kamera varchar(255) default (NULL),    -- Начальная камера
    kod_rs_konechnoy_kamery int default (NULL),   -- Код РС конечной камеры
    konechnaya_kamera varchar(255) default (NULL),    -- Конечная камера
    kod_rs_blizhayshey_kamery varchar(255) default (NULL),    -- Код РС ближайшей камеры
    blizhayshaya_kamera varchar(255) default (NULL),  -- Ближайшая камера
    rasstoyanie_do_kamery__m int default (NULL),  -- Расстояние до камеры, м
    opisanie_defekta text default (NULL),     -- Описание повреждения
    diametr_truby_podayuschiy__uslovn__mm int default (NULL), -- Диаметр трубы подающий, условн, мм
    diametr_truby_obratnyy__uslovn__mm int default (NULL),    -- Диаметр трубы обратный, условн, мм
    dlina_uchastka_truboprovoda__podayuschiy__m int default (NULL),   -- Длина участка трубопровода, подающий, м
    dlina_uchastka_truboprovoda__obratnyy__m int default (NULL),  -- Длина участка трубопровода, обратный, м
    uchastok_osmotren_na_dline__m int default (NULL), -- Участок осмотрен на длине, м
    glubina_zalozheniya_truboprovodov float default (NULL),   -- Глубина заложения трубопроводов
    rasstoyanie_mezhdu_osyami_teploprovodov float default (NULL), -- Расстояние между осями теплопроводов
    harakter_grunta int default (NULL),       -- Характер грунта
    poverhnost_zemli_nad_trassoy int default (NULL),  -- Поверхность земли над трассой
    nalichie_vblizi_elektrifitsirovannogo_transporta int default (NULL),  -- Наличие вблизи электрифицированного транспорта
    rasstoyanie_do_relsov__m int default (NULL),  -- Расстояние до рельсов, м
    nalichie_vblizi_trassy_elektrokabeley int default (NULL), -- Наличие вблизи трассы электрокабелей
    nalichie_vblizi_trassy_gazoprovodov int default (NULL),   -- Наличие вблизи трассы газопроводов
    nalichie_vblizi_trassy_vodoprovoda int default (NULL),    -- Наличие вблизи трассы водопровода
    nalichie_vblizi_trassy_kanalizatsii int default (NULL),   -- Наличие вблизи трассы канализации
    nalichie_rabotayuschih_elektrozaschitnyh_ustanovok int default (NULL),    -- Наличие работающих электрозащитных установок
    podtoplenie_do_truby int default (NULL),  -- Подтопление до трубы
    konstruktsiya_drenazhnogo_ustroystva int default (NULL),  -- Конструкция дренажного устройства
    rabotosposobnost_drenazhnogo_ustroystva int default (NULL),   -- Работоспособность дренажного устройства
    elementy_osmotra_podayuschego_teploprovoda int default (NULL),    -- Элементы осмотра подающего теплопровода
    elementy_osmotra_obratnogo_teploprovoda int default (NULL),   -- Элементы осмотра обратного теплопровода
    pokrovnyy_sloy_material__podayuschiy int default (NULL),  -- Покровный слой материал, подающий
    pokrovnyy_sloy_material__obratnyy int default (NULL), -- Покровный слой материал, обратный
    konstruktsiya_pokrovnogo_sloya__podayuschiy int default (NULL),   -- Конструкция покровного слоя, подающий
    konstruktsiya_pokrovnogo_sloya__obratnyy int default (NULL),  -- Конструкция покровного слоя, обратный
    kolichestvo_sloev_pokrovnogo_materiala__podayuschiy int default (NULL),   -- Количество слоев покровного материала, подающий
    kolichestvo_sloev_pokrovnogo_materiala__obratnyy int default (NULL),  -- Количество слоев покровного материала, обратный
    sostoyanie_pokrovnogo_sloya_izolyatsii__podayuschiy int default (NULL),   -- Состояние покровного слоя изоляции, подающий
    sostoyanie_pokrovnogo_sloya_izolyatsii__obratnyy int default (NULL),  -- Состояние покровного слоя изоляции, обратный
    teplovaya_izolyatsiya_material__podayuschiy int default (NULL),   -- Тепловая изоляция материал, подающий
    teplovaya_izolyatsiya_material__obratnyy int default (NULL),  -- Тепловая изоляция материал, обратный
    tolschina_izolyatsii__mm__podayuschiy float default (NULL),   -- Толщина изоляции, мм, подающий
    tolschina_izolyatsii__mm__obratnyy float default (NULL),  -- Толщина изоляции, мм, обратный
    konstruktsiya_izolyatsii__podayuschiy int default (NULL), -- Конструкция изоляции, подающий
    konstruktsiya_izolyatsii__obratnyy int default (NULL),    -- Конструкция изоляции, обратный
    izdelie_izolyatsii__podayuschiy int default (NULL),   -- Изделие изоляции, подающий
    izdelie_izolyatsii__obratnyy int default (NULL),  -- Изделие изоляции, обратный
    sostoyanie_teplovoy_izolyatsii__podayuschiy int default (NULL),   -- Состояние тепловой изоляции, подающий
    sostoyanie_teplovoy_izolyatsii__obratnyy int default (NULL),  -- Состояние тепловой изоляции, обратный
    tolschina_naruzhnogo_pokrytiya__mm__podayuschiy float default (NULL), -- Толщина наружного покрытия, мм, подающий
    tolschina_naruzhnogo_pokrytiya__mm__obratnyy float default (NULL),    -- Толщина наружного покрытия, мм, обратный
    sostoyanie_gidroizolyatsionnoy_konstruktsii__podayuschiy int default (NULL),  -- Состояние гидроизоляционной конструкции, подающий
    sostoyanie_gidroizolyatsionnoy_konstruktsii__obratnyy int default (NULL), -- Состояние гидроизоляционной конструкции, обратный
    sostoyanie_protivokorrozionnogo_pokrytiya__podayuschiy int default (NULL),    -- Состояние противокоррозионного покрытия, подающий
    sostoyanie_protivokorrozionnogo_pokrytiya__obratnyy int default (NULL),   -- Состояние противокоррозионного покрытия, обратный
    nalichie_korrozii__podayuschiy int default (NULL),    -- Наличие коррозии, подающий
    nalichie_korrozii__obratnyy int default (NULL),   -- Наличие коррозии, обратный
    maksimalnaya_glubina_korrozii__podayuschiy__mm int default (NULL),    -- Максимальная глубина коррозии, подающий, мм
    maksimalnaya_glubina_korrozii__obratnyy__mm int default (NULL),   -- Максимальная глубина коррозии, обратный, мм
    diametr_kavern__podayuschiy__mm int default (NULL),   -- Диаметр каверн, подающий, мм
    diametr_kavern__obratnyy__mm int default (NULL),  -- Диаметр каверн, обратный, мм
    mesto_raspolozheniya_povrezhdeniya_po_perimetru_truby__podayusch int default (NULL),  -- Место расположения повреждения по периметру трубы, подающий
    mesto_raspolozheniya_povrezhdeniya_po_perimetru_truby__obratnyy int default (NULL),   -- Место расположения повреждения по периметру трубы, обратный
    nalichie_razryva_stenki_truby__prichiny__podayuschiy int default (NULL),  -- Наличие разрыва стенки трубы, причины, подающий
    nalichie_razryva_stenki_truby__prichiny__obratnyy int default (NULL), -- Наличие разрыва стенки трубы, причины, обратный
    nalichie_razryva_svarnogo_shva_truby__prichiny__podayuschiy int default (NULL),   -- Наличие разрыва сварного шва трубы, причины, подающий
    nalichie_razryva_svarnogo_shva_truby__prichiny__obratnyy int default (NULL),  -- Наличие разрыва сварного шва трубы, причины, обратный
    shema_privyazki varchar(255) default (NULL),  -- Схема привязки
    nalichie_svischa_truby__prichiny__podayuschiy int default (NULL), -- Наличие свища трубы, причины, подающий
    nalichie_svischa_truby__prichiny__obratnyy int default (NULL),    -- Наличие свища трубы, причины, обратный
    nalichie_povrezhdeniy_elementov_truboprovoda int default (NULL),  -- Наличие повреждений элементов трубопровода
    predpolagaemye_prichiny_korrozionnogo_povrezhdeniya_metalla_trub int default (NULL),  -- Предполагаемые причины коррозионного повреждения металла трубы
    foto_korroziynogo_povrezhdeniya_truby text default (NULL),    -- Фото коррозийного повреждения трубы
    foto_mesta_avarii text default (NULL),    -- Фото места аварии
    shurf int default (NULL),                 -- Шурф
    akt_osmotra_v_shurfe int default (NULL),  -- Акт осмотра в шурфе
    nomer_akta_osmotra_v_shurfe varchar(255) default (NULL),  -- Номер акта осмотра в шурфе
    data_sozdaniya_akta_osmotra_v_shurfe date default (NULL), -- Дата создания акта осмотра в шурфе
    nomer_akta_osmotra_uchastka_truboprovoda int default (NULL),  -- Номер акта осмотра участка трубопровода
    data_sozdaniya_akta_osmotra_uchastka_truboprovoda date default (NULL),    -- Дата создания акта осмотра участка трубопровода
    vlazhnost_grunta int default (NULL),      -- Влажность грунта
    uroven_gruntovyh_vod_po_dannym_ekspluatatsii int default (NULL),  -- Уровень грунтовых вод по данным эксплуатации
    uroven_gruntovyh_vod_v_moment_osmotra_shurfa int default (NULL),  -- Уровень грунтовых вод в момент осмотра шурфа
    prichiny_nalichiya_gruntovyh_vod int default (NULL),  -- Причины наличия грунтовых вод
    tip_teploizolyatsionnoy_konstruktsii int default (NULL),  -- Тип теплоизоляционной конструкции
    konstruktsiyu_pokrovnogo_sloya int default (NULL),    -- Конструкцию покровного слоя
    tip_teploizolyatsionnogo_materiala int default (NULL),    -- Тип теплоизоляционного материала
    sostoyanie_kanala int default (NULL),     -- Состояние канала
    sostoyanie_konstruktsii_kanala int default (NULL),    -- Состояние конструкции канала
    nalichie_gidroizolyatsii_kanala int default (NULL),   -- Наличие гидроизоляции канала
    vysota_stoyaniya_vody_pri_zatoplenii_kanala__mm int default (NULL),   -- Высота стояния воды при затоплении канала, мм
    tolschina_sloya_ilistyh_otlozheniy_v_kanale__mm int default (NULL),   -- Толщина слоя илистых отложений в канале, мм
    pervonachalnaya_tolschina_metalla_trub__mm int default (NULL),    -- Первоначальная толщина металла труб, мм
    ostatochnaya_tolschina_metalla_trub__mm int default (NULL),   -- Остаточная толщина металла труб, мм
    namechennye_meropriyatiya_po_kanalu int default (NULL),
    namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii__podayu int default (NULL),  -- Намеченные мероприятия по изоляционной конструкции, подающий
    namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii__obratn int default (NULL),  -- Намеченные мероприятия по изоляционной конструкции, обратный
    namechennye_meropriyatiya_po_vosstanovleniyu_kanala varchar(255) default (NULL),  -- Намеченные мероприятия по восстановлению канала
    namechennye_meropriyatiya_po_truboprovodu__podayuschiy varchar(255) default (NULL),   -- Намеченные мероприятия по трубопроводу, подающий
    namechennye_meropriyatiya_po_truboprovodu__obratnyy varchar(255) default (NULL),  -- Намеченные мероприятия по трубопроводу, обратный
    namechennye_meropriyatiya_po_elementam_truboprovoda__podayuschiy varchar(255) default (NULL), -- Намеченные мероприятия по элементам трубопровода, подающий
    namechennye_meropriyatiya_po_elementam_truboprovoda__obratnyy varchar(255) default (NULL),    -- Намеченные мероприятия по элементам трубопровода, обратный
    vosstanovitelnye_raboty_shurfa text default (NULL),   -- Восстановительные работы шурфа
    data_vosstanovleniya_shurfa date default (NULL),  -- Дата восстановления шурфа
    shema_remontiruemogo_uchastka text default (NULL),    -- Схема ремонтируемого участка
    data_nachala_remonta date default (NULL), -- Дата начала ремонта
    data_zaversheniya_remonta date default (NULL),    -- Дата завершения ремонта
    remont_izolyatsionnoy_konstruktsii__podayuschiy int default (NULL),   -- Ремонт изоляционной конструкции, подающий
    remont_izolyatsionnoy_konstruktsii__obratnyy int default (NULL),  -- Ремонт изоляционной конструкции, обратный
    foto_remonta_izolyatsionnoy_konstruktsii text default (NULL), -- Фото ремонта изоляционной конструкции
    remont_po_vosstanovleniyu_kanala int default (NULL),  -- Ремонт по восстановлению канала
    foto_remonta_kanala text default (NULL),  -- Фото ремонта канала
    remont_po_truboprovodu__podayuschiy varchar(255) default (NULL),  -- Ремонт по трубопроводу, подающий
    remont_po_truboprovodu__obratnyy varchar(255) default (NULL), -- Ремонт по трубопроводу, обратный
    remont_po_elementam_truboprovoda__podayuschiy varchar(255) default (NULL),    -- Ремонт по элементам трубопровода, подающий
    remont_po_elementam_truboprovoda__obratnyy varchar(255) default (NULL),   -- Ремонт по элементам трубопровода, обратный
    rezervnye_linii text default (NULL),      -- Резервные линии
    litso__vnesshee_izmenenie__dolzhnost int default (NULL),  -- Лицо, внесшее изменение, должность
    litso__vnesshee_izmenenie__fio varchar(255) default (NULL),   -- Лицо, внесшее изменение, ФИО
    akt_shurfa text default (NULL),           -- Акт шурфа
    akt_osmotra text default (NULL),          -- Акт осмотра
    otklyuchennye_ot_tepla_potrebiteli text default (NULL),   -- Отключенные от тепла потребители
    otchet_po_remontu text default (NULL),    -- Отчет по ремонту
    otchet_osmotra text default (NULL),       -- Отчет осмотра
    shape geometry default (NULL) 
);
CREATE INDEX shurf_lineid_idx ON shurf (lineid);
-- CREATE INDEX shurf_shape_idx ON shurf USING GIST (shape);
---------------------------------
-- opressovka_defekt - Геобаза
-- opressovka_defekt - Опрессовка Повреждение
drop table if exists opressovka_defekt;

create table opressovka_defekt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    opressovki_uchastok_ocheredi int,         -- Опрессовки участок очереди
    data_provedeniya date,                    -- Дата проведения
    kod_rs_nachalnoy_kamery varchar(255),     -- Код РС начальной камеры
    nachalnaya_kamera varchar(255),           -- Начальная камера
    kod_rs_konechnoy_kamery varchar(255),     -- Код РС конечной камеры
    konechnaya_kamera varchar(255),           -- Конечная камера
    shape geometry 
);
CREATE INDEX opressovka_defekt_lineid_idx ON opressovka_defekt (lineid);
CREATE INDEX opressovka_defekt_nodeid_idx ON opressovka_defekt (nodeid);
-- CREATE INDEX opressovka_defekt_shape_idx ON opressovka_defekt USING GIST (shape);
---------------------------------
-- capital2 - Геобаза
-- capital2 - Капитальный ремонт
drop table if exists capital2;

create table capital2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    stateID int default ((1)),
    data_osmotra timestamp default (now()),
    vremya_osmotra varchar(6) default (NULL),
    rayon_ekspluatatsii int default (NULL),
    uchastok_ekspluatatsii int default (NULL),
    magistral int default (NULL),
    uchastok_ms int default (NULL),
    uchastok_rs int default (NULL),
    kod_rs_nachalnoy_kamery varchar(255) default (NULL),
    nachalnaya_kamera varchar(255) default (NULL),
    kod_rs_konechnoy_kamery varchar(255) default (NULL),
    konechnaya_kamera varchar(255) default (NULL),
    otchet_po_defektu text default (NULL),
    dlina_zamenennoy_truby float default (NULL),
    data_nachala_remonta date default (NULL),
    data_zaversheniya_remonta date default (NULL),
    shape geometry default (NULL) 
);
CREATE INDEX capital2_lineid_idx ON capital2 (lineid);
-- CREATE INDEX capital2_shape_idx ON capital2 USING GIST (shape);
---------------------------------
-- kontrol_tehnicheskogo_sostoyaniya - Геобаза
-- kontrol_tehnicheskogo_sostoyaniya - Контроль технического состояния
drop table if exists kontrol_tehnicheskogo_sostoyaniya;

create table kontrol_tehnicheskogo_sostoyaniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int default (NULL),
    nodeID int default (NULL),
    data_kontrolya date,                      -- Дата контроля
    organizatsiya int,                        -- Владелец
    rayon_ekspluatatsii varchar(255),         -- Район эксплуатации
    uchastok_ekspluatatsii varchar(255),      -- Участок эксплуатации
    magistral int,                            -- Магистраль
    uchastok_ms int,                          -- Участок МС
    uchastok_rs int,                          -- Участок РС
    kod_rs_nachalnoy_kamery varchar(255),     -- Код РС начальной камеры
    nachalnaya_kamera varchar(255),           -- Начальная камера
    kod_rs_konechnoy_kamery varchar(255),     -- Код РС конечной камеры
    konechnaya_kamera varchar(255),           -- Конечная камера
    otchet_po_izmereniyu text,                -- Отчет по измерению
    tip_pribora varchar(255),                 -- Тип прибора
    data_gospoverki date,                     -- Дата госповерки
    preobrazovatel varchar(255),              -- Преобразователь
    master varchar(255),                      -- Мастер
    master_udostoverenie varchar(255),        -- Мастер удостоверение
    defektoskopist varchar(255),              -- Дефектоскопист
    defektoskopist_udostoverenie varchar(255),    -- Дефектоскопист удостоверение
    shape geometry 
);
CREATE INDEX kontrol_tehnicheskogo_sostoyaniya_lineid_idx ON kontrol_tehnicheskogo_sostoyaniya (lineid);
CREATE INDEX kontrol_tehnicheskogo_sostoyaniya_nodeid_idx ON kontrol_tehnicheskogo_sostoyaniya (nodeid);
-- CREATE INDEX kontrol_tehnicheskogo_sostoyaniya_shape_idx ON kontrol_tehnicheskogo_sostoyaniya USING GIST (shape);
---------------------------------
-- channels - Геобаза
-- channels - Каналы 2
drop table if exists channels;

create table channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatChamberID1 int default (NULL),
    heatChamberID2 int default (NULL),
    channelTypeID int default (NULL),
    materialID int default (NULL),
    constructionID int default (NULL),
    pipelineID int default (NULL),
    width float default ((0)),
    height float default ((0)),
    length float default ((0)),
    diameterCondit int default (NULL),
    drainageLinesCount int default (NULL),
    hydroIsol int default (NULL),
    scheme varchar(255) default (NULL),
    drainageLines int default (NULL),
    physPerson int default (NULL),
    juridPerson int default (NULL),
    name_typ int default (NULL),
    shape geometry default (NULL) 
);
-- CREATE INDEX channels_shape_idx ON channels USING GIST (shape);
---------------------------------
-- act - Геобаза
-- act - Акты
drop table if exists act;

create table act (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    data_gp date,                             -- Дата гп
    data_vydachi date,                        -- Дата выдачи
    rayon int,                                -- Район
    uchastok int,                             -- Участок
    nomer_papki int,                          -- Номер папки
    kvartal varchar(50),                      -- Квартал
    tm varchar(2),                            -- Тм
    ut varchar(10),                           -- Ут
    nomer_akta varchar(50),                   -- Номер акта
    abonent varchar(50),                      -- Абонент
    obekt varchar(30),                        -- Объект
    telefon varchar(30),                      -- Телефон
    adres_staryy varchar(50),                 -- Адрес старый
    adres varchar(50),                        -- Адрес
    akt varchar(100),                         -- Акт
    vremennyy int,                            -- Временный
    shape geometry 
);
-- CREATE INDEX act_shape_idx ON act USING GIST (shape);
---------------------------------
-- passports - Геобаза
-- passports - Паспорта
drop table if exists passports;

create table passports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objectName varchar(50) default (NULL),
    heatSourceID int default (NULL),
    magistralID int default (NULL),
    quarter varchar(255) default (NULL),
    nodeID int default (NULL),
    address varchar(50) default (NULL),
    serviceOrganizationID int not null,
    bindingScheme varchar default (NULL),
    shape geometry not null 
);
CREATE INDEX passports_nodeid_idx ON passports (nodeid);
-- CREATE INDEX passports_shape_idx ON passports USING GIST (shape);
--- Геобаза: 26
--===========================--
--         lookup            --
--===========================--

---------------------------------
-- channels heatsysobjmaterials - lookup Геобаза
-- heatsysobjmaterials - heatsysobjmaterials
drop table if exists heatsysobjmaterials;

create table heatsysobjmaterials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);

---------------------------------
-- channels channeltypes - lookup Геобаза
-- channeltypes - Типы каналов
drop table if exists channeltypes;

create table channeltypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);

---------------------------------
-- channels channelcoverconstructions - lookup Геобаза
-- channelcoverconstructions - Конструкции крышки канала
drop table if exists channelcoverconstructions;

create table channelcoverconstructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);

---------------------------------
-- corrosionindicators indicatorstates - lookup Геобаза
-- indicatorstates - indicatorstates
drop table if exists indicatorstates;

create table indicatorstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "indicatorstates" ("id","name","code","ord") VALUES
(1,'План','НАДО',1),
(2,'Анализ','НАДО',2),
(3,'После расчета','НАДО',3);


-- SELECT setval('"indicatorstates_id_seq"', 3);

---------------------------------
-- shurf2 plan_defect - lookup Геобаза
-- plan_defect - plan_defect
----- Нет таблцы plan_defect

---------------------------------
-- defekt izolyatsiya_truby - lookup Геобаза
-- izolyatsiya_truby - Изоляция трубы
drop table if exists izolyatsiya_truby;

create table izolyatsiya_truby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(5),                           -- Код
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "izolyatsiya_truby" ("id","kod","znachenie","primechanie") VALUES
(1,'ППУ','ППУ изоляция',NULL),
(2,'Р','Ручная изоляция',NULL),
(3,NULL,'Сталь листовая оцинкованная S=0.6мм',NULL);


-- SELECT setval('"izolyatsiya_truby_id_seq"', 3);

---------------------------------
-- defekt material_pokrovnogo_sloya - lookup Геобаза
-- material_pokrovnogo_sloya - Материал покровного слоя
drop table if exists material_pokrovnogo_sloya;

create table material_pokrovnogo_sloya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id2 varchar(5),
    znachenie varchar(255),                   -- Значение
    tolschina__mm varchar(255),               -- Толщина, мм
    primechanie varchar(255),                 -- Примечание
    gost varchar(255),                        -- ГОСТ
    marki varchar(255),                       -- Марки
    goryuchest varchar(255)                   -- Горючесть
);

INSERT INTO "material_pokrovnogo_sloya" ("id","id2","znachenie","tolschina__mm","primechanie","gost","marki","goryuchest") VALUES
(1,'1','Листы из алюминия','0,3; 0,5-1','Металлизационное','ГОСТ 21631-76','АДО, АД1, АМц, Амг2, В95','Негорючие'),
(2,'2','Ленты из алюминия','0,25-1','Металлизационное','ГОСТ 13726-78','АДО, АД1, АМц, Амг2, В95','Негорючие'),
(3,'3','Сталь оцинкованная','0,35-1','Металлизационное','ГОСТ 14918-80',NULL,'Негорючие'),
(4,'4','Сталь кровельная','0,5-0,8','Металлизационное','ГОСТ 14918-80',NULL,'Негорючие'),
(5,'5','Прокат углеродистой стали','0,35-1','Металлизационное','ГОСТ 16523-70',NULL,'Негорючие'),
(6,'6','Оболочки гофрированные','0,2; 2,5','Металлизационное','ОСТ 36-67-82',NULL,'Негорючие; Горючие'),
(7,'7','Металлопласт','0,8-1,3','Металлизационное','ТУ 14-1-1114-74',NULL,'Трудногорючие'),
(8,'8','Стеклотекстолит конструкционный','0,5-1,2','Синтетический полимер','ГОСТ 10292-74Е',NULL,'Горючие'),
(9,'9','Армопластмассовый, АПМ-1','2,2','Синтетический полимер',NULL,'АПМ-1','Горючий'),
(10,'10','Армопластмассовый, АПМ-2','2,1','Синтетический полимер',NULL,'АПМ-2','Трудногорючий'),
(11,'11','Армопластмассовый, АПМ-3','2,1','Синтетический полимер',NULL,'АПМ-3','Горючий'),
(12,'12','Стеклопластик рулонный РСТ','0,25-0,5','Синтетический полимер','ТУ 6-11-145-80','РСТ-А, РСТ-Б, РСТ-Х','Трудногорючий'),
(13,'13','Стеклопластик фенольный','0,3; 0,6','Синтетический полимер','ТУ 6-11-150-76',NULL,'Горючий'),
(14,'14','Пленка винипластовая КПО','0,4-1','Синтетический полимер','ГОСТ 16398-81','КПО','Горючая'),
(15,'15','Пленка из поливинилхлоридного сырья','1,3','Синтетический полимер','ТУ 63.032.3-88',NULL,'Горючая'),
(16,'16','Стеклотекстолит  листовой СТПЛ-СБ','0,3','Синтетический полимер','ТУ 36-1583-88','СТПЛ-СБ','Трудногорючий'),
(17,'17','Стеклотекстолит  листовой СТПЛ-ТБ','0,5','Синтетический полимер','ТУ 36-1583-88','СТПЛ-ТБ','Трудногорючий'),
(18,'18','Стеклотекстолит  листовой СТПЛ-ВП','0,8','Синтетический полимер','ТУ 36-1583-88','СТПЛ-ВП','Трудногорючий'),
(19,'19','Рубероид','2-3','Природный полимер','ГОСТ 10923-82','РКК-420','Горючий'),
(20,'20','Стеклорубероид','2,5','Природный полимер','ГОСТ 15879-70',NULL,'Горючий'),
(21,'21','Толь','1,0-1,5','Природный полимер','ГОСТ 10999-76','ТКК-350, ТКК-400','Горючий'),
(22,'22','Пергамин','1,0-1,5','Природный полимер','ГОСТ 2697-83',NULL,'Горючий'),
(23,'23','Рубероид, покрытый стеклотканью',NULL,'Природный полимер','ТУ 21 ЭССР 48-83',NULL,'Горючий'),
(24,'24','Изол','2','Природный полимер','ГОСТ 10296-79',NULL,'Горючий'),
(25,'25','Стеклоцемент текстолитовый','1,5-2','Минеральные','ТУ 36-940-85',NULL,'Негорючий'),
(26,'26','Листы асбестоцементные плоские','6-10','Минеральные','ГОСТ 18124-75',NULL,'Негорючий'),
(27,'27','Листы асбестоцементные волнистые','5-8','Минеральные','ГОСТ 16233-77',NULL,'Негорючий'),
(28,'28','Штукатурка асбестоцементная','10-20','Минеральные',NULL,NULL,'Негорючий'),
(29,'29','Фольга алюминиевая','0,5-1,5','Дублированные фольгой','ТУ 36-1177 -77',NULL,'Горючий; Трудногорючий'),
(30,'30','Фольгорубероид','1,7-2','Дублированные фольгой','ТУ 21 ЭССР 69-83',NULL,'Горючий'),
(31,'31','Фольгоизол','2-2,5','Дублированные фольгой','ГОСТ 20429-84',NULL,'Горючий'),
(32,'СЛ','Сталь листовая холоднокатанная',NULL,'Металлизационное',NULL,NULL,NULL),
(33,'ОЦ','Сталь листовая Оцинкованная',NULL,'Металлизационное',NULL,NULL,NULL),
(34,'ПО','ППУ ОЦ',NULL,'Синтетический полимер',NULL,NULL,NULL),
(35,'СТК','Cтеклоткань',NULL,'Синтетический полимер',NULL,NULL,NULL),
(36,'АСБ','Асбест (хризалит)',NULL,'Минеральные',NULL,NULL,NULL),
(37,'РУБ','Рубероид',NULL,'Природный полимер',NULL,NULL,NULL),
(38,'ПЭ','Полиэтилен',NULL,'Синтетический полимер',NULL,NULL,NULL),
(39,'К-F','k-flex',NULL,'Синтетический полимер',NULL,NULL,NULL),
(40,'СР','стеклопластик рулоновый РСТ',NULL,'Синтетический полимер',NULL,NULL,NULL);


-- SELECT setval('"material_pokrovnogo_sloya_id_seq"', 40);

---------------------------------
-- defekt tip_izolyatsii - lookup Геобаза
-- tip_izolyatsii - Тип изоляции
drop table if exists tip_izolyatsii;

create table tip_izolyatsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "tip_izolyatsii" ("id","znachenie","primechanie") VALUES
(1,'1 тип',NULL),
(2,'2 тип',NULL);


-- SELECT setval('"tip_izolyatsii_id_seq"', 2);

---------------------------------
-- defekt sostoyanie_izolyatsionnogo_materiala - lookup Геобаза
-- sostoyanie_izolyatsionnogo_materiala - Состояние изоляционного материала
drop table if exists sostoyanie_izolyatsionnogo_materiala;

create table sostoyanie_izolyatsionnogo_materiala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "sostoyanie_izolyatsionnogo_materiala" ("id","znachenie","primechanie") VALUES
(1,'в хорошем состоянии',NULL),
(2,'отсутствует частично',NULL),
(3,'отсутствует полностью',NULL);


-- SELECT setval('"sostoyanie_izolyatsionnogo_materiala_id_seq"', 3);

---------------------------------
-- defekt prichiny_svischa - lookup Геобаза
-- prichiny_svischa - Причины свища
drop table if exists prichiny_svischa;

create table prichiny_svischa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "prichiny_svischa" ("id","znachenie","primechanie") VALUES
(1,'внутренняя коррозия',NULL),
(2,'электрокоррозия',NULL),
(3,'дефект металла',NULL),
(4,'нарушение технологии сварки, электродов',NULL);


-- SELECT setval('"prichiny_svischa_id_seq"', 4);

---------------------------------
-- defekt prichiny_razryva_svarnogo_shva - lookup Геобаза
-- prichiny_razryva_svarnogo_shva - Причины разрыва сварного шва
drop table if exists prichiny_razryva_svarnogo_shva;

create table prichiny_razryva_svarnogo_shva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "prichiny_razryva_svarnogo_shva" ("id","znachenie","primechanie") VALUES
(1,'дефект сварки',NULL),
(2,'наружная коррозии',NULL),
(3,'внутренняя коррозии',NULL),
(4,'предельная нагрузка от внутреннего давления',NULL);


-- SELECT setval('"prichiny_razryva_svarnogo_shva_id_seq"', 4);

---------------------------------
-- defekt prichiny_razryva_stenki_truby - lookup Геобаза
-- prichiny_razryva_stenki_truby - Причины разрыва стенки трубы
drop table if exists prichiny_razryva_stenki_truby;

create table prichiny_razryva_stenki_truby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "prichiny_razryva_stenki_truby" ("id","znachenie","primechanie") VALUES
(1,'наружная коррозия',NULL),
(2,'внутренняя коррозия',NULL),
(3,'дефект металла трубы',NULL),
(4,'превышение допустимого давления, гидроудар, механическое повреждение',NULL);


-- SELECT setval('"prichiny_razryva_stenki_truby_id_seq"', 4);

---------------------------------
-- defekt prichiny_korrozii - lookup Геобаза
-- prichiny_korrozii - Причины коррозии
drop table if exists prichiny_korrozii;

create table prichiny_korrozii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "prichiny_korrozii" ("id","znachenie","primechanie") VALUES
(1,'теплопровод постоянно, периодически подтопляется грунтовыми сточными водами до контакта с теплоизоляц. конструкцией',NULL),
(2,'канал местами, сплошь, заилен до контакта ила с трубами',NULL),
(3,'на теплопровод постоянно, периодически, попадает вода сверху, неплотность муфты',NULL),
(4,'бесканальная прокладка в неблагоприятных условиях',NULL),
(5,'наличие смежных коммуникаций: кабели, трубопроводы',NULL),
(6,'длительная утечка сетевой воды из поврежденного участка',NULL),
(7,'электрифицированный транспорт',NULL),
(8,'коррозионно-активный теплоноситель (внутренняя коррозия), качество сетевой воды',NULL);


-- SELECT setval('"prichiny_korrozii_id_seq"', 8);

---------------------------------
-- defekt vid_korrozii - lookup Геобаза
-- vid_korrozii - Вид коррозии
drop table if exists vid_korrozii;

create table vid_korrozii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "vid_korrozii" ("id","znachenie","primechanie") VALUES
(1,'Сплошная наружная коррозия на всем осмотренном участке',NULL),
(2,'Сплошная наружная коррозия в месте повреждения',NULL),
(3,'Локальная наружная коррозия (язвы)',NULL),
(4,'Внутренняя коррозия, отдельные язвы',NULL),
(5,'Внутренняя коррозия в виде цепочек язв или канавок',NULL),
(6,'Сплошная внутренняя коррозия',NULL);


-- SELECT setval('"vid_korrozii_id_seq"', 6);

---------------------------------
-- defekt sostoyanie_konstruktsii_kanala - lookup Геобаза
-- sostoyanie_konstruktsii_kanala - Состояние конструкции канала
drop table if exists sostoyanie_konstruktsii_kanala;

create table sostoyanie_konstruktsii_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "sostoyanie_konstruktsii_kanala" ("id","znachenie","primechanie") VALUES
(1,'в хорошем состоянии',NULL),
(2,'разрушена частично',NULL),
(3,'разрушена полностью',NULL);


-- SELECT setval('"sostoyanie_konstruktsii_kanala_id_seq"', 3);

---------------------------------
-- defekt sostoyanie_teploizolyatsionnoy_konstruktsii - lookup Геобаза
-- sostoyanie_teploizolyatsionnoy_konstruktsii - Состояние теплоизоляционной конструкции
drop table if exists sostoyanie_teploizolyatsionnoy_konstruktsii;

create table sostoyanie_teploizolyatsionnoy_konstruktsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "sostoyanie_teploizolyatsionnoy_konstruktsii" ("id","znachenie","primechanie") VALUES
(1,'в хорошем состоянии',NULL),
(2,'разрушена частично',NULL),
(3,'разрушена полностью',NULL);


-- SELECT setval('"sostoyanie_teploizolyatsionnoy_konstruktsii_id_seq"', 3);

---------------------------------
-- defekt sostoyanie_pokrovnogo_sloya_izolyatsii - lookup Геобаза
-- sostoyanie_pokrovnogo_sloya_izolyatsii - Состояние покровного слоя изоляции
drop table if exists sostoyanie_pokrovnogo_sloya_izolyatsii;

create table sostoyanie_pokrovnogo_sloya_izolyatsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "sostoyanie_pokrovnogo_sloya_izolyatsii" ("id","znachenie","primechanie") VALUES
(1,'в хорошем состоянии',NULL),
(2,'отсутствует частично',NULL),
(3,'отсутствует полностью',NULL);


-- SELECT setval('"sostoyanie_pokrovnogo_sloya_izolyatsii_id_seq"', 3);

---------------------------------
-- defekt harakter_grunta - lookup Геобаза
-- harakter_grunta - Характер грунта
drop table if exists harakter_grunta;

create table harakter_grunta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "harakter_grunta" ("id","znachenie","primechanie") VALUES
(1,'супесь',NULL),
(2,'песок',NULL),
(3,'суглинок',NULL),
(4,'глина',NULL),
(5,'строительный мусор',NULL);


-- SELECT setval('"harakter_grunta_id_seq"', 5);

---------------------------------
-- defekt tip_teploizolyatsionnogo_materiala - lookup Геобаза
-- tip_teploizolyatsionnogo_materiala - tip_teploizolyatsionnogo_materiala
----- Нет таблцы tip_teploizolyatsionnogo_materiala

---------------------------------
-- defekt groundwatercauses - lookup Геобаза
-- groundwatercauses - groundwatercauses
drop table if exists groundwatercauses;

create table groundwatercauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "groundwatercauses" ("id","name","code","ord") VALUES
(1,'грунтовая вода','1',1),
(2,'ливневая','2',2),
(3,'сетевая','2',3),
(4,'водопроводная','2',4);


-- SELECT setval('"groundwatercauses_id_seq"', 4);

---------------------------------
-- defekt channelstates - lookup Геобаза
-- channelstates - Состояния канала
drop table if exists channelstates;

create table channelstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "channelstates" ("id","name","code","ord") VALUES
(1,'наличия влаги капельной','НВК',1),
(2,'наличия влаги пленочной','НВП',2);


-- SELECT setval('"channelstates_id_seq"', 2);

---------------------------------
-- defekt typeofwork - lookup Геобаза
-- typeofwork - typeofwork
drop table if exists typeofwork;

create table typeofwork (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "typeofwork" ("id","name","code","ord") VALUES
(1,'Текущий','Т',1),
(2,'Инвестиционный','И',2),
(3,'Капитальный','К',3),
(4,'Аварийный','А',4);


-- SELECT setval('"typeofwork_id_seq"', 4);

---------------------------------
-- defekt groundhumidities - lookup Геобаза
-- groundhumidities - groundhumidities
drop table if exists groundhumidities;

create table groundhumidities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "groundhumidities" ("id","name","code","ord") VALUES
(1,'сильно увлажнен','1',1),
(2,'средней влажности','2',2),
(3,'сухой','2',3);


-- SELECT setval('"groundhumidities_id_seq"', 3);

---------------------------------
-- defekt roadsurfacetypes - lookup Геобаза
-- roadsurfacetypes - roadsurfacetypes
drop table if exists roadsurfacetypes;

create table roadsurfacetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "roadsurfacetypes" ("id","name","code","ord") VALUES
(1,'асфальт, бетон','1',1),
(2,'газон','2',2),
(3,'граница между 1 и 2','3',3),
(4,'утрамбованный грунт','4',4),
(5,'поверхность, защищенная от атмосферных осадков','5',5);


-- SELECT setval('"roadsurfacetypes_id_seq"', 5);

---------------------------------
-- defekt yesorno12 - lookup Геобаза
-- yesorno12 - yesorno12
drop table if exists yesorno12;

create table yesorno12 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);

INSERT INTO "yesorno12" ("id","name","code","ord") VALUES
(1,'да','1',1),
(2,'нет','0',2);


-- SELECT setval('"yesorno12_id_seq"', 2);

---------------------------------
-- defekt konstruktsiya_drenazhnogo_ustroystva - lookup Геобаза
-- konstruktsiya_drenazhnogo_ustroystva - Конструкция дренажного устройства
drop table if exists konstruktsiya_drenazhnogo_ustroystva;

create table konstruktsiya_drenazhnogo_ustroystva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);

INSERT INTO "konstruktsiya_drenazhnogo_ustroystva" ("id","znachenie","primechanie") VALUES
(1,'отводные линии',NULL),
(2,'дренажные трубы',NULL);


-- SELECT setval('"konstruktsiya_drenazhnogo_ustroystva_id_seq"', 2);

---------------------------------
-- kontrol_tehnicheskogo_sostoyaniya tolschinometr - lookup Геобаза
-- tolschinometr - Толщинометр
drop table if exists tolschinometr;

create table tolschinometr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip varchar(255),                         -- Тип
    zavodskoy_nomer varchar(255),             -- Заводской номер
    preobrazovatel varchar(255),              -- Преобразователь
    data_gospoverki date,                     -- Дата госповерки
    diapozon_izmereniy__minimalnoe__mm float, -- Диапозон измерений, минимальное, мм
    diapozon_izmereniy__maksimalnoe__mm float,    -- Диапозон измерений, максимальное, мм
    diametr_rabochey_poverhnosti float        -- Диаметр рабочей поверхности
);

INSERT INTO "tolschinometr" ("id","tip","zavodskoy_nomer","preobrazovatel","data_gospoverki","diapozon_izmereniy__minimalnoe__mm","diapozon_izmereniy__maksimalnoe__mm","diametr_rabochey_poverhnosti") VALUES
(1,'Булат-1S','1',NULL,'2015-01-01',NULL,NULL,NULL),
(2,'Туз-1','2',NULL,'2016-01-01',NULL,NULL,NULL),
(3,'Туз-2','3','П112-10-6/2-Т-003','2017-01-01',0.6,50.0,8.0),
(4,'DM-4','4',NULL,'2014-01-01',NULL,NULL,NULL),
(5,'DMS','5',NULL,'2014-01-01',NULL,NULL,NULL),
(6,'Туз-2','6','П112-5-10/2-Т-003','1899-12-30',NULL,1.2,300.0);


-- SELECT setval('"tolschinometr_id_seq"', 6);
--- Геобаза lookup: 27
--===========================--
--        Другие             --
--===========================--
---------------------------------
-- addresses - Другие
-- addresses - Адрес
drop table if exists addresses;

create table addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street varchar(50) default (NULL),
    home_numer varchar(50) default (NULL),
    home_korpus varchar(50) default (NULL),
    nomer_building varchar(50) default (NULL),
    name_building varchar(50) default (NULL),
    kod_building varchar(50) default (NULL) 
);
---------------------------------
-- administrativedistricts - Другие
-- administrativedistricts - Административные районы
drop table if exists administrativedistricts;

create table administrativedistricts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- administrativnyy_rayon - Другие
-- administrativnyy_rayon - Административный район
drop table if exists administrativnyy_rayon;

create table administrativnyy_rayon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) 
);
---------------------------------
-- agressivnost_setevoy_vody - Другие
-- agressivnost_setevoy_vody - Агрессивность сетевой воды
drop table if exists agressivnost_setevoy_vody;

create table agressivnost_setevoy_vody (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    srednyaya_skorost_korrozii float,         -- Средняя скорость коррозии
    agressivnost_setevoy_vody int             -- Агрессивность сетевой воды
);
---------------------------------
-- airgroundmonthtemperatures - Другие
-- airgroundmonthtemperatures - Воздушно-земные температуры месяца
drop table if exists airgroundmonthtemperatures;

create table airgroundmonthtemperatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tn_long_1 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_2 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_3 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_4 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_5 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_6 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_7 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_8 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_9 float default ((0)),            -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_10 float default ((0)),           -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_11 float default ((0)),           -- Ожидаемая среднемес. температура воздуха, °C
    tn_long_12 float default ((0)),           -- Ожидаемая среднемес. температура воздуха, °C
    tgr_long_1 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_2 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_3 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_4 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_5 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_6 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_7 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_8 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_9 float default ((0)),           -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_10 float default ((0)),          -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_11 float default ((0)),          -- Ожидаемая среднемес. температура грунта, °C
    tgr_long_12 float default ((0)),          -- Ожидаемая среднемес. температура грунта, °C
    tn_fakt_1 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_2 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_3 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_4 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_5 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_6 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_7 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_8 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_9 float default ((0)),            -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_10 float default ((0)),           -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_11 float default ((0)),           -- Фактическая среднемес. температура воздуха, °C
    tn_fakt_12 float default ((0)),           -- Фактическая среднемес. температура воздуха, °C
    tgr_fakt_1 float default ((0)),           -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_2 float default ((0)),
    tgr_fakt_3 float default ((0)),
    tgr_fakt_4 float default ((0)),
    tgr_fakt_5 float default ((0)),
    tgr_fakt_6 float default ((0)),           -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_7 float default ((0)),           -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_8 float default ((0)),           -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_9 float default ((0)),           -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_10 float default ((0)),          -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_11 float default ((0)),          -- Фактическая среднемес. температура грунта, °C
    tgr_fakt_12 float default ((0))           -- Фактическая среднемес. температура грунта, °C
);
---------------------------------
-- baza_dannyh_po_adresnym_spravkam - Другие
-- baza_dannyh_po_adresnym_spravkam - База данных по адресным справкам
drop table if exists baza_dannyh_po_adresnym_spravkam;

create table baza_dannyh_po_adresnym_spravkam (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie varchar(150),                -- Наименование
    data_vydachi date,                        -- ДАТА ВЫДАЧИ
    id_geom int 
);
---------------------------------
-- calcschemes - Другие
-- calcschemes - Расчетные схемы
drop table if exists calcschemes;

create table calcschemes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code varchar(50) default (NULL),          -- Код расчетной схемы
    name varchar(50) default (NULL),          -- Наименование объекта
    belongMagistral varchar(50) default (NULL),   -- Принадлежность магистрали
    objectID int default (NULL),              -- Тип объекта
    exploitRegionID int default (NULL),       -- Район эксплуатации
    exploitSite int default (NULL),           -- Участок эксплуатации
    heatSourceID int default (NULL),
    master int default (NULL),                -- Начальник участка
    performer varchar(50) default (NULL),     -- Лицо, ответственное за подготовку данных
    displaySign int default ((0)),            -- Показывать
    fillDate date default (NULL),
    powerSystem varchar(50) default (NULL),
    region varchar(50) default (NULL),
    passportNum varchar(50) default (NULL),
    networkType varchar(50) default (NULL),
    heatSource varchar(50) default (NULL),
    projectOrganization varchar(50) default (NULL),
    projectNum varchar(50) default (NULL),
    avgWayLength int default (NULL),
    operPressure varchar(50) default (NULL),
    operTemperature varchar(50) default (NULL),
    constructDate varchar(50) default (NULL),
    exploitInitDate varchar(50) default (NULL),
    balanceValue int default (NULL),
    balanceValueYear int default (NULL),
    initChamber varchar(50) default (NULL),
    finalChamber varchar(50) default (NULL),
    lifetime int default (NULL),
    calcLifetime int default (NULL),
    calcStartsNum int default (NULL),
    purpose varchar(50) default (NULL),
    connectNode varchar(50) default (NULL),
    finalNode varchar(50) default (NULL),
    kod2 varchar(50) default (NULL),
    uzel2 varchar(50) default (NULL),
    registNum int default (NULL),
    owner int default (NULL),
    ownerAddress varchar(50) default (NULL),
    workingEnv varchar(50) default (NULL),
    projectDocuments varchar,
    responsiblePerson varchar(50) default (NULL),
    passport varchar 
);
---------------------------------
-- calculatedloads - Другие
-- calculatedloads - Расчетные нагрузки
drop table if exists calculatedloads;

create table calculatedloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    heatSourceName varchar(50),
    gOt_pr float,
    gVent_pr float,
    gGvs_pr float,
    seasonID int 
);
---------------------------------
-- calculatedloadsfact - Другие
-- calculatedloadsfact - Расчетные нагрузки фактические
drop table if exists calculatedloadsfact;

create table calculatedloadsfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    heatSourceName varchar(50),
    gOt_pr float,
    gVent_pr float,
    gGvs_pr float,
    seasonID int 
);
---------------------------------
-- calculation_iznos - Другие
-- calculation_iznos - Расчет износа
drop table if exists calculation_iznos;

create table calculation_iznos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Tn float,
    DateRascheta timestamp default (now()),
    name text 
);
---------------------------------
-- calculations - Другие
-- calculations - Расчеты
drop table if exists calculations;

create table calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fileID int default (NULL) 
);
CREATE INDEX calculations_fileid_idx ON calculations (fileid);
---------------------------------
-- capital2_dokumenty - Другие
-- capital2_dokumenty - Капитальные документы 2
drop table if exists capital2_dokumenty;

create table capital2_dokumenty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defektID int default (NULL),
    docRemontTypeID int default (NULL),
    data1 date default (NULL),
    dokument text default (NULL) 
);
---------------------------------
-- capital2_meropriyatiya - Другие
-- capital2_meropriyatiya - Капитальные мероприятия 2
drop table if exists capital2_meropriyatiya;

create table capital2_meropriyatiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defektID int default (NULL),
    povrezhdeniya int default (NULL),
    meropriyatie int default (NULL),
    plan1 int default (NULL) 
);
---------------------------------
-- changed_object - Другие
-- changed_object - Измененный объект
drop table if exists changed_object;

create table changed_object (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    changeTypeID int,
    old_id int,
    changedID int,
    changedText varchar,
    dateRemoved timestamp default (NULL),
    userRemoved int default ((0)) 
);
---------------------------------
-- cities - Другие
-- cities - Города
drop table if exists cities;

create table cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) 
);
---------------------------------
-- controlconditions - Другие
-- controlconditions - Условия контроля
drop table if exists controlconditions;

create table controlconditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- controlorganizations - Другие
-- controlorganizations - Контролирующие организации
drop table if exists controlorganizations;

create table controlorganizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- controlservices - Другие
-- controlservices - Службы контроля
drop table if exists controlservices;

create table controlservices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- controlstages - Другие
-- controlstages - Этапы контроля
drop table if exists controlstages;

create table controlstages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- defectopis - Другие
-- defectopis - Дефект описание
drop table if exists defectopis;

create table defectopis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- defectopistype - Другие
-- defectopistype - Тип описания дефектов
drop table if exists defectopistype;

create table defectopistype (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(250) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- defectsforshurfy - Другие
-- defectsforshurfy - Дефекты для шурфов
drop table if exists defectsforshurfy;

create table defectsforshurfy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int not null,
    defectID int not null 
);
---------------------------------
-- defekt_elementy - Другие
-- defekt_elementy - Повреждение_Элементы
drop table if exists defekt_elementy;

create table defekt_elementy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defekt int,                               -- Повреждение
    element int,                              -- Элемент
    osmotreno_na_podache float,               -- Осмотрено на подаче
    povrezhdeno_na_podache float,             -- Повреждено на подаче
    meropriyatie_na_podache varchar(255),     -- Мероприятие на подаче
    zaplanirovano_na_podache float,           -- Запланировано на подаче
    ispravleno_na_podache float,              -- Исправлено на подаче
    osmotreno_na_obratke float,               -- Осмотрено на обратке
    povrezhdeno_na_obratke float,             -- Повреждено на обратке
    meropriyatie_na_obratke varchar(255),     -- Мероприятие на обратке
    zaplanirovano_na_obratke float,           -- Запланировано на обратке
    ispravleno_na_obratke float               -- Исправлено на обратке
);
---------------------------------
-- defekt_truby - Другие
-- defekt_truby - Повреждение_Трубы
drop table if exists defekt_truby;

create table defekt_truby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defekt int,                               -- Повреждение
    element int,                              -- Элемент
    osmotreno_na_podache float,               -- Осмотрено на подаче
    povrezhdeno_na_podache float,             -- Повреждено на подаче
    ispravleno_na_podache float,              -- Исправлено на подаче
    osmotreno_na_obratke float,               -- Осмотрено на обратке
    povrezhdeno_na_obratke float,             -- Повреждено на обратке
    ispravleno_na_obratke float               -- Исправлено на обратке
);
---------------------------------
-- defekt2_dokumenty - Другие
-- defekt2_dokumenty - Повреждение2_документы
drop table if exists defekt2_dokumenty;

create table defekt2_dokumenty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defektID int default (NULL),
    docRemontTypeID int default (NULL),
    data date default (NULL),                 -- Дата
    dokument text default (NULL)              -- Документ
);
---------------------------------
-- defekt2_meropriyatiya - Другие
-- defekt2_meropriyatiya - Повреждение2_мероприятия
drop table if exists defekt2_meropriyatiya;

create table defekt2_meropriyatiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defektID int default (NULL),
    povrezhdeniya int default (NULL),         -- Повреждения
    meropriyatie int default (NULL),          -- Мероприятие
    plan1 int default (NULL) 
);
---------------------------------
-- deployedtempgraphsfact - Другие
-- deployedtempgraphsfact - Развернутые температурные графики фактические
drop table if exists deployedtempgraphsfact;

create table deployedtempgraphsfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hSourceID int default (NULL),
    tn float default ((0)) not null,
    Q_otn float default ((0)) not null,
    t1 float default ((0)) not null,
    t2 float default ((0)) not null,
    t3 float default ((0)) not null,
    tv float default ((0)) not null,
    t_bn float default ((0)) not null,
    tg float default ((0)) not null 
);
---------------------------------
-- dgudocuments - Другие
-- dgudocuments - Документы дгу
drop table if exists dgudocuments;

create table dgudocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- docremonttypes - Другие
-- docremonttypes - Типы ремонтных документов
drop table if exists docremonttypes;

create table docremonttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- documenttypes - Другие
-- documenttypes - Типы документов
drop table if exists documenttypes;

create table documenttypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- drenageperformances - Другие
-- drenageperformances - Показатели дренажа
drop table if exists drenageperformances;

create table drenageperformances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- edvdocuments - Другие
-- edvdocuments - Документы ЕДВ
drop table if exists edvdocuments;

create table edvdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- electroprotectdevices - Другие
-- electroprotectdevices - electroprotectdevices
drop table if exists electroprotectdevices;

create table electroprotectdevices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- factorymanufacturers - Другие
-- factorymanufacturers - factorymanufacturers
drop table if exists factorymanufacturers;

create table factorymanufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    orgPhone varchar(50) default (NULL),
    managerPhone varchar(50) default (NULL),
    country varchar(50) default (NULL),
    city varchar(50) default (NULL),
    street varchar(50) default (NULL),
    houseNumber varchar(50) default (NULL) 
);
---------------------------------
-- faktory_riska_truboprovoda - Другие
-- faktory_riska_truboprovoda - faktory_riska_truboprovoda
drop table if exists faktory_riska_truboprovoda;

create table faktory_riska_truboprovoda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineID int,
    objID int,
    obj_type_faktory_riskaID int,             -- Тип факторов риска
    nalichie_vblizi_kommunikacijID int,       -- Наличие вблизи коммуникаций
    harakter_gruntaID int,                    -- Грунт в месте прокладки
    poverhnost_nad_trassojID int,             -- Поверхность над трассой
    podtoplenie_do_truby int,                 -- Подтопление до трубы
    zanos_kanala_gruntomID int,               -- Занос канала грунтом
    stroitelnye_konstrukcii_kanalaID int,     -- Строительные конструкции канала
    sostoyanie_stroitelnyh_konstrukcij_kanalaID int,  -- Состояние строительных конструкций канала
    vnutrennee_sostoyanie_kanalaID int,       -- Внутреннее состояние канала
    konstrukciya_drenazhnogo_ustrojstvaID int,    -- Конструкция дренажного устройства
    sostoyanie_teplovoj_izolyacii_podachaID int,  -- Состояние тепловой изоляции (подача)
    sostoyanie_teplovoj_izolyacii_obratkaID int,  -- Состояние тепловой изоляции (обратка)
    sostoyanie_naruzhnogo_pokrytiya_podachaID int,    -- Состояние наружного покрытия (подача)
    sostoyanie_naruzhnogo_pokrytiya_obratkaID int,    -- Состояние наружного покрытия (обратка)
    sostoyanie_protivokorrozionnogo_pokrytiya_podachaID int,  -- Состоянние противокоррозионного покрытия (подача)
    sostoyanie_protivokorrozionnogo_pokrytiya_obratkaID int,  -- Состоянние противокоррозионного покрытия (обратка)
    Elektrich int,                            -- Наличие эл.коммуникаций, электрохимзащиты газопровода
    TransportElekricht int,                   -- Наличие электрифицированного транспорта на расстоянии
    Ponezial int,                             -- Уровень разности электропотенциала, В
    floodIntensityBWid int,                   -- Интенсивность подтопления фекальными водами
    floodIntensityFWid int,                   -- Интенсивность подтопления паводковыми водами
    floodIntensityGWid int,                   -- Интенсивность подтопления грунтовыми водами
    floodIntensityTWid int,                   -- Интенсивность подтопления водопроводными водами
    Vodootved int,                            -- Водоотведение на участке
    SlozhOkluzh int,                          -- Сложность отключения участка для устранения повреждения
    OtkluzhGkal int,                          -- Объем отключаемых потребителей, при повреждении, Гкал/ч
    AvariiVipoln int,                         -- Сложность выполнения аварийно-восстановительных работ
    Pesehod int,                              -- Прокладка трубопроводов под пешеходными зонами
    ZhdDorogi int,                            -- Прокладка трубопроводов под авто и ж/д дорогами
    LudiProklad int,                          -- Прокладка трубопровода в местах массового скопления жителей города
    UzherbLudi int,                           -- Нанесение ущерба населению от подтопления при возможном повреждении трубопроводов
    UzherbSity int,                           -- Нанесение ущерба инфраструктуре города при возможном повреждении трубопроводов
    VnesniiVid int,                           -- Внешний вид
    SostOborudovania int,                     -- Состояние оборудования
    nalichie_korrozii_podachaID int,          -- Наличие коррозии (подача)
    nalichie_korrozii_obratkaID int,          -- Наличие коррозии (обратка)
    VnesnKorrozia int,                        -- Степень внешней коррозии
    VnunrenKorrozia int,                      -- Степень внутренней коррозии
    SostKonstrukz int,                        -- Состояние строительных конструкций
    zashemID int,                             -- Защемления трубопроводов
    sost_podvID int,                          -- Состояние подвесок
    sost_oporID int,                          -- Состояние опор
    nalich_obrKlID int,                       -- Наличие обратных клапанов
    sootv_nadpID int,                         -- Соответствие надписей на арматуре
    nalich_tabl_regID int,                    -- Наличие табличек с регистрационными номерами
    nalich_tabl_parID int,                    -- Наличие таблички с разрешенными параметрами работы
    int_korID int,                            -- Интенсивности процесса внутренней коррозии
    sostoyanie_metalla_truboprovodaID int,    -- Состояние металла трубопровода
    tol1 float,                               -- Первоначальная толщина металла труб
    tol2 float,                               -- Фактическая толщина стенки трубопровода
    glubina_kor float,                        -- Глубина коррозионных повреждений, мм
    razmery_kor float,                        -- Размеры зон коррозионных повреждений, мм
    document_analiz_vlazhnost varchar(255),   -- Анализ проб на влажность
    document_analiz_korrozia varchar(255),    -- Анализ проб на коррозийную активность
    document_potenzial varchar(255),          -- Разность электрических потенциалов «труба-земля»
    document_analiz_vytyazhka varchar(255),   -- Анализ водяной вытяжки
    dokument_analiz_prob_na_vlazhnost varchar(255),   -- Анализ проб на влажность
    dokument_analiz_prob_na_korrozijnuyu_aktivnost varchar(255),  -- Анализ проб на коррозионную активность
    dokument_raznost_elektricheskih_potencialov varchar(255), -- Разность электрических потенциалов
    dokument_analiz_vodyanoj_vytyazhki varchar(255),  -- Анализ водной вытяжки
    dokument_chertezh_objekta_kontrolya varchar(255), -- Чертеж объекта контроля
    diameterCondit float,                     -- Диаметр условный заменённых труб, мм
    diameterExternal float,                   -- Диаметр внешний заменённых труб, мм
    diameterInternal float,                   -- Диаметр внутренний заменённых труб, мм
    wallThickness float,                      -- Толщина стенки, мм
    pipeSectLength float,
    isolMaterialID int,                       -- Материал изоляции
    isolationTypeID int,                      -- Тип изоляции ППУ
    isolThickness float,                      -- Толщина изоляции, мм
    externMaterialID int,                     -- Материал наружного покрытия
    externCoverThick float,                   -- Толщина наружного покрытия, мм
    anticorrMaterialID int,                   -- Материал антикоррозийного покрытия
    len_tube float,                           -- Длина заменённой трубы, м
    len_izol float,                           -- Восстановление тепловой изоляции поверхности труб, м^2
    asfaltirovanie float,                     -- Асфальтирование, ремонт, м^2
    len_channel float,                        -- Длина замененного канала, м
    zamena_kanala_procent float,              -- Замена канала,%
    zamena_kompensatorov int,                 -- Замена компенсаторов
    rekonstrukciya_kamery_nachalnogo_uzla int,    -- Реконструкция камеры начального узда
    rekonstrukciya_kamery_konechnogo_uzla int,    -- Реконструкция камеры конечного узда
    ustanovka_i_zamena_zadvizhek int,         -- Установка и замена задвижек
    tubingTypeID int                          -- Тип прокладки
);
CREATE INDEX faktory_riska_truboprovoda_lineid_idx ON faktory_riska_truboprovoda (lineid);
---------------------------------
-- faktriska_10_stroykonstr - Другие
-- faktriska_10_stroykonstr - Факторы риска строительных конструкций
drop table if exists faktriska_10_stroykonstr;

create table faktriska_10_stroykonstr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- faktriska_11_vodootvedenie - Другие
-- faktriska_11_vodootvedenie - Факторы риска водоотведения
drop table if exists faktriska_11_vodootvedenie;

create table faktriska_11_vodootvedenie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- faktriska_14_avar_vosst_raboty - Другие
-- faktriska_14_avar_vosst_raboty - faktriska_14_avar_vosst_raboty
drop table if exists faktriska_14_avar_vosst_raboty;

create table faktriska_14_avar_vosst_raboty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- faktriska_16_avto - Другие
-- faktriska_16_avto - Факторы риска автотранспорта
drop table if exists faktriska_16_avto;

create table faktriska_16_avto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- faktriska_18_uscherb_nas - Другие
-- faktriska_18_uscherb_nas - Факторы риска ущерба населению
drop table if exists faktriska_18_uscherb_nas;

create table faktriska_18_uscherb_nas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- faktriska_19_uscherb_infrastr - Другие
-- faktriska_19_uscherb_infrastr - Факторы риска ущерба инфраструктуре
drop table if exists faktriska_19_uscherb_infrastr;

create table faktriska_19_uscherb_infrastr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- faktriska_9_podtoplenie - Другие
-- faktriska_9_podtoplenie - faktriska_9_podtoplenie
drop table if exists faktriska_9_podtoplenie;

create table faktriska_9_podtoplenie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    ves int default (NULL),
    value float default (NULL),
    valueIznos float default (NULL),
    Help varchar default (NULL) 
);
---------------------------------
-- familii_masterov_ao__astana_teplotranzit - Другие
-- familii_masterov_ao__astana_teplotranzit - Фамилии мастеров АО 
drop table if exists familii_masterov_ao__astana_teplotranzit;

create table familii_masterov_ao__astana_teplotranzit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod int,                                  -- Код
    master varchar(50),                       -- Мастер
    colorm float,
    higthm float,
    state int,
    colormkw float,
    statekw int,
    rayon varchar(50),                        -- Район
    uchastok varchar(50),                     -- Участок
    nachalnik_sluzhby_ekspluatatsii_teplovyh_setey varchar(50)    -- НАЧАЛЬНИК СЛУЖБЫ ЭКСПЛУАТАЦИИ ТЕПЛОВЫХ СЕТЕЙ
);
---------------------------------
-- floodingbeforetubes - Другие
-- floodingbeforetubes - Признаки затопления
drop table if exists floodingbeforetubes;

create table floodingbeforetubes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- funktsionalnoe_naznachenie_zdaniy_i_sooruzheniy - Другие
-- funktsionalnoe_naznachenie_zdaniy_i_sooruzheniy - Функциональное назначение зданий и сооружений
drop table if exists funktsionalnoe_naznachenie_zdaniy_i_sooruzheniy;

create table funktsionalnoe_naznachenie_zdaniy_i_sooruzheniy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poleznost varchar(50),                    -- Полезность
    kod int,                                  -- Код
    naimenovanie varchar(255),                -- Наименование
    primechanie varchar(50),                  -- Примечание
    id_geom int 
);
---------------------------------
-- gruzobdocuments - Другие
-- gruzobdocuments - gruzobdocuments
drop table if exists gruzobdocuments;

create table gruzobdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- gvsparallschemes - Другие
-- gvsparallschemes - Виды схем отопления
drop table if exists gvsparallschemes;

create table gvsparallschemes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- heatcarriers - Другие
-- heatcarriers - heatcarriers
drop table if exists heatcarriers;

create table heatcarriers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- heatloses - Другие
-- heatloses - heatloses
drop table if exists heatloses;

create table heatloses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatLosesMainID int,
    cityID int,
    r int,
    m int,
    tn float,
    tpod float,
    tgr float 
);
---------------------------------
-- heatlosesfact - Другие
-- heatlosesfact - heatlosesfact
drop table if exists heatlosesfact;

create table heatlosesfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cityID int,
    r int,
    m int,
    mon varchar(20),
    sezon int,
    tn float,
    tpod float,
    tgr float 
);
---------------------------------
-- heatlosesmain - Другие
-- heatlosesmain - heatlosesmain
drop table if exists heatlosesmain;

create table heatlosesmain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100),
    city varchar(100),
    t_ot float default ((18)),
    t_vent float default ((18)),
    y int,
    a float default ((0.25)),
    tankbattery_q float default ((50)),
    d1 timestamp,
    d2 timestamp,
    useTableData int default ((0)),
    volWaterHS float default ((13.3)),
    volWaterVS float default ((5.5)),
    volWaterOpenGvs float default ((19.5)),
    netWaterFillingNormMS float default ((1.5)),
    netWaterFillingNormRS float default ((1.2)),
    netWaterFillingNormHS float default ((1.2)),
    netWaterFillingNormTB float default ((1.2)),
    netWaterFillingNormHA float default ((1.2)) 
);
---------------------------------
-- heatlosesmainfact - Другие
-- heatlosesmainfact - heatlosesmainfact
drop table if exists heatlosesmainfact;

create table heatlosesmainfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100),
    city varchar(100),
    t_ot float default ((18)),
    t_vent float default ((18)),
    y int,
    a float default ((0.25)),
    tankbattery_q float default ((50)),
    d1 timestamp,
    d2 timestamp,
    useTableData int default ((0)),
    volWaterHS float default ((13.3)),
    volWaterVS float default ((5.5)),
    volWaterOpenGvs float default ((19.5)),
    netWaterFillingNormMS float default ((1.5)),
    netWaterFillingNormRS float default ((1.2)),
    netWaterFillingNormHS float default ((1.2)),
    netWaterFillingNormTB float default ((1.2)),
    netWaterFillingNormHA float default ((1.2)) 
);
---------------------------------
-- heatlosessource - Другие
-- heatlosessource - heatlosessource
drop table if exists heatlosessource;

create table heatlosessource (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    t_percent float default ((60)),
    spring_pressing float default ((60)),
    autumn_pressing float default ((20)),
    pressingMonth1 int default ((5)),
    netTempPressing1 float default ((30)),
    coldTempPressing1 float default ((13.6)),
    pressingMonth2 int default ((9)),
    netTempPressing2 float default ((30)),
    coldTempPressing2 float default ((13.6)),
    discharge_month int default ((5)),
    discharge_temperature float default ((30)),
    discharge_size float default ((30)),
    tubingTypePressing int default ((1)),
    avgGPressingSpring float,
    avgQPressingSpring float,
    avgGPressingAutumn float,
    avgQPressingAutumn float,
    avgGFlushing float,
    avgQFlushing float,
    avgGFlushinghs float,
    avgQFlushinghs float,
    flushinghs_building int default ((1)),
    flushinghs_temp1 float default ((35)),
    flushinghs_temp2 float default ((13.6)),
    flushinghs float default ((2)),
    flushing_temp1 float default ((35)),
    flushing_temp2 float default ((13.6)),
    flushing float default ((2)),
    month_flushing int default ((9)),
    month_flushinghs int default ((9)),
    flushing_flow int default ((0)),
    flushing_ret int default ((0)),
    coeffDefault int default ((1)),
    coeffMsFlowNorms1 float default ((1)),
    coeffMsRetNorms1 float default ((1)),
    coeffMsUndergroundNorms1 float default ((1)),
    coeffRsFlowNorms1 float default ((1)),
    coeffRsRetNorms1 float default ((1)),
    coeffRsUndergroundNorms1 float default ((1)),
    coeffBasementFlowNorms1 float default ((1)),
    coeffBasementRetNorms1 float default ((1)),
    coeffBasementUndergroundNorms1 float default ((1)),
    coeffHarnessFlowNorms1 float default ((1)),
    coeffHarnessRetNorms1 float default ((1)),
    coeffHarnessUndergroundNorms1 float default ((1)),
    coeffMsFlowNorms3 float default ((1)),
    coeffMsRetNorms3 float default ((1)),
    coeffMsUndergroundNorms3 float default ((1)),
    coeffRsFlowNorms3 float default ((1)),
    coeffRsRetNorms3 float default ((1)),
    coeffRsUndergroundNorms3 float default ((1)),
    coeffBasementFlowNorms3 float default ((1)),
    coeffBasementRetNorms3 float default ((1)),
    coeffBasementUndergroundNorms3 float default ((1)),
    coeffHarnessFlowNorms3 float default ((1)),
    coeffHarnessRetNorms3 float default ((1)),
    coeffHarnessUndergroundNorms3 float default ((1)),
    coeffMsFlowNorms1_r float default ((1)),
    coeffMsRetNorms1_r float default ((1)),
    coeffMsUndergroundNorms1_r float default ((1)),
    coeffRsFlowNorms1_r float default ((1)),
    coeffRsRetNorms1_r float default ((1)),
    coeffRsUndergroundNorms1_r float default ((1)),
    coeffBasementFlowNorms1_r float default ((1)),
    coeffBasementRetNorms1_r float default ((1)),
    coeffBasementUndergroundNorms1_r float default ((1)),
    coeffHarnessFlowNorms1_r float default ((1)),
    coeffHarnessRetNorms1_r float default ((1)),
    coeffHarnessUndergroundNorms1_r float default ((1)),
    coeffMsFlowNorms3_r float default ((1)),
    coeffMsRetNorms3_r float default ((1)),
    coeffMsUndergroundNorms3_r float default ((1)),
    coeffRsFlowNorms3_r float default ((1)),
    coeffRsRetNorms3_r float default ((1)),
    coeffRsUndergroundNorms3_r float default ((1)),
    coeffBasementFlowNorms3_r float default ((1)),
    coeffBasementRetNorms3_r float default ((1)),
    coeffBasementUndergroundNorms3_r float default ((1)),
    coeffHarnessFlowNorms3_r float default ((1)),
    coeffHarnessRetNorms3_r float default ((1)),
    coeffHarnessUndergroundNorms3_r float default ((1)) 
);
---------------------------------
-- heatlosessourcefact - Другие
-- heatlosessourcefact - heatlosessourcefact
drop table if exists heatlosessourcefact;

create table heatlosessourcefact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    t_percent float default ((60)),
    spring_pressing float default ((60)),
    autumn_pressing float default ((20)),
    pressingMonth1 int default ((5)),
    netTempPressing1 float default ((30)),
    coldTempPressing1 float default ((13.6)),
    pressingMonth2 int default ((9)),
    netTempPressing2 float default ((30)),
    coldTempPressing2 float default ((13.6)),
    discharge_month int default ((5)),
    discharge_temperature float default ((30)),
    discharge_size float default ((30)),
    tubingTypePressing int default ((1)),
    avgGPressingSpring float,
    avgQPressingSpring float,
    avgGPressingAutumn float,
    avgQPressingAutumn float,
    avgGFlushing float,
    avgQFlushing float,
    avgGFlushinghs float,
    avgQFlushinghs float,
    flushinghs_building int default ((1)),
    flushinghs_temp1 float default ((35)),
    flushinghs_temp2 float default ((13.6)),
    flushinghs float default ((2)),
    flushing_temp1 float default ((35)),
    flushing_temp2 float default ((13.6)),
    flushing float default ((2)),
    month_flushing int default ((9)),
    month_flushinghs int default ((9)),
    flushing_flow int default ((0)),
    flushing_ret int default ((0)),
    coeffDefault int default ((1)),
    coeffMsFlowNorms1 float default ((1)),
    coeffMsRetNorms1 float default ((1)),
    coeffMsUndergroundNorms1 float default ((1)),
    coeffRsFlowNorms1 float default ((1)),
    coeffRsRetNorms1 float default ((1)),
    coeffRsUndergroundNorms1 float default ((1)),
    coeffBasementFlowNorms1 float default ((1)),
    coeffBasementRetNorms1 float default ((1)),
    coeffBasementUndergroundNorms1 float default ((1)),
    coeffHarnessFlowNorms1 float default ((1)),
    coeffHarnessRetNorms1 float default ((1)),
    coeffHarnessUndergroundNorms1 float default ((1)),
    coeffMsFlowNorms3 float default ((1)),
    coeffMsRetNorms3 float default ((1)),
    coeffMsUndergroundNorms3 float default ((1)),
    coeffRsFlowNorms3 float default ((1)),
    coeffRsRetNorms3 float default ((1)),
    coeffRsUndergroundNorms3 float default ((1)),
    coeffBasementFlowNorms3 float default ((1)),
    coeffBasementRetNorms3 float default ((1)),
    coeffBasementUndergroundNorms3 float default ((1)),
    coeffHarnessFlowNorms3 float default ((1)),
    coeffHarnessRetNorms3 float default ((1)),
    coeffHarnessUndergroundNorms3 float default ((1)),
    coeffMsFlowNorms1_r float default ((1)),
    coeffMsRetNorms1_r float default ((1)),
    coeffMsUndergroundNorms1_r float default ((1)),
    coeffRsFlowNorms1_r float default ((1)),
    coeffRsRetNorms1_r float default ((1)),
    coeffRsUndergroundNorms1_r float default ((1)),
    coeffBasementFlowNorms1_r float default ((1)),
    coeffBasementRetNorms1_r float default ((1)),
    coeffBasementUndergroundNorms1_r float default ((1)),
    coeffHarnessFlowNorms1_r float default ((1)),
    coeffHarnessRetNorms1_r float default ((1)),
    coeffHarnessUndergroundNorms1_r float default ((1)),
    coeffMsFlowNorms3_r float default ((1)),
    coeffMsRetNorms3_r float default ((1)),
    coeffMsUndergroundNorms3_r float default ((1)),
    coeffRsFlowNorms3_r float default ((1)),
    coeffRsRetNorms3_r float default ((1)),
    coeffRsUndergroundNorms3_r float default ((1)),
    coeffBasementFlowNorms3_r float default ((1)),
    coeffBasementRetNorms3_r float default ((1)),
    coeffBasementUndergroundNorms3_r float default ((1)),
    coeffHarnessFlowNorms3_r float default ((1)),
    coeffHarnessRetNorms3_r float default ((1)),
    coeffHarnessUndergroundNorms3_r float default ((1)) 
);
---------------------------------
-- heatlosessourcelist - Другие
-- heatlosessourcelist - heatlosessourcelist
drop table if exists heatlosessourcelist;

create table heatlosessourcelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT 
);
---------------------------------
-- heatlosessourcemonths - Другие
-- heatlosessourcemonths - heatlosessourcemonths
drop table if exists heatlosessourcemonths;

create table heatlosessourcemonths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    r int,
    m int,
    sezon int,
    tn float,
    tpod float,
    tgr float,
    tx float default ((0)),
    tgP float,
    tgO float,
    workCount int,
    netWaterExpFlow float,
    regCountFlow int,
    workCountFlow int,
    regCountNodeFlow int,
    netWaterExpRet float,
    regCountRet int,
    workCountRet int,
    regCountNodeRet int,
    avgGsarzFlow float,
    avgQsarzFlow float,
    avgGsarzRet float,
    avgQsarzRet float,
    avgGsarzNodeFlow float,
    avgGsarzNodeRet float 
);
---------------------------------
-- heatlosessourcemonthsfact - Другие
-- heatlosessourcemonthsfact - heatlosessourcemonthsfact
drop table if exists heatlosessourcemonthsfact;

create table heatlosessourcemonthsfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    r int,
    m int,
    sezon int,
    tn float,
    tpod float,
    tgr float,
    tx float default ((0)),
    tgP float,
    tgO float,
    workCount int,
    netWaterExpFlow float,
    regCountFlow int,
    workCountFlow int,
    regCountNodeFlow int,
    netWaterExpRet float,
    regCountRet int,
    workCountRet int,
    regCountNodeRet int,
    avgGsarzFlow float,
    avgQsarzFlow float,
    avgGsarzRet float,
    avgQsarzRet float,
    avgGsarzNodeFlow float,
    avgGsarzNodeRet float 
);
---------------------------------
-- heatpipesectionsharness - Другие
-- heatpipesectionsharness - heatpipesectionsharness
drop table if exists heatpipesectionsharness;

create table heatpipesectionsharness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int default (NULL),
    diameterExternal float default (NULL),
    diameterInternal float default ((1000)),
    belongMS int default ((1)),
    pipeSectLength float default (NULL) 
);
---------------------------------
-- heatpipesectionsharnessfact - Другие
-- heatpipesectionsharnessfact - heatpipesectionsharnessfact
drop table if exists heatpipesectionsharnessfact;

create table heatpipesectionsharnessfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int default (NULL),
    diameterExternal float default (NULL),
    diameterInternal float default ((1000)),
    belongMS int default ((1)),
    pipeSectLength float default (NULL) 
);
---------------------------------
-- help_old - Другие
-- help_old - help_old
drop table if exists help_old;

create table help_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tab varchar(50) default (NULL),
    stroka varchar(2) default (NULL),
    en varchar(50) default (NULL),
    ru varchar(50) default (NULL),
    nm varchar(255) default (NULL),
    hlp varchar(130) default (NULL),
    helpshiftf1 varchar,
    velichina varchar(50) default (NULL),
    stand_razmer varchar(15) default (NULL) 
);
---------------------------------
-- holes - Другие
-- holes - holes
drop table if exists holes;

create table holes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- hsourceworkmonthgraphs - Другие
-- hsourceworkmonthgraphs - hsourceworkmonthgraphs
drop table if exists hsourceworkmonthgraphs;

create table hsourceworkmonthgraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year varchar(50) default (NULL),
    hSourceID int default (NULL),
    length_1 int default ((31)),
    length_2 int default ((28)),
    length_3 int default ((31)),
    length_4 int default ((30)),
    length_5 int default ((31)),
    length_6 int default ((30)),
    length_7 int default ((31)),
    length_8 int default ((31)),
    length_9 int default ((30)),
    length_10 int default ((31)),
    length_11 int default ((30)),
    length_12 int default ((31)),
    t_1 float default ((5)),
    t_2 float default ((5)),
    t_3 float default ((5)),
    t_4 float default ((5)),
    t_5 float default ((15)),
    t_6 float default ((15)),
    t_7 float default ((15)),
    t_8 float default ((15)),
    t_9 float default ((15)),
    t_10 float default ((5)),
    t_11 float default ((5)),
    t_12 float default ((5)),
    t1_1 float default ((0)),
    t1_2 float default ((0)),
    t1_3 float default ((0)),
    t1_4 float default ((0)),
    t1_5 float default ((0)),
    t1_6 float default ((0)),
    t1_7 float default ((0)),
    t1_8 float default ((0)),
    t1_9 float default ((0)),
    t1_10 float default ((0)),
    t1_11 float default ((0)),
    t1_12 float default ((0)),
    t2_1 float default ((0)),
    t2_2 float default ((0)),
    t2_3 float default ((0)),
    t2_4 float default ((0)),
    t2_5 float default ((0)),
    t2_6 float default ((0)),
    t2_7 float default ((0)),
    t2_8 float default ((0)),
    t2_9 float default ((0)),
    t2_10 float default ((0)),
    t2_11 float default ((0)),
    t2_12 float default ((0)),
    length_1_fakt int default ((0)),
    length_2_fakt int default ((0)),
    length_3_fakt int default ((0)),
    length_4_fakt int default ((0)),
    length_5_fakt int default ((0)),
    length_6_fakt int default ((0)),
    length_7_fakt int default ((0)),
    length_8_fakt int default ((0)),
    length_9_fakt int default ((0)),
    length_10_fakt int default ((0)),
    length_11_fakt int default ((0)),
    length_12_fakt int default ((0)),
    t_1_fakt float default ((0)),
    t_2_fakt float default ((0)),
    t_3_fakt float default ((0)),
    t_4_fakt float default ((0)),
    t_5_fakt float default ((0)),
    t_6_fakt float default ((0)),
    t_7_fakt float default ((0)),
    t_8_fakt float default ((0)),
    t_9_fakt float default ((0)),
    t_10_fakt float default ((0)),
    t_11_fakt float default ((0)),
    t_12_fakt float default ((0)),
    t1_1_fakt float default ((0)),
    t1_2_fakt float default ((0)),
    t1_3_fakt float default ((0)),
    t1_4_fakt float default ((0)),
    t1_5_fakt float default ((0)),
    t1_6_fakt float default ((0)),
    t1_7_fakt float default ((0)),
    t1_8_fakt float default ((0)),
    t1_9_fakt float default ((0)),
    t1_10_fakt float default ((0)),
    t1_11_fakt float default ((0)),
    t1_12_fakt float default ((0)),
    t2_1_fakt float default ((0)),
    t2_2_fakt float default ((0)),
    t2_3_fakt float default ((0)),
    t2_4_fakt float default ((0)),
    t2_5_fakt float default ((0)),
    t2_6_fakt float default ((0)),
    t2_7_fakt float default ((0)),
    t2_8_fakt float default ((0)),
    t2_9_fakt float default ((0)),
    t2_10_fakt float default ((0)),
    t2_11_fakt float default ((0)),
    t2_12_fakt float default ((0)),
    Gpod_1_fakt float default ((0)),
    Gpod_2_fakt float default ((0)),
    Gpod_3_fakt float default ((0)),
    Gpod_4_fakt float default ((0)),
    Gpod_5_fakt float default ((0)),
    Gpod_6_fakt float default ((0)),
    Gpod_7_fakt float default ((0)),
    Gpod_8_fakt float default ((0)),
    Gpod_9_fakt float default ((0)),
    Gpod_10_fakt float default ((0)),
    Gpod_11_fakt float default ((0)),
    Gpod_12_fakt float default ((0)),
    Ggvs_pribor_1_fakt float default ((0)),
    Ggvs_pribor_2_fakt float default ((0)),
    Ggvs_pribor_3_fakt float default ((0)),
    Ggvs_pribor_4_fakt float default ((0)),
    Ggvs_pribor_5_fakt float default ((0)),
    Ggvs_pribor_6_fakt float default ((0)),
    Ggvs_pribor_7_fakt float default ((0)),
    Ggvs_pribor_8_fakt float default ((0)),
    Ggvs_pribor_9_fakt float default ((0)),
    Ggvs_pribor_10_fakt float default ((0)),
    Ggvs_pribor_11_fakt float default ((0)),
    Ggvs_pribor_12_fakt float default ((0)),
    Gakt_tex_1_fakt float default ((0)),
    Gakt_tex_2_fakt float default ((0)),
    Gakt_tex_3_fakt float default ((0)),
    Gakt_tex_4_fakt float default ((0)),
    Gakt_tex_5_fakt float default ((0)),
    Gakt_tex_6_fakt float default ((0)),
    Gakt_tex_7_fakt float default ((0)),
    Gakt_tex_8_fakt float default ((0)),
    Gakt_tex_9_fakt float default ((0)),
    Gakt_tex_10_fakt float default ((0)),
    Gakt_tex_11_fakt float default ((0)),
    Gakt_tex_12_fakt float default ((0)),
    Gakt_avarija_1_fakt float default ((0)),
    Gakt_avarija_2_fakt float default ((0)),
    Gakt_avarija_3_fakt float default ((0)),
    Gakt_avarija_4_fakt float default ((0)),
    Gakt_avarija_5_fakt float default ((0)),
    Gakt_avarija_6_fakt float default ((0)),
    Gakt_avarija_7_fakt float default ((0)),
    Gakt_avarija_8_fakt float default ((0)),
    Gakt_avarija_9_fakt float default ((0)),
    Gakt_avarija_10_fakt float default ((0)),
    Gakt_avarija_11_fakt float default ((0)),
    Gakt_avarija_12_fakt float default ((0)) 
);
---------------------------------
-- ispravl - Другие
-- ispravl - ispravl
drop table if exists ispravl;

create table ispravl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    priznak_truboprovoda varchar(50) 
);
---------------------------------
-- iznos - Другие
-- iznos - iznos
drop table if exists iznos;

create table iznos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeSectionID int default (NULL),
    calculationID int default (NULL),
    Iznos int default ((0)),
    DateEndPerekladki date default (NULL),
    DateEndOsvidetel date default (NULL),
    SrokEkcpluataz float default (NULL),
    VnesniiVid int default (NULL),
    SostOborudovania int default (NULL),
    KolKapitalRemont int default (NULL),
    KolTekushRemont int default (NULL),
    KategorNarusenii int default (NULL),
    KoeffPovrezh int default (NULL),
    VnesnKorrozia int default (NULL),
    VnunrenKorrozia int default (NULL),
    SostKonstrukz int default (NULL) 
);
CREATE INDEX iznos_calculationid_idx ON iznos (calculationid);
---------------------------------
-- kapitalnyy_remont - Другие
-- kapitalnyy_remont - Капитальный_ремонт
drop table if exists kapitalnyy_remont;

create table kapitalnyy_remont (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remont varchar(255),                      -- Ремонт
    sostoyanie varchar(255),                  -- Состояние
    uchastok_ekspluatatsii varchar(255),      -- Участок эксплуатации
    istochnik_tepla varchar(255),             -- Источник тепла
    magistral_raspredset varchar(255),        -- Магистраль/Распредсеть
    nachalnik_uchastka varchar(255),          -- Начальник участка
    nomer_prikaza_naznacheniya_komissii varchar(255), -- Номер приказа назначения комиссии
    data_prikaza_naznacheniya_komissii date,  -- Дата приказа назначения комиссии
    chleny_komissii__dolzhnost_predsedatel varchar(255),  -- Члены комиссии: Должность Председатель
    chleny_komissii__predsedatel varchar(255),    -- Члены комиссии: Председатель
    chleny_komissii__dolzhnost_chlen_1 varchar(255),  -- Члены комиссии: Должность Член 1
    chleny_komissii__fio_chlen_1 varchar(50), -- Члены комиссии: ФИО Член 1
    chleny_komissii__dolzhnost_chlen_2 varchar(255),  -- Члены комиссии: Должность Член 2
    chleny_komissii__fio_chlen_2 varchar(255),    -- Члены комиссии: ФИО Член 2
    otvetstvennyy_ispolnitel_dolzhnost varchar(255),  -- Ответственный исполнитель Должность
    otvetstvennyy_ispolnitel_fio varchar(255),    -- Ответственный исполнитель ФИО
    otvetstvennyy_rukovoditel_dolzhnost varchar(255), -- Ответственный руководитель Должность
    otvetstvennyy_rukovoditel_fio varchar(255),   -- Ответственный руководитель ФИО
    reshenie_komissii text,                   -- Решение комиссии
    nomer_plana varchar(255),                 -- Номер плана
    data_plana date,                          -- Дата плана
    proektnaya_organizatsiya varchar(255),    -- Проектная организация
    obschee_opisanie text,                    -- Общее описание
    data_nachala_remonta_plan date,           -- Дата начала ремонта план
    data_zaversheniya_remonta_plan date,      -- Дата завершения ремонта план
    diametr_uslovnyy_podayuschiy_plan_mm float,   -- Диаметр условный подающий план мм
    diametr_uslovnyy_obratnyy_plan_mm float,  -- Диаметр условный обратный план мм
    vid_prokladki_plan varchar(1),            -- Вид прокладки план
    shema_privyazki text,                     -- Схема привязки
    obschaya_protyazhennost_plan_m float,     -- Общая протяженность план, м
    smetnaya_stoimost_tys_tg float,           -- Сметная стоимость тыс тг
    fakticheskaya_stoimost_tys_tg float,      -- Фактическая стоимость тыс, тг
    vypolnenye_raboty text,                   -- Выполненые работы
    otstuplenie_ot_plana text,                -- Отступление от плана
    proverennye_dokumenty_po_remontu text,    -- Проверенные документы по ремонту
    nedodelki_nekritichnye text,              -- Недоделки некритичные
    nomer_akta_priemki_iz_kapitalnogo_remonta varchar(255),   -- Номер акта приемки из капитального ремонта
    data_sozdaniya_akta_priemki_iz_kapitalnogo_remonta date,  -- Дата создания акта приемки из капитального ремонта
    diametr_uslovnyy_podayuschiy_fakt_mm float,   -- Диаметр условный подающий факт мм
    diametr_uslovnyy_obratnyy_fakt_mm float,  -- Диаметр условный обратный факт мм
    data_nachala_remonta_fakt date,           -- Дата начала ремонта факт
    data_zaversheniya_remonta_fakt date,      -- Дата завершения ремонта факт
    vid_prokladki_fakt varchar(1),            -- Вид прокладки факт
    obschaya_protyazhennost_fakt_m float,     -- Общая протяженность факт, м
    data_vvoda_v_ekspluatatsiyu date,         -- Дата ввода в эксплуатацию
    akt_kapitalnogo_remonta text              -- Акт капитального ремонта
);
---------------------------------
-- kapremont_elementy - Другие
-- kapremont_elementy - Капремонт_Элементы
drop table if exists kapremont_elementy;

create table kapremont_elementy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defekt int,                               -- Повреждение
    element int,                              -- Элемент
    osmotreno_na_podache float,               -- Осмотрено на подаче
    povrezhdeno_na_podache float,             -- Повреждено на подаче
    meropriyatie_na_podache varchar(255),     -- Мероприятие на подаче
    zaplanirovano_na_podache float,           -- Запланировано на подаче
    ispravleno_na_podache float,              -- Исправлено на подаче
    osmotreno_na_obratke float,               -- Осмотрено на обратке
    povrezhdeno_na_obratke float,             -- Повреждено на обратке
    meropriyatie_na_obratke varchar(255),     -- Мероприятие на обратке
    zaplanirovano_na_obratke float,           -- Запланировано на обратке
    ispravleno_na_obratke float               -- Исправлено на обратке
);
---------------------------------
-- kapremont_kolodtsy_opory_nadzemnyy - Другие
-- kapremont_kolodtsy_opory_nadzemnyy - Капремонт_колодцы_опоры_надземный
drop table if exists kapremont_kolodtsy_opory_nadzemnyy;

create table kapremont_kolodtsy_opory_nadzemnyy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_remont int,                            -- ID ремонт
    id_kolod_opory_nadz int,                  -- ID колод опоры надз
    id_kolodts_opory_merop int,               -- ID колодц опоры мероп
    kolichestvo_protyazhennost_plan__sht__m int,  -- Количество Протяженность план, шт, м
    kolichestvo_protyazhennost_fakt__sht__m int   -- Количество Протяженность факт, шт, м
);
---------------------------------
-- kapremont_kolodtsy_opory_nadzemnyy2 - Другие
-- kapremont_kolodtsy_opory_nadzemnyy2 - Капремонт_колодцы_опоры_надземный2
drop table if exists kapremont_kolodtsy_opory_nadzemnyy2;

create table kapremont_kolodtsy_opory_nadzemnyy2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- kapremont_kolodtsy_opory_podzemnyy - Другие
-- kapremont_kolodtsy_opory_podzemnyy - Капремонт_колодцы_опоры_подземный
drop table if exists kapremont_kolodtsy_opory_podzemnyy;

create table kapremont_kolodtsy_opory_podzemnyy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_remont int,                            -- ID ремонт
    id_kolod_opory_podz int,                  -- ID колод опоры подз
    id_kolodts_opory_merop int,               -- ID колодц опоры мероп
    kolichestvo_protyazhennost_plan__sht__m int,  -- Количество Протяженность план, шт, м
    kolichestvo_protyazhennost_fakt__sht__m int   -- Количество Протяженность факт, шт, м
);
---------------------------------
-- kapremont_kolodtsy_opory_podzemnyy2 - Другие
-- kapremont_kolodtsy_opory_podzemnyy2 - Капремонт_колодцы_опоры_подземный2
drop table if exists kapremont_kolodtsy_opory_podzemnyy2;

create table kapremont_kolodtsy_opory_podzemnyy2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- kapremont_meropriyatiya - Другие
-- kapremont_meropriyatiya - Капремонт_мероприятия
drop table if exists kapremont_meropriyatiya;

create table kapremont_meropriyatiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_kapremont int,                         -- ID Капремонт
    element int,                              -- Элемент
    meropriyatie int,                         -- Мероприятие
    plan_2 int,
    fakt int                                  -- Факт
);
---------------------------------
-- kapremont_planiruemye_meropriyatiya_kolodtsy_opory - Другие
-- kapremont_planiruemye_meropriyatiya_kolodtsy_opory - Капремонт планируемые мероприятия колодцы опоры
drop table if exists kapremont_planiruemye_meropriyatiya_kolodtsy_opory;

create table kapremont_planiruemye_meropriyatiya_kolodtsy_opory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- kapremont_planiruemye_meropriyatiya_trubopr_izolyatsiya_oborudov - Другие
-- kapremont_planiruemye_meropriyatiya_trubopr_izolyatsiya_oborudov - Капремонт планируемые мероприятия трубопр изоляция оборудование
drop table if exists kapremont_planiruemye_meropriyatiya_trubopr_izolyatsiya_oborudov;

create table kapremont_planiruemye_meropriyatiya_trubopr_izolyatsiya_oborudov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_kapremont_trub_meropr int,             -- ID капремонт труб меропр
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- kapremont_trubopr_izol - Другие
-- kapremont_trubopr_izol - Капремонт_трубопр_изол
drop table if exists kapremont_trubopr_izol;

create table kapremont_trubopr_izol (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_remont int,                            -- ID ремонт
    id_kapremont_trub int,                    -- ID капремонт труб
    id_kapremont_trub_meropr int,             -- ID капремонт труб меропр
    kolichestvo_protyazhennost_plan__sht__m int,  -- Количество Протяженность план, шт, м
    kolichestvo_protyazhennost_fakt__sht__m int   -- Количество Протяженность факт, шт, м
);
---------------------------------
-- kapremont_truboprovod_oborudovanie_izolyatsiya - Другие
-- kapremont_truboprovod_oborudovanie_izolyatsiya - Капремонт_трубопровод_оборудование_изоляция
drop table if exists kapremont_truboprovod_oborudovanie_izolyatsiya;

create table kapremont_truboprovod_oborudovanie_izolyatsiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- kapremont_uchastok_teploprovoda_ishodnyy - Другие
-- kapremont_uchastok_teploprovoda_ishodnyy - Капремонт Участок теплопровода исходный
drop table if exists kapremont_uchastok_teploprovoda_ishodnyy;

create table kapremont_uchastok_teploprovoda_ishodnyy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer int,
    key_ut_p varchar(1),
    key_ut_o varchar(1),
    kod_p varchar(5),
    uzel_p varchar(25),
    pr_p varchar(1),
    kod0 varchar(5),
    kod1 varchar(5),
    uzel1 varchar(25),
    pr1 varchar(1),
    kod2 varchar(5),
    uzel2 varchar(25),
    pr2 varchar(1),
    standard varchar(40),
    kod_truba int,
    truba int,
    diametr float,
    tol float,
    diametr_usl float,
    dlina float,
    scher float,
    mestnoe float,
    dolja float,
    kodkvp varchar(5),
    kodkvo varchar(5),
    sopr float,
    name_calctpr varchar(1),
    name_typ varchar(1),
    kog_canal int,
    chanwidth float,
    chanheight float,
    kti float,
    kolwork int,
    kod_izol int,
    thickizol float,
    k_izol float,
    depth float,
    izoloutair float,
    izol_air float,
    air_ground float,
    tpground float,
    distance float,
    opc varchar(50),
    kod_owner int,
    dolya_owner1 float,
    kod_owner2 int,
    dolya_owner2 float,
    kod_owner3 int,
    dolya_owner3 float,
    kod_owner4 int,
    dolya_owner4 float,
    kod_owner5 int,
    dolya_owner5 float,
    registr varchar(50),
    kol_pereklad int,
    dateend date,
    dateend_izol date,
    datenew date,
    datenew_kapital date,
    dateend_kapital date,
    datenew_repair date,
    dateend_repair date,
    podp varchar(1),
    archives varchar(5),
    date_archives date,
    oper_archives varchar(16),
    operator varchar(50),
    coord text,
    f_kol_let float,
    f_koef_povr float,
    f_koef_povr_2goda float,
    f_10_elektro float,
    f_5_elektro float,
    f_3_elektro float,
    f_1_elektro float,
    f_0_elektro float,
    f_peres_elektro float,
    f_10_gas float,
    f_5_gas float,
    f_3_gas float,
    f_1_gas float,
    f_0_gas float,
    f_peres_gas float,
    f_10_transp float,
    f_5_transp float,
    f_3_transp float,
    f_1_transp float,
    f_0_transp float,
    f_peres_transp float,
    f_elektropotenz varchar(1),
    f_nar_korroz varchar(1),
    f_vnu_korroz varchar(1),
    f_grund_water varchar(1),
    f_pavod_water varchar(1),
    f_vod_water varchar(1),
    f_fek_water varchar(1),
    f_st_stik int,
    f_st_islom int,
    f_st_otkl int,
    f_st_nes int,
    f_st_opor int,
    f_water_otved varchar(50),
    f_otkl varchar(50),
    f_okl_pot varchar(50),
    f_slog_arbeit varchar(50),
    f_tratuar varchar(50),
    f_doroga varchar(50),
    f_ucherb_narod varchar(50),
    f_ucherb_gorod varchar(50),
    pr_videlen int,
    date_isp_gid date,
    g_isp_gid float,
    dp_isp_gid float,
    date_isp_tep date,
    tn_isp_tep float,
    tg_isp_tep float,
    g1_isp_tep float,
    g2_isp_tep float,
    dt1_isp_tep float,
    dt2_isp_tep float,
    t1_isp_tep float,
    t2_isp_tep float,
    diametr_vneshniy int,                     -- Диаметр внешний
    harakteristika_truby varchar(4),          -- Характеристика трубы
    tip_truby varchar(1),                     -- Тип трубы
    material_truby varchar(50),               -- Материал трубы
    maksimalno_dopustimaya_temperatura int,   -- Максимально допустимая температура
    zavod_izgotovitel varchar(255),           -- Завод изготовитель
    material_naruzhnogo_pokrytiya varchar(4), -- Материал наружного покрытия
    tip_izolyatsii varchar(1),                -- Тип изоляции
    tolschina_naruzhnogo_pokrytiya__mm float, -- Толщина наружного покрытия, мм
    material_antikorroziynogo_pokrytiya varchar(80),  -- Материал антикоррозийного покрытия
    uchastok_ms int,                          -- Участок МС
    uchastok_rs int,                          -- Участок РС
    rayon_ekspluatatsii int,                  -- Район эксплуатации
    "set" varchar(5),                         -- Сеть
    magistral int,                            -- Магистраль
    uchastok_ekspluatatsii int,               -- Участок эксплуатации
    vid_seti int                              -- Вид сети
);
---------------------------------
-- kapremont_uchastok_teploprovoda_posle_remonta - Другие
-- kapremont_uchastok_teploprovoda_posle_remonta - Капремонт Участок теплопровода после ремонта
drop table if exists kapremont_uchastok_teploprovoda_posle_remonta;

create table kapremont_uchastok_teploprovoda_posle_remonta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer int,
    key_ut_p varchar(1),
    key_ut_o varchar(1),
    kod_p varchar(5),
    uzel_p varchar(25),
    pr_p varchar(1),
    kod0 varchar(5),
    kod1 varchar(5),
    uzel1 varchar(25),
    pr1 varchar(1),
    kod2 varchar(5),
    uzel2 varchar(25),
    pr2 varchar(1),
    standard varchar(40),
    kod_truba int,
    truba int,
    diametr float,
    tol float,
    diametr_usl float,
    dlina float,
    scher float,
    mestnoe float,
    dolja float,
    kodkvp varchar(5),
    kodkvo varchar(5),
    sopr float,
    name_calctpr varchar(1),
    name_typ varchar(1),
    kog_canal int,
    chanwidth float,
    chanheight float,
    kti float,
    kolwork int,
    kod_izol int,
    thickizol float,
    k_izol float,
    depth float,
    izoloutair float,
    izol_air float,
    air_ground float,
    tpground float,
    distance float,
    opc varchar(50),
    kod_owner int,
    dolya_owner1 float,
    kod_owner2 int,
    dolya_owner2 float,
    kod_owner3 int,
    dolya_owner3 float,
    kod_owner4 int,
    dolya_owner4 float,
    kod_owner5 int,
    dolya_owner5 float,
    registr varchar(50),
    kol_pereklad int,
    dateend date,
    dateend_izol date,
    datenew date,
    datenew_kapital date,
    dateend_kapital date,
    datenew_repair date,
    dateend_repair date,
    podp varchar(1),
    archives varchar(5),
    date_archives date,
    oper_archives varchar(16),
    operator varchar(50),
    coord text,
    f_kol_let float,
    f_koef_povr float,
    f_koef_povr_2goda float,
    f_10_elektro float,
    f_5_elektro float,
    f_3_elektro float,
    f_1_elektro float,
    f_0_elektro float,
    f_peres_elektro float,
    f_10_gas float,
    f_5_gas float,
    f_3_gas float,
    f_1_gas float,
    f_0_gas float,
    f_peres_gas float,
    f_10_transp float,
    f_5_transp float,
    f_3_transp float,
    f_1_transp float,
    f_0_transp float,
    f_peres_transp float,
    f_elektropotenz varchar(1),
    f_nar_korroz varchar(1),
    f_vnu_korroz varchar(1),
    f_grund_water varchar(1),
    f_pavod_water varchar(1),
    f_vod_water varchar(1),
    f_fek_water varchar(1),
    f_st_stik int,
    f_st_islom int,
    f_st_otkl int,
    f_st_nes int,
    f_st_opor int,
    f_water_otved varchar(50),
    f_otkl varchar(50),
    f_okl_pot varchar(50),
    f_slog_arbeit varchar(50),
    f_tratuar varchar(50),
    f_doroga varchar(50),
    f_ucherb_narod varchar(50),
    f_ucherb_gorod varchar(50),
    pr_videlen int,
    date_isp_gid date,
    g_isp_gid float,
    dp_isp_gid float,
    date_isp_tep date,
    tn_isp_tep float,
    tg_isp_tep float,
    g1_isp_tep float,
    g2_isp_tep float,
    dt1_isp_tep float,
    dt2_isp_tep float,
    t1_isp_tep float,
    t2_isp_tep float,
    diametr_vneshniy int,                     -- Диаметр внешний
    harakteristika_truby varchar(4),          -- Характеристика трубы
    tip_truby varchar(1),                     -- Тип трубы
    material_truby varchar(50),               -- Материал трубы
    maksimalno_dopustimaya_temperatura int,   -- Максимально допустимая температура
    zavod_izgotovitel varchar(255),           -- Завод изготовитель
    material_naruzhnogo_pokrytiya varchar(4), -- Материал наружного покрытия
    tip_izolyatsii varchar(1),                -- Тип изоляции
    tolschina_naruzhnogo_pokrytiya__mm float, -- Толщина наружного покрытия, мм
    material_antikorroziynogo_pokrytiya varchar(80),  -- Материал антикоррозийного покрытия
    uchastok_ms int,                          -- Участок МС
    uchastok_rs int,                          -- Участок РС
    rayon_ekspluatatsii int,                  -- Район эксплуатации
    "set" varchar(5),                         -- Сеть
    magistral int,                            -- Магистраль
    uchastok_ekspluatatsii int,               -- Участок эксплуатации
    vid_seti int                              -- Вид сети
);
---------------------------------
-- klapany__ventili__zapornye - Другие
-- klapany__ventili__zapornye - klapany__ventili__zapornye
drop table if exists klapany__ventili__zapornye;

create table klapany__ventili__zapornye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie varchar(255),
    oboznachenie_chertezh_ varchar(255),
    dn_mm int,
    pn_kgs_sm2 int,
    material_korpusa varchar(255),
    rabochaya_sreda varchar(255),
    tip_prisoedineniya varchar(255),
    tsena__rub varchar(255) 
);
---------------------------------
-- konstruktsiya_pokrovnogo_sloya_izolyatsii - Другие
-- konstruktsiya_pokrovnogo_sloya_izolyatsii - Конструкция покровного слоя изоляции
drop table if exists konstruktsiya_pokrovnogo_sloya_izolyatsii;

create table konstruktsiya_pokrovnogo_sloya_izolyatsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- kontrol_tehnicheskogo_sostoyaniya_dokumenty - Другие
-- kontrol_tehnicheskogo_sostoyaniya_dokumenty - Контроль технического состояния_документы
drop table if exists kontrol_tehnicheskogo_sostoyaniya_dokumenty;

create table kontrol_tehnicheskogo_sostoyaniya_dokumenty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id2 int,
    naimenovanie_dokumenta varchar(255),      -- Наименование документа
    data date,                                -- Дата
    dokument text                             -- Документ
);
---------------------------------
-- kotelnye - Другие
-- kotelnye - kotelnye
drop table if exists kotelnye;

create table kotelnye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod int,                                  -- Код
    kod_istochnika varchar(5),                -- Код источника
    naimenovanie varchar(50),                 -- Наименование
    ustanovlennaya_moschnost float,           -- Установленная мощность
    raspologaemaya_moschnost float,           -- Распологаемая мощность
    otoplenie_istochnik float,                -- Отопление источник
    ventilyatsiya_istochnik float,            -- Вентиляция источник
    gvs_istochnik float,                      -- Гвс источник
    normativnye_teplovye_poteri float,        -- Нормативные тепловые потери
    god int                                   -- Год
);
---------------------------------
-- link_elist_diz - Другие
-- link_elist_diz - link_elist_diz
drop table if exists link_elist_diz;

create table link_elist_diz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- link_elist_grpod - Другие
-- link_elist_grpod - link_elist_grpod
drop table if exists link_elist_grpod;

create table link_elist_grpod (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- link_elist_trans - Другие
-- link_elist_trans - link_elist_trans
drop table if exists link_elist_trans;

create table link_elist_trans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    activityID int 
);
---------------------------------
-- list_opres_node1 - Другие
-- list_opres_node1 - list_opres_node1
drop table if exists list_opres_node1;

create table list_opres_node1 (
    nodeID int default (NULL),
    objID int default (NULL) 
);
CREATE INDEX list_opres_node1_nodeid_idx ON list_opres_node1 (nodeid);
---------------------------------
-- list_opres_node2 - Другие
-- list_opres_node2 - list_opres_node2
drop table if exists list_opres_node2;

create table list_opres_node2 (
    nodeID int default (NULL),
    objID int default (NULL) 
);
CREATE INDEX list_opres_node2_nodeid_idx ON list_opres_node2 (nodeid);
---------------------------------
-- listptstables - Другие
-- listptstables - listptstables
drop table if exists listptstables;

create table listptstables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(200) not null,
    rus_name varchar(200) not null 
);
---------------------------------
-- localhydroresistances - Другие
-- localhydroresistances - SM_Местные гидравлические сопротивления
drop table if exists localhydroresistances;

create table localhydroresistances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Elem varchar(50) default (NULL),
    S_min float default ((0)),
    S_max float default ((0)) 
);
---------------------------------
-- lookup1 - Другие
-- lookup1 - lookup1
drop table if exists lookup1;

create table lookup1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- lookup2 - Другие
-- lookup2 - lookup2
drop table if exists lookup2;

create table lookup2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- lookup3 - Другие
-- lookup3 - lookup3
drop table if exists lookup3;

create table lookup3 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- lookup4 - Другие
-- lookup4 - lookup4
drop table if exists lookup4;

create table lookup4 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- lookup5 - Другие
-- lookup5 - lookup5
drop table if exists lookup5;

create table lookup5 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- lookup6 - Другие
-- lookup6 - lookup6
drop table if exists lookup6;

create table lookup6 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(80) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- losesbyfilling - Другие
-- losesbyfilling - losesbyfilling
drop table if exists losesbyfilling;

create table losesbyfilling (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int default (NULL),
    monthID int default (NULL),
    magistralShare float default (NULL),
    distSiteShare float default (NULL),
    heatingSystemShare float default (NULL),
    netTemperature float default (NULL),
    rechargeTemperature float default (NULL),
    magistralQ float default (NULL),
    distSiteQ float default (NULL),
    heatingSystemQ float default (NULL),
    magistralOneTimeFilling float default (NULL),
    distSiteOneTimeFilling float default (NULL),
    heatingSystemFilling float default (NULL) 
);
---------------------------------
-- losesbyfillingfact - Другие
-- losesbyfillingfact - losesbyfillingfact
drop table if exists losesbyfillingfact;

create table losesbyfillingfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int default (NULL),
    monthID int default (NULL),
    magistralShare float default (NULL),
    distSiteShare float default (NULL),
    heatingSystemShare float default (NULL),
    netTemperature float default (NULL),
    rechargeTemperature float default (NULL),
    magistralQ float default (NULL),
    distSiteQ float default (NULL),
    heatingSystemQ float default (NULL),
    magistralOneTimeFilling float default (NULL),
    distSiteOneTimeFilling float default (NULL),
    heatingSystemFilling float default (NULL) 
);
---------------------------------
-- magistrals - Другие
-- magistrals - magistrals
drop table if exists magistrals;

create table magistrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number varchar(50) default (NULL),
    name varchar(50) default (NULL),
    tgidMagistral varchar(255) default (NULL),
    admDistrictID int default (NULL),
    heatSourceID int default (NULL),
    inventNumber varchar(50) default (NULL),
    inventNumberBindDate date default (NULL),
    inventNumberOld varchar(50) default (NULL),
    inventNumberOldBindDate date default (NULL),
    cadastralNumber varchar(50) default (NULL),
    description varchar(255) default (NULL),
    heatSourceCircuit int default (NULL) 
);
---------------------------------
-- material_kamery_opuska_i_pavilonov_setey_teplosnabzh - Другие
-- material_kamery_opuska_i_pavilonov_setey_teplosnabzh - Материал камеры опуска и павильонов сетей теплоснабж
drop table if exists material_kamery_opuska_i_pavilonov_setey_teplosnabzh;

create table material_kamery_opuska_i_pavilonov_setey_teplosnabzh (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- material_teploizolyatsionnyy - Другие
-- material_teploizolyatsionnyy - Материал теплоизоляционный
drop table if exists material_teploizolyatsionnyy;

create table material_teploizolyatsionnyy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    material varchar(255),                    -- Материал
    marka varchar(255),                       -- Марка
    konstruktsiya varchar(255),               -- Конструкция
    gost varchar(255),                        -- ГОСТ
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- materialcharacteristics - Другие
-- materialcharacteristics - materialcharacteristics
drop table if exists materialcharacteristics;

create table materialcharacteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    diameterExternal float,
    diameterInternal float,
    lenP_N float,
    lenO_N float,
    lenPodzP float,
    lenPodzO float,
    lenAll float,
    len_tr float,
    MN_P float,
    MN_O float,
    MP_P float,
    MP_O float,
    M float,
    VV float,
    typnet1 varchar 
);
---------------------------------
-- materialcharacteristicsfact - Другие
-- materialcharacteristicsfact - Материальные характеристики фактические
drop table if exists materialcharacteristicsfact;

create table materialcharacteristicsfact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatSourceID int,
    diameterExternal float,
    diameterInternal float,
    lenP_N float,
    lenO_N float,
    lenPodzP float,
    lenPodzO float,
    lenAll float,
    len_tr float,
    MN_P float,
    MN_O float,
    MP_P float,
    MP_O float,
    M float,
    VV float,
    typnet1 varchar 
);
---------------------------------
-- mikrorayony - Другие
-- mikrorayony - Микрорайоны
drop table if exists mikrorayony;

create table mikrorayony (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    name varchar(255)                         -- Name
);
---------------------------------
-- months - Другие
-- months - months
drop table if exists months;

create table months (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(15) 
);
---------------------------------
-- nagruzki_po_elevatoram - Другие
-- nagruzki_po_elevatoram - nagruzki_po_elevatoram
drop table if exists nagruzki_po_elevatoram;

create table nagruzki_po_elevatoram (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    kod varchar(255),
    uzel varchar(255),
    private int,
    q float,                                  -- Q
    qot float,                                -- Qot
    qgvs float,                               -- Qgvs
    qvent float,                              -- Qvent
    qpar float                                -- Qpar
);
---------------------------------
-- namechennye_meropriyatiya_po_elementam - Другие
-- namechennye_meropriyatiya_po_elementam - Намеченные мероприятия по элементам
drop table if exists namechennye_meropriyatiya_po_elementam;

create table namechennye_meropriyatiya_po_elementam (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii - Другие
-- namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii - Намеченные мероприятия по изоляционной конструкции
drop table if exists namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii;

create table namechennye_meropriyatiya_po_izolyatsionnoy_konstruktsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- namechennye_meropriyatiya_po_kanalu - Другие
-- namechennye_meropriyatiya_po_kanalu - Намеченные мероприятия по каналу
drop table if exists namechennye_meropriyatiya_po_kanalu;

create table namechennye_meropriyatiya_po_kanalu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- namechennye_meropriyatiya_po_teploprovodu - Другие
-- namechennye_meropriyatiya_po_teploprovodu - Намеченные мероприятия по теплопроводу
drop table if exists namechennye_meropriyatiya_po_teploprovodu;

create table namechennye_meropriyatiya_po_teploprovodu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- naznachenie_zapornoy_armatury_setey_teplosnabzheniya - Другие
-- naznachenie_zapornoy_armatury_setey_teplosnabzheniya - Назначение запорной арматуры сетей теплоснабжения
drop table if exists naznachenie_zapornoy_armatury_setey_teplosnabzheniya;

create table naznachenie_zapornoy_armatury_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- normtemperaturesgraphs - Другие
-- normtemperaturesgraphs - normtemperaturesgraphs
drop table if exists normtemperaturesgraphs;

create table normtemperaturesgraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hSourceID int not null,
    year varchar(50) default (NULL),          -- Календарный год
    name varchar(50) default (NULL),          -- Наим.температурного графика
    graphTypeID int not null,
    tn_1 float not null,                      -- Температура наружн.воздуха начала/конца отоп. Сезона, °C
    tn_5 float not null,                      -- Расчетная темп.наружн.воздуха для отопления, °C
    tvn_r float not null,                     -- Расчетная темп. воздуха внутри отапл.помещений, °C
    t1_r float not null,                      -- Расчетная температура сет.воды в под.теплопр., °C
    t2_r float not null,                      -- Расчетная температура сет.воды в обр.теплопр., °C
    t3_r float not null,                      -- Расчетная температура сет.воды после узла смешения, °C
    q_r float not null,                       -- Расчетная нагрузка на отопление, Гкал/ч
    t1_2r float not null,                     -- Температура воды нижней срезки графика, °C
    t1_4r float not null,                     -- Температура воды верхней срезки графика, °C
    tvb_tr float not null,                    -- Требуемая температура воздуха внутри отапл.помещений, °C
    uf float not null,                        -- Фактический коэфф.смещения
    t2_2r float not null,                     -- Температура воды нижней срезки обрат.воды
    q_gv float not null,                      -- Расчетная нагрузка в ГВС, Гкал/ч
    tg_r float not null,                      -- Темпер.горячей воды в точках водоразбора, °C
    tx_r float not null,                      -- Темпер.холодной воды, °C
    t2_gv float not null,                     -- Темпер.воды в обратном трубопр.для переключения водоразбора, °C
    pr float not null,                        -- Признак способа водоразбора горячей воды
    g1 float not null,                        -- Коэфф.гидравл.устойчивости под.теплопровода
    g2 float not null,                        -- Коэфф.гидравл.устойчивости обр.теплопровода
    t_gv1 float not null,                     -- Величина недогрева в первой ступени подогр. ГВС, °C
    deployedTempGraphID int default (NULL),
    v float not null,                         -- Скорость ветра, м/c
    date_on timestamp not null,               -- Дата иcполнения
    name_exe varchar(50) default (NULL),      -- Исполнитель
    name_manager varchar(50) default (NULL),
    dt2_co float not null,                    -- Разность обрат.воды при зав.СО и нез., °C
    t2pod_parl float not null,                -- Темп.на вых.подогр.паралл.ГВ, т.излома, °C
    dt2v_sm_noavm float not null,             -- Недогрев водопр.воды в 1ступ.,смеш.ГВ, част.авт.ТП, °C
    dt2v_sm_avm float not null,               -- Недогрев водопр.воды в 1ступ.,смеш.ГВ, авт.ТП, °C
    t1pod_sm float not null,                  -- Темп.на вых.СО,смеш.ГВ, т.излома, °C
    t1pod_posll float not null,               -- Темп.на вых.СО,послед.ГВ, т.излома, °C
    dt2v_posl float not null                  -- Недогрев водопр.воды в 1ступ.,посл.ГВ, °C
);
---------------------------------
-- obekty - Другие
-- obekty - obekty
drop table if exists obekty;

create table obekty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod int,                                  -- Код
    zhiloy_dom int,                           -- Жилой дом
    adres_kod int                             -- Адрес_Код
);
---------------------------------
-- object_types - Другие
-- object_types - object_types
drop table if exists object_types;

create table object_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- objekt_opressovochnogo_nasosa - Другие
-- objekt_opressovochnogo_nasosa - objekt_opressovochnogo_nasosa
drop table if exists objekt_opressovochnogo_nasosa;

create table objekt_opressovochnogo_nasosa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(100) not null,
    ord int 
);
---------------------------------
-- ochered_opressovok - Другие
-- ochered_opressovok - Очередь опрессовок
drop table if exists ochered_opressovok;

create table ochered_opressovok (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer_ocheredi_opressovki varchar(255),   -- Номер очереди опрессовки
    sostoyanie varchar(255),                  -- Состояние
    obekt varchar(255),                       -- Объект
    planiruemaya_data_provedeniya__nachalo date,  -- Планируемая дата проведения, начало
    planiruemaya_data_provedeniya__okonchanie date,   -- Планируемая дата проведения, окончание
    data_provedeniya date,                    -- Дата проведения
    istochnik_tepla varchar(255),             -- Источник тепла
    probnoe_davleniem__maksimalnoe___mpa float,   -- Пробное давлением (максимальное), МПа
    kod_raschetnoy_shemy_nasosnoy_stantsii varchar(255),  -- Код расчетной схемы насосной станции
    naimenovanie_nasosnoy_stantsii varchar(255),  -- Наименование насосной станции
    ispolzovanie_avtonomnyh_nasosov__kompressorov int,    -- Использование автономных насосов, компрессоров
    tsvet int,                                -- Цвет
    organizatsiya_zakazchika varchar(255),    -- Организация Заказчика
    predstavitel_zakazchika_dolzhnost varchar(255),   -- Представитель Заказчика должность
    predstavitel_zakazchika_fio varchar(255), -- Представитель Заказчика ФИО
    organizatsiya_podryadchika varchar(255),  -- Организация Подрядчика
    predstavitel_podryadchika_dolzhnost varchar(255), -- Представитель Подрядчика должность
    predstavitel_podryadchika_fio varchar(255),   -- Представитель Подрядчика ФИО
    organizatsiya_predstavitelya_oets varchar(255),   -- Организация представителя ОЭТС
    predstavitel_oets_dolzhnost varchar(255), -- Представитель ОЭТС должность
    predstavitel_oets_fio varchar(255),       -- Представитель ОЭТС ФИО
    prodolzhitelnost_ispytaniya__min float,   -- Продолжительность испытания, мин
    razdelnoe_ispytanie_podayuschego_truboprovoda int,    -- Раздельное испытание подающего трубопровода
    razdelnoe_ispytanie_obratnogo_truboprovoda int    -- Раздельное испытание обратного трубопровода
);
---------------------------------
-- operators - Другие
-- operators - operators
drop table if exists operators;

create table operators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- oporatypes - Другие
-- oporatypes - oporatypes
drop table if exists oporatypes;

create table oporatypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- opressovka_meropriyatiya - Другие
-- opressovka_meropriyatiya - Опрессовка_мероприятия
drop table if exists opressovka_meropriyatiya;

create table opressovka_meropriyatiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id2 int,
    povrezhdeniya int,                        -- Повреждения
    meropriyatie int,                         -- Мероприятие
    plan_2 int 
);
---------------------------------
-- opressovka_meropriyatiya_po_ustraneniyu_povrezhdeniy - Другие
-- opressovka_meropriyatiya_po_ustraneniyu_povrezhdeniy - Опрессовка_мероприятия по устранению повреждений
drop table if exists opressovka_meropriyatiya_po_ustraneniyu_povrezhdeniy;

create table opressovka_meropriyatiya_po_ustraneniyu_povrezhdeniy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- opressovka_otvetstvennye - Другие
-- opressovka_otvetstvennye - Опрессовка ответственные
drop table if exists opressovka_otvetstvennye;

create table opressovka_otvetstvennye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deystivie varchar(255),                   -- Дейстивие
    dolzhnost varchar(255),                   -- Должность
    fio varchar(255),                         -- ФИО
    data_oznakomleniya date,                  -- Дата ознакомления
    data_utverzhdeniya date,                  -- Дата утверждения
    nomer_ocheredi_opressovki varchar(255)    -- Номер очереди опрессовки
);
---------------------------------
-- opressovka_povrezhdeniya - Другие
-- opressovka_povrezhdeniya - Опрессовка_повреждения
drop table if exists opressovka_povrezhdeniya;

create table opressovka_povrezhdeniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- opressovki_uchastok_ocheredi - Другие
-- opressovki_uchastok_ocheredi - Опрессовки участок очереди
drop table if exists opressovki_uchastok_ocheredi;

create table opressovki_uchastok_ocheredi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomer_ocheredi_opressovki int,            -- Номер очереди опрессовки
    naimenovanie varchar(255),                -- Наименование
    magistral_raspredset varchar(255),        -- Магистраль/Распредсеть
    kod_raschetnoy_shemy_nachalnoy_kamery varchar(255),   -- Код расчетной схемы начальной камеры
    naimenovanie_nachalnoy_kamery varchar(255),   -- Наименование начальной камеры
    kod_raschetnoy_shemy_konechnoy_kamery varchar(255),   -- Код расчетной схемы конечной камеры
    naimenovanie_konechnoy_kamery varchar(255),   -- Наименование конечной камеры
    nomer_nachalnoy_zadvizhki varchar(255),   -- Номер начальной задвижки
    nomer_konechnoy_zadvizhki varchar(255),   -- Номер конечной задвижки
    ulitsa int,                               -- Улица
    nomer_doma varchar(255),                  -- Номер дома
    diametr_uslovnyy__mm float,               -- Диаметр условный, мм
    obschaya_protyazhennost__m float,         -- Общая протяженность, м
    vid_prokladki varchar(1),                 -- Вид прокладки
    istochnik_tepla int,                      -- Источник тепла
    magistral int,                            -- Магистраль
    prodolzhitelnost_ispytaniya__min int,     -- Продолжительность испытания, мин
    davlenie_opressovki__mpa float,           -- Давление опрессовки, МПа
    nomer_proekta varchar(255),               -- Номер проекта
    dokumenty_registratsii varchar(255),      -- Документы регистрации
    uspeshnost_zaversheniya varchar(255),     -- Успешность завершения
    shema_privyazki text,                     -- Схема привязки
    data_sozdaniya_akta__opressovki date,     -- Дата создания акта опрессовки
    akt_opressovki text,                      -- Акт опрессовки
    nomer_akta_opressovki varchar(255),       -- Номер Акта опрессовки
    data_vydachi_akta_opressovki date         -- Дата выдачи Акта опрессовки
);
---------------------------------
-- organizatsii - Другие
-- organizatsii - organizatsii
drop table if exists organizatsii;

create table organizatsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    nomer_dogovora varchar(255),              -- Номер договора
    naimenovanie_obekta varchar(255),         -- Наименование объекта
    adres_obekta varchar(80),                 -- Адрес объекта
    naznachenie_obekta varchar(30),           -- Назначение объекта
    naimenovanie_kontragenta varchar(255),    -- Наименование контрагента
    ploschad float,                           -- Площадь
    nagruzka__otoplenie_ float,               -- Нагрузка 'Отопление'
    etazhnost int,                            -- Этажность
    srednyaya_nagruzka__otoplenie_ float,     -- Средняя нагрузка 'Отопление'
    nagruzka__ventilyatsiya_ float,           -- Нагрузка 'Вентиляция'
    srednyaya_nagruzka__ventilyatsiya_ float, -- Средняя нагрузка 'Вентиляция'
    nagruzka__gvs_ float,                     -- Нагрузка 'ГВС'
    srednyaya_nagruzka__gvs_ float,           -- Средняя нагрузка 'ГВС'
    nagruzka__par_ float,                     -- Нагрузка 'Пар'
    srednyaya_nagruzka__par_ float,           -- Средняя нагрузка 'Пар'
    nomer_a__pribora_ucheta varchar(255),     -- Номер(а) прибора учета
    ekspluatatsionnyy_rayon_po_obektu varchar(255),   -- Эксплуатационный район по объекту
    ekspluatatsionnyy_uchastok_po_obektu varchar(255),    -- Эксплуатационный участок по объекту
    administrativnyy_rayon_po_obektu varchar(255),    -- Административный район по объекту
    istochnik_tepla varchar(255),             -- Источник тепла
    zdanie int,                               -- Здание
    kod1 varchar(10),
    uzel1 varchar(25),
    protsent_nagruzki_1 float,                -- Процент нагрузки 1
    kod2 varchar(10),
    uzel2 varchar(25),
    protsent_nagruzki_2 float,                -- Процент нагрузки 2
    kod3 varchar(10),
    uzel3 varchar(25),
    protsent_nagruzki_3 float,                -- Процент нагрузки 3
    kod4 varchar(10),
    uzel4 varchar(25),
    protsent_nagruzki_4 float,                -- Процент нагрузки 4
    kod5 varchar(10),
    uzel5 varchar(25),
    protsent_nagruzki_5 float                 -- Процент нагрузки 5
);
---------------------------------
-- organizatsii_vladeltsy - Другие
-- organizatsii_vladeltsy - Организации владельцы
drop table if exists organizatsii_vladeltsy;

create table organizatsii_vladeltsy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie varchar(255),                -- Наименование
    priznak_organizatsii varchar(2),          -- Признак организации
    telefon_organizatsii varchar(50),         -- Телефон организации
    telefon_rukovoditelya varchar(50),        -- Телефон руководителя
    ulitsa varchar(50),                       -- Улица
    nomer_doma varchar(50)                    -- Номер дома
);
---------------------------------
-- osmotr_sostoyanie - Другие
-- osmotr_sostoyanie - osmotr_sostoyanie
drop table if exists osmotr_sostoyanie;

create table osmotr_sostoyanie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) not null,
    ord int 
);
---------------------------------
-- osmotrdeployed - Другие
-- osmotrdeployed - osmotrdeployed
drop table if exists osmotrdeployed;

create table osmotrdeployed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    directionID int,
    lineID int 
);
CREATE INDEX osmotrdeployed_lineid_idx ON osmotrdeployed (lineid);
---------------------------------
-- otsenka_korroziynogo_protsessa - Другие
-- otsenka_korroziynogo_protsessa - Оценка коррозийного процесса
drop table if exists otsenka_korroziynogo_protsessa;

create table otsenka_korroziynogo_protsessa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    srednyaya_skorost_korrozii float,         -- Средняя скорость коррозии
    otsenka_korroziynogo_protsessa int        -- Оценка коррозийного процесса
);
---------------------------------
-- ownerorganizationtypes - Другие
-- ownerorganizationtypes - ownerorganizationtypes
drop table if exists ownerorganizationtypes;

create table ownerorganizationtypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- owners - Другие
-- owners - owners
drop table if exists owners;

create table owners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- pasport_uchastka_ms - Другие
-- pasport_uchastka_ms - Паспорт участка МС
drop table if exists pasport_uchastka_ms;

create table pasport_uchastka_ms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id2 int,
    naimenovanie_dokumenta varchar(255),      -- Наименование документа
    data date,                                -- Дата
    dokument text                             -- Документ
);
---------------------------------
-- pasport_uchastka_rs - Другие
-- pasport_uchastka_rs - Паспорт участка РС
drop table if exists pasport_uchastka_rs;

create table pasport_uchastka_rs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id2 int,
    naimenovanie_dokumenta varchar(255),      -- Наименование документа
    data date,                                -- Дата
    dokument text                             -- Документ
);
---------------------------------
-- passportsdocs - Другие
-- passportsdocs - passportsdocs
drop table if exists passportsdocs;

create table passportsdocs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passportID int not null,
    docTypeID int not null,
    createdDate timestamp not null,
    document varchar not null 
);
---------------------------------
-- password - Другие
-- password - password
drop table if exists password;

create table password (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    "user" varchar(50),
    password varchar(50),
    "right" int 
);
---------------------------------
-- perspektivnye_truby - Другие
-- perspektivnye_truby - perspektivnye_truby
drop table if exists perspektivnye_truby;

create table perspektivnye_truby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    sostoyanie_stroitelstva varchar(1),       -- Состояние строительства
    nachalnaya_kamera varchar(255),           -- Начальная камера
    konechnaya_kamera varchar(255),           -- Конечная камера
    nomer_tu varchar(50),                     -- Номер ТУ
    data_vydachi_tu date,                     -- Дата выдачи ТУ
    sostoyanie_dogovora varchar(1),           -- Состояние договора
    naimenovanie_organizatsii__zaprashivayuschey_tu varchar(255), -- Наименование организации, запрашивающей ТУ
    naimenovanie_obekta varchar(255),         -- Наименование объекта
    rayon_ekspluatatsii varchar(255),         -- Район эксплуатации
    istochnik varchar(255),                   -- Источник
    dlina float,                              -- Длина, м
    diametr_uslovnyy float,                   -- Диаметр условный, мм
    diametr_vnutrenniy float,                 -- Диаметр внутренний, мм
    tolschina_stenki float,                   -- Толщина стенки, мм
    tip_truby varchar(1),                     -- Тип трубы
    vid_prokladki varchar(1),                 -- Вид прокладки
    harakteristika_truby varchar(1)           -- Характеристика трубы
);
---------------------------------
-- plan_remont - Другие
-- plan_remont - plan_remont
drop table if exists plan_remont;

create table plan_remont (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    DateRaschet timestamp default (now()),
    DatePosKapitalRemont int default (NULL),
    DatePoslOsvidetel int default (NULL),
    SrokEkspluatii float default (NULL),
    KolKapitalRemont int default ((0)),
    KolNarusenii int default (NULL),
    KoeffPovrezhd int default (NULL),
    KoeffPovrezhD_2goda int default (NULL),
    Elektrich int default (NULL),
    TransportElekricht int default (NULL),
    Ponezial int default (NULL),
    VnesnKorroz int default (NULL),
    VnutrKorroz int default (NULL),
    PottoplGrunt int default (NULL),
    PottoplPavodok int default (NULL),
    PottoplVodoprovod int default (NULL),
    PottoplFekal int default (NULL),
    StroiKonstrukz int default (NULL),
    Vodootved int default (NULL),
    SlozhOkluzh int default (NULL),
    OtkluzhGkal float default (NULL),
    AvariiVipoln int default (NULL),
    Pesehod int default (NULL),
    ZhdDorogi int default (NULL),
    LudiProklad int default (NULL),
    UzherbLudi int default (NULL),
    UzherbSity int default (NULL) 
);
---------------------------------
-- plity_perekrytiya_teplovyh_kamer - Другие
-- plity_perekrytiya_teplovyh_kamer - Плиты перекрытия тепловых камер
drop table if exists plity_perekrytiya_teplovyh_kamer;

create table plity_perekrytiya_teplovyh_kamer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    konstruktsiya_perekrytiya varchar(255),   -- Конструкция перекрытия
    dlina__mm int,                            -- Длина, мм
    shirina__mm int,                          -- Ширина, мм
    vysota__mm int,                           -- Высота, мм
    material varchar(255),                    -- Материал
    massa varchar(30),                        -- Масса
    oboznachenie varchar(255),                -- Обозначение
    primechanie varchar(255),                 -- Примечание
    shema varchar(255)                        -- Схема
);
---------------------------------
-- pribor - Другие
-- pribor - Прибор
drop table if exists pribor;

create table pribor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tip varchar(255),                         -- Тип
    data_gosprverki date                      -- Дата госпрверки
);
---------------------------------
-- prisoedinennaya_nagruzka_istochnikov - Другие
-- prisoedinennaya_nagruzka_istochnikov - prisoedinennaya_nagruzka_istochnikov
drop table if exists prisoedinennaya_nagruzka_istochnikov;

create table prisoedinennaya_nagruzka_istochnikov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    god int,                                  -- Год
    raspolagaemaya_moschnost_ov float,        -- Располагаемая мощность ОВ
    raspolagaemaya_moschnost_gvs_srednyaya float, -- Располагаемая мощность ГВС средняя
    raspolagaemaya_moschnost_summarnaya float,    -- Располагаемая мощность суммарная
    normativnye_teplovye_poteri float,        -- Нормативные тепловые потери
    prisoedinennaya_moschnost_otoplenie_1 float,  -- Располагаемая мощность отопление 1
    prisoedinennaya_moschnost_ventilyatsiya_1 float,  -- Располагаемая мощность вентиляция 1
    prisoedinennaya_moschnost_gvs_maksimalnaya_1 float,   -- Располагаемая мощность ГВС максимальная 1
    prisoedinennaya_moschnost_par_1 float,    -- Располагаемая мощность Пар 1
    prisoedinennaya_moschnost_otoplenie float,    -- Присоединенная мощность отопление
    prisoedinennaya_moschnost_ventilyatsiya float,    -- Присоединенная мощность вентиляция
    prisoedinennaya_moschnost_gvs_maksimalnaya float, -- Присоединенная мощность ГВС максимальная
    prisoedinennaya_moschnost_par float       -- Присоединенная мощность Пар
);
---------------------------------
-- qualityregtempgraphs - Другие
-- qualityregtempgraphs - qualityregtempgraphs
drop table if exists qualityregtempgraphs;

create table qualityregtempgraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hSourceID int not null,
    name varchar(50) default (NULL),          -- Наименование графика
    tip varchar(50) default (NULL),           -- Тип графика
    tvn_r float default ((0)),                -- Расчетная температура воздуха внутри отапливаемых помещений, °C
    t1_r float default ((0)),                 -- Расчетная температура воды в подающем трубопроводе, °C
    t2_r float default ((0)),                 -- Расчетная температура воды в обратном трубопроводе, °C
    t3_r float default ((0)),                 -- Расчетная температура воды после узла смешения, °C
    q_r float default ((0)),                  -- Расчетная тепловая нагрузка на отопление, Гкал/ч
    tvb_tr float default ((0)),               -- Требуемая температура воздуха внутри отапливаемых помещений, °C
    uf float default ((0)),                   -- Фактический коэффициент смешения
    q_gv float default ((0)),                 -- Расчетная тепловая нагрузка на ГВС, Гкал/ч
    tg_r float default ((60)) not null,       -- Температура горячей воды в местах водоразбора, °C
    tx_r float default ((0)),                 -- Температура холодной подпиточной воды, °C
    pr float default ((0)),                   -- Признак способа водоразбора горячей воды
    t2_gv float default ((60)) not null,      -- Температура воды в обратном теплопровода для переключения водоразбора, °C
    g1 float default ((0)),                   -- Коэффициент гидравлической устойчивости подающего теплопровода
    g2 float default ((0)),                   -- Коэффициент гидравлической устойчивости обратного теплопровода
    t_gv1 float default ((0)),                -- Величина недогрева в первой ступени подогревателя, °C
    deployedTempGraphID int default ((0)),
    dt2_co float default ((10)) not null,
    t2pod_parl float default ((30)) not null,
    dt2v_sm_noavm float default ((5)) not null,
    dt2v_sm_avm float default ((10)) not null,
    t1pod_posll float default ((41.7)) not null,
    dt2v_posl float default ((5)) not null 
);
---------------------------------
-- rabotniki - Другие
-- rabotniki - Работники
drop table if exists rabotniki;

create table rabotniki (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fio varchar(255),                         -- ФИО
    dolzhnost int,                            -- Должность
    udostoverenie varchar(255)                -- Удостоверение
);
---------------------------------
-- raspredseti - Другие
-- raspredseti - Распредсети
drop table if exists raspredseti;

create table raspredseti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod_rs varchar(5),                        -- Код РС
    naimenovanie varchar(255),                -- Наименование
    uchastok_ekspluatatsii int,               -- Участок эксплуатации
    inventarnyy_nomer varchar(10),            -- Инвентарный номер
    nomer_kvartala varchar(255),              -- Номер квартала
    data_prisvoeniya_inventarnogo_nomera date,    -- Дата присвоения инвентарного номера
    opisanie varchar(255),                    -- Описание
    istochnik_tepla int,                      -- Источник тепла
    magistral int                             -- Магистраль
);
---------------------------------
-- regulatortypes - Другие
-- regulatortypes - regulatortypes
drop table if exists regulatortypes;

create table regulatortypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- remont_izolyatsionnoy_konstruktsii - Другие
-- remont_izolyatsionnoy_konstruktsii - Ремонт изоляционной конструкции
drop table if exists remont_izolyatsionnoy_konstruktsii;

create table remont_izolyatsionnoy_konstruktsii (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- remont_po_vosstanovleniyu_kanala - Другие
-- remont_po_vosstanovleniyu_kanala - Ремонт по восстановлению канала
drop table if exists remont_po_vosstanovleniyu_kanala;

create table remont_po_vosstanovleniyu_kanala (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- remont2deployed - Другие
-- remont2deployed - remont2deployed
drop table if exists remont2deployed;

create table remont2deployed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    directionID int,
    lineID int 
);
CREATE INDEX remont2deployed_lineid_idx ON remont2deployed (lineid);
---------------------------------
-- remontkanalkameraspisok - Другие
-- remontkanalkameraspisok - remontkanalkameraspisok
drop table if exists remontkanalkameraspisok;

create table remontkanalkameraspisok (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar not null,
    ord int not null 
);
---------------------------------
-- serviceorganizations - Другие
-- serviceorganizations - serviceorganizations
drop table if exists serviceorganizations;

create table serviceorganizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255) default (NULL),
    responsible varchar(255) default (NULL),
    responsiblePhone varchar(255) default (NULL) 
);
---------------------------------
-- shurf_elementy - Другие
-- shurf_elementy - Шурф_Элементы
drop table if exists shurf_elementy;

create table shurf_elementy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defekt int,                               -- Повреждение
    element int,                              -- Элемент
    osmotreno_na_podache float,               -- Осмотрено на подаче
    povrezhdeno_na_podache float,             -- Повреждено на подаче
    meropriyatie_na_podache varchar(255),     -- Мероприятие на подаче
    zaplanirovano_na_podache float,           -- Запланировано на подаче
    ispravleno_na_podache float,              -- Исправлено на подаче
    osmotreno_na_obratke float,               -- Осмотрено на обратке
    povrezhdeno_na_obratke float,             -- Повреждено на обратке
    meropriyatie_na_obratke varchar(255),     -- Мероприятие на обратке
    zaplanirovano_na_obratke float,           -- Запланировано на обратке
    ispravleno_na_obratke float               -- Исправлено на обратке
);
---------------------------------
-- shurf_korroziynaya_aktivnost - Другие
-- shurf_korroziynaya_aktivnost - Шурф_коррозийная_активность
drop table if exists shurf_korroziynaya_aktivnost;

create table shurf_korroziynaya_aktivnost (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shurf int,                                -- Шурф
    data_otbora_1 date,                       -- Дата отбора 1
    mesto_otbora_1 varchar(255),              -- Место отбора 1
    material_proby_1 varchar(255),            -- Материал пробы 1
    nomer_obraztsa_1 varchar(255),            -- Номер образца 1
    massa_sterzhnya_nachalnaya_g_1 float,     -- Масса стержня начальная,г 1
    massa_sterzhnya_konechnaya_g_1 float,     -- Масса стержня конечная,г 1
    poterya_massy_g_1 float,                  -- Потеря массы,г 1
    stepen_korrozionnoy_aktivnosti_1 int,     -- Степень коррозионной активности 1
    data_otbora_2 date,                       -- Дата отбора 2
    mesto_otbora_2 varchar(255),              -- Место отбора 2
    material_proby_2 varchar(255),            -- Материал пробы 2
    nomer_obraztsa_2 varchar(255),            -- Номер образца 2
    massa_sterzhnya_nachalnaya_g_2 float,     -- Масса стержня начальная,г 2
    massa_sterzhnya_konechnaya_g_2 float,     -- Масса стержня конечная,г 2
    otchet text,                              -- Отчет
    data_analiza_prob date,                   -- Дата анализа проб
    poterya_massy_g_2 float,                  -- Потеря массы,г 2
    stepen_korrozionnoy_aktivnosti_2 int,     -- Степень коррозионной активности 2
    data_otbora_3 date,                       -- Дата отбора 3
    mesto_otbora_3 varchar(255),              -- Место отбора 3
    material_proby_3 varchar(255),            -- Материал пробы 3
    nomer_obraztsa_3 varchar(255),            -- Номер образца 3
    massa_sterzhnya_nachalnaya_g_3 float,     -- Масса стержня начальная,г 3
    massa_sterzhnya_konechnaya_g_3 float,     -- Масса стержня конечная,г 3
    poterya_massy_g_3 float,                  -- Потеря массы,г 3
    stepen_korrozionnoy_aktivnosti_3 int,     -- Степень коррозионной активности 3
    data_otbora_4 date,                       -- Дата отбора 4
    mesto_otbora_4 varchar(255),              -- Место отбора 4
    material_proby_4 varchar(255),            -- Материал пробы 4
    nomer_obraztsa_4 varchar(255),            -- Номер образца 4
    massa_sterzhnya_nachalnaya_g_4 float,     -- Масса стержня начальная,г 4
    massa_sterzhnya_konechnaya_g_4 float,     -- Масса стержня конечная,г 4
    poterya_massy_g_4 float,                  -- Потеря массы,г 4
    stepen_korrozionnoy_aktivnosti_4 int,     -- Степень коррозионной активности 4
    data_otbora_5 date,                       -- Дата отбора 5
    mesto_otbora_5 varchar(255),              -- Место отбора 5
    material_proby_5 varchar(255),            -- Материал пробы 5
    nomer_obraztsa_5 varchar(255),            -- Номер образца 5
    massa_sterzhnya_nachalnaya_g_5 float,     -- Масса стержня начальная,г 5
    massa_sterzhnya_konechnaya_g_5 float,     -- Масса стержня конечная,г 5
    poterya_massy_g_5 float,                  -- Потеря массы,г 5
    stepen_korrozionnoy_aktivnosti_5 int,     -- Степень коррозионной активности 5
    otvetstvennyy__dolzhnost varchar(255),    -- Ответственный, должность
    otvetstvennyy__fio varchar(255),          -- Ответственный, ФИО
    ispolnitel__dolzhnost varchar(255),       -- Исполнитель, должность
    ispolnitel__fio varchar(255),             -- Исполнитель, ФИО
    analiz_na_korroziynost text               -- Анализ на коррозийность
);
---------------------------------
-- shurf_potentsialy_truba_zemlya - Другие
-- shurf_potentsialy_truba_zemlya - Шурф_потенциалы_труба_земля
drop table if exists shurf_potentsialy_truba_zemlya;

create table shurf_potentsialy_truba_zemlya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shurf int,                                -- Шурф
    data_izmereniy_potentsialov date,         -- Дата измерений потенциалов
    nachalo_izmereniy__chas int,              -- Начало измерений, час
    nachalo_izmereniy__min int,               -- Начало измерений, мин
    konets_izmereniy__chas int,               -- Конец измерений, час
    konets_izmereniy__min int,                -- Конец измерений, мин
    ulitsa varchar(255),                      -- Улица
    adres_punkta_izmereniy varchar(255),      -- Адрес пункта измерений
    tip_pribora varchar(255),                 -- Тип прибора
    nomer_pribora varchar(255),               -- Номер прибора
    tip_elektroda_sravneniya varchar(255),    -- Тип электрода сравнения
    protokol_izmereniy text,                  -- Протокол измерений
    nomer_protokola_potentsialov varchar(255),    -- Номер протокола потенциалов
    data_sozdaniya_protokola_potentsialov date,   -- Дата создания протокола потенциалов
    potentsial_1_0 float,                     -- Потенциал 1 0
    potentsial_1_5 float,                     -- Потенциал 1 5
    potentsial_1_10 float,                    -- Потенциал 1 10
    potentsial_1_15 float,                    -- Потенциал 1 15
    potentsial_1_20 float,                    -- Потенциал 1 20
    potentsial_1_25 float,                    -- Потенциал 1 25
    potentsial_1_30 float,                    -- Потенциал 1 30
    potentsial_1_35 float,                    -- Потенциал 1 35
    potentsial_1_40 float,                    -- Потенциал 1 40
    potentsial_1_45 float,                    -- Потенциал 1 45
    potentsial_1_50 float,                    -- Потенциал 1 50
    potentsial_1_55 float,                    -- Потенциал 1 55
    potentsial_2_0 float,                     -- Потенциал 2 0
    potentsial_2_5 float,                     -- Потенциал 2 5
    potentsial_2_10 float,                    -- Потенциал 2 10
    potentsial_2_15 float,                    -- Потенциал 2 15
    potentsial_2_20 float,                    -- Потенциал 2 20
    potentsial_2_25 float,                    -- Потенциал 2 25
    potentsial_2_30 float,                    -- Потенциал 2 30
    potentsial_2_35 float,                    -- Потенциал 2 35
    potentsial_2_40 float,                    -- Потенциал 2 40
    potentsial_2_45 float,                    -- Потенциал 2 45
    potentsial_2_50 float,                    -- Потенциал 2 50
    potentsial_2_55 float,                    -- Потенциал 2 55
    potentsial_3_0 float,                     -- Потенциал 3 0
    potentsial_3_5 float,                     -- Потенциал 3 5
    potentsial_3_10 float,                    -- Потенциал 3 10
    potentsial_3_15 float,                    -- Потенциал 3 15
    potentsial_3_20 float,                    -- Потенциал 3 20
    potentsial_3_25 float,                    -- Потенциал 3 25
    potentsial_3_30 float,                    -- Потенциал 3 30
    potentsial_3_35 float,                    -- Потенциал 3 35
    potentsial_3_40 float,                    -- Потенциал 3 40
    potentsial_3_45 float,                    -- Потенциал 3 45
    potentsial_3_50 float,                    -- Потенциал 3 50
    potentsial_3_55 float,                    -- Потенциал 3 55
    potentsial_4_0 float,                     -- Потенциал 4 0
    potentsial_4_5 float,                     -- Потенциал 4 5
    potentsial_4_10 float,                    -- Потенциал 4 10
    potentsial_4_15 float,                    -- Потенциал 4 15
    potentsial_4_20 float,                    -- Потенциал 4 20
    potentsial_4_25 float,                    -- Потенциал 4 25
    potentsial_4_30 float,                    -- Потенциал 4 30
    potentsial_4_35 float,                    -- Потенциал 4 35
    potentsial_4_40 float,                    -- Потенциал 4 40
    potentsial_4_45 float,                    -- Потенциал 4 45
    potentsial_4_50 float,                    -- Потенциал 4 50
    potentsial_4_55 float,                    -- Потенциал 4 55
    potentsial_5_0 float,                     -- Потенциал 5 0
    potentsial_5_5 float,                     -- Потенциал 5 5
    potentsial_5_10 float,                    -- Потенциал 5 10
    potentsial_5_15 float,                    -- Потенциал 5 15
    potentsial_5_20 float,                    -- Потенциал 5 20
    potentsial_5_25 float,                    -- Потенциал 5 25
    potentsial_5_30 float,                    -- Потенциал 5 30
    potentsial_5_35 float,                    -- Потенциал 5 35
    potentsial_5_40 float,                    -- Потенциал 5 40
    potentsial_5_45 float,                    -- Потенциал 5 45
    potentsial_5_50 float,                    -- Потенциал 5 50
    potentsial_5_55 float,                    -- Потенциал 5 55
    summa__v float,                           -- Сумма, В
    maksimum__v float,                        -- Максимум, В
    srednyaya_velichina__v float,             -- Средняя величина, В
    minimum__v float,                         -- Минимум, В
    chislo_izmereniy int                      -- Число измерений
);
---------------------------------
-- shurf_truby - Другие
-- shurf_truby - Шурф_Трубы
drop table if exists shurf_truby;

create table shurf_truby (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defekt int,                               -- Повреждение
    element int,                              -- Элемент
    osmotreno_na_podache float,               -- Осмотрено на подаче
    povrezhdeno_na_podache float,             -- Повреждено на подаче
    ispravleno_na_podache float,              -- Исправлено на подаче
    osmotreno_na_obratke float,               -- Осмотрено на обратке
    povrezhdeno_na_obratke float,             -- Повреждено на обратке
    ispravleno_na_obratke float               -- Исправлено на обратке
);
---------------------------------
-- shurf_vlazhnost_grunta - Другие
-- shurf_vlazhnost_grunta - Шурф_влажность_грунта
drop table if exists shurf_vlazhnost_grunta;

create table shurf_vlazhnost_grunta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shurf int,                                -- Шурф
    data_analiza_prob date,                   -- Дата анализа проб
    nomer_proby_1 int,                        -- Номер пробы 1
    ispytuemyy_material_1 varchar(255),       -- Испытуемый материал 1
    mesto_otbora_proby_1 varchar(255),        -- Место отбора пробы 1
    "vlazhnost__%_k_suhomu_vesu_1" float,     -- Влажность, % к сухому весу 1
    primechanie_1 varchar(255),               -- Примечание 1
    nomer_proby_2 int,                        -- Номер пробы 2
    ispytuemyy_material_2 varchar(255),       -- Испытуемый материал 2
    mesto_otbora_proby_2 varchar(255),        -- Место отбора пробы 2
    "vlazhnost__%_k_suhomu_vesu_2" float,     -- Влажность, % к сухому весу 2
    primechanie_2 varchar(255),               -- Примечание 2
    nomer_proby_3 int,                        -- Номер пробы 3
    ispytuemyy_material_3 varchar(255),       -- Испытуемый материал 3
    mesto_otbora_proby_3 varchar(255),        -- Место отбора пробы 3
    "vlazhnost__%_k_suhomu_vesu_3" float,     -- Влажность, % к сухому весу 3
    primechanie_3 varchar(255),               -- Примечание 3
    nomer_proby_4 int,                        -- Номер пробы 4
    ispytuemyy_material_4 varchar(255),       -- Испытуемый материал 4
    mesto_otbora_proby_4 varchar(255),        -- Место отбора пробы 4
    "vlazhnost__%_k_suhomu_vesu_4" float,     -- Влажность, % к сухому весу 4
    primechanie_4 varchar(255),               -- Примечание 4
    nomer_proby_5 int,                        -- Номер пробы 5
    ispytuemyy_material_5 varchar(255),       -- Испытуемый материал 5
    mesto_otbora_proby_5 varchar(255),        -- Место отбора пробы 5
    "vlazhnost__%_k_suhomu_vesu_5" float,     -- Влажность, % к сухому весу 5
    primechanie_5 varchar(255),               -- Примечание 5
    otchet text,                              -- Отчет
    otvetstvennyy__dolzhnost varchar(255),    -- Ответственный, должность
    otvetstvennyy__fio varchar(255),          -- Ответственный, ФИО
    ispolnitel__dolzhnost varchar(255),       -- Исполнитель, должность
    ispolnitel__fio varchar(255),             -- Исполнитель, ФИО
    analiz_prob_na_vlazhnost text             -- Анализ проб на влажность
);
---------------------------------
-- shurf_vodnaya_vytyazhka - Другие
-- shurf_vodnaya_vytyazhka - Шурф_водная_вытяжка
drop table if exists shurf_vodnaya_vytyazhka;

create table shurf_vodnaya_vytyazhka (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shurf int,                                -- Шурф
    data_analiza date,                        -- Дата анализа
    ulitsa varchar(255),                      -- Улица
    mesto_otbora_proby varchar(255),          -- Место отбора пробы
    material_proby varchar(255),              -- Материал пробы
    nomer_1 int,                              -- Номер 1
    kaltsiy varchar(255),                     -- Кальций
    kaltsiy_mg_100_g float,                   -- Кальций мг/100 г
    kaltsiy_mg_ekv_100_g float,               -- Кальций мг-экв/100 г
    nomer_2 int,                              -- Номер 2
    magniy varchar(255),                      -- Магний
    magniy_mg_100_g float,                    -- Магний мг/100 г
    magniy_mg_ekv_100_g float,                -- Магний мг-экв/100 г
    nomer_3 int,                              -- Номер 3
    kaliy varchar(255),                       -- Калий
    kaliy_mg_100_g float,                     -- Калий мг/100 г
    kaliy_mg_ekv_100_g float,                 -- Калий мг-экв/100 г
    nomer_4 int,                              -- Номер 4
    natriy varchar(255),                      -- Натрий
    natriy_mg_100_g float,                    -- Натрий мг/100 г
    natriy_mg_ekv_100_g float,                -- Натрий мг-экв/100 г
    nomer_5 int,                              -- Номер 5
    sulfaty varchar(255),                     -- Сульфаты
    sulfaty_mg_100_g float,                   -- Сульфаты мг/100 г
    sulfaty_mg_ekv_100_g float,               -- Сульфаты мг-экв/100 г
    nomer_6 int,                              -- Номер 6
    hloridy varchar(255),                     -- Хлориды
    hloridy_mg_100_g float,                   -- Хлориды мг/100 г
    hloridy_mg_ekv_100_g float,               -- Хлориды мг-экв/100 г
    nomer_7 int,                              -- Номер 7
    nitrity varchar(255),                     -- Нитриты
    nitrity_mg_100_g float,                   -- Нитриты мг/100 г
    nitrity_mg_ekv_100_g float,               -- Нитриты мг-экв/100 г
    nomer_8 int,                              -- Номер 8
    nitraty varchar(255),                     -- Нитраты
    nitraty_mg_100_g float,                   -- Нитраты мг/100 г
    nitraty_mg_ekv_100_g float,               -- Нитраты мг-экв/100 г
    nomer_9 int,                              -- Номер 9
    rn varchar(255),                          -- РН
    rn_mg_100_g float,                        -- РН мг/100 г
    rn_mg_ekv_100_g float,                    -- РН мг-экв/100 г
    otchet text,                              -- Отчет
    otvetstvennyy__dolzhnost varchar(255),    -- Ответственный, должность
    otvetstvennyy__fio varchar(255),          -- Ответственный, ФИО
    ispolnitel__dolzhnost varchar(255),       -- Исполнитель, должность
    ispolnitel__fio varchar(255)              -- Исполнитель, ФИО
);
---------------------------------
-- shurf2_dokumenty - Другие
-- shurf2_dokumenty - Шурф2_документы
drop table if exists shurf2_dokumenty;

create table shurf2_dokumenty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shurfID int default (NULL),
    docRemontTypeID int default (NULL),
    data date default (NULL),                 -- Дата
    dokument text default (NULL)              -- Документ
);
---------------------------------
-- shurf2_meropriyatiya - Другие
-- shurf2_meropriyatiya - Шурф2_мероприятия
drop table if exists shurf2_meropriyatiya;

create table shurf2_meropriyatiya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shurfID int default (NULL),
    povrezhdeniya int default (NULL),         -- Повреждения
    meropriyatie int default (NULL),          -- Мероприятие
    plan1 int default (NULL) 
);
---------------------------------
-- shurfstates - Другие
-- shurfstates - shurfstates
drop table if exists shurfstates;

create table shurfstates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- sortlinesforuchastok - Другие
-- sortlinesforuchastok - sortlinesforuchastok
drop table if exists sortlinesforuchastok;

create table sortlinesforuchastok (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uchastok_ms_id int,
    uchastok_rs_id int,
    nodeID1 int not null,
    nodeID2 int not null,
    orderID int not null,
    pipeSectionID int not null,
    lineID int not null,
    totalLength float not null,
    fileID int not null 
);
CREATE INDEX sortlinesforuchastok_nodeid1_idx ON sortlinesforuchastok (nodeid1);
CREATE INDEX sortlinesforuchastok_lineid_idx ON sortlinesforuchastok (lineid);
CREATE INDEX sortlinesforuchastok_nodeid2_idx ON sortlinesforuchastok (nodeid2);
CREATE INDEX sortlinesforuchastok_fileid_idx ON sortlinesforuchastok (fileid);
---------------------------------
-- sortnodesforuchastok - Другие
-- sortnodesforuchastok - sortnodesforuchastok
drop table if exists sortnodesforuchastok;

create table sortnodesforuchastok (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nodeID int,
    uchastok_ms_id int,
    uchastok_rs_id int,
    orderID int not null 
);
CREATE INDEX sortnodesforuchastok_nodeid_idx ON sortnodesforuchastok (nodeid);
---------------------------------
-- spisok_kamer_drenazh - Другие
-- spisok_kamer_drenazh - spisok_kamer_drenazh
drop table if exists spisok_kamer_drenazh;

create table spisok_kamer_drenazh (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    nodeID int 
);
CREATE INDEX spisok_kamer_drenazh_nodeid_idx ON spisok_kamer_drenazh (nodeid);
---------------------------------
-- spisok_ulits - Другие
-- spisok_ulits - Список улиц
drop table if exists spisok_ulits;

create table spisok_ulits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_street varchar(255) 
);
---------------------------------
-- spisok_ulits_staryy - Другие
-- spisok_ulits_staryy - Список улиц старый
drop table if exists spisok_ulits_staryy;

create table spisok_ulits_staryy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_street varchar(255) 
);
---------------------------------
-- spisok_zhilyh_massivov - Другие
-- spisok_zhilyh_massivov - Список жилых массивов
drop table if exists spisok_zhilyh_massivov;

create table spisok_zhilyh_massivov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_street varchar(255) 
);
---------------------------------
-- sposob_ispolneniya_obektov_setey_teplosnabzheniya - Другие
-- sposob_ispolneniya_obektov_setey_teplosnabzheniya - Способ исполнения объектов сетей теплоснабжения
drop table if exists sposob_ispolneniya_obektov_setey_teplosnabzheniya;

create table sposob_ispolneniya_obektov_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- standartequipment - Другие
-- standartequipment - standartequipment
drop table if exists standartequipment;

create table standartequipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL) 
);
---------------------------------
-- teplo - Другие
-- teplo - teplo
drop table if exists teplo;

create table teplo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heatPipeSectionID int not null,
    q float not null 
);
---------------------------------
-- tip_kanala_setey_teplosnabzheniya - Другие
-- tip_kanala_setey_teplosnabzheniya - Тип канала сетей теплоснабжения
drop table if exists tip_kanala_setey_teplosnabzheniya;

create table tip_kanala_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- tip_kladbischa - Другие
-- tip_kladbischa - Тип кладбища
drop table if exists tip_kladbischa;

create table tip_kladbischa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod int,                                  -- Код
    tip varchar(150),                         -- ТИП
    primechanie varchar(150)                  -- Примечание
);
---------------------------------
-- tip_kompensatora_setey_teplosnabzheniya - Другие
-- tip_kompensatora_setey_teplosnabzheniya - Тип компенсатора сетей теплоснабжения
drop table if exists tip_kompensatora_setey_teplosnabzheniya;

create table tip_kompensatora_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- tip_massiva - Другие
-- tip_massiva - Тип массива
drop table if exists tip_massiva;

create table tip_massiva (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod int,                                  -- Код
    poyasnenie varchar(50),                   -- ПОЯСНЕНИЕ
    kratkoe_naimenovanie varchar(10)          -- КРАТКОЕ Наименование
);
---------------------------------
-- tip_opory_setey_teplosnabzheniya - Другие
-- tip_opory_setey_teplosnabzheniya - Тип опоры сетей теплоснабжения
drop table if exists tip_opory_setey_teplosnabzheniya;

create table tip_opory_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- tip_otklyucheniya_zapornoy_armatury - Другие
-- tip_otklyucheniya_zapornoy_armatury - Тип отключения запорной арматуры
drop table if exists tip_otklyucheniya_zapornoy_armatury;

create table tip_otklyucheniya_zapornoy_armatury (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- tip_soedineniya_truboprovoda_setey_teplosnabzheniya - Другие
-- tip_soedineniya_truboprovoda_setey_teplosnabzheniya - Тип соединения трубопровода сетей теплоснабжения
drop table if exists tip_soedineniya_truboprovoda_setey_teplosnabzheniya;

create table tip_soedineniya_truboprovoda_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- tip_truboprovoda - Другие
-- tip_truboprovoda - Тип трубопровода
drop table if exists tip_truboprovoda;

create table tip_truboprovoda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod int,                                  -- Код
    poyasnenie varchar(50)                    -- ПОЯСНЕНИЕ
);
---------------------------------
-- tip_vertikalnogo_povorota_setey_teplosnabzheniya - Другие
-- tip_vertikalnogo_povorota_setey_teplosnabzheniya - Тип вертикального поворота сетей теплоснабжения
drop table if exists tip_vertikalnogo_povorota_setey_teplosnabzheniya;

create table tip_vertikalnogo_povorota_setey_teplosnabzheniya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_geom int,
    naimenovanie varchar(150),                -- Наименование
    primechanie varchar(250)                  -- Примечание
);
---------------------------------
-- transfdocuments - Другие
-- transfdocuments - transfdocuments
drop table if exists transfdocuments;

create table transfdocuments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objID int,
    remontDocumentTypeID int,
    date_doc date,
    path varchar(256) 
);
---------------------------------
-- tubeisolations - Другие
-- tubeisolations - tubeisolations
drop table if exists tubeisolations;

create table tubeisolations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- tubes - Другие
-- tubes - tubes
drop table if exists tubes;

create table tubes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard varchar(50) default (NULL),
    standardTubeID int default (NULL) 
);
---------------------------------
-- ulitsy - Другие
-- ulitsy - Улицы
drop table if exists ulitsy;

create table ulitsy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    name varchar(255),                        -- Name
    name_2 varchar(255)                       -- Name 2
);
---------------------------------
-- ulitsy_almaty - Другие
-- ulitsy_almaty - Улицы-алматы
drop table if exists ulitsy_almaty;

create table ulitsy_almaty (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(255),
    name_2 varchar(255)                       -- Name 2
);
---------------------------------
-- vidy_elementov - Другие
-- vidy_elementov - Виды элементов
drop table if exists vidy_elementov;

create table vidy_elementov (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- vidy_trub - Другие
-- vidy_trub - Виды труб
drop table if exists vidy_trub;

create table vidy_trub (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie varchar(255),                   -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- vladeltsy_es - Другие
-- vladeltsy_es - Владельцы ЭС
drop table if exists vladeltsy_es;

create table vladeltsy_es (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naimenovanie varchar(255),                -- Наименование
    kontakty varchar(255)                     -- Контакты
);
---------------------------------
-- vosstanovitelnye_raboty_shurf - Другие
-- vosstanovitelnye_raboty_shurf - Восстановительные работы шурф
drop table if exists vosstanovitelnye_raboty_shurf;

create table vosstanovitelnye_raboty_shurf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    znachenie text,                           -- Значение
    primechanie varchar(255)                  -- Примечание
);
---------------------------------
-- vyd - Другие
-- vyd - vyd
drop table if exists vyd;

create table vyd (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod varchar(5),
    uzel varchar(25),
    nom int 
);
---------------------------------
-- yesorno123 - Другие
-- yesorno123 - yesorno123
drop table if exists yesorno123;

create table yesorno123 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name varchar(50) default (NULL),
    code varchar(10) default (NULL),
    ord int 
);
---------------------------------
-- zavod_izgotovitel - Другие
-- zavod_izgotovitel - Завод изготовитель
drop table if exists zavod_izgotovitel;

create table zavod_izgotovitel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazvanie varchar(50),                     -- Название
    telefon_organizatsii varchar(50),         -- Телефон организации
    telefon_rukovoditelya varchar(50),        -- Телефон руководителя
    strana varchar(255),                      -- Страна
    gorod varchar(255),                       -- Город
    ulitsa varchar(50),                       -- Улица
    nomer_doma varchar(50)                    -- Номер дома
);
---------------------------------
-- zhile - Другие
-- zhile - zhile
drop table if exists zhile;

create table zhile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- ID
    adres varchar(255),                       -- Адрес
    ploschad_doma float,                      -- Площадь дома
    nagruzka_otoplenie float,                 -- Нагрузка Отопление
    nagruzka_gvs float,                       -- Нагрузка ГВС
    administrativnyy_rayon varchar(255),      -- Административный район
    priznak_nalichiya_opu varchar(255),       -- Признак наличия ОПУ
    ekspluatatsionnyy_rayon varchar(255),     -- Эксплуатационный район
    istochnik_tepla varchar(255),             -- Источник тепла
    zdanie int,                               -- Здание
    kod1 varchar(10),
    uzel1 varchar(25),
    protsent_nagruzki_1 float,                -- Процент нагрузки 1
    kod2 varchar(10),
    uzel2 varchar(25),
    protsent_nagruzki_2 float,                -- Процент нагрузки 2
    kod3 varchar(10),
    uzel3 varchar(25),
    protsent_nagruzki_3 float,                -- Процент нагрузки 3
    kod4 varchar(10),
    uzel4 varchar(25),
    protsent_nagruzki_4 float,                -- Процент нагрузки 4
    kod5 varchar(10),
    uzel5 varchar(25),
    protsent_nagruzki_5 float                 -- Процент нагрузки 5
);
--- Другие: 330
--===========================--
--         lookup            --
--===========================--

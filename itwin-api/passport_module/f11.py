# Р¤11.РќР°СЂСѓС€РµРЅРёРµ

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import sql2
import excel


def workListTube():
    s = f'''
    
      workListTube = STUFF(
        (
            SELECT
                distinct concat(
                    IIF( rtt2.name != '', CONCAT(', ', rtt2.name, ':'),''),
                    STUFF (
                        (
                            select
                                concat(',', se.name) as n
                            from
                                defectTube dt
                                LEFT JOIN spisokElementov se ON se.id = dt.elementID
                            where
                                objId = z.id
                                and activityID = rt2.activityID FOR XML PATH(''),
                                TYPE
                        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''
                    )
                ) AS n
            FROM
                defect r2
                left JOIN defectTube rt2 ON r2.id = rt2.objID
                left JOIN remontTruboprovodaSpisok rtt2 ON rtt2.id = rt2.activityID
            WHERE
                r2.id = z.id FOR XML PATH(''),
                TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''
      )
      '''
    return s




#-------------------------------------------------------------------------------------

def get_f11(mark_line, mark_pts):
    q = f'''
select distinct top 2147483647
    t.[Наименование начального узла],
    t.[Наименование конечного узла],
    t.[Режим],
    t.[Состояние],
    t.[Дата обнаружения нарушения],
    t.[Адрес],
    t.[Описание повреждения],
    t.[Вид нарушения],
    t.[Категория нарушения],
    t.[Способ ликвидации нарушения],
    t.[Дата начала ремонтных работ],
    t.[Дата завершения ремонтных работ],
    t.workListTube as 'Ремонт трубопровода и элементов',
    t.len_tube as 'Длина заменённой трубы, м',
    t.len_izol as 'Длина заменённой изоляции, м',
    t.workListChannel as 'Ремонт канала',
    t.workListKamera as 'Ремонт камеры',
    t.len_channel as 'Длина участка ремонта канала',
    t.subdivision as 'Подразделение производившего работы',
    t.dolzhnost as 'Должность ответственного',
    t.fio_otv as 'Р¤РРћ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕРіРѕ',
    t.naimenovanie_uchastka as 'Участок эксплуатации',
    t.fio as 'Р¤РРћ',
    t.primechanie
/*
    ,
    t.orderID,
    t.id as 'id_obj',
    t.length,
    t.min_len,
    t.ms,
    t.rs
*/
    FROM (
     SELECT
      IIF (n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ',n1.externalNodeName, n1.nodeName) as 'Наименование начального узла',
      IIF (n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ',n2.externalNodeName, n2.nodeName) as 'Наименование конечного узла',
      deft.name as 'Режим',
      stateDefect.name as 'Состояние',
      FORMAT(obj.data_osmotra,'dd.MM.yyyy' ) as 'Дата обнаружения нарушения',
      obj.vremya_osmotra as 'Время обнаружения повреждения',
      CONCAT(st.name, '', obj.nomer_doma) as 'Адрес',
      obj.defectDescription as 'Описание повреждения',
      vn.code as 'Вид нарушения',
      rc.name as 'Категория нарушения',
      obj.meropriyatiya as 'Способ ликвидации нарушения',
      obj.data_nachala_remonta as 'Дата начала ремонтных работ',
      obj.data_zaversheniya_remonta as 'Дата завершения ремонтных работ',

      workListTube = STUFF(
        (
            SELECT
                distinct concat(
                    IIF( rtt2.name != '', CONCAT(', ', rtt2.name, ':'),''),
                    STUFF (
                        (
                            select
                                concat(',', se.name) as n
                            from
                                defectTube dt
                                LEFT JOIN spisokElementov se ON se.id = dt.elementID
                            where
                                objId = obj.id
                                and activityID = rt2.activityID FOR XML PATH(''),
                                TYPE
                        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''
                    )
                ) AS n
            FROM
                defect r2
                left JOIN defectTube rt2 ON r2.id = rt2.objID
                left JOIN remontTruboprovodaSpisok rtt2 ON rtt2.id = rt2.activityID
            WHERE
                r2.id = obj.id FOR XML PATH(''),
                TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 1, ''
      ),
      remont_kanala.name as workListChannel,
      remont_kamery.name as workListKamera,
      obj.len_tube_cur AS len_tube,
      obj.len_izol_cur AS len_izol,
      obj.len_channel_cur AS len_channel,
      obj.primechanie,
      subd.name as subdivision,
      d.znachenie as dolzhnost,
      nach.fio as fio_otv,
      IIF (ms.opisanie_uchastka_ms is not NULL, ms.opisanie_uchastka_ms, rs.naimenovanie_uchastka_rs) as naimenovanie_uchastka,
      IIF (nu_ms.fio is not NULL, nu_ms.fio, nu_rs.fio) as fio,
--      l.shape.STDistance(obj.shape.STPointN(1)) as length,
--      MIN(l.shape.STDistance(obj.shape.STPointN(1))) OVER(PARTITION BY obj.id ) AS "min_len",
      obj.id,
      mark_pts.ord as orderID
--      ,
--      pss.magistralSite as 'ms',
--      pss.distSite as 'rs'

FROM defect obj
LEFT JOIN linesobj l ON l.shape.STDistance(obj.shape.STPointN(1)) < 0.3
LEFT JOIN heatPipeSections hps ON hps.lineID=l.id
-- left join pipeSections pss on pss.id = hps.pipeSectionID
-- LEFT JOIN sortLinesForUchastok srt ON hps.pipeSectionID = srt.pipeSectionID
left join ulitsy st ON st.id = obj.ulicaID
left join vid_narusheniya vn on vn.id = obj.vid_narusheniyaID
LEFT JOIN defectTypes deft ON deft.id = obj.remontTypeID
left join remont_kanala on remont_kanala.id = obj.remont_kanalaID
left join remont_kamery on remont_kamery.id = obj.remont_kameryID
left join stateDefect on stateDefect.id = obj.stateID
LEFT JOIN remontCat rc ON rc.id = obj.remontCatID
LEFT JOIN nachalniki_uchastkov nach ON nach.id=obj.responsibleID
LEFT JOIN dolzhnosti d ON d.id=nach.dolzhnost
LEFT JOIN subdivisions subd ON subd.id=subdivisionID
left join uchastok_ms ms ON ms.id = hps.magistralSite
left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka
left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka
--left join rayon_ekspluatatsii re_ms ON re_ms.id = ue_ms.rayon_ekspluatatsii
left join uchastok_rs rs ON rs.id = hps.distSite
left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka
left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka

join (values {mark_line}) mark_line(ord, id, napr, pts) on mark_line.id=l.id
join (values {mark_pts}) mark_pts(ord, id, nodeID1, nodeID2) on mark_pts.id=mark_line.pts

LEFT JOIN nodes n1 ON n1.id = mark_pts.nodeID1
LEFT JOIN nodes n2 ON n2.id = mark_pts.nodeID2
left join externalCodes ec1 ON ec1.id = n1.externalCodeID
left join externalCodes ec2 ON ec2.id = n2.externalCodeID



) t
order by orderID


    '''
    return q


def get_f11_old(id, ms_rs, fragments):
    q = f'''
    select 

[Наименование начального узла],
[Наименование конечного узла],
[Режим],
[Состояние],
[Дата обнаружения нарушения],
[Адрес],
[Описание повреждения],

[Вид нарушения],
[Категория нарушения],
[Способ ликвидации нарушения],
[Дата начала ремонтных работ],
[Дата завершения ремонтных работ],
[Ремонт трубопровода и элементов],


[Длина заменённой трубы, м],
[Длина заменённой изоляции, м],
[Ремонт канала],
[Ремонт камеры],
[Длина участка ремонта канала],

[Подразделение производившего работы],
[Должность ответственного],
[Р¤РРћ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕРіРѕ],
[Участок эксплуатации],
[Р¤РРћ],
[primechanie]
    

    from getPts_defect({id},'{ms_rs}','{fragments}')
    '''
    return q


#-------------------------------------------------------------------------------------


def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = sql.get_f1_(mark_line)



    cols = [

#        'otchet_po_defektu',
        'remontTypeID',
        'stateID',
        'data_osmotra',
        'ulicaID',
#        'nomer_doma',
        'defectDescription',
        'vid_narusheniyaID',
        'remontCatID',
        'meropriyatiya',
        'data_nachala_remonta',
        'data_zaversheniya_remonta',
        '\'workListTube\' as workListTube',
        'len_tube_cur',
        'len_izol_cur',
        'remont_kanalaID',
        'remont_kameryID',
        'len_channel_cur',
#        'len_tube_cur',

#        '\'Подразделение производившего работы\' as qq1',
#        '\'Должность ответственного\' as qq2',
#        '\'Р¤РРћ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕРіРѕ\' as qq3',
#        '\'Участок эксплуатации\' as qq4',
#        '\'Р¤РРћ\' as qq5',
#        '\'Примечание\' as qq6',

    ]


    gr_obj = set(x for x in cols if x.find(' ') == -1)



    join_tabs = {
        'remontTypeID': 'defectTypes',
        'stateID': 'stateDefect',
        'ulicaID': 'ulitsy',
        'vid_narusheniyaID': 'vid_narusheniya',
        'remontCatID': 'remontCat',
        'remont_kanalaID': 'remont_kanala',
        'remont_kameryID': 'remont_kamery',
        'subdivisionID': 'subdivisions',
    }

    cols_s = ','.join(cols)


    obj = f'''
select id, shape, {cols_s}
from defect

'''

#    cols.insert(0, 'id')
#    q = sql.get_obj_ps(mark_line, mark_pts, f'({obj})', {'id'})



    q = sql.get_obj_ps2(mark_line, mark_pts, f'({obj})')


    ps2 = sql2.get_ps_obj(conn, q)


#    q = sql.get_obj_ps(mark_line, mark_pts, f'({obj})', cols)
#    q = sql.group_ps1(q, cols, gr_obj)


    cols = [
#        'otchet_po_defektu',
        'remontTypeID',
        'stateID',
        'data_osmotra',
        'ulicaID',
#        'nomer_doma',
        'defectDescription',
        'vid_narusheniyaID',
        'remontCatID',
        'meropriyatiya',
        'data_nachala_remonta',
        'data_zaversheniya_remonta',
#        '\'workListTube\' as workListTube',

        workListTube(),

        'len_tube_cur',
        'len_izol_cur',
        'remont_kanalaID',
        'remont_kameryID',
        'len_channel_cur',
#        'len_tube_cur',

         'subdivisionID',
         'd2.znachenie',
         'nu2.fio',
         'ue.nomer_uchastka',
         'nu.fio',

         'primechanie',

    ]

    ucharstok_ms = f'uchastok_{ms_rs}'


    join_dop = f'''
     left join {ucharstok_ms} ms on ms.id=hps.magistralSite
     left join uchastki_ekspluatatsii ue on ms.nomer_uchastka=ue.id
     left join nachalniki_uchastkov nu on nu.id=ue.nachalnik_uchastka
     left join dolzhnosti d on d.id=nu.dolzhnost

     
     left join nachalniki_uchastkov nu2 on nu2.id=z.responsibleID
     left join dolzhnosti d2 on d2.id=nu2.dolzhnost

     '''



#    q = sql.ps_add(q, cols, join_tabs, node=False)
    q = sql.ps_add2(ps2, 'defect', cols, join_tabs, join_dop=join_dop, node=False)
 


#    q = get_f11_old(id, ms_rs, fragments)
#    q = get_f11(mark_line, mark_pts)


#    print(q)
#    exit(0)

#    ws = wb.create_sheet(title="Ф11.Нарушение")
    row0 = write_header(ws)
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)

    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 11. Нарушение', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C6', 'Режим', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D6', 'Состояние', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E6', 'Дата обнаружения нарушения', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F6', 'Адрес', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G6', 'Описание повреждения', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H6', 'Вид нарушения (авария - А; технологический отказ - ТО; функциональный отказ – ФО.)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I6', 'Категория нарушения ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J6', 'Способ ликвидации нарушения ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:K6', 'Дата начала ремонтных работ ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L3:L6', 'Дата завершения ремонтных работ ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:R3', 'Ремонт/Реконструкция', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S3:U3', 'Ответственное лицо структурного подразделения производившего работы по устранение дефекта', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'V3:W3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'X3:X6', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'A4:A6', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4:B6', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M4:M6', 'Ремонт трубопровода и элементов ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N4:N6', 'Длина заменённой трубы, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O4:O6', 'Длина заменённой изоляции, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4:P6', 'Ремонт канала', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Q4:Q6', 'Ремонт камеры', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R4:R6', 'Длина участка ремонта канала, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S4:S6', 'Подразделение производившего работы ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'T4:T6', 'Должность ответственного', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'U4:U6', 'Р¤РРћ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕРіРѕ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'V4:V6', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'W4:W6', 'Р¤РРћ ', excel.thin_border, alignment=excel.center_alignment, bold=False)

#    ws.row_dimensions[4].height = 25 

    return 7

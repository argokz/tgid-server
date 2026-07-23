# Р¤10.Р РµРјРѕРЅС‚

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import sql2
import excel

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = sql.get_f1_(mark_line)

    q = f'''
select
[Наименование начального узла],
[Наименование конечного узла],
[Вид ремонта],
[Дата начала ремонтных работ],
[Дата завершения ремонтных работ],
[Тип прокладки],

[Длина заменённой трубы, м],
[Восстановление канальной прокладки, м],
[Диаметр условный, заменённой трубы, м],
[Диаметр внутренний, заменённой трубы, м],
[Диаметр наружный, заменённой трубы, м],
[Толщина стенки, , заменённой трубы, мм],
[Восстановление тепловой изоляции поверхности трубы, м2],
[Асфальтирование, ремонт, м2],

[Перечень работ (трубопровода)],
[Перечень работ (канал)],
[Перечень работ (камеры)],

[Номер приказа на ввод в эксплуатацию],
[Дата приказа ввода в эксплуацию],

[Подразделение производившее ремонт],
[Ответственный за ремонт]

from getPts_remont2({id},'{ms_rs}','{fragments}')
'''


    q = f'''
--select distinct
--    pss.id as id,
select
    IIF (n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ',CONCAT(nt1.name, ' ', n1.externalNodeName), n1.nodeName) as 'Наименование начального узла',
    IIF (n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ',CONCAT(nt2.name, ' ', n2.externalNodeName), n2.nodeName) as 'Наименование конечного узла',
    rt.name as 'Вид ремонта',
    --st.name as 'Состояние',
    obj.data_nachala_remonta as 'Дата начала ремонтных работ',
    obj.data_zaversheniya_remonta as 'Дата завершения ремонтных работ',
    tubingTypes.name as 'Тип прокладки',
    faktory_riska_truboprovoda.len_tube as 'Длина заменённой трубы, м',
    faktory_riska_truboprovoda.len_channel as 'Восстановление канальной прокладки, м',
    faktory_riska_truboprovoda.diameterCondit as 'Диаметр условный, заменённой трубы, м',
    faktory_riska_truboprovoda.diameterInternal as 'Диаметр внутренний, заменённой трубы, м',
    faktory_riska_truboprovoda.diameterExternal as 'Диаметр наружный, заменённой трубы, м',
    faktory_riska_truboprovoda.wallThickness as 'Толщина стенки, , заменённой трубы, мм',
    faktory_riska_truboprovoda.len_izol as 'Восстановление тепловой изоляции поверхности трубы, м2',
    faktory_riska_truboprovoda.asfaltirovanie as 'Асфальтирование, ремонт, м2',
    'Перечень работ (трубопровода)' = STUFF(
                (
                    SELECT
                        concat(',', rtt2.name) AS n
                    FROM
                        faktory_riska_truboprovoda r2
                        LEFT JOIN remontCapitalTube rt2 ON r2.id = rt2.objID
                        LEFT JOIN remontCapitalTubeTypes rtt2 ON rtt2.id = rt2.activityID
                    WHERE
                        r2.id = obj.id FOR XML PATH(''),
                        TYPE
                ).value('.', 'NVARCHAR(MAX)'),
                1,
                1,
                ''
            ),
            'Перечень работ (канал)' = STUFF(
                (
                    SELECT
                        concat(',', rtt2.name) AS n
                    FROM
                        faktory_riska_truboprovoda r2
                        LEFT JOIN remontChannel rt2 ON r2.id = rt2.objID
                        LEFT JOIN remontChannelTypes rtt2 ON rtt2.id = rt2.activityID
                    WHERE
                        r2.id = obj.id FOR XML PATH(''),
                        TYPE
                ).value('.', 'NVARCHAR(MAX)'),
                1,
                1,
                ''
            ),
            'Перечень работ (камеры)' = STUFF(
                (
                    SELECT
                        concat(',', rtt2.name) AS n
                    FROM
                        faktory_riska_truboprovoda r2
                        LEFT JOIN remontKamera rt2 ON r2.id = rt2.objID
                        LEFT JOIN remontChannelTypes rtt2 ON rtt2.id = rt2.activityID
                    WHERE
                        r2.id = obj.id FOR XML PATH(''),
                        TYPE
                ).value('.', 'NVARCHAR(MAX)'),
                1,
                1,
                ''
    ),
    obj.nomer_prikaza as 'Номер приказа на ввод в эксплуатацию',
    format(obj.data_prikaza_vvoda_v_ekspluataciyu,'dd.MM.yyyy') as 'Дата приказа ввода в эксплуацию',
    sb.name as 'Подразделение производившее ремонт',
    nu.fio as 'Ответственный за ремонт'
   -- obj.id AS 'Номер контура'
from remont2 obj
    join remont2Deployed d on d.directionID = obj.id
    JOIN heatPipeSections hpss ON hpss.lineID=d.lineID
--    JOIN pipeSections pss ON pss.id=hpss.pipeSectionID

    join linesobj l on l.id = d.lineID
    
    JOIN  (
        values {mark_line}
    ) mark_line(ord, id, napr, pts) on mark_line.id=l.id
    
    JOIN  (
        values  {mark_pts}
    ) pss(ord_p, id, nodeID1, nodeID2) on pss.id=mark_line.pts




    JOIN nodes n1 ON n1.id=pss.nodeID1
    JOIN nodes n2 ON n2.id=pss.nodeID2
    left join externalCodes ec1 ON ec1.id = n1.externalCodeID
    left join externalCodes ec2 ON ec2.id = n2.externalCodeID
    LEFT JOIN nodeTypes nt1 ON nt1.id=n1.nodeTypeID
    LEFT JOIN nodeTypes nt2 ON nt2.id=n2.nodeTypeID

    left join remontTypes rt on rt.id = obj.remontTypeID
    left join stateRemont2 st on st.id = obj.stateID
    left join subdivisions sb on sb.id = obj.subdivisionID
    --  left join responsibles rs on rs.id = obj.responsibleID
    left join nachalniki_uchastkov nu on nu.id = obj.responsibleID
    left join faktory_riska_truboprovoda on faktory_riska_truboprovoda.lineID = hpss.id and faktory_riska_truboprovoda.objID = obj.id and faktory_riska_truboprovoda.obj_type_faktory_riskaID = 3
    left join tubingTypes on tubingTypes.id = hpss.tubingTypeID

    left join uchastok_ms ms ON ms.id = hpss.magistralSite
    left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka
    left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka

    left join uchastok_rs rs ON rs.id = hpss.distSite
    left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka
    left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka

    where obj.stateID = 3 and n1.fileID in ({fragments})

    AND 
    
    {ms_rs}.id={id}

--    AND ( (not ec1.name in ('П1','П2') or not ec2.name in ('П1','П2')) or (ec1.name is null AND ec2.name is null) )
--    and ( (@type = 'ms' and ms.id = @id) or (@type = 'rs' and rs.id = @id) or (@type = 'all'))

    order by pss.ord_p

    '''

#    print(q)

#    ws = wb.create_sheet(title="Ф10.Ремонт")
    row0 = write_header(ws)
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)

    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])

    conn.close()

#-------------------------------------------------------------------------------------


def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 10. Реконструктивные работы и изменения в оборудовании', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C5', 'Вид ремонта ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'D3:D5', 'Дата начала ремонтных работ ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E5', 'Дата завершения ремонтных работ ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F5', 'Тип прокладки', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'G3:Q3', 'Ремонт/Реконструкция', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R3:R5', 'Номер приказа на ввод в эксплуатацию', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S3:S5', 'Дата приказа ввода в эксплуацию ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'T3:U3', 'Ответственное лицо структурного подразделения производившего ремонт/реконструкцию', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4:A5', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4:B5', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G4:G5', 'Длина заменённой трубы, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H4:H5', 'Восстановление канальной прокладки, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I4:I5', 'Диаметр условный, заменённой трубы, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J4:J5', 'Диаметр внутренний, заменённой трубы, м ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K4:K5', 'Диаметр наружный, заменённой трубы, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L4:L5', 'Толщина стенки, , заменённой трубы, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M4:M5', 'Восстановление тепловой изоляции поверхности трубы, м2', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N4:N5', 'Асфальтирование, ремонт, м2 ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O4:O5', 'Перечень работ (трубопровода)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4:P5', 'Перечень работ (канал)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Q4:Q5', 'Перечень работ (камеры)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'T4:T5', 'Подразделение производившее ремонт', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'U4:U5', 'Ответственный за ремонт', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 6

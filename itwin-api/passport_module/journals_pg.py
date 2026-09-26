"""Журнальные формы паспорта на PostgreSQL.

Перевод табличных функций MS SQL из десктопного ТГИД (gid6/gidr/sql2/full_tgid.sql:
getPts_cut_out, getPts_test, getPts_osmotr, getPts_responsible_person / vt_ms_rs).
В базах PostgreSQL этих функций нет, поэтому SQL строится здесь и подставляется
в формы подзапросом. Перевод: IIF → CASE, 'алиас' → "алиас", STDistance/STPointN →
ST_Distance/ST_DWithin (sql.first_point), fn_split_string → fragment_filter.
"""

import sql


def fragment_filter(alias, fragments):
    """Фильтр по фрагментам; пустой список — без ограничения (в вебе фрагменты не выбираются)."""
    ids = [int(x) for x in str(fragments or '').split(',') if x.strip()]
    if not ids:
        return '(1=1)'
    return f"{alias}.fileID in ({','.join(str(i) for i in ids)})"


def _args(id, ms_rs):
    if ms_rs not in ('ms', 'rs', 'pipe', 'all'):
        raise ValueError(f'ms_rs: {ms_rs!r}')
    return int(id), ms_rs


def responsible_person(id, ms_rs):
    """Ф9. Лицо, ответственное за участок (vt_ms_rs)."""
    id, ms_rs = _args(id, ms_rs)
    return f'''
    select * from (
        select
            ms.id as msID,
            NULL::int as rsID,
            ms.opisanie_uchastka_ms as naimenovanie_uchastka,
            re_ms.naimenovanie_rayona_ekspluatatsii_istochnika_tepla as naimenovanie_rayona,
            ue_ms.nomer_uchastka as nomer_uchastka,
            nu_ms.fio as fio,
            ms.nomer_prikaza as nomer_prikaza_otv,
            ms.data_prikaza as data_prikaza_otv,
            otv_d_ms.znachenie as otv_dolznost,
            otv_ms.fio as otv_fio
        from uchastok_ms ms
        left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka
        left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka
        left join rayon_ekspluatatsii re_ms ON re_ms.id = ue_ms.rayon_ekspluatatsii
        LEFT JOIN nachalniki_uchastkov otv_ms ON otv_ms.id = ms.responsibleID
        LEFT JOIN dolzhnosti otv_d_ms ON otv_d_ms.id = otv_ms.dolzhnost
        where not ms.opisanie_uchastka_ms is NULL and ms.opisanie_uchastka_ms != ' ' and nu_ms.fio is not NULL
    UNION ALL
        select
            NULL::int as msID,
            rs.id as rsID,
            rs.naimenovanie_uchastka_rs as naimenovanie_uchastka,
            re_rs.naimenovanie_rayona_ekspluatatsii_istochnika_tepla as naimenovanie_rayona,
            ue_rs.nomer_uchastka as nomer_uchastka,
            nu_rs.fio as fio,
            rs.nomer_prikaza as nomer_prikaza_otv,
            rs.data_prikaza as data_prikaza_otv,
            otv_d_rs.znachenie as otv_dolznost,
            otv_rs.fio as otv_fio
        from uchastok_rs rs
        left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka
        left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka
        left join rayon_ekspluatatsii re_rs ON re_rs.id = ue_rs.rayon_ekspluatatsii
        LEFT JOIN nachalniki_uchastkov otv_rs ON otv_rs.id = rs.responsibleID
        LEFT JOIN dolzhnosti otv_d_rs ON otv_d_rs.id = otv_rs.dolzhnost
        where not rs.naimenovanie_uchastka_rs is NULL and rs.naimenovanie_uchastka_rs != ' ' and nu_rs.fio is not NULL
    ) vt
    WHERE ( ('{ms_rs}' = 'ms' and vt.msID = {id}) or ('{ms_rs}' = 'rs' and vt.rsID = {id}) or ('{ms_rs}' = 'all') )
    '''


def cut_out(id, ms_rs, fragments=''):
    """Ф13. Вырезки (getPts_cut_out)."""
    id, ms_rs = _args(id, ms_rs)
    return f'''
select distinct t.obj_id as id,
    CASE WHEN n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ' THEN n1.externalNodeName ELSE n1.nodeName END AS "Наименование начального узла",
    CASE WHEN n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ' THEN n2.externalNodeName ELSE n2.nodeName END AS "Наименование конечного узла",
    es.name AS "Признак участка трубопровода",
    hpss.diameterExternal AS "Диаметр трубопровода, мм",
    n_vskr.name AS "Назначение вскрытия",
    CONCAT(st.name,' ',t.nomer_doma) AS "Адрес",
    sost_shurf.name AS "Состояние",
    t.data_nachala AS "Дата начала",
    t.data_okonchaniya AS "Дата окончания",
    t.nomer_akta AS "Номер акта",
    t.rezultaty_osmotra AS "Результаты осмотра",
    sostoyanie_metalla_truboprovoda.name AS "Состояние металла трубопровода",
    faktRiska_7_vneshkorroz.name AS "Cтепень внешней коррозии",
    faktRiska_8_vnutkorroz.name AS "Степень внутренней коррозии",
    t.primechanie AS "Примечание",
    t.fio_utverzhdaemogo AS "ФИО утверждающего",
    dolz.znachenie AS "Должность утверждающего",
    subd.name AS "Служба утверждающего",
    CASE WHEN pss.magistralSite is not NULL THEN re_ms.naimenovanie_rayona_ekspluatatsii_istochnika_tepla ELSE re_rs.naimenovanie_rayona_ekspluatatsii_istochnika_tepla END AS "Участок эксплуатации",
    CASE WHEN nu_ms.fio is not NULL THEN nu_ms.fio ELSE nu_rs.fio END AS "ФИО начальника участка",
    srt.orderID
from(
    select distinct
        l.lineID,
        l.externalSignLineID,
        d.id as obj_id,
        d.materialy_i_mekhanizmyID,
        d.data_utverzhdeniya_plana_shurfovok,
        d.naznachenie_vskrID,
        d.ulicaID,
        d.nomer_doma,
        d.sostoyanie_shurfaID,
        d.data_nachala_plan,
        d.data_okonchaniya_plan,
        d.data_nachala,
        d.data_okonchaniya,
        d.rasstoyanie_do_blizhajshej_kamery,
        d.nodeID_bizhajshej_kamery,
        d.dlina_osmotra,
        d.glubina_zalozheniya,
        d.nomer_akta,
        d.predpolagaemye_prichiny_razrusheniya_izolyacii,
        d.rezultaty_osmotra,
        d.namechennye_meropriyatiya,
        d.meropriyatiya_po_vosstanovleniyu_prokladki,
        d.primechanie,
        d.fio_utverzhdaemogo,
        d.dolzhnost_utverzhdaemogoID,
        d.sluzhba_utverzhdaemogoID,
        d.fio_1,
        d.dolzhnost_1,
        d.fio_2,
        d.dolzhnost_2,
        d.fio_viziruemogo_1,
        d.dolzhnost_viziruemogoID_1
    from shurfy d
        JOIN (
            select
                k.lineID,
                k.externalSignLineID,
                k.obj_id
            from (
                select
                    distinct
                        l.id as lineID,
                        d.id as obj_id,
                        l.externalSignLineID,
                        ST_Distance(l.shape, {sql.first_point('d.shape')}) as length,
                        MIN(ST_Distance(l.shape, {sql.first_point('d.shape')})) OVER(PARTITION BY d.id ) AS "min_len"
                from shurfy d
                JOIN linesobj l ON ( l.removed = 0 and ST_DWithin(l.shape, {sql.first_point('d.shape')}, 0.3) )
                where d.utverdit != 0
            )k
        where k.min_len = k.length
    ) l on l.obj_id = d.id
)t
    LEFT JOIN heatPipeSections hpss ON hpss.lineID=t.lineID
    LEFT JOIN pipeSections pss ON pss.id = hpss.pipeSectionID
    LEFT JOIN sortLinesForUchastok srt ON srt.pipeSectionID = pss.id
    left JOIN nodes n1 ON ( n1.id = pss.nodeID1 and n1.removed = 0 )
    LEFT JOIN nodes n2 ON n2.id = pss.nodeID2
    left join externalSigns  es on es.id = t.externalSignLineID
    left join externalCodes ec1 ON ec1.id = n1.externalCodeID
    left join externalCodes ec2 ON ec2.id = n2.externalCodeID
    join faktory_riska_truboprovoda on faktory_riska_truboprovoda.lineID = pss.id and faktory_riska_truboprovoda.objID = t.obj_id and faktory_riska_truboprovoda.obj_type_faktory_riskaID = 1

    left join faktRiska_7_vneshkorroz on faktRiska_7_vneshkorroz.id = faktory_riska_truboprovoda.VnesnKorrozia
    left join faktRiska_8_vnutkorroz on faktRiska_8_vnutkorroz.id = faktory_riska_truboprovoda.VnunrenKorrozia
    left join sostoyanie_metalla_truboprovoda on sostoyanie_metalla_truboprovoda.id = faktory_riska_truboprovoda.sostoyanie_metalla_truboprovodaID

    left join uchastok_ms ms ON ms.id = pss.magistralSite
    left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka

    left join rayon_ekspluatatsii re_ms ON re_ms.id = ue_ms.rayon_ekspluatatsii
    left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka

    left join uchastok_rs rs ON rs.id = pss.distSite
    left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka

    left join rayon_ekspluatatsii re_rs ON re_rs.id = ue_rs.rayon_ekspluatatsii
    left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka

    left join ulitsy st ON st.id = t.ulicaID
    left join sostoyanie_shurfa sost_shurf on sost_shurf.id = t.sostoyanie_shurfaID
    left join naznachenie_vskr n_vskr ON n_vskr.id = t.naznachenie_vskrID

    LEFT JOIN dolzhnosti dolz ON dolz.id=t.dolzhnost_utverzhdaemogoID
    LEFT JOIN subdivisions subd ON subd.id=t.sluzhba_utverzhdaemogoID

where   {fragment_filter('n1', fragments)}  and
        (faktRiska_7_vneshkorroz.id is not null  or faktRiska_8_vnutkorroz.id is not null or sostoyanie_metalla_truboprovoda.id is not null)
        and  ( (not ec1.name in ('П1','П2') or not ec2.name in ('П1','П2')) or (ec1.name is null AND ec2.name is null) )
        and (
                ('{ms_rs}' = 'ms' and  pss.magistralSite = {id})
                or ('{ms_rs}' = 'rs' and pss.distSite = {id})
                or ('{ms_rs}' = 'pipe' and pss.id = {id} )
                or ('{ms_rs}' = 'all')
            )

order by t.data_nachala desc
'''


def pressure_test(id, ms_rs, fragments=''):
    """Ф14. Опрессовки (getPts_test)."""
    id, ms_rs = _args(id, ms_rs)
    return f'''
select
    distinct
     CASE WHEN n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ' THEN n1.externalNodeName ELSE n1.nodeName END AS "Наименование начального узла",
     CASE WHEN n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ' THEN n2.externalNodeName ELSE n2.nodeName END AS "Наименование конечного узла",
     obj.opisaniye_kontura AS "Описание контура",
     ot.name AS "Вид испытания",
     obj.date_opres AS "Дата проведения опрессовки",
     obj.davlenie_opressovki_1_etap AS "Давление опрессовки 1 этапа, кгс/см2",
     obj.davlenie_opressovki_2_etap AS "Давление опрессовки 2 этапа, кгс/см2",
     obj.reshenie_komissii AS "Решение комиссии",
     CONCAT(st.name, '', d.nomer_doma) AS "Адрес нарушения",
     d.defectDescription AS "Описание повреждения",
     d.meropriyatiya AS "Способ ликвидации нарушения",
     obj.fio_rukovoditel_ispytanij AS "ФИО руководителя испытаний",
     dolzhnosti_ruk.znachenie AS "Должность руководителя испытаний",
     subd_ruk.name AS "Подразделение руководителя испытаний",
     CASE WHEN ms.opisanie_uchastka_ms is not NULL THEN ms.opisanie_uchastka_ms ELSE rs.naimenovanie_uchastka_rs END AS "Участок эксплуатации",
     CASE WHEN nu_ms.fio is not NULL THEN nu_ms.fio ELSE nu_rs.fio END AS "ФИО начальника участка",
     obj.id AS "obj_id",
     d.id AS "defect_id",
     ms.id AS "msID",
     rs.id AS "rsID",
     nf.fileID AS "fileID"
from opres obj
    left join opresDeployed od ON od.directionID = obj.id
    left join linesobj l on l.id = od.lineID
    LEFT JOIN heatPipeSections hps ON hps.lineID = l.id
    left join pipeSections pss on pss.id = hps.pipeSectionID
    LEFT JOIN sortLinesForUchastok srt ON hps.pipeSectionID = srt.pipeSectionID
    LEFT JOIN nodes n1 ON n1.id = pss.nodeID1
    LEFT JOIN nodes n2 ON n2.id = pss.nodeID2
    left join externalCodes ec1 ON ec1.id = n1.externalCodeID
    left join externalCodes ec2 ON ec2.id = n2.externalCodeID
    left join opres_types ot on ot.id = obj.opres_typeID
    left join defect d ON ST_DWithin(l.shape, {sql.first_point('d.shape')}, 0.3) and d.opresID = obj.id
    left join ulitsy st ON st.id = d.ulicaID
    left join nodes nf on nf.id = l.nodeID1
    left join vid_ispytani vid_is on vid_is.id = obj.vid_ispytaniID
    LEFT JOIN dolzhnosti dolzhnosti_ruk ON dolzhnosti_ruk.id = obj.dolzhnost_rukovoditel_ispytanijID
    LEFT JOIN subdivisions subd_ruk ON subd_ruk.id = obj.podrazdelenie_rukovoditel_ispytanijID

    left join uchastok_ms ms ON ms.id = pss.magistralSite
    left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka
    left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka

    left join uchastok_rs rs ON rs.id = pss.distSite
    left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka
    left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka
    where obj.sostoyanie_opresID = 3 and {fragment_filter('nf', fragments)}
    AND ( (not ec1.name in ('П1','П2') or not ec2.name in ('П1','П2')) or (ec1.name is null AND ec2.name is null) )
    and ( ('{ms_rs}' = 'ms' and ms.id = {id}) or ('{ms_rs}' = 'rs' and rs.id = {id}) or ('{ms_rs}' = 'all'))
'''


# Длинные русские алиасы заменены: PostgreSQL обрезает идентификаторы до 63 байт,
# и пары «подающий/обратный» совпадали. Заголовки Excel задаёт f15.write_header.
def inspection(id, ms_rs, fragments=''):
    """Ф15. Осмотры (getPts_osmotr)."""
    id, ms_rs = _args(id, ms_rs)
    return f'''
SELECT
    DISTINCT
            pss.id AS "id",
            CASE WHEN n1.nodeName is NULL or n1.nodeName = '' or n1.nodeName = ' ' THEN CONCAT(nt1.name, ' ', n1.externalNodeName) ELSE n1.nodeName END AS "Наименование начального узла",
            CASE WHEN n2.nodeName is NULL or n2.nodeName = '' or n2.nodeName = ' ' THEN CONCAT(nt2.name, ' ', n2.externalNodeName) ELSE n2.nodeName END AS "Наименование конечного узла",
            pss.DiamUslov AS "Диаметр трубопровода, мм",
            es.name AS "Признак участка трубопровода",
            obj.data_osmotra AS "Дата осмотра",
            vneshny_vid.name AS "Внешний вид",
            sost_oborud.name AS "Состояние оборудования",
            sostoyanie_metalla_truboprovoda.name AS "Состояние металла трубопровода",
            sost_konstr.name AS "Состояние строительных конструкций",
            sostoyanie_teplovoj_izolyacii_obratka.name AS izol_obr,
            sostoyanie_teplovoj_izolyacii_podacha.name AS izol_pod,
            sostoyanie_naruzhnogo_pokrytiya_obratka.name AS pokr_obr,
            sostoyanie_naruzhnogo_pokrytiya_podacha.name AS pokr_pod,
            sostoyanie_protivokorrozionnogo_pokrytiya_obratka.name AS antikor_obr,
            sostoyanie_protivokorrozionnogo_pokrytiya_podacha.name AS antikor_pod,
            otv.fio AS "Отвественное лицо",
            subd.name AS "Подразделение проводившее работу",
            CASE WHEN ms.opisanie_uchastka_ms is not NULL THEN ms.opisanie_uchastka_ms ELSE rs.naimenovanie_uchastka_rs END AS "Участок эксплуатации",
            CASE WHEN nu_ms.fio is not NULL THEN nu_ms.fio ELSE nu_rs.fio END AS "Начальник участка",
            --tubingTypes.name AS "Тип прокладки",
            --pss.pipeLength AS "Длина участка теплопровода, м",
            srt.orderID,
            obj.id AS "objID"
        from osmotr obj
        join osmotrDeployed d on d.directionID = obj.id
        JOIN heatPipeSections hpss ON hpss.lineID=d.lineID
        JOIN pipeSections pss ON pss.id=hpss.pipeSectionID
        LEFT JOIN sortLinesForUchastok srt ON pss.id = srt.pipeSectionID
        LEFT join linesobj l on l.id = d.lineID

        left join faktory_riska_truboprovoda on faktory_riska_truboprovoda.lineID = pss.id and faktory_riska_truboprovoda.objID = obj.id and faktory_riska_truboprovoda.obj_type_faktory_riskaID = 2
        LEFT JOIN tubingTypes tt ON pss.tubingTypeID = tt.id
        left join sostoyanie_teplovoj_izolyacii sostoyanie_teplovoj_izolyacii_obratka on sostoyanie_teplovoj_izolyacii_obratka.id = faktory_riska_truboprovoda.sostoyanie_teplovoj_izolyacii_obratkaID
        left join sostoyanie_teplovoj_izolyacii sostoyanie_teplovoj_izolyacii_podacha on sostoyanie_teplovoj_izolyacii_podacha.id = faktory_riska_truboprovoda.sostoyanie_teplovoj_izolyacii_podachaID
        left join sostoyanie_naruzhnogo_pokrytiya sostoyanie_naruzhnogo_pokrytiya_obratka on sostoyanie_naruzhnogo_pokrytiya_obratka.id = faktory_riska_truboprovoda.sostoyanie_naruzhnogo_pokrytiya_obratkaID
        left join sostoyanie_naruzhnogo_pokrytiya sostoyanie_naruzhnogo_pokrytiya_podacha on sostoyanie_naruzhnogo_pokrytiya_podacha.id = faktory_riska_truboprovoda.sostoyanie_naruzhnogo_pokrytiya_podachaID
        left join sostoyanie_protivokorrozionnogo_pokrytiya_shurf sostoyanie_protivokorrozionnogo_pokrytiya_podacha on sostoyanie_protivokorrozionnogo_pokrytiya_podacha.id = faktory_riska_truboprovoda.sostoyanie_protivokorrozionnogo_pokrytiya_podachaID
        left join sostoyanie_protivokorrozionnogo_pokrytiya_shurf sostoyanie_protivokorrozionnogo_pokrytiya_obratka on sostoyanie_protivokorrozionnogo_pokrytiya_obratka.id = faktory_riska_truboprovoda.sostoyanie_protivokorrozionnogo_pokrytiya_obratkaID
        JOIN nodes n1 ON n1.id=pss.nodeID1
        JOIN nodes n2 ON n2.id=pss.nodeID2
        LEFT JOIN nodeTypes nt1 ON nt1.id=n1.nodeTypeID
        LEFT JOIN nodeTypes nt2 ON nt2.id=n2.nodeTypeID
        left join externalCodes ec1 ON ec1.id = n1.externalCodeID
        left join externalCodes ec2 ON ec2.id = n2.externalCodeID
        left join externalSigns  es on es.id = l.externalSignLineID

        LEFT JOIN tubingTypes ON tubingTypes.id=pss.tubingTypeID
        left join vneshny_vid on vneshny_vid.id=faktory_riska_truboprovoda.VnesniiVid
        left join sost_oborud on sost_oborud.id=faktory_riska_truboprovoda.SostOborudovania
        left join sost_konstr on sost_konstr.id=faktory_riska_truboprovoda.SostKonstrukz
        left join sostoyanie_metalla_truboprovoda on sostoyanie_metalla_truboprovoda.id = faktory_riska_truboprovoda.sostoyanie_metalla_truboprovodaID


        left join uchastok_ms ms ON ms.id = pss.magistralSite
        left join uchastki_ekspluatatsii ue_ms ON ue_ms.id = ms.nomer_uchastka
        left join nachalniki_uchastkov nu_ms ON nu_ms.id = ue_ms.nachalnik_uchastka

        left join uchastok_rs rs ON rs.id = pss.distSite
        left join uchastki_ekspluatatsii ue_rs ON ue_rs.id = rs.nomer_uchastka
        left join nachalniki_uchastkov nu_rs ON nu_rs.id = ue_rs.nachalnik_uchastka

        left join nachalniki_uchastkov otv ON otv.id = obj.otvetstvennoe_lico_ID
        left join subdivisions subd ON subd.id = obj.podrazdelenie_provodivshee_raboty

    where
    faktory_riska_truboprovoda.id IS not NULL and
    {fragment_filter('n1', fragments)}
    AND ( (not ec1.name in ('П1','П2') or not ec2.name in ('П1','П2')) or (ec1.name is null AND ec2.name is null) )
    and ( ('{ms_rs}' = 'ms' and ms.id = {id}) or ('{ms_rs}' = 'rs' and rs.id = {id}) or ('{ms_rs}' = 'all'))
'''

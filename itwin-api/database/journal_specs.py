"""Описание записываемых полей эксплуатационных журналов (эталон — gid6 remont).

Ключ поля — имя, под которым журнал отдаётся на чтение (``database/defects.py`` и др.),
значение — колонка таблицы и тип. Так веб-форма пишет теми же ключами, какими читает,
а имена колонок в SQL подставляются только из этого перечня (и сверяются с каталогом
через ``database/sql_ident.py``).

Колонки утверждения плана (``utverdit``, дата и подписанты) здесь не перечислены —
их меняют только эндпоинты утверждения, как диалог «Утверждение плана» в gid6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

TIME_PATTERN = r"^(([0-1]?[0-9]|2[0-3]):[0-5][0-9])$"


@dataclass(frozen=True)
class FieldSpec:
    column: str
    kind: str  # int | float | str | date | timestamp | money | time
    label: str = ""
    ref: Optional[str] = None  # таблица справочника для проверки id
    max_length: Optional[int] = None


@dataclass(frozen=True)
class ApprovalSpec:
    flag_column: str
    date_column: str
    # поле тела запроса → колонка (подписанты, как в диалогах gid6)
    signer_columns: dict[str, FieldSpec]
    state_on_approve: Optional[tuple[str, int]] = None
    # поля (ключи FieldSpec журнала), без которых план не утверждается
    required_fields: tuple[str, ...] = ()
    require_contour: bool = False
    # utverdit, при котором запись не утверждается (текущий ремонт в gid6: utverdit=2)
    not_applicable_flag: Optional[int] = None


@dataclass(frozen=True)
class JournalSpec:
    key: str
    table: str
    title: str
    fields: dict[str, FieldSpec]
    required_on_create: tuple[str, ...] = ()
    unique_fields: tuple[str, ...] = ()
    # пары (раньше, позже) — правило After из *.validate gid6
    date_order: tuple[tuple[str, str], ...] = ()
    # пары «заполнено одно — заполни и другое» (NotNIfExists)
    both_or_none: tuple[tuple[str, str], ...] = ()
    deployed_table: Optional[str] = None
    documents_table: Optional[str] = None
    document_types_table: str = "remontdocumenttypes"
    point_geometry: bool = False
    risk_type: Optional[int] = None  # faktory_riska_truboprovoda.obj_type_faktory_riskaid
    # таблицы-связи, строки которых удаляются вместе с записью: (таблица, колонка)
    cascade: tuple[tuple[str, str], ...] = ()
    # ссылки из других журналов, обнуляемые при удалении: (таблица, колонка)
    detach: tuple[tuple[str, str], ...] = ()
    approval: Optional[ApprovalSpec] = None
    # режимы создания (как пункты меню gid6) → значения колонок по умолчанию
    create_modes: dict[str, dict[str, Any]] = field(default_factory=dict)
    # колонка даты, заполняемая текущим временем при создании (SaveOpresNew)
    created_at_column: Optional[str] = None


def _f(column: str, kind: str, label: str = "", ref: Optional[str] = None) -> FieldSpec:
    return FieldSpec(column=column, kind=kind, label=label, ref=ref)


_PEOPLE = "nachalniki_uchastkov"

REPAIRS = JournalSpec(
    key="repairs",
    table="remont2",
    title="Контур ремонта",
    fields={
        "name": _f("otchet_po_defektu", "str", "Наименование/адрес"),
        "state_id": _f("stateid", "int", "Состояние", "stateremont2"),
        "repair_type_id": _f("remonttypeid", "int", "Вид ремонта", "remonttypes"),
        "category_id": _f("remontcatid", "int", "Категория", "remontcat"),
        "responsible_id": _f("responsibleid", "int", "Ответственный", _PEOPLE),
        "subdivision_id": _f("subdivisionid", "int", "Подразделение", "subdivisions"),
        "network_type_id": _f("teplovaya_setid", "int", "Тепловая сеть (1 — магистральная, 2 — квартальная)"),
        "section_characteristics": _f("harakteristika_uchastkov_remontiruemoj_teplovoj_seti", "str", "Характеристика участков"),
        "work_description": _f("opisanie_rabot", "str", "Описание работ"),
        "work_characteristics": _f("harakteristika_rabot", "str", "Характеристика работ"),
        "results": _f("rezultaty_remonta", "str", "Результаты ремонта"),
        "note": _f("primechanie", "str", "Примечание"),
        "inspected_at": _f("data_osmotra", "timestamp", "Дата осмотра"),
        "inspected_time": _f("vremya_osmotra", "time", "Время осмотра"),
        "planned_start": _f("data_nachala_plan", "date", "Начало по плану"),
        "planned_finish": _f("data_okonchaniya_plan", "date", "Окончание по плану"),
        "actual_start": _f("data_nachala_remonta", "date", "Начало ремонта"),
        "actual_finish": _f("data_zaversheniya_remonta", "date", "Завершение ремонта"),
        "planned_pipe_length": _f("len_tube_plan", "float", "Длина труб, план, м"),
        "planned_pipe_diameter": _f("diametr_trub_plan", "float", "Диаметр труб, план, мм"),
        "planned_insulation_area": _f("len_izol_plan", "float", "Изоляция, план, м²"),
        "planned_channel_length": _f("len_channel_plan", "float", "Канал, план, м"),
        "planned_asphalt_area": _f("asfaltirovanie_plan", "float", "Асфальтирование, план, м²"),
        "planned_budget": _f("vydelennye_sredstva_plan", "float", "Средства, план, тыс. тг"),
        "planned_personnel": _f("remontnyj_personal_plan", "int", "Ремонтный персонал, план"),
        "actual_pipe_length": _f("len_tube_cur", "float", "Длина труб, факт, м"),
        "actual_insulation_area": _f("len_izol_cur", "float", "Изоляция, факт, м²"),
        "actual_channel_length": _f("len_channel_cur", "float", "Канал, факт, м"),
        "actual_asphalt_area": _f("asfaltirovanie", "float", "Асфальтирование, факт, м²"),
        "actual_budget": _f("vydelennye_sredstva", "float", "Средства, факт"),
        "actual_personnel": _f("remontnyj_personal", "int", "Ремонтный персонал, факт"),
        "disconnected_consumers": _f("kolichestvo_otklyuchennyh_potrebitelej", "int", "Отключено потребителей"),
        "undelivered_heat": _f("kolichestvo_nedootpushchennoj_teplovoj_energii", "float", "Недоотпуск тепла"),
        "commissioning_order_number": _f("nomer_prikaza", "str", "Номер приказа"),
        "commissioning_order_date": _f("data_prikaza_vvoda_v_ekspluataciyu", "date", "Дата приказа"),
        "commissioning_order_file": _f("prikaz_vvoda_v_ekspluataciyu", "str", "Файл приказа"),
    },
    required_on_create=("name",),
    unique_fields=("name",),
    date_order=(("planned_start", "planned_finish"), ("actual_start", "actual_finish")),
    both_or_none=(("commissioning_order_number", "commissioning_order_date"),),
    deployed_table="remont2deployed",
    documents_table="remontdocuments",
    risk_type=3,
    detach=(("defect", "remontid"),),
    approval=ApprovalSpec(
        flag_column="utverdit",
        date_column="data_utverzhdeniya_plana",
        signer_columns={},
        state_on_approve=("stateid", 2),
        required_fields=(
            "name", "repair_type_id", "category_id", "network_type_id",
            "planned_start", "planned_finish", "planned_pipe_length", "planned_pipe_diameter",
            "planned_insulation_area", "planned_channel_length", "planned_asphalt_area",
            "planned_budget", "planned_personnel",
        ),
        require_contour=True,
        not_applicable_flag=2,
    ),
    # gid6 OnRemontAddPlan / OnRemontAddCurrent
    create_modes={
        "plan": {"remonttypeid": 1, "stateid": 1, "plan_flag": 1, "utverdit": 0},
        "current": {"remonttypeid": 3, "stateid": 2, "utverdit": 2},
    },
    created_at_column="data_osmotra",
)

PRESSURE_TESTS = JournalSpec(
    key="pressure-tests",
    table="opres",
    title="Контур опрессовки",
    fields={
        "name": _f("name", "str", "Наименование"),
        "contour_description": _f("opisaniye_kontura", "str", "Описание контура"),
        "boundary_description": _f("granitsa_razdela", "str", "Граница раздела"),
        "heat_source_id": _f("istochnik_tepla", "int", "Источник тепла", "istochniki_tepla"),
        "test_type_id": _f("opres_typeid", "int", "Тип опрессовки", "opres_types"),
        "trial_kind_id": _f("vid_ispytaniid", "int", "Вид испытания"),
        "state_id": _f("sostoyanie_opresid", "int", "Состояние", "sostoyanie_opres"),
        "responsible_id": _f("responsibleid", "int", "Ответственный", _PEOPLE),
        "subdivision_id": _f("subdivisionid", "int", "Подразделение", "subdivisions"),
        "pump_node_id": _f("nodeoprid1", "int", "Узел опрессовочного насоса", "nodes"),
        "secondary_pump_node_id": _f("nodeoprid2", "int", "Второй узел насоса", "nodes"),
        "pump_object_id": _f("objekt_opressovochnogo_nasosaid", "int", "Объект насоса", "objekt_opressovochnogo_nasosa"),
        "planned_start": _f("data_nachala_plan", "date", "Начало по плану"),
        "planned_finish": _f("data_okonchaniya_plan", "date", "Окончание по плану"),
        "tested_at": _f("date_opres", "timestamp", "Дата проведения"),
        "tested_time": _f("vremya_provedeniya_opressovki", "time", "Время проведения"),
        "duration_minutes": _f("prodolzhitelnost_opressovki", "int", "Продолжительность, мин"),
        "stage_one_pressure": _f("davlenie_opressovki_1_etap", "float", "Давление I этапа"),
        "stage_two_pressure": _f("davlenie_opressovki_2_etap", "float", "Давление II этапа"),
        "cooling_temperature": _f("temperatura_raskholazhivaniya_kontura", "float", "Температура расхолаживания"),
        "inspection_team_count": _f("kolichestvo_zvenjev_obhodchikov", "int", "Звеньев обходчиков"),
        "commission_decision": _f("reshenie_komissii", "str", "Решение комиссии"),
        "report": _f("otchet", "str", "Отчёт"),
        "defects_text": _f("defects", "str", "Текст нарушений"),
        "note": _f("primechanie", "str", "Примечание"),
        "unnotified_consumers": _f("ne_preduprezhdennye_potrebiteli", "str", "Непредупреждённые потребители"),
        "unnotified_consumer_list": _f("spisok_potrev_ne_predupr", "str", "Список непредупреждённых"),
        "excluded_pipelines": _f("spisok_trub_ne_uchav", "str", "Неучаствующие трубопроводы"),
        "act_approved_on": _f("data_utverzhdeniya_akta_ispytanij", "date", "Дата утверждения акта"),
        "act_file": _f("akt_ispytanij", "str", "Файл акта"),
        "test_manager_name": _f("fio_rukovoditel_ispytanij", "str", "Руководитель испытаний"),
        "mode_manager_name": _f("fio_otvetstvennyj_za_obespechenie_rezhimov", "str", "Обеспечение режимов"),
        "switching_manager_name": _f("fio_otvetstvennyj_za_blank_pereklyuchenij", "str", "Бланк переключений"),
        "meter_manager_name": _f("fio_otvetstvennyj_za_ustanovku_manometrov_i_raskhodomerov", "str", "Манометры и расходомеры"),
        "transport_manager_name": _f("fio_otvetstvennyj_za_obespechenie_avtotransportom", "str", "Автотранспорт"),
        "electrical_manager_name": _f("fio_otvetstvennyj_za_obespechenie_raboty_elektrooborudovaniya", "str", "Электрооборудование"),
        "source_safety_manager_name": _f("fio_otvetstvennyj_po_snip_kontura_istochnika_tepla", "str", "Безопасность контура источника"),
        "public_notification_manager_name": _f("fio_otvetstvennyj_za_opoveshchenie_naseleniya_o_ispytaniyah", "str", "Оповещение населения"),
    },
    required_on_create=("name",),
    unique_fields=("name",),
    date_order=(("planned_start", "planned_finish"),),
    deployed_table="opresdeployed",
    documents_table="opresdocuments",
    cascade=(("list_opres_node1", "objid"), ("list_opres_node2", "objid"), ("opresacts", "objid")),
    detach=(("defect", "opresid"),),
    approval=ApprovalSpec(
        flag_column="utverdit",
        date_column="data_utverzhdeniya_plana",
        signer_columns={
            "approver_name": _f("fio_utverzhdaemogo", "str", "ФИО утверждающего"),
            "approver_position_id": _f("dolzhnost_utverzhdaemogoid", "int", "Должность утверждающего", "dolzhnosti"),
            "approver_subdivision_id": _f("podrazdelenie_utverzhdaemogoid", "int", "Подразделение утверждающего", "subdivisions"),
        },
        required_fields=("name", "heat_source_id", "planned_start", "planned_finish"),
        require_contour=True,
    ),
    # gid6 OnOpresAddPlan
    create_modes={"plan": {"vid_ispytaniid": 1, "sostoyanie_opresid": 1, "utverdit": 0}},
    created_at_column="date_opres",
)

INSPECTIONS = JournalSpec(
    key="inspections",
    table="osmotr",
    title="Контур осмотра",
    fields={
        "name": _f("name", "str", "Наименование контура"),
        "inspected_on": _f("data_osmotra", "date", "Дата осмотра"),
        "act_number": _f("nomer_akta", "str", "Номер акта"),
        "suspected_causes": _f("predpolagaemye_prichiny_razrusheniya_izolyacii_korrozii", "str", "Предполагаемые причины"),
        "results": _f("rezultaty_osmotra", "str", "Результаты осмотра"),
        "planned_measures": _f("namechennye_meropriyatiya", "str", "Намеченные мероприятия"),
        "restoration_measures": _f("meropriyatiya_po_vosstanovleniyu_prokladki", "str", "Восстановление прокладки"),
        "note": _f("primechanie", "str", "Примечание"),
        "responsible_id": _f("otvetstvennoe_lico_id", "int", "Ответственный", _PEOPLE),
        "subdivision_id": _f("podrazdelenie_provodivshee_raboty", "int", "Подразделение", "subdivisions"),
        "approver_name": _f("fio_utverzhdaemogo", "str", "ФИО утверждающего"),
        "approver_position_id": _f("dolzhnost_utverzhdaemogoid", "int", "Должность утверждающего", "dolzhnosti"),
        "approver_service_id": _f("sluzhba_utverzhdaemogoid", "int", "Служба утверждающего", "subdivisions"),
        "commission_member_1": _f("fio_1", "str", "Член комиссии 1"),
        "commission_position_1_id": _f("dolzhnost_1", "int", "Должность члена комиссии 1", "dolzhnosti"),
        "commission_member_2": _f("fio_2", "str", "Член комиссии 2"),
        "commission_position_2_id": _f("dolzhnost_2", "int", "Должность члена комиссии 2", "dolzhnosti"),
        "excluded_pipes": _f("spisok_trub_ne_uchav", "str", "Не участвовавшие трубопроводы"),
        "unnotified_consumers": _f("spisok_potrev_ne_predupr", "str", "Не предупреждённые потребители"),
    },
    required_on_create=("name", "inspected_on"),
    unique_fields=("name",),
    deployed_table="osmotrdeployed",
    documents_table="osmotrdocuments",
    document_types_table="vidy_dokumentov_osmotra",
    risk_type=2,
    detach=(("defect", "osmotrid"),),
)

DEFECTS = JournalSpec(
    key="defects",
    table="defect",
    title="Нарушение",
    fields={
        "name": _f("name", "str", "Название"),
        "line_id": _f("lineid", "int", "Трубопровод", "linesobj"),
        "detected_at": _f("data_osmotra", "timestamp", "Дата обнаружения"),
        "detected_time": _f("vremya_osmotra", "time", "Время обнаружения"),
        "description": _f("defectdescription", "str", "Описание повреждения"),
        "report_note": _f("otchet_po_defektu", "str", "Отчёт по дефекту"),
        "repair_started_on": _f("data_nachala_remonta", "date", "Начало ремонта"),
        "repair_finished_on": _f("data_zaversheniya_remonta", "date", "Завершение ремонта"),
        "repair_start_time": _f("vremianachalaremonta", "time", "Время начала ремонта"),
        "repair_finish_time": _f("vremiazaversheniaremonta", "time", "Время завершения ремонта"),
        "source_id": _f("remonttypeid", "int", "Источник", "defecttypes"),
        "state_id": _f("stateid", "int", "Состояние", "statedefect"),
        "category_id": _f("remontcatid", "int", "Категория", "remontcat"),
        "violation_type_id": _f("vid_narusheniyaid", "int", "Вид нарушения", "vid_narusheniya"),
        "pipeline_sign_id": _f("priznak_truboprovoda", "int", "Трубопровод (подача/обратка)", "externalsigns"),
        "subdivision_id": _f("subdivisionid", "int", "Подразделение", "subdivisions"),
        "responsible_id": _f("responsibleid", "int", "Ответственный", _PEOPLE),
        "brigade_id": _f("brigadesid", "int", "Бригада", "brigades"),
        "street_id": _f("ulicaid", "int", "Улица", "ulitsy"),
        "house_number": _f("nomer_doma", "str", "Номер дома"),
        "nearest_chamber_node_id": _f("nodeid_bizhajshej_kamery", "int", "Ближайшая камера", "nodes"),
        "disconnect_node_1_id": _f("nodeid1", "int", "Узел отключения 1", "nodes"),
        "disconnect_node_2_id": _f("nodeid2", "int", "Узел отключения 2", "nodes"),
        "inspection_id": _f("osmotrid", "int", "Осмотр", "osmotr"),
        "pressure_test_id": _f("opresid", "int", "Опрессовка", "opres"),
        "note": _f("primechanie", "str", "Примечание"),
        "liquidation_method": _f("meropriyatiya", "str", "Мероприятия"),
        "excavation_date": _f("data_shurfovki", "date", "Дата шурфовки"),
        "act_number": _f("nomer_akta", "str", "Номер акта"),
        "act_date": _f("data_sostavleniya_akta", "timestamp", "Дата акта"),
        "order_number": _f("nomer_prikaza", "str", "Номер приказа"),
        "commissioning_order_date": _f("data_prikaza_vvoda_v_ekspluataciyu", "date", "Дата приказа"),
        "distance_to_nearest_chamber": _f("rasstoyaniedopovrezhdeniyanachkamery", "float", "Расстояние до камеры, м"),
        "damage_clock_position": _f("tsentrpovrezhdenia", "str", "Центр повреждения"),
        "damage_height": _f("vysotapovrezhdenia", "float", "Высота повреждения"),
        "damage_width": _f("shirinapovrezhdenia", "float", "Ширина повреждения"),
        "damage_area": _f("ploshchadpovrezhdenia", "float", "Площадь повреждения"),
        "patch_width": _f("shirinazaplatki", "float", "Ширина заплатки"),
        "patch_height": _f("vysotazaplatki", "float", "Высота заплатки"),
        "replaced_pipe_length": _f("len_tube_cur", "float", "Заменено труб, м"),
        "replaced_insulation_length": _f("len_izol_cur", "float", "Заменено изоляции, м"),
        "repaired_channel_length": _f("len_channel_cur", "float", "Отремонтировано канала, м"),
        "repair_labor": _f("trudozatratynaremont", "float", "Трудозатраты"),
        "repair_cost": _f("stoimostremonta", "money", "Стоимость ремонта"),
        "disconnected_consumers": _f("kolichestvo_otklyuchennyh_potrebitelej", "int", "Отключено потребителей"),
        "undelivered_heat": _f("kolichestvo_nedootpushchennoj_teplovoj_energii", "float", "Недоотпуск тепла"),
        "recovery_cost": _f("zatraty_na_vosstanovlenie", "money", "Затраты на восстановление"),
        "social_consequences": _f("inye_socialnye_posledstviya", "str", "Социальные последствия"),
    },
    required_on_create=("detected_at",),
    date_order=(("repair_started_on", "repair_finished_on"),),
    both_or_none=(("act_number", "act_date"),),
    documents_table="defectdocuments",
    point_geometry=True,
    cascade=(
        ("defecttube", "objid"), ("defectkamera", "objid"), ("defectchannel", "objid"),
        ("defectmeropr", "objid"), ("defectopis", "objid"), ("defectsforshurfy", "defectid"),
    ),
    created_at_column="data_osmotra",
)

SHURFS = JournalSpec(
    key="shurfs",
    table="shurfy",
    title="Шурф",
    fields={
        "line_id": _f("lineid", "int", "Трубопровод", "linesobj"),
        "purpose_id": _f("naznachenie_vskrid", "int", "Назначение вскрытия", "naznachenie_vskr"),
        "state_id": _f("sostoyanie_shurfaid", "int", "Состояние", "sostoyanie_shurfa"),
        "material_id": _f("materialy_i_mekhanizmyid", "int", "Материалы", "materialy_i_mekhanizmy"),
        "street_id": _f("ulicaid", "int", "Улица", "ulitsy"),
        "house_number": _f("nomer_doma", "str", "Номер дома"),
        "nearest_chamber_node_id": _f("nodeid_bizhajshej_kamery", "int", "Ближайшая камера", "nodes"),
        "planned_start": _f("data_nachala_plan", "date", "Плановое начало"),
        "planned_finish": _f("data_okonchaniya_plan", "date", "Плановое окончание"),
        "actual_start": _f("data_nachala", "date", "Фактическое начало"),
        "actual_finish": _f("data_okonchaniya", "date", "Фактическое окончание"),
        "act_number": _f("nomer_akta", "str", "Номер акта"),
        "act_approved_on": _f("data_utverzhdenija_akta", "date", "Дата утверждения акта"),
        "inspection_results": _f("rezultaty_osmotra", "str", "Результаты осмотра"),
        "planned_measures": _f("namechennye_meropriyatiya", "str", "Намеченные мероприятия"),
        "restoration_measures": _f("meropriyatiya_po_vosstanovleniyu_prokladki", "str", "Восстановление прокладки"),
        "suspected_causes": _f("predpolagaemye_prichiny_razrusheniya_izolyacii", "str", "Предполагаемые причины"),
        "note": _f("primechanie", "str", "Примечание"),
        "distance_to_nearest_chamber": _f("rasstoyanie_do_blizhajshej_kamery", "float", "Расстояние до камеры, м"),
        "inspection_length": _f("dlina_osmotra", "float", "Длина осмотра, м"),
        "laying_depth": _f("glubina_zalozheniya", "float", "Глубина заложения, м"),
        "distance_to_rails": _f("rasstoyanie_do_relsov", "float", "Расстояние до рельсов, м"),
        "nearby_electric_transport": _f("nalichie_vblizi_elektrificirovannogo_transporta", "int", "Электротранспорт рядом"),
        "control_cut_location": _f("mesto_kontrolnoj_vyrezki_truboprovoda", "str", "Место контрольной вырезки"),
        "cut_results": _f("rezultaty_vyrezki", "str", "Результаты вырезки"),
        "commission_member_1": _f("fio_1", "str", "Член комиссии 1"),
        "commission_position_1_id": _f("dolzhnost_1", "int", "Должность члена комиссии 1", "dolzhnosti"),
        "commission_member_2": _f("fio_2", "str", "Член комиссии 2"),
        "commission_position_2_id": _f("dolzhnost_2", "int", "Должность члена комиссии 2", "dolzhnosti"),
    },
    date_order=(("planned_start", "planned_finish"), ("actual_start", "actual_finish")),
    documents_table="shurfdocuments",
    point_geometry=True,
    cascade=(
        ("defectsforshurfy", "objid"), ("vidy_elementov_for_shurfy", "objid"),
        ("nalichie_vblizi_kommunikacij_for_shurfy", "objid"),
    ),
    approval=ApprovalSpec(
        flag_column="utverdit",
        date_column="data_utverzhdeniya_plana_shurfovok",
        # gid6 OnShurfUtverditALL
        signer_columns={
            "approval_purpose": _f("naznachenie", "str", "Назначение"),
            "approver_name": _f("fio_utverzhdaemogo", "str", "ФИО утверждающего"),
            "approver_position_id": _f("dolzhnost_utverzhdaemogoid", "int", "Должность утверждающего", "dolzhnosti"),
            "approver_service_id": _f("sluzhba_utverzhdaemogoid", "int", "Служба утверждающего", "subdivisions"),
            "reviewer_name": _f("fio_viziruemogo_1", "str", "ФИО визирующего"),
            "reviewer_position_id": _f("dolzhnost_viziruemogoid_1", "int", "Должность визирующего", "dolzhnosti"),
        },
        required_fields=("planned_start", "planned_finish"),
    ),
    # gid6 OnRemontPovrShurfAdd (плановый) / OnRemontPovrShurfAddNeplan
    create_modes={
        "plan": {"naznachenie_vskrid": 1, "sostoyanie_shurfaid": 1, "utverdit": 0},
        "unplanned": {"sostoyanie_shurfaid": 2, "utverdit": 0},
    },
)

JOURNALS: dict[str, JournalSpec] = {
    spec.key: spec for spec in (DEFECTS, SHURFS, INSPECTIONS, REPAIRS, PRESSURE_TESTS)
}

# Все таблицы, которых касается запись журналов (allow-list для sql_ident.resolve_table)
JOURNAL_TABLES: frozenset[str] = frozenset(
    {s.table for s in JOURNALS.values()}
    | {s.deployed_table for s in JOURNALS.values() if s.deployed_table}
    | {s.documents_table for s in JOURNALS.values() if s.documents_table}
    | {s.document_types_table for s in JOURNALS.values()}
    | {t for s in JOURNALS.values() for t, _ in s.cascade}
    | {t for s in JOURNALS.values() for t, _ in s.detach}
    | {f.ref for s in JOURNALS.values() for f in s.fields.values() if f.ref}
    | {
        f.ref
        for s in JOURNALS.values()
        if s.approval
        for f in s.approval.signer_columns.values()
        if f.ref
    }
    | {"linesobj", "heatpipesections", "faktory_riska_truboprovoda"}
)


def get_spec(key: str) -> JournalSpec:
    spec = JOURNALS.get(key)
    if spec is None:
        raise KeyError(key)
    return spec


def spec_for_table(table: str) -> Optional[JournalSpec]:
    table = table.lower()
    for spec in JOURNALS.values():
        if spec.table == table:
            return spec
    return None


def describe(spec: JournalSpec) -> dict[str, Any]:
    """Описание журнала для веб-формы: какие поля писать и каким типом."""
    approval = None
    if spec.approval:
        approval = {
            "signers": {
                key: {"kind": f.kind, "label": f.label, "ref": f.ref}
                for key, f in spec.approval.signer_columns.items()
            },
            "required_fields": list(spec.approval.required_fields),
            "require_contour": spec.approval.require_contour,
            "sets_state": spec.approval.state_on_approve[1] if spec.approval.state_on_approve else None,
        }
    return {
        "key": spec.key,
        "title": spec.title,
        "fields": {
            key: {"kind": f.kind, "label": f.label, "ref": f.ref}
            for key, f in spec.fields.items()
        },
        "required_on_create": list(spec.required_on_create),
        "unique_fields": list(spec.unique_fields),
        "create_modes": sorted(spec.create_modes),
        "has_contour": spec.deployed_table is not None,
        "has_documents": spec.documents_table is not None,
        "has_point_geometry": spec.point_geometry,
        "approval": approval,
    }

"""Карточки объектов как в десктопе gid8: видимость полей (.vis, схема потребителя), подписи, tab/gid8."""
import asyncio

from database.db import hidden_fields, read_cxema
from utils.ini import storage


def _run(coro):
    return asyncio.run(coro)


def test_read_cxema_like_desktop():
    # зависимая элеваторная, без ГВС, с вентиляцией (n1 = 1, n2 = 4)
    assert read_cxema('1.4') == {'elev': '1', 'otop': 'z', 'gvs': '', 'gvs_all': '', 'vent': '1', 'rez': '0'}
    # независимая СО, закрытая смешанная ГВС
    assert read_cxema('4.9') == {'elev': '0', 'otop': 'n', 'gvs': 'sm', 'gvs_all': '1', 'vent': '0', 'rez': '0'}
    # открытая ГВС из обратного с рециркуляцией
    assert read_cxema('7.6')['rez'] == '1'
    # только вентиляция
    assert read_cxema('2.1')['vent'] == '1' and read_cxema('2.1')['otop'] == ''
    # «C» — без отопления
    assert read_cxema('C5.5')['otop'] == ''
    assert read_cxema('') is None


def test_vis_file_parsed_by_indent():
    rules = _run(storage.read_vis('realConsumers'))
    assert 'calchldep' in rules['otop']['z'] and 'calchlindep' in rules['otop']['n']
    # закомментированные «--» строки не попадают
    assert 'calcthrustlosac' not in rules['vent']['1']


def test_realconsumer_fields_hidden_by_scheme():
    rules = _run(storage.read_vis('realConsumers'))
    hidden = hidden_fields('realConsumers', rules, {'schemenum': '1.4'})
    assert 'calchlindep' in hidden          # независимая СО скрыта
    assert 'calchldep' not in hidden        # зависимая видна
    assert 'elevatornuminst' not in hidden  # элеваторная схема
    assert 'avghlgvsclosemix' in hidden     # ГВС нет
    assert 'calchlventil' not in hidden     # вентиляция есть
    hidden = hidden_fields('realConsumers', rules, {'schemenum': '4.9'})
    assert 'calchlindep' not in hidden and 'calchldep' in hidden
    assert 'avghlgvsclosemix' not in hidden and 'avghlgvscloseparall' in hidden
    assert 'elevatornuminst' in hidden


def test_field_rule_uses_code_value():
    rules = _run(storage.read_vis('heatPipeSections'))
    assert 'mestn' in hidden_fields('heatPipeSections', rules, {'pipesectstateidflow': 1})
    assert 'mestn' not in hidden_fields('heatPipeSections', rules, {'pipesectstateidflow': -1})


def test_heatsource_card_from_gid8_with_labels():
    cols = _run(storage.read_tab2('heatSources'))
    assert '!1 Данные для расчета температурного графика' in cols and 't1_r' in cols
    labels = _run(storage.read_tab_labels('heatSources'))
    assert labels['tn_5'] == 'Температура наружного воздуха для отопления'
    assert 'hsourcepower' not in labels  # без подписи в строке — из справочника

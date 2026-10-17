"""Окно свойств: правка карточки как в десктопе (database/card_edit.py, routers/card_edit.py)."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from database import card_edit as ce
from database import typed_edit as te
from utils.ini import storage


def _run(coro):
    return asyncio.run(coro)


def test_fun_name():
    assert ce.fun_name('Table "sprav","14_Шероховатость стальных труб",2') == 'Table'
    assert ce.fun_name('diameter_std') == 'diameter_std'
    assert ce.fun_name('Местные сопротивления') == 'Местные сопротивления'
    assert ce.fun_name(None) is None


def test_readonly_columns_like_desktop_filldvalues():
    # признак подачи — только в колонке подачи, обратки — только в колонке обратки
    assert ce.readonly_columns('line', 'heatPipeSections', 'pipeSectStateIDret', 2, None, True) == [True, False]
    assert ce.readonly_columns('line', 'heatPipeSections', 'pipeSectStateIDflow', 2, None, True) == [False, True]
    # у одиночного участка — правится
    assert ce.readonly_columns('line', 'heatPipeSections', 'pipeSectStateIDflow', 1, None, True) == [False]
    # ReadOnly из .fun, поля узлов в карточке линии, код/имя узла линии
    assert ce.readonly_columns('line', 'heatPipeSections', 'inventNumber', 2, 'ReadOnly', True) == [True, True]
    assert ce.readonly_columns('line', 'nodes', 'externalNodeName', 2, None, True) == [True, True]
    assert ce.readonly_columns('line', 'linesobj', 'externalNodeName', 1, None, True) == [True]
    assert ce.readonly_columns('line', 'heatPipeSections', 'diameterCondit', 2, 'diameter_std', True) == [False, False]
    assert ce.readonly_columns('line', 'heatPipeSections', 'x', 1, None, False) == [True]


def test_desktop_sql_like_ispr_sql():
    q = ('SELECT TOP 2000000 hs.id, hs.name FROM heatSources hs JOIN nodes n ON n.id=hs.nodeID '
         'WHERE n.fileID in ($fragments$) \\n--AND_TXT AND hs.name ilike \'%$txt$%\' \\n  ORDER BY name')
    out = ce.desktop_sql(q, fileids=[3, 7], row_id=5, table='externalCodes')
    assert 'TOP' not in out and 'AND_TXT' not in out and '$' not in out
    assert 'n.fileID in (3,7)' in out
    assert ce.desktop_sql('SELECT TOP 10 id, name FROM t', fileids=[], row_id=None, table='t') == \
        'SELECT id, name FROM t LIMIT 10'
    # без фрагментов — NULL (пустой список), не синтаксическая ошибка
    assert 'in (NULL)' in ce.desktop_sql('SELECT id, name FROM t WHERE f in ($fragments$)', fileids=[], row_id=None, table='t')
    # включения new_baza и неизвестные подстановки — список по таблице
    assert ce.desktop_sql('select n.id from (###select_node###) n', fileids=[1], row_id=1, table='t') is None
    assert ce.desktop_sql("SELECT id, name FROM nodeTypes WHERE PATINDEX('%$node_type$%',visibles) > 0",
                          fileids=[1], row_id=1, table='nodes') is None


def test_inline_options_like_desktop_combobox(monkeypatch):
    monkeypatch.setitem(storage.map_lookup, ('heatpipesections', 'tubingtypeid'),
                        ('heatPipeSections', 'tubingTypeID', 'tubingTypes', 'id', 'name', 0))
    monkeypatch.setitem(storage.map_lookup2, 'tubingtypes', {'2': 'бесканальная', '10': 'прочее', '1': 'канальная'})
    res = _run(ce.field_options(None, 'heatPipeSections', 'tubingTypeID'))
    assert res['source'] == 'list'
    # как std::map<int, QString> десктопа — по возрастанию кода
    assert [i['value'] for i in res['items']] == [1, 2, 10]
    assert _run(ce.field_options(None, 'heatPipeSections', 'tubingTypeID', q='БЕСК'))['items'] == \
        [{'value': 2, 'title': 'бесканальная'}]
    with pytest.raises(te.TypedEditError) as exc:
        _run(ce.field_options(None, 'heatPipeSections', 'nosuchfield'))
    assert exc.value.status == 404


def test_save_card_rejects_tables_outside_card():
    with pytest.raises(te.TypedEditError) as exc:
        _run(ce.save_card(None, [{'table': 'users', 'id': 1, 'field': 'role', 'value': 'admin'}], {}, audit_row=None))
    assert exc.value.status == 403
    with pytest.raises(te.TypedEditError) as exc:
        _run(ce.save_card(None, [{'table': 'heatPipeSections', 'field': 'x', 'value': 1}], {}, audit_row=None))
    assert exc.value.status == 422


def test_read_fun_and_disable_from_desktop_files():
    funs = _run(storage.read_fun('heatPipeSections'))
    assert funs['diametercondit'] == 'diameter_std'
    assert funs['inventnumber'] == 'ReadOnly'
    assert 'locallosesshare' not in funs  # «-localLosesShare» в .fun закомментирована
    assert _run(storage.read_fun('nodes', 'validate'))['externalnodename'] == 'NotNull'
    dis = _run(storage.read_disable('realConsumers'))
    assert 'throtstagesignid' in dis['hydromodesignid']['1']


def test_card_edit_routes_require_editor(monkeypatch):
    import main
    from auth import create_access_token

    def bearer(role):
        return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}

    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    body = {'changes': [{'table': 'heatPipeSections', 'id': 1, 'field': 'x', 'value': 1}]}
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    assert client.put('/api/v1/card-edit', json=body, headers=bearer("viewer")).status_code == 403
    # правка выключена на сервере — 503 и для редактора
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    assert client.put('/api/v1/card-edit', json=body, headers=bearer("editor")).status_code == 503
    # пустой список изменений — ошибка клиента
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    assert client.put('/api/v1/card-edit', json={'changes': []}, headers=bearer("editor")).status_code == 422


def test_transl_like_desktop_any_cpp():
    assert ce.transl('14_Шероховатость стальных труб') == '14_sherohovatost_stalnyh_trub'
    assert ce.transl('02_Теплоотдача от изоляции к окружаемому воздуху') == \
        '02_teplootdacha_ot_izolyatsii_k_okruzhaemomu_vozduhu'
    assert ce.transl('06_Состояние изоляции') == '06_sostoyanie_izolyatsii'
    assert ce.parse_table_fun('Table "sprav","06_Состояние изоляции",2') == ('sprav', '06_Состояние изоляции', 2)
    assert ce.parse_table_fun('diameter_std') is None


def test_helpers_flagged_and_unknown_helper_is_404():
    assert 'diameter_std' in ce.HELPER_FUNS and 'Местные сопротивления' in ce.HELPER_FUNS
    with pytest.raises(te.TypedEditError) as exc:
        _run(ce.field_helper(None, 'heatPipeSections', 'inventNumber'))
    assert exc.value.status == 404
    # поле без ms_rs — зависимых полей нет; участок РС сбрасывает магистраль и участок МС
    assert _run(ce.after_change(None, 'heatPipeSections', 'diameterCondit', '1')) == {'set': {}}
    res = _run(ce.after_change(None, 'heatPipeSections', 'distSite', '5'))
    assert set(res['set']) == {'magistral', 'magistralSite'}
    assert _run(ce.after_change(None, 'heatPipeSections', 'magistral', '5'))['set'] == \
        {'distSite': {'value': None, 'title': None}}


def test_batch_selection_limits():
    from database import card_batch as cb

    with pytest.raises(te.TypedEditError) as exc:
        _run(cb.line_columns(None, []))
    assert exc.value.status == 422
    with pytest.raises(te.TypedEditError) as exc:
        _run(cb.line_columns(None, list(range(1, cb.MAX_LINES + 2))))
    assert exc.value.detail["code"] == "too_many"


def test_batch_routes_require_editor(monkeypatch):
    import main
    from auth import create_access_token

    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    client = TestClient(main.app)
    viewer = {"Authorization": "Bearer " + create_access_token(username="t-viewer", role="viewer")}
    body = {"ids": [1], "changes": [{"table": "linesobj", "id": 1, "field": "hydroRes", "value": 1}]}
    assert client.post('/api/v1/card-edit/batch/preview', json=body, headers=viewer).status_code == 403
    assert client.post('/api/v1/card-edit/batch/apply', json=body, headers=viewer).status_code == 403
    editor = {"Authorization": "Bearer " + create_access_token(username="t-editor", role="editor")}
    assert client.post('/api/v1/card-edit/batch/apply', json={"ids": [1], "changes": []}, headers=editor).status_code == 422


def test_template_values_validated_like_card():
    from database import card_template as ct

    with pytest.raises(te.TypedEditError) as exc:
        _run(ct.clean_values(None, 'node', {'nodes': {'x': 1}}))
    assert exc.value.detail["code"] == "bad_kind"
    with pytest.raises(te.TypedEditError) as exc:
        _run(ct.clean_values(None, 'line', {'users': {'role': 'admin'}}))
    assert exc.value.status == 422 and exc.value.detail["code"] == "table_not_editable"


def test_template_routes_require_editor(monkeypatch):
    import main
    from auth import create_access_token

    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    client = TestClient(main.app)
    viewer = {"Authorization": "Bearer " + create_access_token(username="t-viewer", role="viewer")}
    assert client.get('/api/v1/card-templates', headers=viewer).status_code == 403
    body = {"kind": "line", "name": "t", "values": {"linesobj": {"hydroRes": 1}}}
    assert client.post('/api/v1/card-templates', json=body, headers=viewer).status_code == 403
    assert client.post('/api/v1/card-templates/1/apply', json={"ids": [1]}, headers=viewer).status_code == 403

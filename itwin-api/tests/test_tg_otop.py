"""OTOP curve unit tests (no database)."""

from database.tg_otop import OtopError, calculate_otop_curve, calculate_otop_point


ALMATY_LIKE = {
    "tn_5": -25,
    "tn_1": 8,
    "tvn_r": 18,
    "t1_r": 130,
    "t2_r": 70,
    "t3_r": 95,
    "tvb_tr": 18,
    "uf": 0,
    "t1_2r": 70,
    "t1_4r": 150,
    "t2_2r": 40,
    "q_r": 1,
    "v": 0,
}


def test_otop_point_count():
    points = calculate_otop_curve(ALMATY_LIKE)
    assert len(points) == 34  # -25 … 8 inclusive
    assert points[0]["tn"] == -25
    assert points[-1]["tn"] == 8


def test_otop_colder_means_hotter_supply():
    points = calculate_otop_curve(ALMATY_LIKE)
    by_tn = {p["tn"]: p for p in points}
    assert by_tn[-25]["t1"] > by_tn[8]["t1"]
    assert by_tn[-25]["t2"] > by_tn[8]["t2"]


def test_otop_design_near_t1_r():
    """At design outdoor, supply should sit near TAURP (cutoffs allowing)."""
    cold = calculate_otop_point(
        tn=-25,
        thor=-25,
        tvr=18,
        taurp=130,
        tauro=70,
        taurs=95,
        tb=18,
        uf=(130 - 95) / (95 - 70),
        tsmin=70,
        tsmax=150,
        t2min=40,
        qmax=100,
        wind=0,
    )
    assert 115 <= cold["t1"] <= 135
    assert 60 <= cold["t2"] <= 80
    assert cold["t1"] > cold["t3"] > cold["t2"]


def test_otop_rejects_bad_range():
    bad = dict(ALMATY_LIKE, tn_1=-30)
    try:
        calculate_otop_curve(bad)
        assert False, "expected OtopError"
    except OtopError:
        pass


import pytest

from sety.tg.tg1 import CalculateOT1, make_tg


@pytest.mark.parametrize("uf", [0, 1.4])
@pytest.mark.parametrize("srezki", [False, True])
def test_otop_curve_matches_desktop_tg1(uf, srezki):
    """Кривая совпадает с десктопным sety/tg/tg1.py (CalculateOT1) по всем точкам."""
    params = dict(ALMATY_LIKE, uf=uf)
    if not srezki:
        params.update({"t1_2r": 0, "t1_4r": 200, "t2_2r": 0})
    web = {p["tn"]: p for p in calculate_otop_curve(params)}
    tg = make_tg(params)
    tg.QMAX = 100.0  # make_tg берёт QMAX из пустого ключа; в вебе по умолчанию 100 / q_r
    for tn, point in web.items():
        tau01, tau02, tau03, tb, qo, tau01v = CalculateOT1(tg, tn, True)
        assert point["t1"] == pytest.approx(tau01, abs=0.051), tn
        assert point["t2"] == pytest.approx(tau02, abs=0.051), tn
        assert point["t3"] == pytest.approx(tau03, abs=0.051), tn

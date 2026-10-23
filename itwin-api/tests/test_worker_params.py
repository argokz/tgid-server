"""Диапазоны числовых параметров sety (worker.validate_sety_params): -Tn, -iter, -fileID."""

import pytest

from worker import SETY_NUMERIC_RANGES, validate_sety_params


@pytest.mark.parametrize("params", [
    "-fileID 74 -Tn -25 -iter 20",
    "-fileID 74 -Tn=-25.5",
    "-fileID 74 -Tn 40 -iter 1",
    "-fileID 74 -Tn -60 -iter 200",
])
def test_sety_numeric_params_in_range(params):
    assert validate_sety_params(params)


@pytest.mark.parametrize("params, flag", [
    ("-fileID 74 -Tn -70", "-Tn"),
    ("-fileID 74 -Tn 41", "-Tn"),
    ("-fileID 74 -iter 0", "-iter"),
    ("-fileID 74 -iter 201", "-iter"),
    ("-fileID 0", "-fileID"),
])
def test_sety_numeric_params_out_of_range(params, flag):
    with pytest.raises(ValueError, match=f"{flag}.*диапазон"):
        validate_sety_params(params)


@pytest.mark.parametrize("params", ["-fileID 74 -Tn", "-fileID 74 -Tn abc", "-Tn -leto"])
def test_sety_numeric_params_need_value(params):
    with pytest.raises(ValueError, match="-Tn"):
        validate_sety_params(params)


def test_sety_numeric_ranges_cover_tn_and_iter():
    assert {"-Tn", "-iter", "-fileID"} <= set(SETY_NUMERIC_RANGES)

"""Key normalization and value parsing in _parse."""

from __future__ import annotations

from pykosis._parse import _snake, _to_float, map_rows


def test_snake_lowercases_upper_snake():
    assert _snake("C1_NM_ENG") == "c1_nm_eng"
    assert _snake("PRD_DE") == "prd_de"
    assert _snake("LST_CHN_DE") == "lst_chn_de"


def test_snake_splits_camelcase():
    assert _snake("writingPurps") == "writing_purps"
    assert _snake("statsNm") == "stats_nm"
    assert _snake("examinObjArea") == "examin_obj_area"


def test_snake_renames_dt_to_data_value():
    assert _snake("DT") == "data_value"


def test_to_float_parses_numbers_and_strips_commas():
    assert _to_float("83.5") == 83.5
    assert _to_float("1,234") == 1234.0


def test_to_float_missing_markers_become_none():
    assert _to_float("") is None
    assert _to_float("-") is None
    assert _to_float(None) is None
    assert _to_float("X") is None  # a statistical symbol, not a number


def test_map_rows_maps_keys_and_value():
    rows = map_rows([{"ORG_ID": "101", "ITM_NM": "기대수명", "DT": "83.5"}])
    assert rows == [{"org_id": "101", "itm_nm": "기대수명", "data_value": 83.5}]

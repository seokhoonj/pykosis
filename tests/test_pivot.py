"""pivot_items: long observations reshaped to one column per item."""

from __future__ import annotations

import pytest

from pykosis import pivot_items


def _rows() -> list[dict]:
    # Two periods, two items each -- the long shape fetch_data returns.
    return [
        {"c1": "00", "c1_nm": "전국", "prd_de": "2020",
         "itm_id": "T1", "itm_nm": "기대수명", "unit_nm": "년", "data_value": 83.5},
        {"c1": "00", "c1_nm": "전국", "prd_de": "2020",
         "itm_id": "T2", "itm_nm": "남자", "unit_nm": "년", "data_value": 80.5},
        {"c1": "00", "c1_nm": "전국", "prd_de": "2021",
         "itm_id": "T1", "itm_nm": "기대수명", "unit_nm": "년", "data_value": 83.6},
        {"c1": "00", "c1_nm": "전국", "prd_de": "2021",
         "itm_id": "T2", "itm_nm": "남자", "unit_nm": "년", "data_value": 80.6},
    ]


def test_pivot_by_item_name():
    wide = pivot_items(_rows())
    assert wide == [
        {"c1": "00", "c1_nm": "전국", "prd_de": "2020", "기대수명": 83.5, "남자": 80.5},
        {"c1": "00", "c1_nm": "전국", "prd_de": "2021", "기대수명": 83.6, "남자": 80.6},
    ]


def test_pivot_by_item_id():
    wide = pivot_items(_rows(), label="itm_id")
    assert wide[0]["T1"] == 83.5
    assert wide[0]["T2"] == 80.5
    assert "기대수명" not in wide[0]


def test_pivot_by_english_item_name():
    english = {"T1": "Life expectancy", "T2": "Male"}
    rows = [{**row, "itm_nm_eng": english[row["itm_id"]]} for row in _rows()]
    wide = pivot_items(rows, label="itm_nm_eng")
    assert wide[0]["Life expectancy"] == 83.5
    assert wide[0]["Male"] == 80.5


def test_missing_item_for_a_key_is_none():
    rows = _rows()[:3]  # drop 2021/남자
    wide = pivot_items(rows)
    assert wide[1] == {"c1": "00", "c1_nm": "전국", "prd_de": "2021",
                       "기대수명": 83.6, "남자": None}


def test_empty_input_returns_empty():
    assert pivot_items([]) == []


def test_bad_label_rejected():
    with pytest.raises(ValueError):
        pivot_items(_rows(), label="nope")


def test_label_absent_from_data_raises():
    with pytest.raises(ValueError):
        pivot_items([{"c1": "00", "data_value": 1.0}], label="itm_nm")


def test_non_string_label_value_row_is_skipped():
    # A row whose label value is not a string cannot name a column; it drops out
    # rather than crashing, leaving the well-formed rows pivoted normally.
    rows = _rows() + [{"c1": "00", "c1_nm": "전국", "prd_de": "2022",
                       "itm_id": "T1", "itm_nm": None, "data_value": 83.7}]
    wide = pivot_items(rows)
    assert [row["prd_de"] for row in wide] == ["2020", "2021"]


def test_duplicate_label_with_conflicting_value_raises():
    # Two rows share the (c1, prd_de) key and the same itm_nm but differ in value --
    # itm_nm is not a unique label here, so the pivot refuses rather than silently
    # dropping one; pivoting on itm_id would separate them.
    rows = [
        {"c1": "00", "prd_de": "2020", "itm_nm": "기대수명", "data_value": 83.5},
        {"c1": "00", "prd_de": "2020", "itm_nm": "기대수명", "data_value": 99.9},
    ]
    with pytest.raises(ValueError):
        pivot_items(rows)

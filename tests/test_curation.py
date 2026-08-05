"""The curated 100대 지표 tree: named access resolves to a table and fetches it."""

from __future__ import annotations

import httpx

from pykosis import KOSIS


def _handler(responses: list, recorded: list[httpx.Request]):
    remaining = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=remaining.pop(0))

    return httpx.MockTransport(handle)


def test_indicator_carries_source_table():
    kosis = KOSIS("TESTKEY", transport=_handler([], []))
    spec = kosis.population.total_fertility_rate.spec
    assert (spec.org_id, spec.tbl_id) == ("101", "DT_1B8000H")
    assert spec.name_ko == "합계출산율"
    assert spec.path == "population.total_fertility_rate"


def test_indicator_fetch_hits_its_table_with_its_frequency():
    recorded: list[httpx.Request] = []
    row = {"ORG_ID": "101", "TBL_ID": "DT_1J22001", "PRD_DE": "202401", "DT": "119.8"}
    kosis = KOSIS("TESTKEY", transport=_handler([[row]], recorded))
    rows = kosis.income_consumption.consumer_price_index.fetch()
    assert rows[0]["data_value"] == 119.8
    url = recorded[0].url
    assert url.params["orgId"] == "101"
    assert url.params["tblId"] == "DT_1J22001"
    assert url.params["prdSe"] == "M"  # CPI is monthly


def test_fetch_sends_pinned_obj_levels_without_escalating():
    recorded: list[httpx.Request] = []
    row = {"ORG_ID": "101", "TBL_ID": "DT_1IN1502", "PRD_DE": "2023", "DT": "21400000"}
    kosis = KOSIS("TESTKEY", transport=_handler([[row]], recorded))
    rows = kosis.population.households.fetch()  # spec pins obj_levels=("00",)
    assert rows[0]["data_value"] == 21400000.0
    assert len(recorded) == 1  # pinned -> one call, no err=20 escalation loop
    params = recorded[0].url.params
    assert params["objL1"] == "00"
    assert "objL2" not in params


def test_fetch_escalates_obj_levels_on_missing_objl():
    recorded: list[httpx.Request] = []
    missing = {"err": "20", "errMsg": "필수요청변수값이 누락되었습니다."}
    row = {"ORG_ID": "101", "TBL_ID": "DT_1B8000H", "PRD_DE": "2023", "DT": "0.72"}
    kosis = KOSIS("TESTKEY", transport=_handler([missing, missing, [row]], recorded))
    rows = kosis.population.total_fertility_rate.fetch()  # whole-table, no pins
    assert rows[0]["data_value"] == 0.72
    assert len(recorded) == 3  # objL1, then +objL2, then +objL3 succeeds
    params = recorded[-1].url.params
    assert params["objL1"] == "ALL"
    assert params["objL2"] == "ALL"
    assert params["objL3"] == "ALL"


def test_every_group_and_indicator_is_reachable():
    kosis = KOSIS("TESTKEY", transport=_handler([], []))
    groups = ["population", "economy", "environment_energy", "health_welfare",
              "education_labor", "income_consumption", "leisure", "housing_transport",
              "crime_safety", "industry"]
    total = 0
    for group_name in groups:
        group = getattr(kosis, group_name)
        indicators = [v for v in vars(group).values() if hasattr(v, "spec")]
        assert indicators, f"{group_name} has no indicators"
        total += len(indicators)
    assert total == 100  # all of KOSIS's 100대 지표


def test_group_cached():
    kosis = KOSIS("TESTKEY", transport=_handler([], []))
    assert kosis.population is kosis.population  # cached_property

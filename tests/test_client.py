"""Client behavior against a mocked KOSIS, exercised without a network."""

from __future__ import annotations

import json

import httpx
import pytest

from pykosis import (
    KOSIS,
    Frequency,
    IndicatorSection,
    KOSISAuthError,
    KOSISConfigError,
    KOSISNetworkError,
    KOSISRateLimitError,
    KOSISResponseError,
    ViewCode,
)


def _handler(responses: list, recorded: list[httpx.Request]):
    """Return a MockTransport handler that replays ``responses`` in order."""
    remaining = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json=remaining.pop(0))

    return httpx.MockTransport(handle)


def _client(responses: list, recorded: list | None = None) -> KOSIS:
    recorded = [] if recorded is None else recorded
    return KOSIS("TESTKEY", transport=_handler(responses, recorded))


# -- config ----------------------------------------------------------------


def test_missing_api_key_raises_config_error(monkeypatch, tmp_path):
    monkeypatch.delenv("KOSIS_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # empty -- no credentials file
    with pytest.raises(KOSISConfigError):
        KOSIS()


def test_api_key_read_from_environment(monkeypatch):
    monkeypatch.setenv("KOSIS_API_KEY", "FROMENV")
    kosis = KOSIS(transport=_handler([[]], []))
    assert kosis._api_key == "FROMENV"


def test_repr_never_shows_key():
    assert "TESTKEY" not in repr(_client([[]]))


# -- fetch_list ------------------------------------------------------------


def test_fetch_list_maps_rows_and_builds_request():
    recorded: list[httpx.Request] = []
    kosis = _client([[{"VW_CD": "MT_ZTITLE", "LIST_ID": "F", "ORG_ID": "101",
                       "TBL_ID": "DT_1B42", "TBL_NM": "생명표"}]], recorded)
    rows = kosis.fetch_list(view_code="MT_ZTITLE", parent_list_id="F")

    assert rows == [{"vw_cd": "MT_ZTITLE", "list_id": "F", "org_id": "101",
                     "tbl_id": "DT_1B42", "tbl_nm": "생명표"}]
    url = recorded[0].url
    assert url.path == "/openapi/statisticsList.do"
    assert url.params["method"] == "getList"
    assert url.params["vwCd"] == "MT_ZTITLE"
    assert url.params["parentListId"] == "F"
    assert url.params["apiKey"] == "TESTKEY"
    assert url.params["format"] == "json"


# -- search ----------------------------------------------------------------


def test_search_builds_paging_and_sort():
    recorded: list[httpx.Request] = []
    kosis = _client([[{"ORG_ID": "101", "TBL_ID": "DT_1B42", "TBL_NM": "생명표"}]],
                    recorded)
    rows = kosis.search("생명표", page=2, page_size=10, sort="DATE",
                        org_id="101")

    assert rows[0]["tbl_id"] == "DT_1B42"
    url = recorded[0].url
    assert url.path == "/openapi/statisticsSearch.do"
    assert url.params["searchNm"] == "생명표"
    assert url.params["startCount"] == "2"
    assert url.params["resultCount"] == "10"
    assert url.params["sort"] == "DATE"
    assert url.params["orgId"] == "101"


# -- fetch_data ------------------------------------------------------------


def _data_row(**overrides):
    row = {"ORG_ID": "101", "TBL_ID": "DT_1B42", "TBL_NM": "생명표",
           "PRD_SE": "Y", "PRD_DE": "2020", "ITM_NM": "기대수명",
           "UNIT_NM": "년", "DT": "83.5"}
    row.update(overrides)
    return row


def test_fetch_data_parses_value_and_defaults_recent_window():
    recorded: list[httpx.Request] = []
    kosis = _client([[_data_row()]], recorded)
    rows = kosis.fetch_data(org_id="101", tbl_id="DT_1B42")

    assert rows[0]["data_value"] == 83.5
    assert isinstance(rows[0]["data_value"], float)
    url = recorded[0].url
    assert url.path == "/openapi/Param/statisticsParameterData.do"
    assert url.params["prdSe"] == "Y"
    assert url.params["orgId"] == "101"
    assert url.params["tblId"] == "DT_1B42"
    assert url.params["itmId"] == "ALL"
    assert url.params["objL1"] == "ALL"
    assert url.params["newEstPrdCnt"] == "3"
    assert url.params["prdInterval"] == "1"


def test_fetch_data_period_window_uses_start_end():
    recorded: list[httpx.Request] = []
    kosis = _client([[_data_row()]], recorded)
    kosis.fetch_data(
        org_id="101", tbl_id="DT_1B42", frequency="M", start_period="202001")
    url = recorded[0].url
    assert url.params["prdSe"] == "M"
    assert url.params["startPrdDe"] == "202001"
    assert url.params["endPrdDe"] == "202001"  # end defaults to start
    assert "newEstPrdCnt" not in url.params


def test_fetch_data_end_without_start_raises_value_error():
    kosis = _client([[_data_row()]])
    with pytest.raises(ValueError):
        kosis.fetch_data(org_id="101", tbl_id="DT_1B42", end_period="2020")


def test_fetch_data_obj_levels_sends_first_and_nonempty_only():
    recorded: list[httpx.Request] = []
    kosis = _client([[_data_row()]], recorded)
    kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l2="ALL")
    url = recorded[0].url
    assert url.params["objL1"] == "ALL"
    assert url.params["objL2"] == "ALL"
    assert "objL3" not in url.params  # empty higher levels are dropped


def test_fetch_data_blank_value_becomes_none():
    kosis = _client([[_data_row(DT="-")]])
    rows = kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    assert rows[0]["data_value"] is None


def test_fetch_data_error_object_raises_response_error():
    kosis = _client(
        [{"err": "20", "errMsg": "필수요청변수값이 누락되었습니다. (objL)"}])
    with pytest.raises(KOSISResponseError) as info:
        kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    assert info.value.code == "20"


def test_auth_error_from_code_11():
    # Verified live: a rejected key returns err "11", "유효하지 않은 인증KEY입니다."
    kosis = _client([{"err": "11", "errMsg": "유효하지 않은 인증KEY입니다."}])
    with pytest.raises(KOSISAuthError):
        kosis.fetch_list()


def test_non_auth_vendor_error_stays_response_error():
    kosis = _client([{"err": "20", "errMsg": "required objL is missing"}])
    with pytest.raises(KOSISResponseError) as info:
        kosis.fetch_list()
    assert type(info.value) is KOSISResponseError  # not the KOSISAuthError subclass


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("21", "해당하는 통계표가 존재하지 않습니다."),   # no such table (live)
        ("31", "셀 최대 개수(40,000)를 초과하였습니다."),  # cell-count cap (live)
        ("99", "알 수 없는 오류가 발생하였습니다."),       # any other vendor code
    ],
)
def test_other_vendor_codes_preserved_on_response_error(code, message):
    # Every vendor err besides auth (11) and no-data (30) surfaces verbatim, neither
    # downgraded to [] nor promoted to KOSISAuthError, with .code kept for branching.
    kosis = _client([{"err": code, "errMsg": message}])
    with pytest.raises(KOSISResponseError) as info:
        kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL")
    assert type(info.value) is KOSISResponseError
    assert info.value.code == code


def test_error_object_without_err_key_still_raises():
    # A malformed error carrying only errMsg must not be returned as a data row.
    kosis = _client([{"errMsg": "service temporarily unavailable"}])
    with pytest.raises(KOSISResponseError):
        kosis.fetch_list()


def test_empty_result_is_empty_list():
    kosis = _client([[]])
    assert kosis.fetch_data(org_id="101", tbl_id="DT_1B42") == []


def test_no_data_error_code_returns_empty_list():
    # Verified live: a query matching nothing returns err "30", not an empty array; it
    # must surface as [] (no data), not raise.
    kosis = _client([{"err": "30", "errMsg": "데이터가 존재하지 않습니다."}])
    assert kosis.fetch_data(org_id="101", tbl_id="DT_1B42", start_period="1800") == []


# -- fetch_explanation -----------------------------------------------------


def test_fetch_explanation_requires_stat_id_or_org_and_tbl():
    kosis = _client([[]])
    with pytest.raises(ValueError):
        kosis.fetch_explanation()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"org_id": "101"},                                  # half a table pair
        {"tbl_id": "DT_1B42"},                              # the other half
        {"stat_id": "S1", "org_id": "101", "tbl_id": "T"},  # both forms at once
    ],
)
def test_fetch_explanation_rejects_ambiguous_identifiers(kwargs):
    kosis = _client([[]])
    with pytest.raises(ValueError):
        kosis.fetch_explanation(**kwargs)


def test_fetch_explanation_maps_camelcase_keys():
    recorded: list[httpx.Request] = []
    kosis = _client(
        [[{"statsNm": "생명표", "writingPurps": "기대수명 산출"}]], recorded)
    rows = kosis.fetch_explanation(org_id="101", tbl_id="DT_1B42")
    assert rows[0]["stats_nm"] == "생명표"
    assert rows[0]["writing_purps"] == "기대수명 산출"
    assert recorded[0].url.params["jsonMVD"] == "Y"


# -- fetch_meta ------------------------------------------------------------


def test_fetch_meta_uses_getmeta_and_type():
    recorded: list[httpx.Request] = []
    kosis = _client([[{"TBL_NM": "생명표", "TBL_NM_ENG": "Life Table"}]], recorded)
    rows = kosis.fetch_meta(org_id="101", tbl_id="DT_1B42", meta_type="ITM")
    assert rows[0]["tbl_nm_eng"] == "Life Table"
    url = recorded[0].url
    assert url.path == "/openapi/statisticsData.do"
    assert url.params["method"] == "getMeta"
    assert url.params["type"] == "ITM"


# -- fetch_indicator -------------------------------------------------------


def test_fetch_indicator_builds_request_and_maps_keys():
    recorded: list[httpx.Request] = []
    kosis = _client(
        [[{"jipyoId": "160", "jipyoNm": "합계출산율", "jipyoExplan1": "개념",
           "jipyoExplan2": "산정방법", "jipyoExplan3": "출처"}]],
        recorded)
    rows = kosis.fetch_indicator("160", page=2, page_size=5)

    assert rows[0]["jipyo_id"] == "160"
    assert rows[0]["jipyo_explan1"] == "개념"
    assert rows[0]["jipyo_explan3"] == "출처"
    url = recorded[0].url
    assert url.path == "/openapi/pkNumberService.do"
    assert url.params["service"] == "1"
    assert url.params["serviceDetail"] == "pkCompleteExplan"  # default: complete
    assert url.params["jipyoId"] == "160"
    assert url.params["pageNo"] == "2"
    assert url.params["numOfRows"] == "5"


def test_fetch_indicator_section_selects_detail_code():
    recorded: list[httpx.Request] = []
    kosis = _client([[{"jipyoId": "160"}]], recorded)
    kosis.fetch_indicator("160", section=IndicatorSection.CONCEPT)
    assert recorded[0].url.params["serviceDetail"] == "pkNotion"


# -- enum coercion (friendly name, vendor code, or the enum all work) -------


def test_enum_arg_accepts_friendly_name():
    recorded: list[httpx.Request] = []
    kosis = _client([[], [], []], recorded)
    kosis.fetch_list(view_code="subject")               # member name
    kosis.search("x", sort="date")                       # member name
    kosis.fetch_data(org_id="1", tbl_id="T", frequency="annual")
    assert recorded[0].url.params["vwCd"] == "MT_ZTITLE"
    assert recorded[1].url.params["sort"] == "DATE"
    assert recorded[2].url.params["prdSe"] == "Y"


def test_enum_arg_accepts_vendor_code():
    recorded: list[httpx.Request] = []
    kosis = _client([[]], recorded)
    kosis.fetch_data(org_id="1", tbl_id="T", frequency="M")  # vendor code
    assert recorded[0].url.params["prdSe"] == "M"


def test_enum_arg_accepts_enum_instance():
    recorded: list[httpx.Request] = []
    kosis = _client([[], []], recorded)
    kosis.fetch_data(org_id="1", tbl_id="T", frequency=Frequency.MONTHLY)
    kosis.fetch_list(view_code=ViewCode.SUBJECT)
    assert recorded[0].url.params["prdSe"] == "M"
    assert recorded[1].url.params["vwCd"] == "MT_ZTITLE"


def test_enum_arg_rejects_unknown_with_valueerror():
    kosis = _client([[]])
    with pytest.raises(ValueError):
        kosis.fetch_data(org_id="1", tbl_id="T", frequency="weekly")


# -- cross-cutting ---------------------------------------------------------


def test_cache_serves_repeat_without_second_request():
    recorded: list[httpx.Request] = []
    kosis = KOSIS("TESTKEY", cache_ttl=60,
                  transport=_handler([[_data_row()], [_data_row()]], recorded))
    kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    assert len(recorded) == 1  # second call served from cache


def test_clear_cache_forces_refetch():
    recorded: list[httpx.Request] = []
    kosis = KOSIS("TESTKEY", cache_ttl=60,
                  transport=_handler([[_data_row()], [_data_row(DT="84.0")]], recorded))
    kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    kosis.clear_cache()
    rows = kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    assert len(recorded) == 2
    assert rows[0]["data_value"] == 84.0


def test_cached_rows_isolated_from_caller_mutation():
    kosis = KOSIS("TESTKEY", cache_ttl=60,
                  transport=_handler([[_data_row()]], []))
    first = kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    first[0]["data_value"] = 0.0  # caller mutates its copy
    second = kosis.fetch_data(org_id="101", tbl_id="DT_1B42")
    assert second[0]["data_value"] == 83.5  # cache entry untouched


def test_http_429_is_rate_limit_not_retried():
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429)

    kosis = KOSIS("TESTKEY", transport=httpx.MockTransport(handle))
    with pytest.raises(KOSISRateLimitError):
        kosis.fetch_list()
    assert calls["n"] == 1  # Too Many Requests is the server's answer, not retried


def test_other_4xx_is_network_error():
    kosis = KOSIS(
        "TESTKEY", transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(KOSISNetworkError):
        kosis.fetch_list()


def test_non_json_success_raises_response_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="<html>maintenance</html>"))
    kosis = KOSIS("TESTKEY", transport=transport)
    with pytest.raises(KOSISResponseError) as info:
        kosis.fetch_list()
    assert info.value.code == "UNKNOWN"
    assert isinstance(info.value.__cause__, json.JSONDecodeError)


def test_context_manager_closes():
    with _client([[]]) as kosis:
        assert kosis.fetch_list() == []


def test_server_error_retries_then_raises_network_error(monkeypatch):
    monkeypatch.setattr("pykosis._transport.time.sleep", lambda _seconds: None)
    calls = {"n": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    kosis = KOSIS("TESTKEY", transport=httpx.MockTransport(handle))
    with pytest.raises(KOSISNetworkError):
        kosis.fetch_list()
    assert calls["n"] == 3  # one try plus two retries


def test_bad_cache_ttl_rejected():
    with pytest.raises(ValueError):
        KOSIS("TESTKEY", cache_ttl=0)

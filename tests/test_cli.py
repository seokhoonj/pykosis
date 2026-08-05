"""CLI parsing, rendering, and exit codes, with a stubbed client (no network)."""

from __future__ import annotations

import pytest

from pykosis import cli
from pykosis.exceptions import KOSISConfigError, KOSISResponseError


class _FakeKOSIS:
    """Stand-in for the client: records calls and returns canned rows.

    The class attributes are set per test; instances are what ``with KOSIS() as k``
    yields.
    """

    rows: list[dict] = []
    error: Exception | None = None
    calls: list[tuple[str, dict]] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> _FakeKOSIS:
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def _run(self, method: str, **kwargs):
        type(self).calls.append((method, kwargs))
        if type(self).error is not None:
            raise type(self).error
        return type(self).rows

    def fetch_list(self, **kwargs):
        return self._run("fetch_list", **kwargs)

    def search(self, query, **kwargs):
        return self._run("search", query=query, **kwargs)

    def fetch_data(self, **kwargs):
        return self._run("fetch_data", **kwargs)

    def fetch_explanation(self, **kwargs):
        return self._run("fetch_explanation", **kwargs)

    def fetch_indicator(self, indicator_id, **kwargs):
        return self._run("fetch_indicator", indicator_id=indicator_id, **kwargs)

    def fetch_meta(self, **kwargs):
        return self._run("fetch_meta", **kwargs)


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    _FakeKOSIS.rows = []
    _FakeKOSIS.error = None
    _FakeKOSIS.calls = []
    monkeypatch.setattr(cli, "KOSIS", _FakeKOSIS)


# -- version / usage -------------------------------------------------------


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as info:
        cli.main(["--version"])
    assert info.value.code == 0
    assert "kosis" in capsys.readouterr().out


def test_no_subcommand_is_usage_error():
    with pytest.raises(SystemExit) as info:
        cli.main([])
    assert info.value.code == 2


# -- rendering -------------------------------------------------------------


def test_search_text_render(capsys):
    _FakeKOSIS.rows = [{"org_id": "101", "tbl_id": "DT_1B42", "tbl_nm": "생명표",
                        "strt_prd_de": "1970", "end_prd_de": "2023"}]
    assert cli.main(["search", "생명표"]) == 0
    out = capsys.readouterr().out
    assert "DT_1B42" in out
    assert "생명표" in out
    assert "(1 rows)" in out
    assert _FakeKOSIS.calls[0][0] == "search"


def test_data_json_render(capsys):
    _FakeKOSIS.rows = [{"prd_de": "2020", "itm_nm": "기대수명", "data_value": 83.5}]
    assert cli.main(["data", "101", "DT_1B42", "--json"]) == 0
    out = capsys.readouterr().out
    assert '"data_value": 83.5' in out
    assert "기대수명" in out  # non-ASCII kept unescaped


def test_data_passes_frequency_and_obj_levels():
    _FakeKOSIS.rows = []
    cli.main(["data", "101", "DT_1B42", "--frequency", "monthly", "--obj-l2", "ALL"])
    _method_name, kwargs = _FakeKOSIS.calls[0]
    assert str(kwargs["frequency"]) == "M"
    assert kwargs["obj_l1"] == "ALL"
    assert kwargs["obj_l2"] == "ALL"


def test_data_pivot(capsys):
    _FakeKOSIS.rows = [
        {"prd_de": "2020", "itm_nm": "기대수명", "data_value": 83.5},
        {"prd_de": "2020", "itm_nm": "남자", "data_value": 80.5},
    ]
    assert cli.main(["data", "101", "DT_1B42", "--pivot"]) == 0
    out = capsys.readouterr().out
    assert "기대수명" in out
    assert "남자" in out


def test_meta_type_choice_mapped():
    _FakeKOSIS.rows = []
    cli.main(["meta", "101", "DT_1B42", "--type", "item"])
    _method_name, kwargs = _FakeKOSIS.calls[0]
    assert str(kwargs["meta_type"]) == "ITM"


def test_empty_result_render(capsys):
    _FakeKOSIS.rows = []
    assert cli.main(["list"]) == 0
    assert "(no rows)" in capsys.readouterr().out


def test_indicator_forwards_and_renders(capsys):
    _FakeKOSIS.rows = [{"stat_jipyo_nm": "경제활동인구", "jipyo_explan1": "개념"}]
    assert cli.main(["indicator", "160", "--page-size", "5"]) == 0
    method_name, kwargs = _FakeKOSIS.calls[0]
    assert method_name == "fetch_indicator"
    assert kwargs == {"indicator_id": "160", "page": 1, "page_size": 5}
    assert "경제활동인구" in capsys.readouterr().out


def test_explanation_success_forwards_identifiers(capsys):
    _FakeKOSIS.rows = [{"stats_nm": "생명표", "writing_purps": "기대수명 산출"}]
    assert cli.main(["explanation", "--org", "101", "--tbl", "DT_1B42"]) == 0
    method_name, kwargs = _FakeKOSIS.calls[0]
    assert method_name == "fetch_explanation"
    assert kwargs["org_id"] == "101"
    assert kwargs["tbl_id"] == "DT_1B42"
    assert "생명표" in capsys.readouterr().out


# -- error handling --------------------------------------------------------


def test_explanation_requires_identifiers(capsys):
    assert cli.main(["explanation"]) == 2
    assert "stat-id" in capsys.readouterr().err


def test_vendor_error_reported_as_one_line(capsys):
    _FakeKOSIS.error = KOSISResponseError("20", "필수요청변수값이 누락되었습니다.")
    assert cli.main(["data", "101", "DT_1B42"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("kosis: ")
    assert "[20]" in err


def test_config_error_reported(capsys):
    _FakeKOSIS.error = KOSISConfigError("no KOSIS API key")
    assert cli.main(["list"]) == 1
    assert "no KOSIS API key" in capsys.readouterr().err


def test_value_error_reported_as_usage_error(capsys):
    # A library ValueError (bad argument combination / pivot key clash) must relay as a
    # clean one-line error with exit 2, not a raw traceback.
    _FakeKOSIS.error = ValueError("end_period requires start_period")
    assert cli.main(["data", "101", "DT_1B42", "--end", "2024"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("kosis: ")
    assert "Traceback" not in err

"""The ``KOSIS`` client -- the one public handle to the KOSIS Open API.

One object holds the API key and a pooled HTTP connection; its methods mirror the
KOSIS services one-to-one, each taking named arguments and returning a list of dict
rows. Which base URL a service lives at, and the vendor's parameter spelling, stay in
this module and never surface to the caller.
"""

from __future__ import annotations

from enum import StrEnum
from types import TracebackType
from typing import Any, Self, TypeVar, cast

import httpx

from . import _parse
from ._cache import _Cache
from ._config import resolve_api_key
from ._transport import _Transport
from .curation._generated import _CurationGroups
from .types import (
    DataRow,
    ExplanationRow,
    Frequency,
    IndicatorRow,
    IndicatorSection,
    ListRow,
    MetaRow,
    MetaType,
    SearchRow,
    Sort,
    ViewCode,
)

_DEFAULT_TIMEOUT = 30.0

# Each service lives at its own base URL (KOSIS is not a single-endpoint API).
_URL_LIST = "https://kosis.kr/openapi/statisticsList.do"
_URL_SEARCH = "https://kosis.kr/openapi/statisticsSearch.do"
_URL_DATA = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
_URL_EXPL = "https://kosis.kr/openapi/statisticsExplData.do"
_URL_META = "https://kosis.kr/openapi/statisticsData.do"
_URL_INDICATOR = "https://kosis.kr/openapi/pkNumberService.do"

# Present on every request: JSON output, with vendor blanks rendered as empty strings.
_COMMON = {"format": "json", "jsonVD": "Y"}

# KOSIS keys an observation by up to eight classification levels (objL1..objL8).
_MAX_OBJ_LEVELS = 8

_E = TypeVar("_E", bound=StrEnum)


def _to_enum(enum_cls: type[_E], value: _E | str) -> _E:
    """Coerce ``value`` to an ``enum_cls`` member, forgiving three spellings.

    Accepts the member itself, its vendor code value (``"MT_ZTITLE"``, ``"Y"``), or its
    member name case-insensitively (``"subject"``, ``"annual"``) -- so both
    ``fetch_data(frequency="annual")`` and ``fetch_data(frequency="Y")`` work. Raises
    ``ValueError`` naming the accepted words otherwise.
    """
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)  # by vendor code value
    except ValueError:
        pass
    try:
        return enum_cls[value.upper()]  # by member name
    except KeyError:
        words = ", ".join(member.name.lower() for member in enum_cls)
        raise ValueError(
            f"{value!r} is not a valid {enum_cls.__name__}; use one of: {words}"
        ) from None


class KOSIS(_CurationGroups):
    """A client for the KOSIS (Korean Statistical Information Service) Open API.

    Construct it with an API key, or leave it out to resolve one from the
    ``KOSIS_API_KEY`` environment variable or
    ``~/.config/pykosis/credentials.json``::

        with KOSIS() as kosis:
            rows = kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL")

    For KOSIS's headline "100대 지표" you need not remember a table code: the client
    carries a tree of curated indicators grouped by category, so the call above is also
    ``kosis.population.life_expectancy.fetch()`` and
    ``kosis.income_consumption.consumer_price_index.fetch()``.

    Discover the ``org_id`` / ``tbl_id`` a statistic lives under with :meth:`search`
    (by keyword) or :meth:`fetch_list` (browsing the category tree); read a table's
    metadata with :meth:`fetch_meta` and its survey documentation with
    :meth:`fetch_explanation`. Every method returns a list of plain dicts, one per row,
    ready for ``pd.DataFrame(rows)`` without this package importing pandas.

    The client owns a pooled HTTP connection, so reuse one instance across calls and
    close it when done -- as a context manager, or via :meth:`close`. Set
    ``delay_seconds`` to space out requests when fetching in bulk, so a burst stays
    under the KOSIS cap of 200 calls per minute; 0.3s keeps one client under it
    indefinitely. ``cache_ttl`` (off by default) turns on an in-memory cache: a repeated
    query returns the stored rows for that many seconds without a network call.

    Construction raises :class:`KOSISConfigError` if no API key can be resolved, and
    ``ValueError`` for a non-positive ``cache_ttl``. Every service method then raises
    from the :class:`KOSISError` family: :class:`KOSISAuthError` if the key is rejected,
    :class:`KOSISResponseError` on any other vendor error (KOSIS reports these as a
    ``{"err", "errMsg"}`` body -- e.g. ``err=20`` when a required ``objL`` is missing),
    and :class:`KOSISNetworkError` if the request never completes (transient timeout or
    5xx is retried with backoff first). A query that matches no data returns an empty
    list, not an error. A bad argument raises the standard ``ValueError`` -- an
    unrecognized ``frequency`` / ``view_code`` / ``sort`` / ``meta_type`` string, or an
    invalid combination such as ``end_period`` without ``start_period``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        delay_seconds: float = 0.0,
        cache_ttl: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if cache_ttl is not None and cache_ttl <= 0:
            raise ValueError(f"cache_ttl must be positive seconds, got {cache_ttl}")
        self._api_key = resolve_api_key(api_key)
        self._client = httpx.Client(timeout=timeout, transport=transport)
        self._transport = _Transport(self._client, delay_seconds=delay_seconds)
        self._cache = _Cache(ttl=cache_ttl) if cache_ttl is not None else None
        self._data_client = self  # curation groups build lazily off this (fetch_data)

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def clear_cache(self) -> None:
        """Drop any cached results, forcing the next query to refetch.

        Rarely needed -- the cache expires and evicts (see ``cache_ttl``); this is
        the escape hatch for forcing fresh data before an entry's TTL is up. A no-op
        when caching is off.
        """
        if self._cache is not None:
            self._cache.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        # Deliberately never shows the API key.
        return "KOSIS()"

    # -- services ----------------------------------------------------------

    def fetch_list(
        self,
        *,
        view_code: ViewCode | str = ViewCode.SUBJECT,
        parent_list_id: str = "",
    ) -> list[ListRow]:
        """Browse the statistical-table catalog tree (service statisticsList).

        ``view_code`` picks a classification view (:class:`ViewCode` -- by subject, by
        organization, international, ...). ``parent_list_id`` descends a level: leave it
        empty for the top of the tree, then pass a returned ``list_id`` to list its
        children. A row with a ``tbl_id`` is a table you can pass to :meth:`fetch_data`.
        """
        params = {
            "method": "getList",
            "vwCd": str(_to_enum(ViewCode, view_code)),
            "parentListId": parent_list_id,
        }
        return cast("list[ListRow]", self._collect(_URL_LIST, params))

    def search(
        self,
        query: str,
        *,
        org_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort: Sort | str = Sort.RANK,
    ) -> list[SearchRow]:
        """Search tables by keyword (service statisticsSearch).

        ``query`` is the keyword. ``sort`` orders by relevance (:attr:`Sort.RANK`) or
        recency (:attr:`Sort.DATE`). Results are paged: ``page_size`` hits per page,
        ``page`` the 1-based page (so ``page=2`` with ``page_size=20`` returns hits
        21-40). ``org_id`` optionally restricts the search to one organization.
        """
        params = {
            "method": "getList",
            "searchNm": query,
            "startCount": str(page),
            "resultCount": str(page_size),
            "sort": str(_to_enum(Sort, sort)),
        }
        if org_id is not None:
            params["orgId"] = org_id
        return cast("list[SearchRow]", self._collect(_URL_SEARCH, params))

    def fetch_data(
        self,
        *,
        org_id: str,
        tbl_id: str,
        frequency: Frequency | str = Frequency.ANNUAL,
        start_period: str | None = None,
        end_period: str | None = None,
        recent_count: int = 3,
        interval: int = 1,
        item_id: str = "ALL",
        obj_l1: str = "ALL",
        obj_l2: str = "",
        obj_l3: str = "",
        obj_l4: str = "",
        obj_l5: str = "",
        obj_l6: str = "",
        obj_l7: str = "",
        obj_l8: str = "",
    ) -> list[DataRow]:
        """Fetch a table's observations (service statisticsParameterData).

        Identify the table with ``org_id`` + ``tbl_id`` (find them via :meth:`search` or
        :meth:`fetch_list`). ``frequency`` is how often it is recorded
        (:class:`Frequency`).

        Choose the time window one of two ways: pass ``start_period`` (and optionally
        ``end_period``, defaulting to ``start_period``) as period-formatted bounds
        (``"2024"`` annual, ``"202401"`` monthly, ...); or leave both out to take the
        most recent ``recent_count`` periods, every ``interval``-th one.

        A table has up to eight classification levels. ``obj_l1`` defaults to ``"ALL"``
        (every value of the first level); the rest default to empty. If KOSIS answers
        with ``err=20`` (required ``objL`` is missing), set the next level to ``"ALL"``
        -- ``obj_l2="ALL"``, then ``obj_l3="ALL"``, and so on. ``item_id`` defaults to
        ``"ALL"`` (every item).

        KOSIS caps one call at 40,000 cells; narrow the window or classifications if a
        very large table is refused.
        """
        params = {
            "method": "getList",
            "prdSe": str(_to_enum(Frequency, frequency)),
            "orgId": org_id,
            "tblId": tbl_id,
            "itmId": item_id,
        }
        if start_period is None and end_period is not None:
            raise ValueError("end_period requires start_period")
        if start_period is not None:
            params["startPrdDe"] = start_period
            params["endPrdDe"] = end_period if end_period is not None else start_period
        else:
            params["newEstPrdCnt"] = str(recent_count)
            params["prdInterval"] = str(interval)
        params.update(_obj_levels(
            (obj_l1, obj_l2, obj_l3, obj_l4, obj_l5, obj_l6, obj_l7, obj_l8)))
        return cast("list[DataRow]", self._collect(_URL_DATA, params))

    def fetch_explanation(
        self,
        *,
        org_id: str | None = None,
        tbl_id: str | None = None,
        stat_id: str | None = None,
        meta_item: str = "ALL",
    ) -> list[ExplanationRow]:
        """Fetch a survey's documentation (service statisticsExplData).

        Identify the survey either by ``stat_id`` (the survey code), or by ``org_id`` +
        ``tbl_id`` (a table belonging to it). ``meta_item`` selects one documentation
        field (e.g. ``"writingPurps"`` for the survey purpose); the default ``"ALL"``
        returns every field -- legal basis, cycle, target scope, key terms, and more.

        Raises ``ValueError`` unless given exactly one identifier form: ``stat_id``,
        or both ``org_id`` and ``tbl_id`` (passing both forms, or a lone ``org_id`` /
        ``tbl_id``, is rejected rather than silently resolved).
        """
        has_stat_id = stat_id is not None
        has_table_ids = org_id is not None and tbl_id is not None
        if has_stat_id == has_table_ids:  # neither, both, or a half-filled table pair
            raise ValueError("pass either stat_id, or both org_id and tbl_id")
        params = {"method": "getList", "jsonMVD": "Y", "metaItm": meta_item}
        if stat_id is not None:
            params["statId"] = stat_id
        elif org_id is not None and tbl_id is not None:
            params["orgId"] = org_id
            params["tblId"] = tbl_id
        return cast("list[ExplanationRow]", self._collect(_URL_EXPL, params))

    def fetch_meta(
        self,
        *,
        org_id: str,
        tbl_id: str,
        meta_type: MetaType | str = MetaType.TABLE,
    ) -> list[MetaRow]:
        """Fetch one slice of a table's metadata (service statisticsData/getMeta).

        ``meta_type`` (:class:`MetaType`) picks the slice: the table name
        (:attr:`MetaType.TABLE`), its classifications and items (:attr:`MetaType.ITEM`),
        recorded periods, units, source, annotations, weights, or last-update record.
        """
        params = {
            "method": "getMeta",
            "type": str(_to_enum(MetaType, meta_type)),
            "orgId": org_id,
            "tblId": tbl_id,
        }
        return cast("list[MetaRow]", self._collect(_URL_META, params))

    def fetch_indicator(
        self,
        indicator_id: str,
        *,
        section: IndicatorSection | str = IndicatorSection.COMPLETE,
        page: int = 1,
        page_size: int = 10,
    ) -> list[IndicatorRow]:
        """Fetch a key indicator's explanation (service pkNumberService, 통계주요지표).

        ``indicator_id`` is the KOSIS indicator id (vendor ``jipyoId``). Returns the
        indicator's explanation text -- its name and description -- not a value series.
        ``section`` (:class:`IndicatorSection`) picks how much: the concept only, the
        calculation method and source, or (the default) everything together. Results are
        paged: ``page_size`` per page, ``page`` the 1-based page number.
        """
        params = {
            "method": "getList",
            "service": "1",
            "serviceDetail": str(_to_enum(IndicatorSection, section)),
            "jipyoId": indicator_id,
            "pageNo": str(page),
            "numOfRows": str(page_size),
        }
        return cast("list[IndicatorRow]", self._collect(_URL_INDICATOR, params))

    # -- internals ---------------------------------------------------------

    def _collect(self, base_url: str, params: dict[str, str]) -> list[dict[str, Any]]:
        request_params = {**_COMMON, **params, "apiKey": self._api_key}
        key = (base_url, tuple(sorted(
            (name, value) for name, value in request_params.items()
            if name != "apiKey")))
        if self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
        rows = _parse.map_rows(
            self._transport.request(base_url=base_url, params=request_params))
        if self._cache is not None:
            self._cache.set(key, rows)
        return rows


def _obj_levels(values: tuple[str, ...]) -> dict[str, str]:
    """The ``objL1..objL8`` params to send: level 1 always, higher levels if non-empty.

    KOSIS treats an omitted optional ``objL`` the same as an empty one, so the empty
    higher levels are dropped rather than sent blank; ``objL1`` is present because
    the service requires a first classification level.
    """
    levels = {}
    for index, value in enumerate(values, start=1):
        if index == 1 or value != "":
            levels[f"objL{index}"] = value
    return levels

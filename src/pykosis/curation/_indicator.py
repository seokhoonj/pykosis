"""The curated-indicator objects: a static spec plus a client-bound accessor.

An :class:`IndicatorSpec` is the frozen description of one KOSIS headline indicator --
which table it comes from and how often it is recorded. An :class:`Indicator` pairs that
spec with a live client, so ``.fetch()`` returns the table's observations. The specs are
generated from the curation worksheet into ``_generated.py``; the two classes here are
hand-written and shared by every generated namespace.

The curated set is KOSIS's own "100대 지표" (key indicators). Unlike the Bank of Korea
ECOS curation, a KOSIS indicator points at a *table*, not a single series -- so
``.fetch()`` returns that table (every classification value and item), which the caller
filters. The table and frequency were auto-extracted from the KOSIS portal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..exceptions import KOSISResponseError
from ..types import DataRow, Frequency

# KOSIS answers err "20" when a table needs more classification levels than were sent.
_MISSING_OBJ_LEVEL = "20"
# KOSIS keys an observation by up to eight classification levels (objL1..objL8).
_MAX_OBJ_LEVELS = 8


class _DataClient(Protocol):
    """The single client capability an :class:`Indicator` needs.

    Kept minimal so the curation tree depends on a behavior, not on the concrete
    :class:`~pykosis.KOSIS` class -- which would be a circular import, since ``KOSIS``
    exposes the tree.
    """

    def fetch_data(
        self,
        *,
        org_id: str,
        tbl_id: str,
        frequency: Frequency | str = ...,
        start_period: str | None = ...,
        end_period: str | None = ...,
        recent_count: int = ...,
        interval: int = ...,
        item_id: str = ...,
        obj_l1: str = ...,
        obj_l2: str = ...,
        obj_l3: str = ...,
        obj_l4: str = ...,
        obj_l5: str = ...,
        obj_l6: str = ...,
        obj_l7: str = ...,
        obj_l8: str = ...,
    ) -> list[DataRow]: ...


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    """Static definition of one curated indicator -- no client, no I/O.

    ``path`` is the dotted accessor under the client
    (``"population.total_fertility_rate"``); ``org_id`` + ``tbl_id`` identify the KOSIS
    source table, and ``frequency`` is how often it is recorded. ``obj_levels`` pins the
    ``obj_l1..`` classification codes for a large table (empty = fetch the whole table
    with auto-escalation). ``frequency`` / ``obj_levels`` were inferred from the portal.
    """

    path: str
    name_ko: str
    name_en: str
    group: str
    org_id: str
    tbl_id: str
    frequency: Frequency
    # empty = whole table (obj_l1=ALL, auto-escalated); otherwise the obj_l1.. codes
    # that pin a slice of a large table under the 40,000-cell cap.
    obj_levels: tuple[str, ...] = ()


class Indicator:
    """A curated indicator bound to a client; call :meth:`fetch` for its table.

    Reached by walking the curation tree on a client, e.g.
    ``kosis.population.total_fertility_rate``. The :class:`IndicatorSpec` it carries
    names the source table; :meth:`fetch` forwards it to the client's ``fetch_data``, so
    the caller never handles an org/table code.
    """

    __slots__ = ("_client", "spec")

    _client: _DataClient
    spec: IndicatorSpec

    def __init__(self, client: _DataClient, spec: IndicatorSpec) -> None:
        self._client = client
        self.spec = spec

    def fetch(
        self,
        *,
        start_period: str | None = None,
        end_period: str | None = None,
        recent_count: int = 3,
        interval: int = 1,
        item_id: str = "ALL",
    ) -> list[DataRow]:
        """Fetch this indicator's source table (every classification value and item).

        ``start_period`` / ``end_period`` are period-formatted bounds for its
        :attr:`~IndicatorSpec.frequency`; leaving them out takes the most recent
        ``recent_count`` periods. The result is the whole table -- filter it for the
        series you want (e.g. the nationwide total).

        Most tables are fetched whole: this asks for ``obj_l1="ALL"`` and, if KOSIS
        answers ``err=20`` (a required ``objL`` is missing), adds the next level and
        retries through the eight KOSIS classification levels -- so a caller need not
        know a table's depth. A few large tables would exceed the 40,000-cell cap that
        way; for those the spec pins specific classification codes
        (:attr:`~IndicatorSpec.obj_levels`) and this sends exactly those.
        """
        spec = self.spec
        if spec.obj_levels:
            pinned = {f"obj_l{i + 1}": code for i, code in enumerate(spec.obj_levels)}
            return self._client.fetch_data(
                org_id=spec.org_id, tbl_id=spec.tbl_id, frequency=spec.frequency,
                start_period=start_period, end_period=end_period,
                recent_count=recent_count, interval=interval, item_id=item_id, **pinned)
        levels: dict[str, str] = {}
        last_error: KOSISResponseError | None = None
        for level in range(1, _MAX_OBJ_LEVELS + 1):
            levels[f"obj_l{level}"] = "ALL"
            try:
                return self._client.fetch_data(
                    org_id=spec.org_id,
                    tbl_id=spec.tbl_id,
                    frequency=spec.frequency,
                    start_period=start_period,
                    end_period=end_period,
                    recent_count=recent_count,
                    interval=interval,
                    item_id=item_id,
                    **levels,
                )
            except KOSISResponseError as err:
                if err.code != _MISSING_OBJ_LEVEL:
                    raise
                last_error = err
        assert last_error is not None  # loop ran >=1 time and only err=20 lands here
        raise last_error

    def __repr__(self) -> str:
        return f"Indicator(path={self.spec.path!r}, name={self.spec.name_ko!r})"

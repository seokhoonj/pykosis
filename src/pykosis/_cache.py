"""An opt-in, TTL-bounded store of prior fetch results, keyed by the logical query.

Off unless :class:`KOSIS` is given a ``cache_ttl``. When on, a repeated query returns
the stored rows without a network round trip -- cutting calls so a burst stays under
the KOSIS rate cap (200 calls per minute), and repeating work for free.

The store holds *complete* results (a whole mapped result set), never a partial one.
Entries expire after ``ttl`` seconds, so the staleness a caller accepts is exactly the
bound they chose -- a table whose latest period has since updated is re-fetched once its
entry expires. Least-recently-used entries are evicted past ``maxsize`` so the store
cannot grow without bound.

Each entry is copied on store and on retrieval, row by row, so a caller mutating a
returned row cannot corrupt the stored entry or another caller's copy; the rows carry
only scalar values, so a per-row ``dict`` copy fully isolates them.

Not thread-safe: the entries are mutable instance state with no lock, like the client
that owns it -- use one client per thread.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

# (base URL, sorted request params minus the API key) -- the logical query. The paging
# params (search's startCount/resultCount) are ordinary members, so different pages of
# the same search cache separately; the API key is excluded so it never keys an entry.
_CacheKey = tuple[str, tuple[tuple[str, str], ...]]

_Rows = list[dict[str, Any]]

_DEFAULT_MAXSIZE = 256


def _isolate_rows(rows: _Rows) -> _Rows:
    """A copy of ``rows`` sharing none of its dicts (values are scalars)."""
    return [dict(row) for row in rows]


class _Cache:
    """A TTL + LRU store mapping a query key to its rows."""

    def __init__(self, *, ttl: float, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._entries: OrderedDict[_CacheKey, tuple[float, _Rows]] = OrderedDict()

    def get(self, key: _CacheKey) -> _Rows | None:
        """The cached rows for ``key`` if present and unexpired, else ``None``.

        Returns an isolated copy, so a caller mutating the rows cannot corrupt the
        entry.
        """
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, rows = entry
        if time.monotonic() >= expires_at:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)  # mark most-recently-used
        return _isolate_rows(rows)

    def set(self, key: _CacheKey, rows: _Rows) -> None:
        """Store an isolated copy of ``rows``, evicting the LRU entry past maxsize."""
        self._entries[key] = (time.monotonic() + self._ttl, _isolate_rows(rows))
        self._entries.move_to_end(key)
        while len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)  # drop the least-recently-used

    def clear(self) -> None:
        """Drop every entry."""
        self._entries.clear()

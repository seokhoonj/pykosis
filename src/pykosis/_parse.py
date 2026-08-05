"""Turn KOSIS's raw vendor rows into snake_cased dicts, faithful to the vendor keys.

KOSIS returns two key styles depending on the service: ``UPPER_SNAKE`` for data, list,
and metadata rows (``C1_NM_ENG``, ``PRD_DE``, ``DT``) and ``camelCase`` for the
explanation service (``writingPurps``, ``statsNm``). :func:`_snake` handles both, so
every key lands as lower snake_case -- and *only* that, so the field names stay 1:1 with
the KOSIS documentation (a reader who knows ``OBJ_NM`` finds ``obj_nm``). The one rename
is ``DT`` (the observation value) to ``data_value``: a bare ``dt`` reads as a date, and
this is the field callers actually compute on, so it earns a clear name and is parsed to
``float``. Every other key passes through, so a field new to the API is never dropped.
"""

from __future__ import annotations

import re
from typing import Any

# Insert a break between a lowercase/digit and an uppercase letter, so camelCase splits
# while an already-underscored UPPER_SNAKE key is left for lowercase() to finish.
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

# The only vendor key whose snake_case is not kept verbatim (a bare "dt" is misleading).
_RENAMED = {"DT": "data_value"}


def map_rows(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a list of raw vendor rows to snake_cased dicts with a parsed value."""
    return [_map_row(row) for row in raw]


def _map_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = {_snake(key): value for key, value in raw.items()}
    if "data_value" in row:
        row["data_value"] = _to_float(row["data_value"])
    return row


def _snake(key: str) -> str:
    """Lower snake_case for both ``UPPER_SNAKE`` and ``camelCase`` vendor keys."""
    renamed = _RENAMED.get(key)
    if renamed is not None:
        return renamed
    return _CAMEL_BOUNDARY.sub("_", key).lower()


def _to_float(text: object) -> float | None:
    # KOSIS marks a missing cell with an empty string or a lone dash; with statistical
    # symbols enabled (smblChk) a cell may also carry a non-numeric mark. Any value that
    # does not parse becomes None (reported as missing) rather than raising.
    if text in (None, "", "-"):
        return None
    try:
        return float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return None

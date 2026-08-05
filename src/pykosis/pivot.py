"""Reshape KOSIS observations from long to wide -- one column per item.

:meth:`KOSIS.fetch_data` returns *long* rows: one row per (classification, item,
period), with the number in ``data_value`` and the item named in ``itm_nm``. For
analysis you usually want one row per (classification, period) with each item as its
own column. :func:`pivot_items` does that pivot over plain ``list[dict]`` rows, using
only the standard library -- no pandas -- so the result stays one ``pd.DataFrame(...)``
call away without this package depending on pandas::

    rows = kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL")
    wide = pivot_items(rows)                 # each item -> its own column
    wide = pivot_items(rows, label="itm_id") # ... named by item code instead

The item and unit columns collapse into the new value columns; every other column (the
organization, table, classifications ``c1``..``c8``, and period) becomes the row key.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

# Columns describing the item/unit rather than a classification dimension; they collapse
# into the pivoted value columns and so drop out of the row key.
_ITEM_COLUMNS = frozenset({
    "itm_id", "itm_nm", "itm_nm_eng",
    "unit_id", "unit_nm", "unit_nm_eng",
    "data_value",
})

# The item columns whose values may label the pivoted columns.
_LABELS = ("itm_nm", "itm_id", "itm_nm_eng")


def pivot_items(
    rows: Sequence[Mapping[str, Any]],
    label: Literal["itm_nm", "itm_id", "itm_nm_eng"] = "itm_nm",
) -> list[dict[str, Any]]:
    """Pivot long rows to wide, one value column per distinct item.

    ``label`` chooses which item column names the new columns: ``"itm_nm"`` (the Korean
    item name, the default), ``"itm_id"`` (the item code), or ``"itm_nm_eng"`` (the
    English name). Each output row carries classification and period columns plus one
    value column per item, holding that item's ``data_value`` (``None`` where an item is
    absent for that key). Row and column order follow first appearance in ``rows``; an
    empty input returns ``[]``.

    Raises ``ValueError`` if ``label`` is not one of the three item columns, if it is
    not present in the data, or if two rows sharing a classification/period key carry
    the same ``label`` value but different data (which ``"itm_nm"`` can when item names
    repeat -- pivot on ``"itm_id"`` instead).
    """
    if label not in _LABELS:
        raise ValueError(f"label must be one of {_LABELS}, got {label!r}")
    if not rows:
        return []
    if not any(label in row for row in rows):
        raise ValueError(f"no {label!r} column in the data")

    key_columns = [col for col in _ordered_keys(rows) if col not in _ITEM_COLUMNS]
    items: list[str] = []
    seen_items: set[str] = set()  # membership test kept O(1); items[] keeps order
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        item = row.get(label)
        if not isinstance(item, str):
            continue  # a row with no string item value cannot name a column
        key = tuple(row.get(col) for col in key_columns)
        entry = grouped.setdefault(key, {col: row.get(col) for col in key_columns})
        if item not in seen_items:
            seen_items.add(item)
            items.append(item)
        value = row.get("data_value")
        if item in entry and entry[item] != value:
            raise ValueError(
                f"two rows share key {key} and {label}={item!r} but differ; "
                f"pivot on 'itm_id' for a unique label")
        entry[item] = value

    wide_rows: list[dict[str, Any]] = []
    for entry in grouped.values():
        wide_row = {col: entry[col] for col in key_columns}
        for item in items:
            wide_row[item] = entry.get(item)
        wide_rows.append(wide_row)
    return wide_rows


def _ordered_keys(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every key seen across ``rows``, in first-seen order."""
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return keys

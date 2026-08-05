"""Command-line shell over ``KOSIS`` -- ``kosis list`` / ``search`` / ``data`` / ...

The shell over the shell: it parses ``argv``, runs one library call, and renders the
returned rows as aligned text (or ``--json``). All request and parsing knowledge stays
in the library -- this only formats what the library returns -- and it is stdlib-only,
so the package's single runtime dependency (``httpx``) is not widened by having a CLI.

    $ export KOSIS_API_KEY=...
    $ kosis search 생명표
    $ kosis list --view organization --parent F_29
    $ kosis data 101 DT_1B42 --obj-l1 ALL --pivot
    $ kosis meta 101 DT_1B42 --type item
    $ kosis explanation --org 101 --tbl DT_1B42
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import TypeAlias

from . import __version__
from .client import KOSIS
from .exceptions import KOSISError
from .pivot import pivot_items
from .types import Frequency, IndicatorSection, MetaType, Sort, ViewCode

# Flag words derive from the enums so the CLI never restates the taxonomy: a member
# added to an enum becomes an accepted choice with no edit here. The word is the member
# name lowercased; Enum[word.upper()] maps it back.
_VIEW_CHOICES = tuple(view.name.lower() for view in ViewCode)
_FREQUENCY_CHOICES = tuple(frequency.name.lower() for frequency in Frequency)
_META_CHOICES = tuple(meta.name.lower() for meta in MetaType)
_SORT_CHOICES = tuple(sort.name.lower() for sort in Sort)
_SECTION_CHOICES = tuple(section.name.lower() for section in IndicatorSection)

# The item columns a --pivot may key on (the library validates too; restated as choices
# here only so argparse can reject a bad value with usage rather than a traceback).
_PIVOT_CHOICES = ("itm_nm", "itm_id", "itm_nm_eng")

# KOSIS keys an observation by up to eight classification levels.
_MAX_OBJ_LEVELS = 8

# How many rows the text view of `data` prints; the full result is always in --json.
_MAX_DATA_ROWS = 40

# The command name, single-sourced: the argparse prog, the --version banner, and the
# stderr error prefix all derive from it, so a rename touches one line.
_PROG = "kosis"
_ERROR_PREFIX = f"{_PROG}: "

Row: TypeAlias = Mapping[str, object]


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv``, run one call, and return a process exit code.

    A failure -- a missing API key, a rejected key, a vendor error, or a transport
    problem -- is printed as a one-line ``kosis: <message>`` to stderr and returns 1, so
    a shell caller sees a clean error rather than a traceback. A usage error -- a bad
    flag, a missing subcommand (both via argparse), or invalid argument combination --
    returns 2.
    """
    args = _make_parser().parse_args(argv)
    run: Callable[[argparse.Namespace], int] = args.run
    try:
        return run(args)
    except KOSISError as err:
        print(f"{_ERROR_PREFIX}{err}", file=sys.stderr)
        return 1
    except ValueError as err:
        # A bad argument combination (e.g. --end without --start) or a pivot key
        # clash surfaces as a library ValueError; relay it as a clean usage error
        # rather than a raw traceback.
        print(f"{_ERROR_PREFIX}{err}", file=sys.stderr)
        return 2


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description="Read the KOSIS (Statistics Korea) Open API from the command line.")
    parser.add_argument("--version", action="version", version=f"{_PROG} {__version__}")
    commands = parser.add_subparsers(required=True)

    list_ = commands.add_parser(
        "list", help="browse the statistical-table catalog tree (statisticsList)")
    list_.add_argument("--view", choices=_VIEW_CHOICES, default=None,
                       help="classification view (default: subject)")
    list_.add_argument("--parent", default="", metavar="LIST_ID",
                       help="parent list id; omit for the top of the tree")
    _add_json_flag(list_)
    list_.set_defaults(run=_run_list)

    search = commands.add_parser(
        "search", help="search tables by keyword (statisticsSearch)")
    search.add_argument("query", help="the search term")
    search.add_argument("--org", default=None, metavar="ORG_ID",
                        help="restrict to one organization")
    search.add_argument("--sort", choices=_SORT_CHOICES, default=None,
                        help="result ordering (default: rank)")
    search.add_argument("--page-size", type=int, default=20, metavar="N",
                        dest="page_size", help="hits per page (default: 20)")
    search.add_argument("--page", type=int, default=1, metavar="N",
                        help="1-based page number (default: 1)")
    _add_json_flag(search)
    search.set_defaults(run=_run_search)

    data = commands.add_parser(
        "data", help="a table's observations (statisticsParameterData)")
    data.add_argument("org_id", help="organization id (e.g. 101)")
    data.add_argument("tbl_id", help="table id (e.g. DT_1B42)")
    data.add_argument("--frequency", choices=_FREQUENCY_CHOICES, default=None,
                      help="how often the table is recorded (default: annual)")
    data.add_argument("--start", default=None, help="period-formatted start bound")
    data.add_argument("--end", default=None, help="period-formatted end bound")
    data.add_argument("--recent", type=int, default=3, metavar="N",
                      help="most recent N periods when no start/end (default: 3)")
    data.add_argument("--interval", type=int, default=1, metavar="N",
                      help="take every Nth period (default: 1)")
    data.add_argument("--item", default="ALL", metavar="ITM_ID",
                      help="item id (default: ALL)")
    for level in range(1, _MAX_OBJ_LEVELS + 1):
        data.add_argument(f"--obj-l{level}", default=("ALL" if level == 1 else ""),
                          metavar="CODE", dest=f"obj_l{level}",
                          help=f"classification level {level}"
                               + (" (default: ALL)" if level == 1 else ""))
    data.add_argument("--pivot", nargs="?", const="itm_nm", default=None,
                      choices=_PIVOT_CHOICES,
                      help="pivot items to columns, labeled by this column "
                           "(default label: itm_nm)")
    _add_json_flag(data)
    data.set_defaults(run=_run_data)

    explanation = commands.add_parser(
        "explanation", help="a survey's documentation (statisticsExplData)")
    explanation.add_argument("--org", default=None, metavar="ORG_ID",
                             help="organization id")
    explanation.add_argument("--tbl", default=None, metavar="TBL_ID", help="table id")
    explanation.add_argument("--stat-id", default=None, metavar="STAT_ID",
                             dest="stat_id", help="survey id (instead of org+tbl)")
    explanation.add_argument("--meta-item", default="ALL", metavar="ITEM",
                             dest="meta_item",
                             help="one documentation field, or ALL (default)")
    _add_json_flag(explanation)
    explanation.set_defaults(run=_run_explanation)

    meta = commands.add_parser(
        "meta", help="a table's metadata (statisticsData/getMeta)")
    meta.add_argument("org_id", help="organization id (e.g. 101)")
    meta.add_argument("tbl_id", help="table id (e.g. DT_1B42)")
    meta.add_argument("--type", choices=_META_CHOICES, default=None, dest="meta_type",
                      help="metadata slice (default: table)")
    _add_json_flag(meta)
    meta.set_defaults(run=_run_meta)

    indicator = commands.add_parser(
        "indicator", help="a key indicator's explanation (pkNumberService)")
    indicator.add_argument("indicator_id", help="indicator id (jipyoId, e.g. 160)")
    indicator.add_argument("--section", choices=_SECTION_CHOICES, default=None,
                           help="how much explanation (default: complete)")
    indicator.add_argument("--page", type=int, default=1, metavar="N",
                           help="1-based page number (default: 1)")
    indicator.add_argument("--page-size", type=int, default=10, metavar="N",
                           dest="page_size", help="records per page (default: 10)")
    _add_json_flag(indicator)
    indicator.set_defaults(run=_run_indicator)

    return parser


def _add_json_flag(command: argparse.ArgumentParser) -> None:
    command.add_argument("--json", action="store_true",
                         help="emit JSON instead of text")


def _run_list(args: argparse.Namespace) -> int:
    view_kw = {"view_code": ViewCode[args.view.upper()]} if args.view else {}
    with KOSIS() as kosis:
        rows = kosis.fetch_list(parent_list_id=args.parent, **view_kw)
    print(_to_json(rows) if args.json else _render_table(
        rows, [("list_id", "list_id"), ("org", "org_id"),
               ("tbl", "tbl_id"), ("name", "tbl_nm")]))
    return 0


def _run_search(args: argparse.Namespace) -> int:
    sort_kw = {"sort": Sort[args.sort.upper()]} if args.sort else {}
    with KOSIS() as kosis:
        rows = kosis.search(args.query, org_id=args.org, page=args.page,
                            page_size=args.page_size, **sort_kw)
    print(_to_json(rows) if args.json else _render_table(
        rows, [("org", "org_id"), ("tbl", "tbl_id"), ("from", "strt_prd_de"),
               ("to", "end_prd_de"), ("name", "tbl_nm")]))
    return 0


def _run_data(args: argparse.Namespace) -> int:
    frequency_kw = (
        {"frequency": Frequency[args.frequency.upper()]} if args.frequency else {})
    obj_kw = {f"obj_l{level}": getattr(args, f"obj_l{level}")
              for level in range(1, _MAX_OBJ_LEVELS + 1)}
    with KOSIS() as kosis:
        rows = kosis.fetch_data(
            org_id=args.org_id, tbl_id=args.tbl_id, start_period=args.start,
            end_period=args.end, recent_count=args.recent, interval=args.interval,
            item_id=args.item, **frequency_kw, **obj_kw)
    if args.pivot is not None:
        wide = pivot_items(rows, label=args.pivot)
        print(_to_json(wide) if args.json else _render_auto(wide))
        return 0
    print(_to_json(rows) if args.json else _render_data(rows, args.tbl_id))
    return 0


def _run_explanation(args: argparse.Namespace) -> int:
    if args.stat_id is None and not (args.org and args.tbl):
        print(f"{_ERROR_PREFIX}pass --stat-id, or both --org and --tbl",
              file=sys.stderr)
        return 2
    with KOSIS() as kosis:
        rows = kosis.fetch_explanation(org_id=args.org, tbl_id=args.tbl,
                                       stat_id=args.stat_id, meta_item=args.meta_item)
    print(_to_json(rows) if args.json else _render_records(rows))
    return 0


def _run_meta(args: argparse.Namespace) -> int:
    type_kw = {"meta_type": MetaType[args.meta_type.upper()]} if args.meta_type else {}
    with KOSIS() as kosis:
        rows = kosis.fetch_meta(org_id=args.org_id, tbl_id=args.tbl_id, **type_kw)
    print(_to_json(rows) if args.json else _render_auto(rows))
    return 0


def _run_indicator(args: argparse.Namespace) -> int:
    section_kw = (
        {"section": IndicatorSection[args.section.upper()]} if args.section else {})
    with KOSIS() as kosis:
        rows = kosis.fetch_indicator(args.indicator_id, page=args.page,
                                     page_size=args.page_size, **section_kw)
    print(_to_json(rows) if args.json else _render_records(rows))
    return 0


def _to_json(rows: Sequence[Row]) -> str:
    """The full row list as indented JSON, Korean names kept unescaped."""
    return json.dumps(list(rows), ensure_ascii=False, indent=2)


def _render_data(rows: Sequence[Row], tbl_id: str) -> str:
    """A one-line summary, then the most recent observations as an aligned table."""
    if not rows:
        label = f"{tbl_id}  " if tbl_id else ""
        return f"{label}(no observations)"
    name = rows[-1].get("tbl_nm") or tbl_id or ""
    head = f"{name}  {len(rows)} obs"
    shown = rows[-_MAX_DATA_ROWS:]
    table = _render_table(
        shown, [("period", "prd_de"), ("item", "itm_nm"), ("c1", "c1_nm"),
                ("value", "data_value"), ("unit", "unit_nm")])
    if len(rows) > _MAX_DATA_ROWS:
        head += f"  (showing last {_MAX_DATA_ROWS}; use --json for all)"
    return f"{head}\n{table}"


def _render_records(rows: Sequence[Row]) -> str:
    """Each record as ``field: value`` lines -- the shape of the explanation service."""
    if not rows:
        return "(no records)"
    blocks = []
    for row in rows:
        lines = [f"{key}: {value}" for key, value in row.items()
                 if value not in ("", None)]
        blocks.append("\n".join(lines) if lines else "(empty record)")
    return "\n\n".join(blocks)


def _render_auto(rows: Sequence[Row]) -> str:
    """An aligned table over every column present, in first-seen order."""
    columns = [(key, key) for key in _ordered_keys(rows)]
    return _render_table(rows, columns)


def _render_table(rows: Sequence[Row], columns: list[tuple[str, str]]) -> str:
    """Rows as an aligned table over ``columns`` (label, key), one row per line.

    A missing or None cell prints as ``-``; an empty result prints ``(no rows)``. A
    trailing ``(N rows)`` count follows a non-empty table. Columns with no value in any
    row are dropped, so a fixed column list stays readable on a narrow table.
    """
    if not rows:
        return "(no rows)"
    present = [(label, key) for label, key in columns
               if any(row.get(key) not in (None, "") for row in rows)]
    if not present:
        return f"({len(rows)} rows)"
    labels = [label for label, _ in present]
    cells = [[_cell(row.get(key)) for _, key in present] for row in rows]
    by_column = list(zip(labels, *cells, strict=True))  # each: header then its cells
    widths = [max(len(text) for text in column) for column in by_column]
    header = "  ".join(label.ljust(w) for label, w in zip(labels, widths, strict=True))
    body = "\n".join(
        "  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True))
        for row in cells)
    return f"{header}\n{body}\n({len(rows)} rows)"


def _cell(value: object) -> str:
    return "-" if value is None else str(value)


def _ordered_keys(rows: Sequence[Row]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


if __name__ == "__main__":
    raise SystemExit(main())

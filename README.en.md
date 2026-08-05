# pykosis

[![check](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/pykosis)](https://pypi.org/project/pykosis/)
[![Python](https://img.shields.io/pypi/pyversions/pykosis)](https://pypi.org/project/pykosis/)
[![License](https://img.shields.io/pypi/l/pykosis)](https://github.com/seokhoonj/pykosis/blob/main/LICENSE)

**English** | [한국어](README.md)

Read Korea's national statistics from **KOSIS** (the Korean Statistical Information
Service, run by Statistics Korea).

Population and households, labor and wages, prices, national accounts, finance, trade and
balance of payments, health and welfare, housing and land, education, agriculture and
fisheries, mining and manufacturing, construction, transport and logistics, ICT,
environment and energy, and regional statistics -- fetch any approved KOSIS table by its
code, and pivot items into columns for analysis.

## 1. Install

```bash
pip install pykosis
```

Get a free API key at <https://kosis.kr/openapi/>. The key is resolved from
`KOSIS(api_key=...)`, the `KOSIS_API_KEY` environment variable, then a config file, in
that order.

**Config file (all platforms, recommended)** -- create
`~/.config/pykosis/credentials.json`:

```json
{ "KOSIS_API_KEY": "..." }
```

**Environment variable** -- macOS/Linux (bash/zsh) `export KOSIS_API_KEY=...`; Windows
PowerShell `setx KOSIS_API_KEY "..."` (persistent) or `$env:KOSIS_API_KEY = "..."` (current
session). This is the same name the R `kosis` package uses, so a key in `.Renviron`-style
shells is picked up unchanged.

## 2. Quick start

KOSIS identifies a statistic by an **organization** (`org_id`) and a **table** (`tbl_id`).
If you do not know the codes, find them with `search`, then call `fetch_data`.

```python
from pykosis import KOSIS, pivot_items

kosis = KOSIS()                                        # resolves the key from env / config

hits = kosis.search("생명표")                          # 1) find the table codes by keyword
org_id, tbl_id = hits[0]["org_id"], hits[0]["tbl_id"]  #    e.g. "101", "DT_1B42"

rows = kosis.fetch_data(org_id=org_id, tbl_id=tbl_id,  # 2) fetch its data (long form)
                        obj_l1="ALL")
wide = pivot_items(rows)                               # 3) pivot items to columns for analysis
```

Every result is a `list[dict]`, so it becomes a pandas or polars DataFrame in one line.

```python
import pandas as pd
import polars as pl

pd.DataFrame(wide)   # or pl.DataFrame(wide)
```

A query that matches no data returns an empty list, not an error.

### Headline indicators by name (KOSIS 100대 지표)

You need not know a table code for KOSIS's key indicators -- reach them as
`kosis.<group>.<indicator>`, grouped by KOSIS's own ten categories: `population`,
`economy`, `health_welfare`, `education_labor`, `income_consumption`, `leisure`,
`housing_transport`, `crime_safety`, `environment_energy`, `industry`.

```python
kosis.population.total_fertility_rate.fetch()
kosis.income_consumption.consumer_price_index.fetch()
kosis.health_welfare.life_expectancy.fetch()
```

`.fetch(start_period=, end_period=)` sets the window; omit it for the latest. Each
indicator returns its whole source table (nationwide plus breakdowns -- filter for the
row you want); its classification depth (objL) and frequency are handled automatically.

Indicators and frequencies were extracted from the KOSIS portal, and **all 100 are
live-verified**. Large multi-dimensional tables have their nationwide/total classification
pinned automatically to stay under the 40,000-cell cap; land area alone uses an equivalent
table because its source (a cadastral table) can't be fetched whole.

## 3. API

Every method returns a `list[dict]`.

| Method | What it does |
|---|---|
| `search(query, *, org_id=, sort=, page=, page_size=)` | Search tables by keyword |
| `fetch_list(*, view_code=, parent_list_id=)` | Browse the catalog tree one level at a time |
| `fetch_data(*, org_id, tbl_id, ...)` | A table's observations (time series) |
| `fetch_explanation(*, org_id=, tbl_id=, stat_id=, meta_item=)` | Survey documentation (purpose, legal basis, cycle, terms) |
| `fetch_meta(*, org_id, tbl_id, meta_type=)` | Table metadata (name, items, units, source) |
| `fetch_indicator(indicator_id, *, section=, page=, page_size=)` | A key indicator's explanation (concept / method / source) |
| `pivot_items(rows, label=)` | Reshape long observations to wide, one column per item |
| `clear_cache()` | Empty the response cache enabled with `cache_ttl` |

### fetch_data -- a table's data

```python
rows = kosis.fetch_data(
    org_id="101", tbl_id="DT_1B42",
    frequency="annual",                       # how often (see the table below)
    start_period="2015", end_period="2023",   # a window (omit both for the recent recent_count)
    item_id="ALL",                            # every item
    obj_l1="ALL",                             # every value of classification level 1
)
```

- **Window**: pass `start_period`/`end_period` for a range, or leave both out to take the
  most recent `recent_count` periods (default 3).
- **Classification levels**: a table has up to eight levels (`obj_l1`..`obj_l8`). `obj_l1`
  defaults to `"ALL"`, the rest are empty. If KOSIS answers with `err=20` (a required level
  is missing), set the next level to `"ALL"` -- `obj_l2="ALL"`, then `obj_l3="ALL"`, ...
- An empty cell comes back as `data_value = None`. One call is capped at 40,000 cells, so
  narrow the window or the classifications for a very large table.

### pivot_items -- items to columns

`fetch_data` returns **long** rows (one per classification, item, and period). Pivoting the
items into columns gives an analysis-friendly **wide** shape.

```python
pivot_items(rows)                  # label columns by item name (itm_nm, default)
pivot_items(rows, label="itm_id")  # label columns by item code (itm_id)
```

### search / fetch_list -- find tables

```python
kosis.search("소비자물가", sort="date", page_size=10)   # sort by RANK or DATE

kosis.fetch_list(view_code="subject")                      # top of the subject view
kosis.fetch_list(view_code="subject", parent_list_id="A")  # its children
```

`view_code` selects a view -- `subject`, `organization`, `international`, and nine more
(`ViewCode`). The KOSIS tree is deep, so pass a returned `list_id` as `parent_list_id` to
descend one level at a time.

## 4. Command line

Installing the package puts a `kosis` command on PATH (also `python -m pykosis`).

```sh
kosis search 생명표                                 # search tables
kosis list --view organization --parent F_29        # browse the catalog tree
kosis data 101 DT_1B42 --obj-l1 ALL --pivot         # data (items pivoted to columns)
kosis meta 101 DT_1B42 --type item                  # table metadata
kosis explanation --org 101 --tbl DT_1B42           # survey documentation
kosis indicator 160                                 # key-indicator explanation
```

| Command | What it does |
|---|---|
| `search <term>` | Search tables. `--sort`, `--page-size`, `--page`, `--org` |
| `list` | Catalog tree. `--view`, `--parent` |
| `data <org_id> <tbl_id>` | Observations. `--frequency`, `--start`/`--end`, `--recent`, `--interval`, `--obj-l1`..`--obj-l8`, `--item`, `--pivot` |
| `explanation` | Survey documentation. `--org`+`--tbl` or `--stat-id`, `--meta-item` |
| `meta <org_id> <tbl_id>` | Table metadata. `--type` |
| `indicator <indicator_id>` | A key indicator's explanation. `--section`, `--page`, `--page-size` |

Each command defaults to a readable table; `--json` emits the full result. `kosis --version`
prints the version, and `kosis <command> --help` lists every option.

## 5. AI coding agents

This repo doubles as a plugin marketplace for Claude Code and Codex -- `find`, `data`, and
`meta` are skills that call the `kosis` command. Install the package and set the API key
first.

### 5.1. Claude Code

```
/plugin marketplace add seokhoonj/pykosis
/plugin install kosis@pykosis
```

Then ask normally ("find the table code for the life table", "fetch that table's data"), or
call a skill directly -- `/kosis:find 생명표`, `/kosis:data 101 DT_1B42`.

### 5.2. Codex

```
codex plugin marketplace add seokhoonj/pykosis
codex plugin add kosis@pykosis
```

The `find`, `data`, and `meta` skills respond to statistics requests, or run `kosis <command>`
directly.

To use them without installing the plugin, symlink a skill into your skills directory and
call it bare (`/data`, no `kosis:` prefix):

```sh
ln -s "$PWD/plugins/kosis/skills/data" ~/.claude/skills/data
```

## 6. Frequencies

The values `fetch_data(frequency=)` and `data --frequency` accept. The library takes
either the word (`"annual"`) or the code (`"Y"`); the command takes the word.
Period-formatted bounds (`start_period`, ...) match the frequency.

| Frequency | Code | Word | Period example |
|---|---|---|---|
| Annual | `Y` | `annual` | `2024` |
| Half-yearly | `H` | `half_yearly` | `2024H1` |
| Quarterly | `Q` | `quarterly` | `2024Q1` |
| Monthly | `M` | `monthly` | `202401` |
| Daily | `D` | `daily` | `20240115` |
| Multi-year | `F` | `multiyear` | `2024` |
| Irregular | `IR` | `irregular` | `2024` |

## 7. Errors and rate limiting

| Exception | When |
|---|---|
| `KOSISConfigError` | No API key found (raised before any request) |
| `KOSISAuthError` | KOSIS rejected the key |
| `KOSISResponseError` | KOSIS returned an error (`.code` / `.message`; e.g. `err=20`) |
| `KOSISRateLimitError` | The call rate limit was hit (HTTP 429; a subclass of `KOSISResponseError`) |
| `KOSISNetworkError` | The request never completed (a transient error is retried first) |

All derive from `KOSISError`. KOSIS caps calls at 200 per minute, so when reading many
tables in a row, set `KOSIS(delay_seconds=0.3)` to stay under the cap, and
`KOSIS(cache_ttl=600)` to cache repeated queries.

## 8. License

MIT © Seokhoon Joo

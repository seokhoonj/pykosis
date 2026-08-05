---
name: data
description: "Fetch a KOSIS statistical table as a time series, optionally pivoting items to columns. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis data`) and shows the result to the user. Needs an organization code and a table code (find them with the find skill). Trigger phrases: KOSIS 데이터 가져와, 통계표 데이터, 국가통계 시계열, KOSIS statistic time series, fetch KOSIS table data, life table data, 인구 통계 가져와."
---

# kosis -- statistical table data

Take a KOSIS organization code and table code and print that table's observations. The
fetching and parsing live in the pykosis package (on PyPI); this skill is a thin wrapper
that calls its CLI and relays the result. A rejected key or a vendor error comes back as a
one-line `kosis: <message>` -- relay it as-is rather than throwing a stack trace at the
user. (A missing or malformed argument is caught earlier by argparse, which prints usage
and exits 2.)

## Prerequisite

This plugin calls the `kosis` CLI, so the package must be installed and an API key set:

```
pipx install pykosis          # or: pip install pykosis
export KOSIS_API_KEY=...       # a free key from https://kosis.kr/openapi/
```

That puts the `kosis` command on PATH. The key can also be stored in
`~/.config/pykosis/credentials.json` as `{"KOSIS_API_KEY": "..."}`. Without a key the CLI
exits with `kosis: no KOSIS API key ...`; relay that and point the user at the KOSIS site.

## Running

```
kosis data <ORG_ID> <TBL_ID> [--frequency ...] [--start ...] [--end ...] [--recent N] [--interval N] [--obj-l1 ...] [--item ...] [--pivot [LABEL]] [--json]
```

Options (`kosis data --help` is the source of truth):
- `--frequency annual|half|quarterly|monthly|daily|multiyear|irregular` -- how often (default: annual).
- `--start` / `--end` -- period-formatted bounds: `2024` (annual), `202401` (monthly),
  `2024Q1` (quarterly), `20240115` (daily). Omit both to take the most recent `--recent` periods.
- `--obj-l1` .. `--obj-l8` -- classification levels; `--obj-l1` defaults to `ALL`. If the
  vendor returns `err=20` (a required classification is missing), add the next level:
  `--obj-l2 ALL`, then `--obj-l3 ALL`, and so on.
- `--item` -- item id (default `ALL`).
- `--pivot [LABEL]` -- pivot items to columns, labeled by `itm_nm` (default), `itm_id`, or `itm_nm_eng`.
- `--json` -- the full result as JSON instead of the text summary.

## Procedure

1. **Get the codes.** You need an `org_id` and a `tbl_id`. If the user gave a concept
   ("생명표", "주민등록인구") but no codes, use the **find** skill first, then come back here.
2. **Run.** Add `--start`/`--end`/`--frequency` for the window and frequency, `--pivot` to lay
   items out as columns, and `--json` when the user wants the whole result.
   ```bash
   kosis data 101 DT_1B42 --obj-l1 ALL --pivot
   ```
3. **Relay the result.** Show the CLI's stdout. You may trim a long result, but keep the
   summary line.
4. **Error handling.** When the CLI exits non-zero, relay the one-line `kosis: <message>`
   from stderr as-is. Common ones:
   - `command not found: kosis` -> not installed; point the user at `pipx install pykosis`.
   - `no KOSIS API key ...` -> no key was found (env var and config file both empty).
   - `[20] ...` -> a required classification is missing; retry with the next `--obj-l* ALL`.
   - other `[code] ...` -> a vendor error (often a wrong org/table code or period).
   An empty result (no rows) is not an error.

## What this skill does not do

- It does not re-implement fetching or parsing (the package does); it always calls the CLI.
- It is the observation data only -- to discover org and table codes, use the **find**
  skill; for a table's metadata or survey documentation, use **meta**.

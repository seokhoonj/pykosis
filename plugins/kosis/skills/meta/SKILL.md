---
name: meta
description: "Read a KOSIS table's structural metadata -- its items, classifications, units, source, and recorded periods. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis meta`) and shows the result to the user. Trigger phrases: KOSIS 메타데이터, 통계표 설명, 통계표 항목, 단위 출처, KOSIS table metadata, what items does this table have, KOSIS table units and source."
---

# kosis -- table metadata

Describe how a KOSIS table is built rather than fetch its numbers: its name, items,
classifications, units, source, and recorded periods. The metadata and parsing live in the
pykosis package (on PyPI); this skill is a thin wrapper that calls its CLI and relays the
result. For the survey documentation behind a table (purpose, legal basis, terms), use the
**explanation** skill.

## Prerequisite

This plugin calls the `kosis` CLI, so the package must be installed and an API key set:

```
pipx install pykosis          # or: pip install pykosis
export KOSIS_API_KEY=...       # a free key from https://kosis.kr/openapi/
```

The key can also be stored in `~/.config/pykosis/credentials.json` as
`{"KOSIS_API_KEY": "..."}`. Without a key the CLI exits with
`kosis: no KOSIS API key ...`; relay that and point the user at the KOSIS site.

## Running

```
kosis meta <ORG_ID> <TBL_ID> [--type table|item|period|unit|source|comment|weight|update|organization] [--json]
```

- `kosis meta` returns one slice of a table's metadata; `--type item` lists its
  classifications and items, `--type unit` its units, `--type source` its source, and so
  on (default `table`).
- `--json` emits the full records; the text view shows aligned columns.

## Procedure

1. **Get the codes.** You need an `org_id` + `tbl_id`. If the user gave a concept but no
   codes, use the **search** (or **list**) skill first.
2. **Pick the slice.** Choose `--type` for what the user asked (items, units, source, ...).
   ```bash
   kosis meta 101 DT_1B42 --type item
   ```
3. **Relay the result.** Show the CLI's stdout. If the user asked about one field, point
   out that row.
4. **Error handling.** Relay the one-line `kosis: <message>` from stderr as-is -- the same
   key and install errors as the other kosis skills apply.

## What this skill does not do

- It does not re-implement fetching or parsing (the package does); it always calls the CLI.
- It reads a table's structure only -- for the survey documentation, use the **explanation**
  skill; to fetch its observations, use **data**; to discover org and table codes, use
  **search** or **list**.

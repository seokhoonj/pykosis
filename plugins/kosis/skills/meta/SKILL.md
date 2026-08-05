---
name: meta
description: "Read a KOSIS table's metadata and its survey documentation. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis meta` / `kosis explanation`) and shows the result to the user. Use to understand a table's items, units, and source, or a survey's purpose and method. Trigger phrases: KOSIS 메타데이터, 통계표 설명, 통계조사 설명, KOSIS table metadata, KOSIS survey documentation, what does this table contain, 통계 용어 설명."
---

# kosis -- metadata and documentation

Explain a KOSIS table rather than fetch its numbers. Two reads: `meta` returns a table's
structural metadata (name, items, units, source, periods), and `explanation` returns the survey's
documentation (purpose, legal basis, cycle, key terms). Both live in the pykosis package
(on PyPI); this skill is a thin wrapper that calls its CLI and relays the result.

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
kosis explanation [--org ORG_ID --tbl TBL_ID | --stat-id STAT_ID] [--meta-item ITEM] [--json]
```

- `kosis meta` returns one slice of a table's metadata; `--type item` lists its
  classifications and items, `--type unit` its units, `--type source` its source, and so
  on (default `table`).
- `kosis explanation` returns the survey documentation behind a table -- identify it by
  `--org`+`--tbl`, or by `--stat-id`. `--meta-item` narrows to one field (default `ALL`).
- `--json` emits the full records; the text view is aligned columns (meta) or
  `field: value` blocks (explanation).

## Procedure

1. **Get the codes.** You need an `org_id` + `tbl_id` (or a `stat_id` for `explanation`). If the
   user gave a concept but no codes, use the **find** skill first.
2. **Pick the read.** Use `meta` for structure (what items/units/classifications a table
   has), `explanation` for documentation (why and how the survey is conducted).
   ```bash
   kosis meta 101 DT_1B42 --type item
   kosis explanation --org 101 --tbl DT_1B42
   ```
3. **Relay the result.** Show the CLI's stdout. If the user asked about one field, point
   out that row or block.
4. **Error handling.** Relay the one-line `kosis: <message>` from stderr as-is -- the same
   key and install errors as the other kosis skills apply.

## What this skill does not do

- It does not re-implement fetching or parsing (the package does); it always calls the CLI.
- It explains a table -- to fetch its observations, use the **data** skill; to discover org
  and table codes, use **find**.

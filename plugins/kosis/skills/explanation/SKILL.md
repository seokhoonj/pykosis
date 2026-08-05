---
name: explanation
description: "Read the survey documentation behind a KOSIS table -- its purpose, legal basis, cycle, and key terms. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis explanation`) and shows the result to the user. Trigger phrases: 통계조사 설명, 통계 작성목적, 통계 용어 설명, 법적근거 주기, KOSIS survey documentation, why is this survey conducted, KOSIS statistic definitions."
---

# kosis -- survey documentation

Explain the survey behind a KOSIS table rather than its structure or numbers: its purpose,
legal basis, cycle, and key terms. The documentation and parsing live in the pykosis package
(on PyPI); this skill is a thin wrapper that calls its CLI and relays the result. For a
table's structural metadata (items, units, source), use the **meta** skill.

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
kosis explanation [--org ORG_ID --tbl TBL_ID | --stat-id STAT_ID] [--meta-item ITEM] [--json]
```

- Identify the survey by `--org`+`--tbl`, or directly by `--stat-id`.
- `--meta-item` narrows to one field (default `ALL`).
- `--json` emits the full records; the text view shows `field: value` blocks.

## Procedure

1. **Get the codes.** You need an `org_id` + `tbl_id`, or a `stat_id`. If the user gave a
   concept but no codes, use the **search** (or **list**) skill first.
2. **Run.** Ask for the whole documentation, or narrow with `--meta-item`.
   ```bash
   kosis explanation --org 101 --tbl DT_1B42
   ```
3. **Relay the result.** Show the CLI's stdout. If the user asked about one field, point
   out that block.
4. **Error handling.** Relay the one-line `kosis: <message>` from stderr as-is -- the same
   key and install errors as the other kosis skills apply.

## What this skill does not do

- It does not re-implement fetching or parsing (the package does); it always calls the CLI.
- It reads the survey documentation only -- for a table's items/units/source, use the
  **meta** skill; to fetch its observations, use **data**; to discover org and table codes,
  use **search** or **list**.

---
name: list
description: "Find KOSIS organization and table codes (orgId/tblId) by browsing the classification tree one level at a time. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis list`) and shows the result to the user. Use this to walk a subject or organization view down to its tables. Trigger phrases: KOSIS 분류 트리, 통계 목록 훑어, 주제별 통계 목록, 기관별 통계 목록, browse KOSIS catalog, KOSIS statistics list, list tables under, 국가통계 목록."
---

# kosis -- list (catalog tree)

Discover the codes a KOSIS statistic is stored under by browsing its catalog tree. KOSIS
keys every table by an organization code (`org_id`) plus a table code (`tbl_id`), and
`kosis list` walks the classification tree one level at a time until it reaches the tables.
The listing and parsing live in the pykosis package (on PyPI); this skill is a thin wrapper
that calls its CLI and relays the result. To find a table by keyword instead, use the
**search** skill.

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
kosis list [--view VIEW] [--parent LIST_ID] [--json]
```

- With no `--parent`, `kosis list` lists the top of a view; pass a returned `list_id` as
  `--parent` to descend one level. The KOSIS tree is deep, so drill down one step at a time.
- A row with a `tbl_id` is a table you can hand to the **data** skill; a row with only a
  `list_id` is a folder to descend into.
- `--view` picks a classification view (`subject`, `organization`, `international`, ...);
  the default is `subject`.
- `--json` emits the full rows; the text view shows aligned columns and a row count.

## Procedure

1. **Start at a view.** Run `kosis list --view subject` (or another view) for the top level.
2. **Descend.** Take a `list_id` from the result and pass it as `--parent` to list its
   children; repeat until rows carry a `tbl_id`.
3. **Relay the result.** Show the CLI's stdout as-is (aligned columns + row count).
4. **Error handling.** Relay the one-line `kosis: <message>` from stderr as-is. An empty
   listing prints `(no rows)`.

## What this skill does not do

- It does not re-implement the catalog or parsing (the package does); it always calls the CLI.
- It browses the tree only -- to find a table by keyword, use the **search** skill; to fetch
  a table's observations, use the **data** skill; for a table's metadata use **meta**, and
  for its survey documentation **explanation**.

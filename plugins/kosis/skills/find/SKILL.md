---
name: find
description: "Find KOSIS organization and table codes (orgId/tblId) by keyword or by browsing the catalog tree. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis search` / `kosis list`) and shows the result to the user. Use this to turn a concept (생명표, 소비자물가) into the codes the data skill needs. Trigger phrases: KOSIS 통계표 찾아, 통계표 코드, orgId tblId 찾아, find KOSIS table code, KOSIS table id, what org and table code is, 국가통계 목록."
---

# kosis -- find (search and catalog)

Discover the codes a KOSIS statistic is stored under. KOSIS keys every table by an
organization code (`org_id`) plus a table code (`tbl_id`), and this skill finds them:
`search` looks tables up by keyword, `list` browses the classification tree one level at
a time. The searching and parsing live in the pykosis package (on PyPI); this skill is a
thin wrapper that calls its CLI and relays the result.

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
kosis search "<검색어>" [--sort rank|date] [--page-size N] [--page N] [--org ORG_ID] [--json]
kosis list [--view VIEW] [--parent LIST_ID] [--json]
```

- `kosis search "<검색어>"` finds tables whose name matches the keyword; each hit carries
  its `org_id` and `tbl_id` -- the codes the **data** skill needs.
- `kosis list` browses the catalog tree: with no `--parent` it lists the top of a view;
  pass a returned `list_id` as `--parent` to descend a level. The KOSIS tree is deep, so
  drill down one step at a time.
- `--view` picks a classification view (`subject`, `organization`, `international`, ...).
- `--json` emits the full rows; the text view shows aligned columns and a row count.

## Procedure

1. **Prefer search from a concept.** Given a keyword ("생명표", "소비자물가"), run
   `kosis search` and scan the hits for the right table; take its `org_id` + `tbl_id`.
2. **Browse when exploring.** To walk a theme rather than search, use `kosis list`,
   drilling in with `--parent`.
   ```bash
   kosis search 생명표
   kosis list --view subject
   ```
3. **Relay the result.** Show the CLI's stdout. When the goal is a single table, point out
   the one row the user needs (its `org_id` / `tbl_id`), then offer to hand it to the
   **data** skill.
4. **Error handling.** Relay the one-line `kosis: <message>` from stderr as-is. An empty
   listing prints `(no rows)`.

## What this skill does not do

- It does not re-implement searching or parsing (the package does); it always calls the CLI.
- It finds codes only -- to fetch the observations for a code, use the **data** skill; for
  a table's metadata or survey documentation, use **meta**.

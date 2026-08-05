---
name: search
description: "Find KOSIS organization and table codes (orgId/tblId) by keyword. Holds no logic of its own -- it calls the pykosis package's CLI (`kosis search`) and shows the result to the user. Use this to turn a concept (생명표, 소비자물가) into the codes the data skill needs. Trigger phrases: KOSIS 통계표 검색, 통계표 코드 찾아, orgId tblId 찾아, 생명표 코드, search KOSIS tables, find KOSIS table code, KOSIS table id, what org and table code is."
---

# kosis -- search (keyword)

Discover the codes a KOSIS statistic is stored under by keyword. KOSIS keys every table by
an organization code (`org_id`) plus a table code (`tbl_id`), and `kosis search` returns
every table whose name matches a keyword, ranked. The searching and parsing live in the
pykosis package (on PyPI); this skill is a thin wrapper that calls its CLI and relays the
result. To walk the classification tree instead of searching, use the **list** skill.

## Prerequisite

This plugin calls the `kosis` CLI, so the package must be installed and an API key set:

```
pipx install pykosis          # or: pip install pykosis
export KOSIS_API_KEY=...       # a free key from https://kosis.kr/openapi/
```

The key can also be stored in `~/.config/pykosis/credentials.json` as
`{"KOSIS_API_KEY": "..."}`. Without a key the CLI exits with
`kosis: no KOSIS API key ...`; relay that and point the user at the KOSIS site.

**Never print, log, quote, or echo the `KOSIS_API_KEY` value itself** -- confirm only that a key is set.

## Running

```
kosis search "<검색어>" [--sort rank|date] [--page-size N] [--page N] [--org ORG_ID] [--json]
```

- `kosis search "<검색어>"` finds tables whose name matches the keyword; each hit carries
  its `org_id` and `tbl_id` -- the codes the **data** skill needs.
- A keyword can match tables across many subjects (e.g. `생명` hits both 생명표 and
  생명보험 tables). Each row also carries `full_path_id` / `mt_atitle`, its classification
  path -- use `--json` to see them and tell categories apart.
- `--sort` orders by relevance (`rank`, default) or recency (`date`); `--page-size` /
  `--page` page the hits; `--org` restricts to one organization.
- `--json` emits the full rows; the text view shows aligned columns and a row count.

## Procedure

1. **Search from a concept.** Given a keyword ("생명표", "소비자물가"), run `kosis search`.
2. **Narrow if noisy.** If the keyword is broad, tighten it (`kosis search 완전생명표`) or
   restrict with `--org`.
3. **Relay the result.** Show the CLI's stdout as-is (aligned columns + row count).
4. **Error handling.** Relay the one-line `kosis: <message>` from stderr as-is. An empty
   result prints `(no rows)`.

## What this skill does not do

- It does not re-implement searching or parsing (the package does); it always calls the CLI.
- It finds codes by keyword only -- to browse the classification tree, use the **list**
  skill; to fetch a table's observations, use the **data** skill; for a table's metadata use
  **meta**, and for its survey documentation **explanation**.

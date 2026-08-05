# pykosis

[![check](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/pykosis)](https://pypi.org/project/pykosis/)
[![Python](https://img.shields.io/pypi/pyversions/pykosis)](https://pypi.org/project/pykosis/)
[![License](https://img.shields.io/pypi/l/pykosis)](https://github.com/seokhoonj/pykosis/blob/main/LICENSE)

[English](README.en.md) | **한국어**

통계청 국가통계포털 **KOSIS**의 국가통계를 읽어옵니다.

인구·가구, 노동·임금, 물가, 국민계정, 금융, 무역·국제수지, 보건·복지, 주거·국토, 교육,
농림·수산, 광공업, 건설, 교통·물류, 정보통신, 환경·에너지, 지역통계까지 — KOSIS가
서비스하는 승인통계를 통계표 코드로 조회하고, 항목을 열로 펼쳐 바로 분석에 씁니다.

## 1. 설치

```bash
pip install pykosis
```

무료 API 키는 <https://kosis.kr/openapi/> 에서 발급받으실 수 있습니다. 키는
`KOSIS(api_key=...)`, 환경변수 `KOSIS_API_KEY`, config 파일 순으로 찾습니다.

**config 파일 (모든 OS 공통, 권장)** — `~/.config/pykosis/credentials.json` 파일을 만들고
아래를 넣으세요.

```json
{ "KOSIS_API_KEY": "..." }
```

**환경변수** — macOS·Linux(bash/zsh)는 `export KOSIS_API_KEY=...`, Windows PowerShell은
`setx KOSIS_API_KEY "..."`(영구) 또는 `$env:KOSIS_API_KEY = "..."`(현재 세션). R `kosis`
패키지와 같은 이름이라 `.Renviron`에 넣어둔 키도 그대로 잡힙니다.

## 2. 빠른 시작

KOSIS는 통계를 **기관(`org_id`)** 과 **통계표(`tbl_id`)** 로 식별합니다. 코드를 모르면
`search`로 찾고, 그 코드로 `fetch_data`를 부릅니다.

```python
from pykosis import KOSIS, pivot_items

kosis = KOSIS()                                        # 환경변수·config 파일에서 키를 찾습니다

hits = kosis.search("생명표")                          # 1) 키워드로 통계표 코드 찾기
org_id, tbl_id = hits[0]["org_id"], hits[0]["tbl_id"]  #    예: "101", "DT_1B42"

rows = kosis.fetch_data(org_id=org_id, tbl_id=tbl_id,  # 2) 그 통계표의 데이터 (long 형태)
                        obj_l1="ALL")
wide = pivot_items(rows)                               # 3) 항목을 열로 펼쳐 분석용 wide로
```

반환은 `list[dict]`이라 pandas·polars 표(DataFrame)로 바로 만들 수 있습니다.

```python
import pandas as pd
import polars as pl

pd.DataFrame(wide)   # 또는 pl.DataFrame(wide)
```

해당 자료가 없는 조회는 오류가 아니라 빈 목록으로 옵니다.

### 이름으로 꺼내는 주요지표

통계표 코드를 몰라도, **KOSIS 100대 지표**는 `kosis.그룹.지표`로 바로 꺼냅니다. KOSIS의
10개 분류를 그대로 따릅니다 — `population` · `economy` · `health_welfare` ·
`education_labor` · `income_consumption` · `leisure` · `housing_transport` ·
`crime_safety` · `environment_energy` · `industry`.

```python
kosis.population.total_fertility_rate.fetch()          # 합계출산율
kosis.income_consumption.consumer_price_index.fetch()  # 소비자물가지수
kosis.health_welfare.life_expectancy.fetch()           # 기대수명
```

`.fetch(start_period=, end_period=)`로 기간을, 생략하면 최근값을 가져옵니다. 각 지표는
원본 **통계표 전체**를 돌려주니(전국·세부 계열 포함) 필요한 행을 골라 쓰세요. 표마다 다른
분류 깊이(objL)와 주기는 자동으로 맞춥니다.

지표·주기는 KOSIS 포털에서 추출해 **100개 전부 라이브로 검증**했습니다. 대형 다차원 표는
전국·계 분류를 자동으로 고정해 40,000셀 한도 안에서 조회하고, 국토면적만 원본 지적통계 표가
전체 조회 불가라 동등한 국토면적 표로 대체했습니다.

## 3. API

모든 메서드는 `list[dict]`을 돌려줍니다.

| 메서드 | 하는 일 |
|---|---|
| `search(query, *, org_id=, sort=, page=, page_size=)` | 키워드로 통계표 검색 |
| `fetch_list(*, view_code=, parent_list_id=)` | 분류 트리를 한 레벨씩 탐색 |
| `fetch_data(*, org_id, tbl_id, …)` | 한 통계표의 관측치(시계열) |
| `fetch_explanation(*, org_id=, tbl_id=, stat_id=, meta_item=)` | 통계조사 설명(목적·법적근거·주기·용어) |
| `fetch_meta(*, org_id, tbl_id, meta_type=)` | 통계표 메타데이터(표명·항목·단위·출처) |
| `fetch_indicator(indicator_id, *, section=, page=, page_size=)` | 통계주요지표 설명(개념·산정방법·출처) |
| `pivot_items(rows, label=)` | long 관측치를 항목별 열로 펼친 wide로 |
| `clear_cache()` | `cache_ttl`로 켠 응답 캐시를 비움 |

### fetch_data — 한 통계표의 데이터

```python
rows = kosis.fetch_data(
    org_id="101", tbl_id="DT_1B42",
    frequency="annual",                       # 수록 주기 (아래 표 참고)
    start_period="2015", end_period="2023",   # 기간 지정 (생략하면 최근 recent_count개)
    item_id="ALL",                            # 항목 전체
    obj_l1="ALL",                             # 분류 1레벨 전체
)
```

- **기간**: `start_period`/`end_period`를 주면 그 구간을, 둘 다 생략하면 최근
  `recent_count`개(기본 3)를 가져옵니다.
- **분류 레벨**: 통계표는 최대 8개 분류축(`obj_l1`~`obj_l8`)을 가집니다. `obj_l1`은 기본
  `"ALL"`, 나머지는 비어 있습니다. KOSIS가 `err=20`(필수 분류 누락) 오류를 내면 다음
  레벨을 `"ALL"`로 채우세요 — `obj_l2="ALL"`, 그래도 나면 `obj_l3="ALL"`, ...
- 값이 없는 셀은 `data_value`가 `None`으로 옵니다. 한 번에 40,000셀까지이므로 큰 표는
  기간이나 분류를 좁혀 부르세요.

### pivot_items — 항목을 열로

`fetch_data`는 (분류, 항목, 기간)마다 한 행인 **long** 형태입니다. 항목을 열로 펼치면
분석하기 좋은 **wide**가 됩니다.

```python
pivot_items(rows)                  # 항목명(itm_nm)을 열 이름으로 (기본)
pivot_items(rows, label="itm_id")  # 항목코드(itm_id)를 열 이름으로
```

### search · fetch_list — 통계표 찾기

```python
kosis.search("소비자물가", sort="date", page_size=10)   # 정확도순 RANK / 최신순 DATE

kosis.fetch_list(view_code="subject")                      # 주제별 최상위
kosis.fetch_list(view_code="subject", parent_list_id="A")  # 그 하위 목록
```

`view_code`는 주제별(`subject`)·기관별(`organization`)·국제통계(`international`) 등 12가지
뷰가 있습니다(`ViewCode`). KOSIS 분류 트리는 깊으므로 반환된 `list_id`를
`parent_list_id`로 넘기며 한 단계씩 내려갑니다.

## 4. 터미널

설치하면 `kosis` 명령이 등록됩니다(`python -m pykosis`로도 실행).

```sh
kosis search 생명표                                 # 통계표 검색
kosis list --view organization --parent F_29        # 분류 트리 탐색
kosis data 101 DT_1B42 --obj-l1 ALL --pivot         # 데이터 (항목을 열로 펼침)
kosis meta 101 DT_1B42 --type item                  # 통계표 메타데이터
kosis explanation --org 101 --tbl DT_1B42           # 통계조사 설명
kosis indicator 160                                 # 통계주요지표 설명
```

| 명령 | 하는 일 |
|---|---|
| `search <검색어>` | 통계표 검색. `--sort`, `--page-size`, `--page`, `--org` |
| `list` | 분류 트리. `--view` 뷰, `--parent` 하위 목록 |
| `data <org_id> <tbl_id>` | 관측치. `--frequency`, `--start`·`--end`, `--recent`, `--interval`, `--obj-l1`~`--obj-l8`, `--item`, `--pivot` |
| `explanation` | 통계조사 설명. `--org`+`--tbl` 또는 `--stat-id`, `--meta-item` |
| `meta <org_id> <tbl_id>` | 통계표 메타데이터. `--type` |
| `indicator <indicator_id>` | 통계주요지표 설명. `--section`, `--page`, `--page-size` |

각 명령은 기본이 읽기 좋은 표이고, `--json`은 전체 결과를 냅니다. `kosis --version`으로
버전을, `kosis <명령> --help`로 전체 옵션을 봅니다.

## 5. AI 코딩 에이전트에서 사용

이 저장소는 Claude Code·Codex용 플러그인 마켓플레이스도 겸합니다 — `find`·`data`·`meta`를
`kosis` 명령을 호출하는 스킬로 제공합니다. 먼저 위에서 패키지를 설치하고 API 키를
설정하세요.

### 5.1. Claude Code

```
/plugin marketplace add seokhoonj/pykosis
/plugin install kosis@pykosis
```

그런 다음 평범하게 물어보거나("생명표 통계표 코드 찾아줘", "그 표 데이터 가져와"), 스킬을
직접 호출하세요 — `/kosis:find 생명표`, `/kosis:data 101 DT_1B42`.

### 5.2. Codex

```
codex plugin marketplace add seokhoonj/pykosis
codex plugin add kosis@pykosis
```

`find`·`data`·`meta` 스킬은 국가통계 요청에 반응하며, `kosis <명령>`으로 직접 실행해도
됩니다.

플러그인으로 설치하지 않고 쓰려면, 스킬을 스킬 디렉터리에 symlink한 뒤 접두사(`kosis:`)
없이 `/data`처럼 부르면 됩니다:

```sh
ln -s "$PWD/plugins/kosis/skills/data" ~/.claude/skills/data
```

## 6. 수록 주기 (frequency)

`fetch_data(frequency=)`와 `data --frequency`가 받는 값입니다. 라이브러리는
단어(`"annual"`)·코드(`"Y"`) 어느 쪽이든, 명령은 단어를 씁니다. 기간 형식
(`start_period` 등)은 이 주기에 맞춥니다.

| 주기 | 코드 | 단어 | 기간 예시 |
|---|---|---|---|
| 연 | `Y` | `annual` | `2024` |
| 반기 | `H` | `half_yearly` | `2024H1` |
| 분기 | `Q` | `quarterly` | `2024Q1` |
| 월 | `M` | `monthly` | `202401` |
| 일 | `D` | `daily` | `20240115` |
| 다년 | `F` | `multiyear` | `2024` |
| 부정기 | `IR` | `irregular` | `2024` |

## 7. 오류와 요청 속도

| 예외 | 언제 |
|---|---|
| `KOSISConfigError` | API 키를 찾지 못했을 때 (요청 전) |
| `KOSISAuthError` | KOSIS가 키를 거부했을 때 |
| `KOSISResponseError` | KOSIS가 오류를 돌려줬을 때 (`.code`·`.message` 포함, 예: `err=20`) |
| `KOSISRateLimitError` | 호출 속도 제한(HTTP 429)에 걸렸을 때 (`KOSISResponseError`의 하위) |
| `KOSISNetworkError` | 네트워크가 끝내 안 됐을 때 (일시적 오류는 재시도 후) |

모두 `KOSISError`의 하위입니다. KOSIS는 분당 200회로 호출을 제한하므로, 여러 표를 잇달아
읽을 때는 `KOSIS(delay_seconds=0.3)`으로 간격을 두고, `KOSIS(cache_ttl=600)`으로 같은
질의를 캐시할 수 있습니다.

## 8. 라이선스

MIT © Seokhoon Joo

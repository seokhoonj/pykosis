# pykosis

[![check](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/pykosis)](https://pypi.org/project/pykosis/)
[![Python](https://img.shields.io/pypi/pyversions/pykosis)](https://pypi.org/project/pykosis/)
[![License](https://img.shields.io/pypi/l/pykosis)](https://github.com/seokhoonj/pykosis/blob/main/LICENSE)

**한국어** | [English](README.en.md)

통계청 국가통계포털 **KOSIS**의 국가통계를 읽어옵니다.

인구와 가구, 노동과 임금, 소득·소비·자산, 물가와 국민계정, 금융과 무역·국제수지, 보건과 복지,
교육, 주거와 국토, 농림·수산, 광공업과 건설, 교통·물류, 정보통신, 과학·기술, 환경·에너지,
지역통계까지 다룹니다.

자주 쓰는 지표는 `kosis.economy.gdp`(국내총생산) 같은 **접근자**로 바로 꺼내고, 그 밖의 통계는
통계표 코드로 조회합니다.

## 1. 설치

```bash
pip install pykosis
```

이 패키지는 KOSIS API 키가 필요합니다. <https://kosis.kr/openapi/>에서 무료로 발급받으세요.
발급하신 키를 넣는 방법은 다음과 같습니다.

**방법 1 — 코드에서 직접 넣기** (바로 한 번 써볼 때)

```python
from pykosis import KOSIS

kosis = KOSIS(api_key="발급받은-키")
```

**방법 2 — 파일에 저장해서 계속 쓰기** (권장 — 한 번 저장하면 매번 안 넣어도 됩니다)

`~/.config/pykosis/credentials.json` 파일을 만들고 아래를 넣으세요.

```json
{ "KOSIS_API_KEY": "발급받은-키" }
```

그러면 이후로는 인자 없이 `KOSIS()`만 써도 이 키를 자동으로 찾습니다.

> 환경변수를 선호하면, macOS·Linux는 터미널에서 `export KOSIS_API_KEY="발급받은-키"`,
> Windows는 PowerShell에서 `setx KOSIS_API_KEY "발급받은-키"`.

## 2. 예제

```python
from pykosis import KOSIS, pivot_items

kosis = KOSIS()

# 1) 키워드로 통계표 코드 찾기 → 완전생명표 = 101 / DT_1B42
kosis.search("생명표")

# 2) 고른 코드로 통계자료 가져오기 (완전생명표)
data = kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL")

# 3) 항목을 가로 열로 펼치기
life_table = pivot_items(data, label="itm_nm")
```

반환은 `dict`의 목록이라, 표(DataFrame)로 한 줄에 바꿉니다(pandas는 필수가 아닙니다).

```python
import pandas as pd

pd.DataFrame(life_table)   # 또는 polars.DataFrame(life_table)
```

## 3. 사용법

### 3.1 `search` · `fetch_list` — 통계표 코드 찾기

KOSIS는 통계를 **기관(`org_id`)** 과 **통계표(`tbl_id`)** 로 식별합니다. 코드를 모르면
`search`(키워드)나 `fetch_list`(분류 트리)로 찾습니다.

#### 3.1.1 `search` — 키워드로 찾기

키워드가 든 표가 **순위대로 여러 개** 나옵니다. 맨 위가 꼭 원하는 표는 아니니, 표 이름
(`tbl_nm`)을 보고 원하는 `org_id`·`tbl_id`를 고릅니다.

```python
hits = kosis.search("생명")   # '생명'이 든 표를 순위대로 (여러 개)
# org  tbl               name
# 367  DT_36701_18_A001  생명보험 가구가입률      <- 맨 위지만 생명표가 아님
# 101  DT_1B41           간이생명표(5세별)
# 101  DT_1B42           완전생명표(1세별)       <- 원하는 표
# 101  DT_1B43           사망원인생명표(5세별)
# ...
```

- 각 행에는 분류 경로(`full_path_id`, 예: `"F > F_29"`)도 담겨 있어 분류를 구분할 수 있습니다.
- 키워드를 좁히면(`kosis.search("완전생명표")`) 원하는 표가 상위에 바로 뜹니다.

고른 `org_id`·`tbl_id`는 [`fetch_data`(§3.2)](#32-fetch_data--통계자료-가져오기)에 넘겨 데이터를
가져옵니다.

#### 3.1.2 `fetch_list` — 분류 트리로 찾기

코드를 모르고 분류부터 훑고 싶을 때, 트리를 한 단계씩 내려갑니다.

```python
kosis.fetch_list(view_code="MT_ZTITLE")                         # 최상위 분류 (주제별)
kosis.fetch_list(view_code="MT_ZTITLE", parent_list_id="F_29")  # 그 아래 목록 (F_29 = 생명표)
```

#### 3.1.3 `view_code` — 12가지 분류 뷰

`fetch_list`의 `view_code`는 아래 12가지 뷰 중 하나입니다. KOSIS **코드**(`"MT_ZTITLE"`)는
외우기 어려우니, 알기 쉬운 **대체명**(`"subject"`)으로도 쓸 수 있습니다.

- **함수** `view_code=` — 코드든 대체명이든 받습니다.
- **`kosis` 명령·플러그인 스킬** — 대체명만 받습니다(`--view subject`).

| Service View Code | Service View Name | Function/CLI/SKILL |
|---|---|---|
| `MT_ZTITLE` | 국내통계 주제별 | `subject` |
| `MT_OTITLE` | 국내통계 기관별 | `organization` |
| `MT_GTITLE01` | e-지방지표(주제별) | `local_subject` |
| `MT_GTITLE02` | e-지방지표(지역별) | `local_region` |
| `MT_CHOSUN_TITLE` | 광복이전통계(1908~1943) | `chosun` |
| `MT_HANKUK_TITLE` | 대한민국통계연감 | `yearbook` |
| `MT_STOP_TITLE` | 작성중지통계 | `discontinued` |
| `MT_RTITLE` | 국제통계 | `international` |
| `MT_BUKHAN` | 북한통계 | `north_korea` |
| `MT_TM1_TITLE` | 대상별통계 | `by_target` |
| `MT_TM2_TITLE` | 이슈별통계 | `by_issue` |
| `MT_ETITLE` | 영문 KOSIS | `english` |

### 3.2 `fetch_data` — 통계자료 가져오기

- `org_id`·`tbl_id`로 데이터를 내려받습니다.
- 통계표마다 분류축이 달라 `obj_l1`~`obj_l8`을 씁니다. 기본은 `obj_l1="ALL"` 하나만 켜져 있습니다.
- 오류 `err=20`(필수 분류 누락)이 나면 `obj_l2="ALL"`을 더합니다. 또 나면 `obj_l3="ALL"`, ... 반복.
- `obj_l5`~`obj_l8`이 필요한 표는 드뭅니다.

예로, **암유병자수**(`117`/`DT_117N_A00124`)는 암종·성·연령으로 나뉘어 `obj_l1`만으론 부족합니다.

```python
# 기본값: obj_l1="ALL", obj_l2="", obj_l3="", ...
kosis.fetch_data(org_id="117", tbl_id="DT_117N_A00124")

# err=20 이면 obj_l2 를 켠다
kosis.fetch_data(org_id="117", tbl_id="DT_117N_A00124", obj_l2="ALL")

# 또 err=20 이면 obj_l3 를 켠다
kosis.fetch_data(org_id="117", tbl_id="DT_117N_A00124", obj_l2="ALL", obj_l3="ALL")
```

기간은 `start_period`·`end_period`로 정하고(생략하면 최근 3개), 주기는 `frequency`로 맞춥니다(§7).

```python
# 완전생명표를 2015~2023년, 연 단위로
kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL",
                 frequency="annual", start_period="2015", end_period="2023")
```

한 번에 40,000셀까지이므로, 큰 표는 기간이나 분류를 좁혀 부릅니다.

### 3.3 `pivot_items` — 항목을 열로

- 세로로 긴 데이터에서 항목을 가로 열로 펼칩니다. 기본은 항목명(`itm_nm`).

```python
pivot_items(data)                     # itm_nm (기본)
pivot_items(data, label="itm_id")     # 항목코드로
```

### 3.4 `fetch_explanation` · `fetch_meta` — 설명과 메타데이터

- `fetch_explanation`은 통계조사 설명(목적·법적근거·주기·용어)을 줍니다.
- `fetch_meta`는 통계표 정보를 줍니다. `meta_type`으로 골라 봅니다 — `TBL`(표명)·`ORG`(기관)·
  `PRD`(수록기간)·`ITM`(항목·분류)·`CMMT`(주석). 코드(`"ITM"`)도 대체명(`"item"`)도 됩니다.

```python
kosis.fetch_explanation(org_id="101", tbl_id="DT_1B42")             # 완전생명표(101/DT_1B42) 조사 설명
kosis.fetch_meta(org_id="101", tbl_id="DT_1B42", meta_type="ITM")   # 그 표의 항목·분류(ITM)
```

### 3.5 `fetch_indicator` — 통계주요지표 설명

```python
kosis.fetch_indicator("160")   # 지표번호 160 = 합계출산율 (개념·산정방법·출처)
```

## 4. 큐레이션 지표 (100대 지표)

통계표 코드를 외우지 않고, **KOSIS 100대 지표**를 `kosis.그룹.지표.fetch()` 접근자로 바로
꺼냅니다. 편집기에서 `kosis.` 뒤를 점(`.`)으로 타고 들어가면 자동완성으로 찾을 수 있습니다.

```python
kosis.economy.gdp.fetch()                        # 국내총생산(GDP)
kosis.income_consumption.cpi.fetch()             # 소비자물가지수
kosis.health_welfare.life_expectancy.fetch()     # 기대수명
```

- `.fetch(start_period=, end_period=)`로 기간을 정하고, 생략하면 최근 3개를 가져옵니다.
- 원본 표 **전체**를 돌려주니, 필요한 행만 골라 씁니다.

지표는 KOSIS의 **10개 분야**로 묶여 있습니다.

| 그룹 | 분야 | 지표 수 |
|---|---|---|
| `population` | 인구·가구 | 15 |
| `economy` | 경제·기업 | 14 |
| `environment_energy` | 환경·에너지 | 6 |
| `health_welfare` | 보건·복지 | 13 |
| `education_labor` | 교육·노동 | 12 |
| `income_consumption` | 소득·소비 | 6 |
| `leisure` | 여가·문화 | 7 |
| `housing_transport` | 주거·교통 | 9 |
| `crime_safety` | 범죄·안전 | 5 |
| `industry` | 산업·농림·수산 | 13 |

각 분야 안의 지표는 아래 트리에서 봅니다. **끝에 `/`가 붙은 줄은 분야(그룹)**, **`/`가 없는 줄이
실제 지표**입니다 — 예: `population/`의 `total_fertility_rate` → `kosis.population.total_fertility_rate`.

```
kosis
├── population/  # 인구·가구
│   ├── single_person_households                  # 1인가구
│   ├── elderly_population                        # 고령인구
│   ├── internal_migrants                         # 국내인구 이동자수
│   ├── aging_index                               # 노령화지수
│   ├── multicultural_households                  # 다문화가구
│   ├── registered_foreigners                     # 외국인등록인구
│   ├── projected_population                      # 인구(장래인구추계)
│   ├── population_density                        # 인구밀도
│   ├── resident_registered_households            # 주민등록세대수
│   ├── resident_registered_population            # 주민등록인구
│   ├── births                                    # 출생아수
│   ├── total_fertility_rate                      # 합계출산율
│   ├── marriages                                 # 혼인건수
│   ├── households                                # 가구수
│   └── average_household_size                    # 평균 가구원수
├── economy/  # 경제·기업
│   ├── composite_economic_index                  # 경기종합지수
│   ├── gdp_growth_rate                           # 경제성장률
│   ├── gdp                                       # 국내총생산(GDP)
│   ├── equipment_investment_index                # 설비투자지수
│   ├── consumer_sentiment_index                  # 소비자심리지수
│   ├── exports                                   # 수출액
│   ├── bank_lending_rate                         # 예금은행 대출금리
│   ├── all_industry_production_index             # 전산업생산지수
│   ├── sme_count                                 # 중소기업수
│   ├── grdp                                      # 지역내총생산(GRDP)
│   ├── startups                                  # 창업기업수
│   ├── kospi                                     # 코스피지수(KOSPI)
│   ├── consolidated_fiscal_balance               # 통합재정수지
│   └── business_establishments                   # 사업체수
├── environment_energy/  # 환경·에너지
│   ├── electricity_consumption_per_capita        # 1인당 전력소비량
│   ├── pm10_concentration                        # 미세먼지 농도(PM 10)
│   ├── power_generation                          # 발전실적
│   ├── household_waste_generation                # 생활폐기물 발생량
│   ├── renewable_energy_production               # 신·재생에너지생산량
│   └── greenhouse_gas_emissions                  # 온실가스배출량
├── health_welfare/  # 보건·복지
│   ├── infectious_disease_cases                  # 감염병발생건수
│   ├── basic_livelihood_recipients               # 국민기초생활보장수급자수
│   ├── life_expectancy                           # 기대수명
│   ├── obesity_rate                              # 비만율
│   ├── cancer_cases                              # 암발생자수
│   ├── daycare_centers                           # 어린이집수
│   ├── drinking_rate                             # 음주율
│   ├── medical_institutions                      # 의료기관수
│   ├── medical_personnel                         # 의료인력수
│   ├── suicide_rate                              # 자살률
│   ├── persons_with_disabilities                 # 장애인인구
│   ├── average_height                            # 평균신장
│   └── death_rate                                # 사망률
├── education_labor/  # 교육·노동
│   ├── career_interrupted_women                  # 경력단절여성
│   ├── economically_active_population            # 경제활동인구
│   ├── employment_rate                           # 고용률
│   ├── working_hours                             # 근로시간
│   ├── wages                                     # 근로임금
│   ├── labor_productivity_index                  # 노동생산성지수
│   ├── universities                              # 대학교 수
│   ├── dual_income_households                    # 맞벌이가구
│   ├── job_vacancies                             # 빈일자리
│   ├── unemployment_rate                         # 실업률
│   ├── school_students                           # 초중고학생수
│   └── private_education_expenditure             # 학생사교육비
├── income_consumption/  # 소득·소비
│   ├── household_debt                            # 가구부채
│   ├── household_consumption_expenditure         # 가구소비지출
│   ├── median_household_income                   # 가구중위소득
│   ├── farm_household_income                     # 농가소득
│   ├── ppi                                       # 생산자물가지수
│   └── cpi                                       # 소비자물가지수
├── leisure/  # 여가·문화
│   ├── books_read_per_capita                     # 1인당 평균독서권수
│   ├── domestic_travel_rate                      # 국내여행 경험률
│   ├── libraries                                 # 도서관수
│   ├── arts_attendance_rate                      # 문화예술행사 관람률
│   ├── smartphone_overdependence_rate            # 스마트폰 과의존 위험군
│   ├── inbound_tourists                          # 외래관광객수
│   └── overseas_travel_rate                      # 해외여행 경험률
├── housing_transport/  # 주거·교통
│   ├── urban_population_ratio                    # 도시지역 인구비율
│   ├── housing_construction_permits              # 주택건설 인허가수
│   ├── housing_sales_price_index                 # 주택매매가격지수
│   ├── housing_supply_ratio                      # 주택보급률
│   ├── housing_units                             # 주택수
│   ├── land_price_change_rate                    # 지가변동률
│   ├── registered_motorcycles                    # 이륜차 신고대수
│   ├── registered_vehicles                       # 자동차 등록대수
│   └── land_area                                 # 국토면적
├── crime_safety/  # 범죄·안전
│   ├── traffic_accident_deaths                   # 교통사고 사망자수
│   ├── crime_cases                               # 범죄발생건수
│   ├── industrial_accident_victims               # 산업재해자수
│   ├── child_abuse_cases                         # 아동학대건수
│   └── earthquake_frequency                      # 지진발생빈도
└── industry/  # 산업·농림·수산
    ├── rice_consumption_per_capita               # 1인당쌀소비량
    ├── cultivated_area                           # 경지면적
    ├── return_to_farming_population              # 귀농인구
    ├── farm_population                           # 농가인구
    ├── service_production_index                  # 서비스업생산지수
    ├── retail_sales                              # 소매판매액
    ├── food_crop_production                      # 식량작물 생산량
    ├── online_shopping_transaction_value         # 온라인쇼핑몰 거래액
    ├── manufacturing_capacity_utilization_index  # 제조업 생산능력 및 가동률지수
    ├── manufacturing_production_index            # 제조업생산지수
    ├── service_establishments                    # 서비스업 사업체수
    ├── fishery_production                        # 어업생산량
    └── manufacturing_establishments              # 제조업 사업체수
```

전체 목록:

| 그룹 | 불러오기 | 지표 |
|---|---|---|
| population | `kosis.population.single_person_households` | 1인가구 |
| population | `kosis.population.elderly_population` | 고령인구 |
| population | `kosis.population.internal_migrants` | 국내인구 이동자수 |
| population | `kosis.population.aging_index` | 노령화지수 |
| population | `kosis.population.multicultural_households` | 다문화가구 |
| population | `kosis.population.registered_foreigners` | 외국인등록인구 |
| population | `kosis.population.projected_population` | 인구(장래인구추계) |
| population | `kosis.population.population_density` | 인구밀도 |
| population | `kosis.population.resident_registered_households` | 주민등록세대수 |
| population | `kosis.population.resident_registered_population` | 주민등록인구 |
| population | `kosis.population.births` | 출생아수 |
| population | `kosis.population.total_fertility_rate` | 합계출산율 |
| population | `kosis.population.marriages` | 혼인건수 |
| population | `kosis.population.households` | 가구수 |
| population | `kosis.population.average_household_size` | 평균 가구원수 |
| economy | `kosis.economy.composite_economic_index` | 경기종합지수 |
| economy | `kosis.economy.gdp_growth_rate` | 경제성장률 |
| economy | `kosis.economy.gdp` | 국내총생산(GDP) |
| economy | `kosis.economy.equipment_investment_index` | 설비투자지수 |
| economy | `kosis.economy.consumer_sentiment_index` | 소비자심리지수 |
| economy | `kosis.economy.exports` | 수출액 |
| economy | `kosis.economy.bank_lending_rate` | 예금은행 대출금리 |
| economy | `kosis.economy.all_industry_production_index` | 전산업생산지수 |
| economy | `kosis.economy.sme_count` | 중소기업수 |
| economy | `kosis.economy.grdp` | 지역내총생산(GRDP) |
| economy | `kosis.economy.startups` | 창업기업수 |
| economy | `kosis.economy.kospi` | 코스피지수(KOSPI) |
| economy | `kosis.economy.consolidated_fiscal_balance` | 통합재정수지 |
| economy | `kosis.economy.business_establishments` | 사업체수 |
| environment_energy | `kosis.environment_energy.electricity_consumption_per_capita` | 1인당 전력소비량 |
| environment_energy | `kosis.environment_energy.pm10_concentration` | 미세먼지 농도(PM 10) |
| environment_energy | `kosis.environment_energy.power_generation` | 발전실적 |
| environment_energy | `kosis.environment_energy.household_waste_generation` | 생활폐기물 발생량 |
| environment_energy | `kosis.environment_energy.renewable_energy_production` | 신·재생에너지생산량 |
| environment_energy | `kosis.environment_energy.greenhouse_gas_emissions` | 온실가스배출량 |
| health_welfare | `kosis.health_welfare.infectious_disease_cases` | 감염병발생건수 |
| health_welfare | `kosis.health_welfare.basic_livelihood_recipients` | 국민기초생활보장수급자수 |
| health_welfare | `kosis.health_welfare.life_expectancy` | 기대수명 |
| health_welfare | `kosis.health_welfare.obesity_rate` | 비만율 |
| health_welfare | `kosis.health_welfare.cancer_cases` | 암발생자수 |
| health_welfare | `kosis.health_welfare.daycare_centers` | 어린이집수 |
| health_welfare | `kosis.health_welfare.drinking_rate` | 음주율 |
| health_welfare | `kosis.health_welfare.medical_institutions` | 의료기관수 |
| health_welfare | `kosis.health_welfare.medical_personnel` | 의료인력수 |
| health_welfare | `kosis.health_welfare.suicide_rate` | 자살률 |
| health_welfare | `kosis.health_welfare.persons_with_disabilities` | 장애인인구 |
| health_welfare | `kosis.health_welfare.average_height` | 평균신장 |
| health_welfare | `kosis.health_welfare.death_rate` | 사망률 |
| education_labor | `kosis.education_labor.career_interrupted_women` | 경력단절여성 |
| education_labor | `kosis.education_labor.economically_active_population` | 경제활동인구 |
| education_labor | `kosis.education_labor.employment_rate` | 고용률 |
| education_labor | `kosis.education_labor.working_hours` | 근로시간 |
| education_labor | `kosis.education_labor.wages` | 근로임금 |
| education_labor | `kosis.education_labor.labor_productivity_index` | 노동생산성지수 |
| education_labor | `kosis.education_labor.universities` | 대학교 수 |
| education_labor | `kosis.education_labor.dual_income_households` | 맞벌이가구 |
| education_labor | `kosis.education_labor.job_vacancies` | 빈일자리 |
| education_labor | `kosis.education_labor.unemployment_rate` | 실업률 |
| education_labor | `kosis.education_labor.school_students` | 초중고학생수 |
| education_labor | `kosis.education_labor.private_education_expenditure` | 학생사교육비 |
| income_consumption | `kosis.income_consumption.household_debt` | 가구부채 |
| income_consumption | `kosis.income_consumption.household_consumption_expenditure` | 가구소비지출 |
| income_consumption | `kosis.income_consumption.median_household_income` | 가구중위소득 |
| income_consumption | `kosis.income_consumption.farm_household_income` | 농가소득 |
| income_consumption | `kosis.income_consumption.ppi` | 생산자물가지수 |
| income_consumption | `kosis.income_consumption.cpi` | 소비자물가지수 |
| leisure | `kosis.leisure.books_read_per_capita` | 1인당 평균독서권수 |
| leisure | `kosis.leisure.domestic_travel_rate` | 국내여행 경험률 |
| leisure | `kosis.leisure.libraries` | 도서관수 |
| leisure | `kosis.leisure.arts_attendance_rate` | 문화예술행사 관람률 |
| leisure | `kosis.leisure.smartphone_overdependence_rate` | 스마트폰 과의존 위험군 |
| leisure | `kosis.leisure.inbound_tourists` | 외래관광객수 |
| leisure | `kosis.leisure.overseas_travel_rate` | 해외여행 경험률 |
| housing_transport | `kosis.housing_transport.urban_population_ratio` | 도시지역 인구비율 |
| housing_transport | `kosis.housing_transport.housing_construction_permits` | 주택건설 인허가수 |
| housing_transport | `kosis.housing_transport.housing_sales_price_index` | 주택매매가격지수 |
| housing_transport | `kosis.housing_transport.housing_supply_ratio` | 주택보급률 |
| housing_transport | `kosis.housing_transport.housing_units` | 주택수 |
| housing_transport | `kosis.housing_transport.land_price_change_rate` | 지가변동률 |
| housing_transport | `kosis.housing_transport.registered_motorcycles` | 이륜차 신고대수 |
| housing_transport | `kosis.housing_transport.registered_vehicles` | 자동차 등록대수 |
| housing_transport | `kosis.housing_transport.land_area` | 국토면적 |
| crime_safety | `kosis.crime_safety.traffic_accident_deaths` | 교통사고 사망자수 |
| crime_safety | `kosis.crime_safety.crime_cases` | 범죄발생건수 |
| crime_safety | `kosis.crime_safety.industrial_accident_victims` | 산업재해자수 |
| crime_safety | `kosis.crime_safety.child_abuse_cases` | 아동학대건수 |
| crime_safety | `kosis.crime_safety.earthquake_frequency` | 지진발생빈도 |
| industry | `kosis.industry.rice_consumption_per_capita` | 1인당쌀소비량 |
| industry | `kosis.industry.cultivated_area` | 경지면적 |
| industry | `kosis.industry.return_to_farming_population` | 귀농인구 |
| industry | `kosis.industry.farm_population` | 농가인구 |
| industry | `kosis.industry.service_production_index` | 서비스업생산지수 |
| industry | `kosis.industry.retail_sales` | 소매판매액 |
| industry | `kosis.industry.food_crop_production` | 식량작물 생산량 |
| industry | `kosis.industry.online_shopping_transaction_value` | 온라인쇼핑몰 거래액 |
| industry | `kosis.industry.manufacturing_capacity_utilization_index` | 제조업 생산능력 및 가동률지수 |
| industry | `kosis.industry.manufacturing_production_index` | 제조업생산지수 |
| industry | `kosis.industry.service_establishments` | 서비스업 사업체수 |
| industry | `kosis.industry.fishery_production` | 어업생산량 |
| industry | `kosis.industry.manufacturing_establishments` | 제조업 사업체수 |

## 5. 커맨드라인

설치하면 `kosis` 명령이 함께 깔립니다.

```sh
kosis list --view subject --parent F_29       # 통계표 목록 탐색
kosis search 생명표                            # 키워드 검색
kosis data 101 DT_1B42 --obj-l1 ALL --pivot   # 통계자료 (항목을 열로)
kosis meta 101 DT_1B42 --type item            # 메타데이터
kosis explanation --org 101 --tbl DT_1B42     # 통계조사 설명
kosis indicator 160                           # 주요지표 설명
```

`--json`으로 전체 결과를, `kosis <명령> --help`로 옵션을 봅니다.

## 6. AI 코딩 에이전트에서 사용

- 이 저장소는 Claude Code·Codex용 플러그인 마켓플레이스도 겸합니다.
- `search`·`list`·`data`·`meta`·`explanation` 스킬을 제공하며, 각각 같은 이름의 `kosis` 명령에
  대응합니다.
- 먼저 패키지를 설치하고 API 키를 설정하세요.

**Claude Code**

```
/plugin marketplace add seokhoonj/pykosis
/plugin install kosis@pykosis
```

설치 후 평범하게 물어보거나("생명표 통계표 코드 찾아줘", "그 표 데이터 가져와"), 스킬을 직접
부르세요 — `/kosis:search 생명표`, `/kosis:data 101 DT_1B42`.

**Codex**

```
codex plugin marketplace add seokhoonj/pykosis
codex plugin add kosis@pykosis
```

플러그인으로 설치하지 않고 쓰려면, 스킬을 각 에이전트의 스킬 디렉터리에 symlink합니다.

```sh
ln -s "$PWD/plugins/kosis/skills/data" ~/.claude/skills/data   # Claude Code → /data
ln -s "$PWD/plugins/kosis/skills/data" ~/.codex/skills/data    # Codex → $kosis:data
```

Claude Code는 바로 인식하고, Codex는 재시작해야 로딩됩니다.

## 7. 수록 주기 (frequency)

`fetch_data(frequency=)`가 받는 값입니다. 단어·코드 어느 쪽이든 됩니다.

| 주기 | 코드 | 단어 | 기간 예시 |
|---|---|---|---|
| 연 | `Y` | `annual` | `2024` |
| 반기 | `H` | `half_yearly` | `2024H1` |
| 분기 | `Q` | `quarterly` | `2024Q1` |
| 월 | `M` | `monthly` | `202401` |
| 일 | `D` | `daily` | `20240115` |
| 다년 | `F` | `multiyear` | `2024` |
| 부정기 | `IR` | `irregular` | `2024` |

## 8. 오류

| 예외 | 언제 |
|---|---|
| `KOSISConfigError` | API 키를 찾지 못했을 때 |
| `KOSISAuthError` | KOSIS가 키를 거부했을 때 |
| `KOSISResponseError` | KOSIS가 오류를 돌려줬을 때 (`.code`·`.message`, 예: `err=20`) |
| `KOSISRateLimitError` | 호출 속도 제한(HTTP 429)에 걸렸을 때 |
| `KOSISNetworkError` | 네트워크가 끝내 안 됐을 때 |

- 모든 예외는 `KOSISError`의 하위입니다.
- 자료가 없을 뿐이면 오류가 아니라 빈 목록으로 옵니다.
- 분당 200회 제한이라, 여러 표를 잇달아 읽을 때는 `KOSIS(delay_seconds=0.3)`으로 간격을 둡니다.
- 같은 질의는 `KOSIS(cache_ttl=600)`으로 캐시하고, TTL 전에 새로 받아야 하면 `kosis.clear_cache()`로
  비웁니다.

## 9. 라이선스

MIT © Seokhoon Joo

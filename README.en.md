# pykosis

[![check](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/pykosis/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/pykosis)](https://pypi.org/project/pykosis/)
[![Python](https://img.shields.io/pypi/pyversions/pykosis)](https://pypi.org/project/pykosis/)
[![License](https://img.shields.io/pypi/l/pykosis)](https://github.com/seokhoonj/pykosis/blob/main/LICENSE)

**English** | [한국어](README.md)

Read Korea's national statistics from **KOSIS** (the Korean Statistical Information Service).

KOSIS serves approved statistics across nearly every field -- population, the economy,
prices, employment, housing, health, education, industry. pykosis wraps the six KOSIS Open
API services so you can search the table catalog, fetch a table's data, and pivot its items
into columns for analysis.

The **top-100 KOSIS headline indicators** are also reachable by name, without a table code,
like `kosis.population.total_fertility_rate` (see the section below).

## Install

```bash
pip install pykosis
```

Get a free API key at <https://kosis.kr/openapi/>. The key is resolved from
`KOSIS(api_key="...")`, the `KOSIS_API_KEY` environment variable, then
`~/.config/pykosis/credentials.json`, in that order. It is the same name the R `kosis`
package uses, so a key in `.Renviron` is picked up unchanged.

## Example

```python
from pykosis import KOSIS, pivot_items

kosis = KOSIS()

# find a table code (org_id, tbl_id) in the catalog
kosis.fetch_list(view_code="MT_ZTITLE")                         # "MT_ZTITLE" or "subject" both work
kosis.fetch_list(view_code="MT_ZTITLE", parent_list_id="F_29")  # the life-table tables

# fetch a table (the complete life table)
data = kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL")
life_table = pivot_items(data, label="itm_nm")
```

`view_code` accepts either the KOSIS code (`"MT_ZTITLE"`) or the short name (`"subject"`) --
the twelve views are listed in Usage 1 below. Every result is a `list[dict]`, so
`pandas.DataFrame(life_table)` or `polars.DataFrame(life_table)` turns it into a table in one
line.

## Usage

### 1. `fetch_list` · `search` -- find a table code

KOSIS identifies a statistic by an organization (`org_id`) and a table (`tbl_id`). If you do
not know the codes, find them with `search` (keyword) or by browsing the tree with
`fetch_list`.

`search` returns a **page of matching tables**, ranked (20 by default) -- the top hit is not
necessarily the one you want. Read each `tbl_nm`, pick the `org_id` / `tbl_id` you need, and
pass it to `fetch_data`.

```python
hits = kosis.search("생명")   # many tables contain "생명" (life / life-insurance)
# org  tbl               name
# 367  DT_36701_18_A001  생명보험 가구가입률      <- top hit, but NOT a life table
# 101  DT_1B41           간이생명표(5세별)
# 101  DT_1B42           완전생명표(1세별)       <- the one we want
# 101  DT_1B43           사망원인생명표(5세별)
# ...

# don't just take hits[0] -- pick the org_id/tbl_id you want
data = kosis.fetch_data(org_id="101", tbl_id="DT_1B42", obj_l1="ALL")
```

Each hit also carries its classification path (`full_path_id`, e.g. `"F > F_29"`), so you
can tell categories apart. Narrowing the keyword (`kosis.search("완전생명표")`) floats the
right table to the top. To browse by classification instead of searching, descend the tree:

```python
kosis.fetch_list(view_code="MT_ZTITLE")                         # top level
kosis.fetch_list(view_code="MT_ZTITLE", parent_list_id="F_29")  # one level down (life tables)
```

`view_code` is one of twelve classification views. The Service View Code (`"MT_ZTITLE"`)
works in the function only; the short name (`"subject"`) works everywhere -- the function
takes either, while the `kosis` command and the plugin skills take the short name
(`--view subject`).

| Service View Code | Service View Name | Function/CLI/SKILL |
|---|---|---|
| `MT_ZTITLE` | domestic, by subject | `subject` |
| `MT_OTITLE` | domestic, by organization | `organization` |
| `MT_GTITLE01` | e-local indicators (by subject) | `local_subject` |
| `MT_GTITLE02` | e-local indicators (by region) | `local_region` |
| `MT_CHOSUN_TITLE` | pre-liberation statistics (1908-1943) | `chosun` |
| `MT_HANKUK_TITLE` | Korea statistical yearbook | `yearbook` |
| `MT_STOP_TITLE` | discontinued statistics | `discontinued` |
| `MT_RTITLE` | international statistics | `international` |
| `MT_BUKHAN` | North Korea statistics | `north_korea` |
| `MT_TM1_TITLE` | statistics by target | `by_target` |
| `MT_TM2_TITLE` | statistics by issue | `by_issue` |
| `MT_ETITLE` | English KOSIS | `english` |

### 2. `fetch_data` -- fetch a table

- Download data by `org_id` + `tbl_id`.
- A table's classification axes vary, so it takes `obj_l1`..`obj_l8`. Only `obj_l1="ALL"`
  is on by default.
- On error `err=20` (a required classification is missing), add `obj_l2="ALL"`. If it
  recurs, add `obj_l3="ALL"`, and so on.
- Tables that need `obj_l5`..`obj_l8` are rare.

```python
# defaults: obj_l1="ALL", obj_l2="", obj_l3="", ...
kosis.fetch_data(org_id="117", tbl_id="DT_117N_A00124")

# on err=20, turn on obj_l2
kosis.fetch_data(org_id="117", tbl_id="DT_117N_A00124", obj_l2="ALL")

# on err=20 again, turn on obj_l3
kosis.fetch_data(org_id="117", tbl_id="DT_117N_A00124", obj_l2="ALL", obj_l3="ALL")
```

Set the window with `start_period` / `end_period` (omit for the most recent 3), and the
frequency with `frequency` (see the table below). A single call returns up to 40,000 cells,
so narrow the window or classification for large tables.

### 3. `pivot_items` -- items to columns

- Spread a table's items from rows into columns. The default label is the item name
  (`itm_nm`).

```python
pivot_items(data)                     # itm_nm (default)
pivot_items(data, label="itm_id")     # by item code
```

### 4. `fetch_explanation` · `fetch_meta` -- documentation and metadata

- `fetch_explanation` returns the survey documentation (purpose, legal basis, cycle, terms).
- `fetch_meta` returns a table's structural metadata. Pick a slice with `meta_type` --
  `TBL` (name), `ORG` (organization), `PRD` (periods), `ITM` (items and classifications),
  `CMMT` (annotations). Either the code (`"ITM"`) or the friendly name (`"item"`) works.

```python
kosis.fetch_explanation(org_id="101", tbl_id="DT_1B42")
kosis.fetch_meta(org_id="101", tbl_id="DT_1B42", meta_type="ITM")
```

### 5. `fetch_indicator` -- key-indicator documentation

```python
kosis.fetch_indicator("160")   # a key indicator's concept, method, and source by number
```

## Headline indicators by name (top 100)

Without memorizing a table code, reach the **top-100 KOSIS indicators** as
`kosis.<group>.<indicator>.fetch()`. In an editor, tab through `kosis.` with the dot to find
them by autocomplete.

```python
kosis.population.total_fertility_rate.fetch()          # total fertility rate
kosis.income_consumption.consumer_price_index.fetch()  # consumer price index
kosis.health_welfare.life_expectancy.fetch()           # life expectancy
```

Set a window with `.fetch(start_period=, end_period=)`; omit it for the most recent 3. Each
indicator returns its whole source table, so filter it for the rows you want.

In the tree below, **a line ending in `/` is a group** and **a line without `/` is an actual
indicator**. Join the dots to call one -- e.g. `total_fertility_rate` under `population/` is
`kosis.population.total_fertility_rate`.

```
kosis
├── population/  # Population & households
│   ├── single_person_households                  # Single person households
│   ├── elderly_population                        # Elderly population
│   ├── internal_migrants                         # Internal migrants
│   ├── aging_index                               # Aging index
│   ├── multicultural_households                  # Multicultural households
│   ├── registered_foreigners                     # Registered foreigners
│   ├── projected_population                      # Projected population
│   ├── population_density                        # Population density
│   ├── resident_registered_households            # Resident registered households
│   ├── resident_registered_population            # Resident registered population
│   ├── births                                    # Births
│   ├── total_fertility_rate                      # Total fertility rate
│   ├── marriages                                 # Marriages
│   ├── households                                # Households
│   └── average_household_size                    # Average household size
├── economy/  # Economy & business
│   ├── composite_economic_index                  # Composite economic index
│   ├── gdp_growth_rate                           # GDP growth rate
│   ├── gdp                                       # GDP
│   ├── equipment_investment_index                # Equipment investment index
│   ├── consumer_sentiment_index                  # Consumer sentiment index
│   ├── exports                                   # Exports
│   ├── bank_lending_rate                         # Bank lending rate
│   ├── all_industry_production_index             # All industry production index
│   ├── sme_count                                 # SME count
│   ├── grdp                                      # GRDP
│   ├── startups                                  # Startups
│   ├── kospi                                     # KOSPI
│   ├── consolidated_fiscal_balance               # Consolidated fiscal balance
│   └── business_establishments                   # Business establishments
├── environment_energy/  # Environment & energy
│   ├── electricity_consumption_per_capita        # Electricity consumption per capita
│   ├── pm10_concentration                        # PM10 concentration
│   ├── power_generation                          # Power generation
│   ├── household_waste_generation                # Household waste generation
│   ├── renewable_energy_production               # Renewable energy production
│   └── greenhouse_gas_emissions                  # Greenhouse gas emissions
├── health_welfare/  # Health & welfare
│   ├── infectious_disease_cases                  # Infectious disease cases
│   ├── basic_livelihood_recipients               # Basic livelihood recipients
│   ├── life_expectancy                           # Life expectancy
│   ├── obesity_rate                              # Obesity rate
│   ├── cancer_cases                              # Cancer cases
│   ├── daycare_centers                           # Daycare centers
│   ├── drinking_rate                             # Drinking rate
│   ├── medical_institutions                      # Medical institutions
│   ├── medical_personnel                         # Medical personnel
│   ├── suicide_rate                              # Suicide rate
│   ├── persons_with_disabilities                 # Persons with disabilities
│   ├── average_height                            # Average height
│   └── death_rate                                # Death rate
├── education_labor/  # Education & labor
│   ├── career_interrupted_women                  # Career interrupted women
│   ├── economically_active_population            # Economically active population
│   ├── employment_rate                           # Employment rate
│   ├── working_hours                             # Working hours
│   ├── wages                                     # Wages
│   ├── labor_productivity_index                  # Labor productivity index
│   ├── universities                              # Universities
│   ├── dual_income_households                    # Dual income households
│   ├── job_vacancies                             # Job vacancies
│   ├── unemployment_rate                         # Unemployment rate
│   ├── school_students                           # School students
│   └── private_education_spending                # Private education spending
├── income_consumption/  # Income & consumption
│   ├── household_debt                            # Household debt
│   ├── household_consumption_expenditure         # Household consumption expenditure
│   ├── median_household_income                   # Median household income
│   ├── farm_household_income                     # Farm household income
│   ├── producer_price_index                      # Producer price index
│   └── consumer_price_index                      # Consumer price index
├── leisure/  # Leisure & culture
│   ├── books_read_per_capita                     # Books read per capita
│   ├── domestic_travel_rate                      # Domestic travel rate
│   ├── libraries                                 # Libraries
│   ├── arts_attendance_rate                      # Arts attendance rate
│   ├── smartphone_overdependence_rate            # Smartphone overdependence rate
│   ├── inbound_tourists                          # Inbound tourists
│   └── overseas_travel_rate                      # Overseas travel rate
├── housing_transport/  # Housing & transport
│   ├── urban_population_ratio                    # Urban population ratio
│   ├── housing_construction_permits              # Housing construction permits
│   ├── house_sale_price_index                    # House sale price index
│   ├── housing_supply_ratio                      # Housing supply ratio
│   ├── housing_units                             # Housing units
│   ├── land_price_change_rate                    # Land price change rate
│   ├── registered_motorcycles                    # Registered motorcycles
│   ├── registered_vehicles                       # Registered vehicles
│   └── land_area                                 # Land area
├── crime_safety/  # Crime & safety
│   ├── traffic_accident_deaths                   # Traffic accident deaths
│   ├── crime_cases                               # Crime cases
│   ├── industrial_accident_victims               # Industrial accident victims
│   ├── child_abuse_cases                         # Child abuse cases
│   └── earthquake_frequency                      # Earthquake frequency
└── industry/  # Industry, farming & fishing
    ├── rice_consumption_per_capita               # Rice consumption per capita
    ├── cultivated_area                           # Cultivated area
    ├── return_to_farming_population              # Return to farming population
    ├── farm_population                           # Farm population
    ├── service_production_index                  # Service production index
    ├── retail_sales                              # Retail sales
    ├── grain_production                          # Grain production
    ├── online_shopping_transaction_value         # Online shopping transaction value
    ├── manufacturing_capacity_utilization_index  # Manufacturing capacity utilization index
    ├── manufacturing_production_index            # Manufacturing production index
    ├── service_establishments                    # Service establishments
    ├── fishery_production                        # Fishery production
    └── manufacturing_establishments              # Manufacturing establishments
```

Full list:

| Group | Call | Indicator |
|---|---|---|
| population | `kosis.population.single_person_households` | Single person households |
| population | `kosis.population.elderly_population` | Elderly population |
| population | `kosis.population.internal_migrants` | Internal migrants |
| population | `kosis.population.aging_index` | Aging index |
| population | `kosis.population.multicultural_households` | Multicultural households |
| population | `kosis.population.registered_foreigners` | Registered foreigners |
| population | `kosis.population.projected_population` | Projected population |
| population | `kosis.population.population_density` | Population density |
| population | `kosis.population.resident_registered_households` | Resident registered households |
| population | `kosis.population.resident_registered_population` | Resident registered population |
| population | `kosis.population.births` | Births |
| population | `kosis.population.total_fertility_rate` | Total fertility rate |
| population | `kosis.population.marriages` | Marriages |
| population | `kosis.population.households` | Households |
| population | `kosis.population.average_household_size` | Average household size |
| economy | `kosis.economy.composite_economic_index` | Composite economic index |
| economy | `kosis.economy.gdp_growth_rate` | GDP growth rate |
| economy | `kosis.economy.gdp` | GDP |
| economy | `kosis.economy.equipment_investment_index` | Equipment investment index |
| economy | `kosis.economy.consumer_sentiment_index` | Consumer sentiment index |
| economy | `kosis.economy.exports` | Exports |
| economy | `kosis.economy.bank_lending_rate` | Bank lending rate |
| economy | `kosis.economy.all_industry_production_index` | All industry production index |
| economy | `kosis.economy.sme_count` | SME count |
| economy | `kosis.economy.grdp` | GRDP |
| economy | `kosis.economy.startups` | Startups |
| economy | `kosis.economy.kospi` | KOSPI |
| economy | `kosis.economy.consolidated_fiscal_balance` | Consolidated fiscal balance |
| economy | `kosis.economy.business_establishments` | Business establishments |
| environment_energy | `kosis.environment_energy.electricity_consumption_per_capita` | Electricity consumption per capita |
| environment_energy | `kosis.environment_energy.pm10_concentration` | PM10 concentration |
| environment_energy | `kosis.environment_energy.power_generation` | Power generation |
| environment_energy | `kosis.environment_energy.household_waste_generation` | Household waste generation |
| environment_energy | `kosis.environment_energy.renewable_energy_production` | Renewable energy production |
| environment_energy | `kosis.environment_energy.greenhouse_gas_emissions` | Greenhouse gas emissions |
| health_welfare | `kosis.health_welfare.infectious_disease_cases` | Infectious disease cases |
| health_welfare | `kosis.health_welfare.basic_livelihood_recipients` | Basic livelihood recipients |
| health_welfare | `kosis.health_welfare.life_expectancy` | Life expectancy |
| health_welfare | `kosis.health_welfare.obesity_rate` | Obesity rate |
| health_welfare | `kosis.health_welfare.cancer_cases` | Cancer cases |
| health_welfare | `kosis.health_welfare.daycare_centers` | Daycare centers |
| health_welfare | `kosis.health_welfare.drinking_rate` | Drinking rate |
| health_welfare | `kosis.health_welfare.medical_institutions` | Medical institutions |
| health_welfare | `kosis.health_welfare.medical_personnel` | Medical personnel |
| health_welfare | `kosis.health_welfare.suicide_rate` | Suicide rate |
| health_welfare | `kosis.health_welfare.persons_with_disabilities` | Persons with disabilities |
| health_welfare | `kosis.health_welfare.average_height` | Average height |
| health_welfare | `kosis.health_welfare.death_rate` | Death rate |
| education_labor | `kosis.education_labor.career_interrupted_women` | Career interrupted women |
| education_labor | `kosis.education_labor.economically_active_population` | Economically active population |
| education_labor | `kosis.education_labor.employment_rate` | Employment rate |
| education_labor | `kosis.education_labor.working_hours` | Working hours |
| education_labor | `kosis.education_labor.wages` | Wages |
| education_labor | `kosis.education_labor.labor_productivity_index` | Labor productivity index |
| education_labor | `kosis.education_labor.universities` | Universities |
| education_labor | `kosis.education_labor.dual_income_households` | Dual income households |
| education_labor | `kosis.education_labor.job_vacancies` | Job vacancies |
| education_labor | `kosis.education_labor.unemployment_rate` | Unemployment rate |
| education_labor | `kosis.education_labor.school_students` | School students |
| education_labor | `kosis.education_labor.private_education_spending` | Private education spending |
| income_consumption | `kosis.income_consumption.household_debt` | Household debt |
| income_consumption | `kosis.income_consumption.household_consumption_expenditure` | Household consumption expenditure |
| income_consumption | `kosis.income_consumption.median_household_income` | Median household income |
| income_consumption | `kosis.income_consumption.farm_household_income` | Farm household income |
| income_consumption | `kosis.income_consumption.producer_price_index` | Producer price index |
| income_consumption | `kosis.income_consumption.consumer_price_index` | Consumer price index |
| leisure | `kosis.leisure.books_read_per_capita` | Books read per capita |
| leisure | `kosis.leisure.domestic_travel_rate` | Domestic travel rate |
| leisure | `kosis.leisure.libraries` | Libraries |
| leisure | `kosis.leisure.arts_attendance_rate` | Arts attendance rate |
| leisure | `kosis.leisure.smartphone_overdependence_rate` | Smartphone overdependence rate |
| leisure | `kosis.leisure.inbound_tourists` | Inbound tourists |
| leisure | `kosis.leisure.overseas_travel_rate` | Overseas travel rate |
| housing_transport | `kosis.housing_transport.urban_population_ratio` | Urban population ratio |
| housing_transport | `kosis.housing_transport.housing_construction_permits` | Housing construction permits |
| housing_transport | `kosis.housing_transport.house_sale_price_index` | House sale price index |
| housing_transport | `kosis.housing_transport.housing_supply_ratio` | Housing supply ratio |
| housing_transport | `kosis.housing_transport.housing_units` | Housing units |
| housing_transport | `kosis.housing_transport.land_price_change_rate` | Land price change rate |
| housing_transport | `kosis.housing_transport.registered_motorcycles` | Registered motorcycles |
| housing_transport | `kosis.housing_transport.registered_vehicles` | Registered vehicles |
| housing_transport | `kosis.housing_transport.land_area` | Land area |
| crime_safety | `kosis.crime_safety.traffic_accident_deaths` | Traffic accident deaths |
| crime_safety | `kosis.crime_safety.crime_cases` | Crime cases |
| crime_safety | `kosis.crime_safety.industrial_accident_victims` | Industrial accident victims |
| crime_safety | `kosis.crime_safety.child_abuse_cases` | Child abuse cases |
| crime_safety | `kosis.crime_safety.earthquake_frequency` | Earthquake frequency |
| industry | `kosis.industry.rice_consumption_per_capita` | Rice consumption per capita |
| industry | `kosis.industry.cultivated_area` | Cultivated area |
| industry | `kosis.industry.return_to_farming_population` | Return to farming population |
| industry | `kosis.industry.farm_population` | Farm population |
| industry | `kosis.industry.service_production_index` | Service production index |
| industry | `kosis.industry.retail_sales` | Retail sales |
| industry | `kosis.industry.grain_production` | Grain production |
| industry | `kosis.industry.online_shopping_transaction_value` | Online shopping transaction value |
| industry | `kosis.industry.manufacturing_capacity_utilization_index` | Manufacturing capacity utilization index |
| industry | `kosis.industry.manufacturing_production_index` | Manufacturing production index |
| industry | `kosis.industry.service_establishments` | Service establishments |
| industry | `kosis.industry.fishery_production` | Fishery production |
| industry | `kosis.industry.manufacturing_establishments` | Manufacturing establishments |

## Command line

Installing pykosis also installs the `kosis` command.

```sh
kosis list --view subject --parent F_29       # browse the catalog tree
kosis search 생명표                            # search by keyword
kosis data 101 DT_1B42 --obj-l1 ALL --pivot   # a table's data (items as columns)
kosis meta 101 DT_1B42 --type item            # table metadata
kosis explanation --org 101 --tbl DT_1B42     # survey documentation
kosis indicator 160                           # key-indicator documentation
```

`--json` prints the full result; `kosis <command> --help` lists the options.

## Use from AI coding agents

This repo doubles as a plugin marketplace for Claude Code and Codex -- it provides
`search`, `list`, `data`, `meta`, and `explanation` skills, each named after the matching
`kosis` command (the `indicator` command has no skill). Install the package and set an API
key first.

**Claude Code**

```
/plugin marketplace add seokhoonj/pykosis
/plugin install kosis@pykosis
```

Then just ask ("find the KOSIS code for the life table", "fetch that table"), or call a
skill directly -- `/kosis:search 생명표`, `/kosis:data 101 DT_1B42`.

**Codex**

```
codex plugin marketplace add seokhoonj/pykosis
codex plugin add kosis@pykosis
```

To use a skill in **Claude Code** without installing the plugin, symlink it into Claude's
skills directory and call it without the `kosis:` prefix (e.g. `/data`).

```sh
ln -s "$PWD/plugins/kosis/skills/data" ~/.claude/skills/data
```

## Frequency

The value `fetch_data(frequency=)` accepts. Either the word or the code works.

| Frequency | Code | Word | Period example |
|---|---|---|---|
| annual | `Y` | `annual` | `2024` |
| half-yearly | `H` | `half_yearly` | `2024H1` |
| quarterly | `Q` | `quarterly` | `2024Q1` |
| monthly | `M` | `monthly` | `202401` |
| daily | `D` | `daily` | `20240115` |
| multi-year | `F` | `multiyear` | `2024` |
| irregular | `IR` | `irregular` | `2024` |

## Errors

| Exception | When |
|---|---|
| `KOSISConfigError` | no API key was found |
| `KOSISAuthError` | KOSIS rejected the key |
| `KOSISResponseError` | KOSIS returned an error (`.code` / `.message`, e.g. `err=20`) |
| `KOSISRateLimitError` | the call-rate limit (HTTP 429) was hit |
| `KOSISNetworkError` | the network failed after retries |

All subclass `KOSISError`. A query that simply has no data returns an empty list, not an
error. KOSIS caps calls at 200/min, so when reading many tables in a row, space them with
`KOSIS(delay_seconds=0.3)` and cache repeated queries with `KOSIS(cache_ttl=600)`; call
`kosis.clear_cache()` to force fresh results before the TTL expires.

## License

MIT © Seokhoon Joo

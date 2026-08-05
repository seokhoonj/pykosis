"""Row shapes and enumerations for the KOSIS Open API.

Rows come back as plain dicts (``TypedDict``) so a caller can turn them into a
DataFrame in one line -- ``pd.DataFrame(rows)`` -- without this package ever
importing pandas. Each row type is ``total=False`` because KOSIS omits fields that
do not apply to a given table (a series with three classification levels fills
``c1``..``c3`` and leaves ``c4``..``c8`` out), and the response parser passes
through *every* key the vendor sends, so a field new to the API still arrives in the
dict even before it is declared here.

Unlike the Bank of Korea ECOS API, KOSIS has no response-language parameter: every
row carries both the Korean name (``*_nm``) and the English name (``*_nm_eng``) side
by side, so there is no ``Language`` enum here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TypedDict


class ViewCode(StrEnum):
    """A KOSIS service-view classification -- the ``vwCd`` of :meth:`KOSIS.fetch_list`.

    The value is the code KOSIS expects in a request; the member name is its meaning.
    A bare string (``"MT_ZTITLE"``) is accepted anywhere a ``ViewCode`` is, because
    ``StrEnum`` members compare equal to their value.
    """

    SUBJECT       = "MT_ZTITLE"        # 국내통계 주제별
    ORGANIZATION  = "MT_OTITLE"        # 국내통계 기관별
    LOCAL_SUBJECT = "MT_GTITLE01"      # e-지방지표(주제별)
    LOCAL_REGION  = "MT_GTITLE02"      # e-지방지표(지역별)
    CHOSUN        = "MT_CHOSUN_TITLE"  # 광복이전통계(1908~1943)
    YEARBOOK      = "MT_HANKUK_TITLE"  # 대한민국통계연감
    DISCONTINUED  = "MT_STOP_TITLE"    # 작성중지통계
    INTERNATIONAL = "MT_RTITLE"        # 국제통계
    NORTH_KOREA   = "MT_BUKHAN"        # 북한통계
    BY_TARGET     = "MT_TM1_TITLE"     # 대상별통계
    BY_ISSUE      = "MT_TM2_TITLE"     # 이슈별통계
    ENGLISH       = "MT_ETITLE"        # 영문 KOSIS


class Frequency(StrEnum):
    """How often a statistic is recorded -- the KOSIS ``prdSe`` code.

    The value is the code KOSIS expects; the member name is its English meaning. This is
    the *frequency* (how often); a single observation's time label is the *period*, and
    the period-formatted bounds passed as ``start_period`` / ``end_period`` match
    the frequency: ``"2024"`` annual, ``"2024H1"`` half-yearly, ``"2024Q1"`` quarterly,
    ``"202401"`` monthly, ``"20240115"`` daily.
    """

    ANNUAL      = "Y"
    HALF_YEARLY = "H"
    QUARTERLY   = "Q"
    MONTHLY    = "M"
    DAILY      = "D"
    MULTIYEAR  = "F"
    IRREGULAR  = "IR"


class MetaType(StrEnum):
    """Which slice of a table's metadata :meth:`KOSIS.fetch_meta` returns (``type``)."""

    TABLE       = "TBL"     # table name
    ORGANIZATION = "ORG"    # organization name
    PERIOD      = "PRD"     # recorded periods
    ITEM        = "ITM"     # classifications and items
    COMMENT     = "CMMT"    # annotations
    UNIT        = "UNIT"    # units
    SOURCE      = "SOURCE"  # data source and contact
    WEIGHT      = "WGT"     # weights
    UPDATE      = "NCD"     # last-update record


class Sort(StrEnum):
    """Result ordering for :meth:`KOSIS.search` (``sort``)."""

    RANK = "RANK"  # by relevance
    DATE = "DATE"  # newest first


class IndicatorSection(StrEnum):
    """Which section :meth:`KOSIS.fetch_indicator` returns (vendor ``serviceDetail``).

    The value is the vendor detail code; the member is its meaning. ``COMPLETE`` returns
    the concept, calculation method, and source together (``jipyo_explan1``..``3``).
    """

    CONCEPT       = "pkNotion"         # concept only (jipyo_explan1)
    METHOD_SOURCE = "pkCalcMethod"     # calculation method and source
    COMPLETE      = "pkCompleteExplan"  # everything


class ListRow(TypedDict, total=False):
    """One catalog entry from :meth:`KOSIS.fetch_list` (service statisticsList).

    Field names are the KOSIS vendor keys, lower snake_cased (``VW_CD`` -> ``vw_cd``).
    """

    vw_cd: str
    vw_nm: str
    list_id: str
    list_nm: str
    org_id: str
    tbl_id: str
    tbl_nm: str
    stat_id: str
    send_de: str      # last-update date, YYYYMMDD
    rec_tbl_se: str   # recommended-table flag


class SearchRow(TypedDict, total=False):
    """One hit from :meth:`KOSIS.search` (service statisticsSearch)."""

    org_id: str
    org_nm: str
    tbl_id: str
    tbl_nm: str
    stat_id: str
    stat_nm: str
    vw_cd: str
    contents: str
    strt_prd_de: str  # earliest recorded period
    end_prd_de: str   # latest recorded period
    tbl_view_url: str
    link_url: str
    stat_db_cnt: str  # total result count
    query: str


class DataRow(TypedDict, total=False):
    """One observation from :meth:`KOSIS.fetch_data` (service statisticsParameterData).

    A table has up to eight classification levels (``c1``..``c8``); each carries a value
    code (``c1``), a value name (``c1_nm`` / ``c1_nm_eng``), and the level's own name
    (``c1_obj_nm`` / ``c1_obj_nm_eng``). Field names are the KOSIS vendor keys, lower
    snake_cased; ``data_value`` (vendor ``DT``) is the numeric cell, ``None`` when the
    vendor sent it blank or a lone dash.
    """

    org_id: str
    tbl_id: str
    tbl_nm: str
    c1: str
    c1_nm: str
    c1_nm_eng: str
    c1_obj_nm: str
    c1_obj_nm_eng: str
    c2: str
    c2_nm: str
    c2_nm_eng: str
    c2_obj_nm: str
    c2_obj_nm_eng: str
    c3: str
    c3_nm: str
    c3_nm_eng: str
    c3_obj_nm: str
    c3_obj_nm_eng: str
    c4: str
    c4_nm: str
    c4_nm_eng: str
    c4_obj_nm: str
    c4_obj_nm_eng: str
    c5: str
    c5_nm: str
    c5_nm_eng: str
    c5_obj_nm: str
    c5_obj_nm_eng: str
    c6: str
    c6_nm: str
    c6_nm_eng: str
    c6_obj_nm: str
    c6_obj_nm_eng: str
    c7: str
    c7_nm: str
    c7_nm_eng: str
    c7_obj_nm: str
    c7_obj_nm_eng: str
    c8: str
    c8_nm: str
    c8_nm_eng: str
    c8_obj_nm: str
    c8_obj_nm_eng: str
    itm_id: str
    itm_nm: str
    itm_nm_eng: str
    unit_id: str
    unit_nm: str
    unit_nm_eng: str
    prd_se: str               # frequency, e.g. "M"
    prd_de: str               # period, e.g. "202401" for monthly
    lst_chn_de: str           # last-change date
    data_value: float | None  # vendor DT, None when blank


class ExplanationRow(TypedDict, total=False):
    """One record from :meth:`KOSIS.fetch_explanation` (statisticsExplData)."""

    stats_nm: str          # survey name
    stats_kind: str        # creation type
    stats_continue: str    # continuity
    basis_law: str         # legal basis
    writing_purps: str     # survey purpose
    stats_period: str      # survey cycle
    writing_system: str    # survey system
    writing_tel: str       # contact
    stats_field: str       # statistics field
    examin_objrange: str   # target scope
    examin_obj_area: str   # target region
    josa_unit: str         # survey unit
    apply_group: str       # applied classification
    josa_itm: str          # survey items
    pub_period: str        # publication cycle
    pub_extent: str        # publication scope
    publict_mth: str       # publication method
    examin_trget_pd: str   # target period
    data_user_note: str    # usage cautions
    main_term_expl: str    # key terms
    data_collect_mth: str  # collection method
    examin_history: str    # survey history
    confm_no: str          # approval number
    confm_dt: str          # approval date
    stats_end: str         # statistics category


class MetaRow(TypedDict, total=False):
    """One metadata record from :meth:`KOSIS.fetch_meta` (statisticsData/getMeta).

    The fields present depend on the requested :class:`MetaType`; every key the vendor
    sends passes through, so this declares only the most common ones.
    """

    tbl_nm: str
    tbl_nm_eng: str
    org_nm: str
    org_nm_eng: str
    prd_se: str
    prd_de: str
    obj_id: str
    obj_nm: str
    itm_id: str
    itm_nm: str
    unit_nm: str
    cmmt_nm: str
    cmmt_dc: str


class IndicatorRow(TypedDict, total=False):
    """One record from :meth:`KOSIS.fetch_indicator` (service pkNumberService).

    Field names are the KOSIS vendor keys, lower snake_cased. ``jipyo`` is the romanized
    Korean for "indicator" (지표), kept as the vendor sends it. Which ``jipyo_explan*``
    fields are filled depends on the requested :class:`IndicatorSection`.
    """

    jipyo_id: str        # vendor jipyoId, indicator id
    jipyo_nm: str        # indicator name
    jipyo_explan: str    # explanation title
    jipyo_explan1: str   # concept
    jipyo_explan2: str   # calculation method
    jipyo_explan3: str   # source

"""Curated indicators: named shortcuts to KOSIS's 100대 지표 (key indicators).

Where :meth:`~pykosis.KOSIS.fetch_data` takes an org/table code, the curation tree takes
a name: ``kosis.population.total_fertility_rate.fetch()`` instead of remembering
``org_id="101", tbl_id="DT_1B8000H"``. Each leaf is an :class:`Indicator` carrying the
source table for one headline indicator; the groups mirror KOSIS's own categories.
"""

from ._indicator import Indicator, IndicatorSpec

__all__ = ["Indicator", "IndicatorSpec"]

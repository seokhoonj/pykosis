"""pykosis -- a Python client for the KOSIS Open API (Statistics Korea)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .client import KOSIS
from .curation import Indicator, IndicatorSpec
from .exceptions import (
    KOSISAuthError,
    KOSISConfigError,
    KOSISError,
    KOSISNetworkError,
    KOSISRateLimitError,
    KOSISResponseError,
)
from .pivot import pivot_items
from .types import (
    DataRow,
    ExplanationRow,
    Frequency,
    IndicatorRow,
    IndicatorSection,
    ListRow,
    MetaRow,
    MetaType,
    SearchRow,
    Sort,
    ViewCode,
)

try:
    __version__ = version("pykosis")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"

__all__ = [
    "KOSIS",
    "Indicator",
    "IndicatorSpec",
    "pivot_items",
    "ViewCode",
    "Frequency",
    "MetaType",
    "Sort",
    "IndicatorSection",
    "ListRow",
    "SearchRow",
    "DataRow",
    "ExplanationRow",
    "MetaRow",
    "IndicatorRow",
    "KOSISError",
    "KOSISConfigError",
    "KOSISAuthError",
    "KOSISRateLimitError",
    "KOSISResponseError",
    "KOSISNetworkError",
    "__version__",
]

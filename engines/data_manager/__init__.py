"""Engine data managers.

LAZY re-exports (PEP 562). This package's public API is unchanged — both
``from engines.data_manager import EarningsDataManager`` and
``import engines.data_manager as dm; dm.MacroDataManager`` still work — but the
submodules are now imported ON FIRST ACCESS rather than at package import.

Why (T-295): the eager imports dragged `earnings_data` (yfinance, python-dotenv),
`insider_data` (requests, bs4) and `macro_data` (requests) into EVERY import of
anything under this package. That made the dependency-light
`engines.data_manager.macro_calendar` (json + pandas only) UNIMPORTABLE in the
lean paper/Fargate image, which installs none of those scraping/HTTP deps —
`ModuleNotFoundError: yfinance` on a pure FOMC-calendar read. It broke the T-295
cloud population job and would break C/T-291's EventStateDetector the same way,
since that also consumes `macro_calendar`.

Fail-loud is preserved: touching a name whose submodule's real dependency is
absent still raises ImportError, now at first USE instead of at package import.
Note `earnings_data`'s import-time ``load_dotenv()`` side effect is likewise
deferred to first use of an earnings symbol.
"""
from __future__ import annotations

import importlib
from typing import Any

# public name -> owning submodule (imported on first attribute access)
_LAZY_EXPORTS: dict[str, str] = {
    # earnings_data (yfinance, python-dotenv)
    "EVENT_COLUMNS": "earnings_data",
    "EarningsDataError": "earnings_data",
    "EarningsDataManager": "earnings_data",
    "EarningsEvent": "earnings_data",
    "surprise_pct": "earnings_data",
    # insider_data (requests, bs4)
    "INSIDER_TXN_COLUMNS": "insider_data",
    "InsiderDataError": "insider_data",
    "InsiderDataManager": "insider_data",
    "InsiderTxn": "insider_data",
    "parse_insider_table": "insider_data",
    # macro_data (requests)
    "MACRO_SERIES": "macro_data",
    "MacroDataError": "macro_data",
    "MacroDataManager": "macro_data",
    "MacroSeries": "macro_data",
    "credit_quality_slope": "macro_data",
    "list_series": "macro_data",
    "real_fed_funds": "macro_data",
    "yoy_change": "macro_data",
    # universe
    "MEMBERSHIP_COLUMNS": "universe",
    "SP500MembershipLoader": "universe",
    "UniverseError": "universe",
    "active_at": "universe",
    "current_tickers": "universe",
    "normalize_ticker": "universe",
    "parse_membership_html": "universe",
}


def __getattr__(name: str) -> Any:
    """PEP 562: resolve a re-exported name by importing its submodule once."""
    submodule = _LAZY_EXPORTS.get(name)
    if submodule is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f"{__name__}.{submodule}"), name)
    globals()[name] = value          # cache so subsequent access skips __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(__all__)


__all__ = [
    "EVENT_COLUMNS",
    "EarningsDataError",
    "EarningsDataManager",
    "EarningsEvent",
    "INSIDER_TXN_COLUMNS",
    "InsiderDataError",
    "InsiderDataManager",
    "InsiderTxn",
    "MACRO_SERIES",
    "MEMBERSHIP_COLUMNS",
    "MacroDataError",
    "MacroDataManager",
    "MacroSeries",
    "SP500MembershipLoader",
    "UniverseError",
    "active_at",
    "credit_quality_slope",
    "current_tickers",
    "list_series",
    "normalize_ticker",
    "parse_insider_table",
    "parse_membership_html",
    "real_fed_funds",
    "surprise_pct",
    "yoy_change",
]

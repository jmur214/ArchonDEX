"""SimFin → fundamentals panel adapter.

Converts SimFin's three quarterly bulk datasets (income / balance / cashflow)
into a single PIT-aware panel keyed on (ticker, publish_date) and computes
the six Value / Quality / Accruals factors specified in
docs/Core/Ideas_Pipeline/path_c_unblock_plan.md.

PIT discipline: we use SimFin's `Publish Date` (not `Restated Date`) as the
join key. SimFin's docs state the figures themselves are latest-restated;
filtering on Publish Date gives us a defensible PIT approximation. Documented
restatement bias for accruals factors — see ws_f_fundamentals_data_scoping.md.

Free tier covers ~3,985 US tickers, ~5 years (2020-mid → present).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import simfin as sf

REPO_ROOT = Path(__file__).resolve().parents[3]
SIMFIN_RAW_DIR = REPO_ROOT / "data" / "raw" / "simfin"
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "fundamentals_simfin.parquet"


# ---------------------------------------------------------------------------
# Loaders (cached on disk by simfin package)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cached read vs declared rebuild (the 2026-10-22 incident)
# ---------------------------------------------------------------------------
# WHAT HAPPENED: `sf.load_*` RE-DOWNLOADS any raw dataset older than its refresh window
# (`refresh_days`, default 30). A panel build in a worktree whose data/raw was a symlink into
# the main tree therefore replaced the six pinned raw files (three zips, three CSVs) at 23:21;
# and `build_and_cache` rebuilt the panel whenever the raw CSVs were NEWER than it (and a key
# was set), so from then on the first load_panel() in ANY tree pointing at main's data rewrote
# the pinned data/processed/fundamentals_simfin.parquet — which the merge-gate suite did at 23:49.
#
# THE RULE NOW ([NN-FAIL-CLOSED]): a CACHED read never rebuilds and never downloads. A raw
# dataset newer than the panel is a FACT the read RECORDS (a log line), never a trigger. A
# rebuild, and a refresh of the raw datasets, happen only through the declared entrypoint
# `rebuild_panel()` — the class of scripts/rebake_fundamentals.py (explicit, non-canonical,
# WARNs that the manifest reads red until a re-pin) — and are REFUSED under the canonical /
# measured / hermetic switches. tests/test_simfin_cached_read_2026_10_22.py locks both halves.
_NEVER_REFRESH_DAYS = 10 ** 9   # simfin downloads again when file_age_days >= refresh_days
RAW_DATASETS = ("us-income-quarterly.csv", "us-balance-quarterly.csv", "us-cashflow-quarterly.csv")
REBAKE_WARN = ("[SIMFIN][WARN] rebuild_panel writes INTO the pinned scope (data/raw/simfin and "
               "data/processed/fundamentals_simfin.parquet) — the substrate manifest's verify "
               "reads red until a re-pin (scripts/gen_substrate_manifest.py generate)")


class FundamentalsPanelMissing(FileNotFoundError):
    """A cached read found no panel. The read never builds one; run the declared rebuild."""


class FundamentalsRebuildRefused(RuntimeError):
    """A rebuild/refresh asked for under a switch that forbids it, or without its inputs."""


# The canonical switch, by NAME: the same variable as data_manager.REFUSE_YFINANCE_ENV (the lock
# test asserts equality). Spelled here rather than imported so this module does not reach the
# data manager in the import graph — tests/test_env_entries_2026_10_15.py's reachability lock
# would otherwise make every script that reads the panel an "entry that reaches the data layer".
CANONICAL_SWITCH_ENV = "ARCHONDEX_REFUSE_YFINANCE_FALLBACK"


def _rebuild_refused_reason() -> Optional[str]:
    """Why a rebuild must not run here, or None. Read fresh on every call (test-friendly)."""
    from core.hermetic import hermetic_mode
    from core.measured import is_measured
    if is_measured():
        return "ARCHONDEX_MEASURED (a measured run never rebuilds a pinned input)"
    mode = hermetic_mode()
    if mode != "off":
        return f"ARCHONDEX_HERMETIC={mode} (a rebuild or refresh is the network)"
    if os.environ.get(CANONICAL_SWITCH_ENV):
        return f"{CANONICAL_SWITCH_ENV} (a canonical run refuses a rebuild)"
    return None


def raw_cache_present() -> bool:
    return all((SIMFIN_RAW_DIR / n).exists() for n in RAW_DATASETS)


def raw_staleness() -> dict[str, str]:
    """The fact a cached read records: each raw dataset's mtime relative to the panel's."""
    panel_m = PROCESSED_PATH.stat().st_mtime if PROCESSED_PATH.exists() else None
    out: dict[str, str] = {}
    for n in RAW_DATASETS:
        p = SIMFIN_RAW_DIR / n
        if not p.exists():
            out[n] = "absent"
        elif panel_m is None:
            out[n] = "present"
        else:
            out[n] = "newer_than_panel" if p.stat().st_mtime > panel_m else "older_than_panel"
    return out


def _configure_simfin(*, download: bool) -> None:
    """Point the library at data/raw/simfin. A cached read needs no key: a placeholder keeps the
    library configured, and with `refresh_days` that cannot fire it never contacts the API when
    the file is present. A DOWNLOAD needs the real key."""
    api_key = os.environ.get("SIMFIN_API_KEY")
    if download and not api_key:
        raise FundamentalsRebuildRefused("SIMFIN_API_KEY not set: a download needs the key")
    sf.set_api_key(api_key or "offline-cache-read")
    sf.set_data_dir(str(SIMFIN_RAW_DIR))   # the library keeps download/ info/ cache/ here


def load_raw_panels(*, allow_download: bool = False
                    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The 3 quarterly bulk datasets from data/raw/simfin — READ ONLY unless `allow_download`.

    A cached read with any dataset absent is REFUSED (never fetched), and an existing dataset is
    never refreshed however old (a `refresh_days` that cannot fire). `allow_download=True` is the
    declared refresh: the library downloads regardless of age (`refresh_days=0`).
    """
    if not allow_download and not raw_cache_present():
        missing = [n for n in RAW_DATASETS if not (SIMFIN_RAW_DIR / n).exists()]
        raise FundamentalsRebuildRefused(
            f"raw simfin datasets absent under {SIMFIN_RAW_DIR}: {missing}; a cached read never "
            f"downloads — the declared rebuild is scripts/rebake_simfin_panel.py --download")
    _configure_simfin(download=allow_download)
    refresh = 0 if allow_download else _NEVER_REFRESH_DAYS
    inc = sf.load_income(variant="quarterly", market="us", refresh_days=refresh)
    bal = sf.load_balance(variant="quarterly", market="us", refresh_days=refresh)
    cf = sf.load_cashflow(variant="quarterly", market="us", refresh_days=refresh)
    return inc, bal, cf


# ---------------------------------------------------------------------------
# Panel construction — join + canonical column names
# ---------------------------------------------------------------------------

# Income statement columns we keep (renamed to snake_case canonical)
_INC_KEEP = {
    "Publish Date": "publish_date",
    "Restated Date": "restated_date",
    "Fiscal Year": "fiscal_year",
    "Fiscal Period": "fiscal_period",
    "Shares (Diluted)": "shares_diluted",
    "Revenue": "revenue",
    "Gross Profit": "gross_profit",
    "Operating Income (Loss)": "operating_income",
    "Net Income (Common)": "net_income",
}

# Balance sheet columns
_BAL_KEEP = {
    "Cash, Cash Equivalents & Short Term Investments": "cash_and_st_investments",
    "Accounts & Notes Receivable": "accounts_receivable",
    "Inventories": "inventories",
    "Total Current Assets": "total_current_assets",
    "Total Assets": "total_assets",
    "Short Term Debt": "short_term_debt",
    "Total Current Liabilities": "total_current_liabilities",
    "Long Term Debt": "long_term_debt",
    "Total Liabilities": "total_liabilities",
    "Total Equity": "total_equity",
}

# Cashflow columns (used for accruals + capex)
_CF_KEEP = {
    "Net Cash from Operating Activities": "operating_cash_flow",
    "Change in Working Capital": "change_in_working_capital",
    "Change in Fixed Assets & Intangibles": "capex_change",
}


def _select_and_rename(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    available = {src: dst for src, dst in mapping.items() if src in df.columns}
    return df[list(available.keys())].rename(columns=available)


def build_panel(
    income: Optional[pd.DataFrame] = None,
    balance: Optional[pd.DataFrame] = None,
    cashflow: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Join the 3 statements into a single ticker × report_date panel.

    Returns a DataFrame indexed by (Ticker, Report Date) with canonical
    snake_case columns covering all fields needed for V/Q/A factors.
    """
    if income is None or balance is None or cashflow is None:
        income, balance, cashflow = load_raw_panels()

    inc = _select_and_rename(income, _INC_KEEP)
    bal = _select_and_rename(balance, _BAL_KEEP)
    cf = _select_and_rename(cashflow, _CF_KEEP)

    # Income carries the Publish Date / fiscal-period metadata; the other
    # two statements are joined on the same (Ticker, Report Date) index.
    panel = inc.join(bal, how="outer", rsuffix="_bal")
    panel = panel.join(cf, how="outer", rsuffix="_cf")

    panel = panel.sort_index()
    panel["publish_date"] = pd.to_datetime(panel["publish_date"])
    return panel


# ---------------------------------------------------------------------------
# Factor computation — six V/Q/A primitives
# ---------------------------------------------------------------------------

def compute_factors(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute the six V/Q/A factors specified in path_c_unblock_plan.md.

    Note: P/E and P/B require market price; we expose the BOOK-side primitives
    that don't need price. Price-relative ratios are computed at backtest time
    when daily prices are available.

    Returns the input panel with new columns appended:
      - earnings_yield_book = net_income / total_equity   (book-relative E/P proxy)
      - book_to_assets       = total_equity / total_assets (B/P proxy without price)
      - roe                  = net_income / total_equity
      - roa                  = net_income / total_assets
      - gross_margin         = gross_profit / revenue
      - gross_profitability  = gross_profit / total_assets   (Novy-Marx)
      - sloan_accruals       = (net_income - operating_cash_flow) / total_assets
      - asset_growth         = ΔTotal Assets / lagged Total Assets (per-ticker)
    """
    df = panel.copy()

    safe_div = lambda num, den: np.where(
        (den != 0) & den.notna() & num.notna(),
        num / den,
        np.nan,
    )

    df["earnings_yield_book"] = safe_div(df["net_income"], df["total_equity"])
    df["book_to_assets"] = safe_div(df["total_equity"], df["total_assets"])
    df["roe"] = safe_div(df["net_income"], df["total_equity"])
    df["roa"] = safe_div(df["net_income"], df["total_assets"])
    df["gross_margin"] = safe_div(df["gross_profit"], df["revenue"])
    df["gross_profitability"] = safe_div(df["gross_profit"], df["total_assets"])

    # Sloan accruals = NI - OCF (scaled by assets)
    df["sloan_accruals"] = safe_div(
        df["net_income"] - df["operating_cash_flow"],
        df["total_assets"],
    )

    # Per-ticker year-over-year asset growth
    df["_assets_lag4"] = df.groupby(level="Ticker")["total_assets"].shift(4)
    df["asset_growth"] = safe_div(
        df["total_assets"] - df["_assets_lag4"],
        df["_assets_lag4"],
    )
    df = df.drop(columns=["_assets_lag4"])

    return df


# ---------------------------------------------------------------------------
# Cache + public API
# ---------------------------------------------------------------------------

def cached_panel_path() -> Path:
    """THE CACHED READ: the pinned panel if present. Never a build, never a download, no
    directory created. Raw datasets newer than the panel are recorded, not acted on."""
    if not PROCESSED_PATH.exists():
        raise FundamentalsPanelMissing(
            f"{PROCESSED_PATH} absent; a cached read never builds it — the declared rebuild is "
            f"scripts/rebake_simfin_panel.py")
    stale = raw_staleness()
    if any(v == "newer_than_panel" for v in stale.values()):
        print(f"[SIMFIN][INFO] raw datasets newer than the panel: {stale} — recorded, NOT a "
              f"trigger; the pinned panel is served unchanged (a rebuild is a declared act)")
    return PROCESSED_PATH


def rebuild_panel(*, download: bool = False) -> Path:
    """THE DECLARED REBUILD — never reached by a read. Rebuilds the panel from the raw datasets,
    refreshing them from SimFin first when `download=True`. Refused under the canonical /
    measured / hermetic switches before anything is touched."""
    reason = _rebuild_refused_reason()
    if reason:
        raise FundamentalsRebuildRefused(f"rebuild refused under {reason}")
    print(REBAKE_WARN)
    inc, bal, cf = load_raw_panels(allow_download=download)
    panel = compute_factors(build_panel(inc, bal, cf))
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PROCESSED_PATH)
    return PROCESSED_PATH


def build_and_cache(force: bool = False) -> Path:
    """Compatibility name. `force=False` is the cached read (never builds, never downloads);
    `force=True` is the declared rebuild from the on-disk raw datasets (no download)."""
    return rebuild_panel(download=False) if force else cached_panel_path()


def load_panel(force_rebuild: bool = False) -> pd.DataFrame:
    """Load the cached PIT panel. Builds nothing and downloads nothing unless `force_rebuild`,
    which is the declared rebuild (refused under the canonical / measured / hermetic switches)."""
    return pd.read_parquet(build_and_cache(force=force_rebuild))

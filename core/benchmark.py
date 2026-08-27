"""
core/benchmark.py
=================
Rolling-window metrics for benchmark instruments.

Used by Discovery's validation gates and Governance's retirement gates to
replace absolute Sharpe thresholds with benchmark-relative ones. An edge that
produces Sharpe 0.5 during a bull market when SPY is at Sharpe 1.5 is
DESTROYING value vs buy-and-hold, even though Sharpe > 0.

The "right" gate is: `edge_sharpe > benchmark_sharpe - margin`. This module
supplies the benchmark_sharpe side.

Multi-benchmark gating (Phase 0.2):
- SPY alone is a flattering benchmark for a long-bias system. The honest
  test is "beat the strongest of: SPY (broad equity), QQQ (tech tilt
  representative of the universe's natural factor exposure), 60/40
  (risk-parity reference portfolio)."
- `compute_multi_benchmark_metrics()` returns metrics for all three.
- `gate_sharpe_vs_benchmark()` defaults to mode='strongest' which
  applies the strongest threshold; pass mode='spy_only' for the legacy
  single-benchmark behavior.

Design:
- Computes metrics from the SAME data source the backtest uses (data/processed).
- Caches results by (ticker, start, end) to avoid recomputation across a
  Discovery cycle where many candidates are validated against the same window.
- 60/40 portfolio is constructed from SPY + a bond proxy (TLT by default
  since AGG isn't in the cache; documented as a substitution).

No network calls. All data comes from the existing processed CSVs.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Literal, Optional

import numpy as np
import pandas as pd


DEFAULT_BENCHMARK_TICKER = "SPY"
# T-256 substrate. `tr_reconciled/` is dividend-reconciled AND deep; the flat
# `data/processed/` copies of the ETF benchmarks (QQQ, TLT, GLD, IEF, IWM, DBC)
# were never backfilled past the 2020-04-09 Alpaca window, so a benchmark built
# from them silently truncates to the post-COVID bull. Measured 2026-08-26 on
# 2005-2026: QQQ Sharpe 0.998 (shallow) vs 0.753 (deep) — the promotion gate's
# threshold ran ~0.245 too HIGH. tr_reconciled is preferred; the flat dir remains
# the fallback for tickers it does not carry (it holds the 39 ETFs only).
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
TR_RECONCILED_DIR = DEFAULT_DATA_DIR / "tr_reconciled"

# 60/40 portfolio composition. TLT (20+ year treasuries) substitutes for
# the canonical AGG (aggregate bond) since AGG is not in the cache. TLT
# has higher duration so the resulting Sharpe will be slightly different
# from a true 60/40 — documented as a known approximation.
DEFAULT_60_40_EQUITY_TICKER = "SPY"
DEFAULT_60_40_BOND_TICKER = "TLT"
DEFAULT_60_40_EQUITY_WEIGHT = 0.6


@dataclass(frozen=True)
class BenchmarkMetrics:
    """Point-in-time buy-and-hold benchmark metrics over a date window."""
    ticker: str
    start: str
    end: str
    sharpe: float
    cagr: float
    mdd: float  # negative
    vol: float
    total_return: float
    n_obs: int
    source: str = "unknown"      # which substrate the prices came from
    first_obs: str = ""          # actual first date used (NOT the requested start)
    last_obs: str = ""

    def gate_threshold(self, margin: float = 0.2) -> float:
        """The Sharpe value an edge must exceed to be worth trading over benchmark.

        margin is the tolerance — edges within `margin` of benchmark are
        accepted (transaction costs, capital-efficiency gains). Default 0.2
        requires the edge to clearly beat, not merely match, the benchmark.
        """
        return self.sharpe - margin


def _resolve_path(ticker: str, data_dir: Optional[Path] = None) -> Path:
    """THE substrate-selection rule. Single authority — `_load_benchmark_prices`
    and `_source_of` both call this so a reported provenance can never drift
    from the file actually read (they did, briefly, during this fix).

    The tr_reconciled directory is resolved RELATIVE TO THE EFFECTIVE data dir,
    at call time — never from a module-level constant frozen at import. A
    frozen constant silently defeats `DEFAULT_DATA_DIR` overrides and makes an
    isolated run read PRODUCTION prices (caught by test_synthetic_downtrend_*,
    which had written synthetic data and got real market Sharpe back).
    """
    base = DEFAULT_DATA_DIR if data_dir is None else data_dir
    tr_path = base / "tr_reconciled" / f"{ticker}_1d.csv"
    return tr_path if tr_path.exists() else base / f"{ticker}_1d.csv"


def _source_of(ticker: str, data_dir: Optional[Path] = None) -> str:
    """Which substrate `_load_benchmark_prices` WILL pick — same rule, no copy."""
    return "tr_reconciled" if _resolve_path(ticker, data_dir).parent.name == "tr_reconciled" else "processed"


@lru_cache(maxsize=512)
def _first_date(path: Path) -> "pd.Timestamp":
    """First Date in a price csv, read cheaply (header + one row)."""
    with open(path) as f:
        f.readline()
        return pd.Timestamp(f.readline().split(",")[0])


def _load_benchmark_prices(ticker: str, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load processed OHLCV for benchmark ticker. Raises FileNotFoundError if missing.

    `data_dir` defaults to whatever `DEFAULT_DATA_DIR` resolves to AT CALL TIME
    (not at module import time). This lets tests / scripts swap the data
    directory at runtime via `core.benchmark.DEFAULT_DATA_DIR = ...`. Using
    `data_dir: Path = DEFAULT_DATA_DIR` would have frozen the path at module
    load and silently ignored runtime overrides.
    """
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    # T-256 source selection. NEITHER substrate dominates:
    #   * `tr_reconciled/` is dividend-reconciled (correct TOTAL return) but
    #     carries only the 39 ETFs and starts ~2005.
    #   * the flat `data/processed/` is PRICE-ONLY, and while SPY was backfilled
    #     deep (1993), the ETF benchmarks (QQQ, TLT, GLD, IEF, IWM, DBC) were
    #     NOT and still stop at 2020-04-09.
    # CONVENTION CONSISTENCY WINS over span: a comparison mixing a price-only
    # SPY against a total-return QQQ is biased by the missing dividend yield
    # (T-256 measured SPY at 0.685%/yr) — a subtler error than a short window,
    # because nothing about the output looks wrong. So tr_reconciled is used
    # whenever it carries the ticker, and `_assert_covers_request` announces
    # when that costs the caller requested history.
    path = _resolve_path(ticker, data_dir)
    if not path.exists():
        # Processed file sometimes has only the latest row. Fall back to raw.
        raw = Path(__file__).resolve().parents[1] / "data" / "raw" / f"{ticker}_1d.csv"
        if raw.exists():
            df = pd.read_csv(raw)
            # raw format has lowercase columns + 'timestamp'
            df = df.rename(columns={
                "timestamp": "Date", "open": "Open", "high": "High",
                "low": "Low", "close": "Close", "volume": "Volume",
            })
        else:
            raise FileNotFoundError(f"No benchmark data for {ticker} in {data_dir} or raw/")
    else:
        df = pd.read_csv(path)

    # Normalize
    if "Date" not in df.columns:
        raise ValueError(f"Benchmark file {path} has no Date column")
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    df = df.sort_values("Date").drop_duplicates(subset="Date").reset_index(drop=True)
    if "Close" not in df.columns:
        raise ValueError(f"Benchmark file {path} has no Close column")
    return df[["Date", "Close"]]


@lru_cache(maxsize=256)
def compute_benchmark_metrics(
    start: str,
    end: str,
    ticker: str = DEFAULT_BENCHMARK_TICKER,
) -> BenchmarkMetrics:
    """Compute Sharpe / CAGR / MDD for benchmark buy-and-hold over [start, end].

    Dates are ISO strings (YYYY-MM-DD). Cached by args — safe to call many
    times in a Discovery cycle with the same window.

    If the benchmark file doesn't cover the window, falls back to whatever
    coverage is available (logs nothing; caller can inspect `n_obs`).
    """
    df = _load_benchmark_prices(ticker)
    start_ts = pd.Timestamp(start).tz_localize(None)
    end_ts = pd.Timestamp(end).tz_localize(None)
    mask = (df["Date"] >= start_ts) & (df["Date"] <= end_ts)
    sub = df.loc[mask].copy()

    if len(sub) < 2:
        # No coverage — return a zero-reference so gates don't accidentally pass
        return BenchmarkMetrics(
            ticker=ticker, start=start, end=end,
            sharpe=0.0, cagr=0.0, mdd=0.0, vol=0.0, total_return=0.0, n_obs=len(sub),
        )

    sub["ret"] = sub["Close"].pct_change()
    sub = sub.dropna(subset=["ret"])
    if len(sub) < 2 or not np.isfinite(sub["ret"].std()) or sub["ret"].std() < 1e-12:
        return BenchmarkMetrics(
            ticker=ticker, start=start, end=end,
            sharpe=0.0, cagr=0.0, mdd=0.0, vol=0.0, total_return=0.0, n_obs=len(sub),
        )

    daily_ret = sub["ret"]
    total_return = (1 + daily_ret).prod() - 1
    years = (sub["Date"].iloc[-1] - sub["Date"].iloc[0]).days / 365.25
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    vol = daily_ret.std() * float(np.sqrt(252))
    sharpe = (daily_ret.mean() * 252) / vol if vol > 0 else 0.0
    cum = (1 + daily_ret).cumprod()
    mdd = float(((cum - cum.cummax()) / cum.cummax()).min())

    return BenchmarkMetrics(
        ticker=ticker, start=start, end=end,
        sharpe=float(sharpe), cagr=float(cagr), mdd=float(mdd),
        vol=float(vol), total_return=float(total_return), n_obs=len(sub),
        source=_source_of(ticker),
        first_obs=str(sub["Date"].iloc[0].date()), last_obs=str(sub["Date"].iloc[-1].date()),
    )


@lru_cache(maxsize=128)
def compute_blend_metrics(
    start: str,
    end: str,
    equity_ticker: str = DEFAULT_60_40_EQUITY_TICKER,
    bond_ticker: str = DEFAULT_60_40_BOND_TICKER,
    equity_weight: float = DEFAULT_60_40_EQUITY_WEIGHT,
) -> BenchmarkMetrics:
    """Compute Sharpe / CAGR / MDD for a daily-rebalanced equity/bond blend.

    The 60/40 portfolio is rebalanced to target weights at each bar's close.
    Daily return = w_eq * eq_return + (1 - w_eq) * bond_return.

    Note on TLT vs AGG: traditional 60/40 uses an aggregate bond fund
    (AGG, BND). We substitute TLT (long-duration treasuries) since AGG
    isn't in the local cache. TLT has higher duration so realized vol
    is higher than canonical 60/40; results are directionally
    representative but not exactly comparable to public 60/40 indices.
    """
    eq = _load_benchmark_prices(equity_ticker)
    bond = _load_benchmark_prices(bond_ticker)
    start_ts = pd.Timestamp(start).tz_localize(None)
    end_ts = pd.Timestamp(end).tz_localize(None)

    eq_sub = eq.loc[(eq["Date"] >= start_ts) & (eq["Date"] <= end_ts)].copy()
    bond_sub = bond.loc[(bond["Date"] >= start_ts) & (bond["Date"] <= end_ts)].copy()
    if len(eq_sub) < 2 or len(bond_sub) < 2:
        return BenchmarkMetrics(
            ticker=f"{int(equity_weight*100)}/{int((1-equity_weight)*100)}_{equity_ticker}_{bond_ticker}",
            start=start, end=end,
            sharpe=0.0, cagr=0.0, mdd=0.0, vol=0.0, total_return=0.0,
            n_obs=min(len(eq_sub), len(bond_sub)),
        )

    eq_sub["ret"] = eq_sub["Close"].pct_change()
    bond_sub["ret"] = bond_sub["Close"].pct_change()
    merged = pd.merge(
        eq_sub[["Date", "ret"]].rename(columns={"ret": "eq_ret"}),
        bond_sub[["Date", "ret"]].rename(columns={"ret": "bond_ret"}),
        on="Date", how="inner",
    ).dropna()
    if len(merged) < 2:
        return BenchmarkMetrics(
            ticker=f"{int(equity_weight*100)}/{int((1-equity_weight)*100)}_{equity_ticker}_{bond_ticker}",
            start=start, end=end,
            sharpe=0.0, cagr=0.0, mdd=0.0, vol=0.0, total_return=0.0, n_obs=len(merged),
        )

    bw = 1.0 - equity_weight
    merged["port_ret"] = equity_weight * merged["eq_ret"] + bw * merged["bond_ret"]
    if not np.isfinite(merged["port_ret"].std()) or merged["port_ret"].std() < 1e-12:
        return BenchmarkMetrics(
            ticker=f"{int(equity_weight*100)}/{int((1-equity_weight)*100)}_{equity_ticker}_{bond_ticker}",
            start=start, end=end,
            sharpe=0.0, cagr=0.0, mdd=0.0, vol=0.0, total_return=0.0, n_obs=len(merged),
        )

    daily_ret = merged["port_ret"]
    total_return = float((1 + daily_ret).prod() - 1)
    years = (merged["Date"].iloc[-1] - merged["Date"].iloc[0]).days / 365.25
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    vol = float(daily_ret.std() * np.sqrt(252))
    sharpe = float((daily_ret.mean() * 252) / vol) if vol > 0 else 0.0
    cum = (1 + daily_ret).cumprod()
    mdd = float(((cum - cum.cummax()) / cum.cummax()).min())

    return BenchmarkMetrics(
        ticker=f"{int(equity_weight*100)}/{int((1-equity_weight)*100)}_{equity_ticker}_{bond_ticker}",
        start=start, end=end,
        sharpe=sharpe, cagr=float(cagr), mdd=mdd, vol=vol,
        total_return=total_return, n_obs=len(merged),
        source=f"{_source_of(equity_ticker)}+{_source_of(bond_ticker)}",
        first_obs=str(merged["Date"].iloc[0].date()), last_obs=str(merged["Date"].iloc[-1].date()),
    )


class BenchmarkCoverageError(RuntimeError):
    """A benchmark comparison whose members do not span the same window.

    Raised rather than returned because a "strongest benchmark" threshold built
    from unequal windows is a wrong number that LOOKS right — `[NN-FAIL-CLOSED]`.
    """


# Members of a comparison set must span within this ratio of each other.
COVERAGE_TOLERANCE = 0.98


def _assert_covers_request(metrics: Dict[str, BenchmarkMetrics], start: str, end: str) -> None:
    """Each benchmark must actually span the REQUESTED window.

    The cross-benchmark check below cannot see the case where every member
    truncates together — three benchmarks that agree with each other and all
    silently ignore ten requested years still produce a wrong threshold.
    """
    want = pd.Timestamp(start)
    late = {
        k: m for k, m in metrics.items()
        if m.n_obs > 0 and m.first_obs and pd.Timestamp(m.first_obs) > want + pd.Timedelta(days=45)
    }
    if not late:
        return
    detail = ", ".join(f"{k} starts {m.first_obs} [{m.source}]" for k, m in late.items())
    raise BenchmarkCoverageError(
        f"Benchmark data does not reach the requested start {start}: {detail}. "
        f"The dividend-reconciled substrate begins ~2005; for deeper windows use the "
        f"multi-decade substrate (data/research/substrate_multidecade) rather than "
        f"silently benchmarking a shorter period, or pass allow_unequal_coverage=True."
    )


def _assert_equal_coverage(metrics: Dict[str, BenchmarkMetrics], start: str, end: str) -> None:
    obs = {k: m.n_obs for k, m in metrics.items() if m.n_obs > 0}
    if len(obs) < 2:
        return
    lo_k, hi_k = min(obs, key=obs.get), max(obs, key=obs.get)
    if obs[lo_k] / obs[hi_k] >= COVERAGE_TOLERANCE:
        return
    detail = ", ".join(
        f"{k}={m.n_obs} obs ({m.first_obs}..{m.last_obs})" for k, m in metrics.items()
    )
    raise BenchmarkCoverageError(
        f"Benchmark comparison over {start}..{end} spans UNEQUAL windows: {detail}. "
        f"'{lo_k}' covers only {obs[lo_k]/obs[hi_k]:.0%} of '{hi_k}'. A strongest-of "
        f"threshold across different windows is not a benchmark. Either narrow the "
        f"window to the common span, or pass allow_unequal_coverage=True to state "
        f"explicitly that you accept the mismatch."
    )


def compute_multi_benchmark_metrics(
    start: str,
    end: str,
    allow_unequal_coverage: bool = False,
) -> Dict[str, BenchmarkMetrics]:
    """Compute the standard three benchmarks: SPY, QQQ, 60/40 (SPY+TLT).

    Returns a dict keyed by benchmark name. The "60/40" key uses TLT as
    the bond proxy (see compute_blend_metrics for the rationale).

    Raises BenchmarkCoverageError when the three do not span the same window —
    the defect found 2026-08-26, where QQQ/60-40 silently covered only
    2020-04-09+ while SPY covered the full request, inflating the gate
    threshold by ~0.245 Sharpe on deep windows.
    """
    out = {
        "SPY": compute_benchmark_metrics(start=start, end=end, ticker="SPY"),
        "QQQ": compute_benchmark_metrics(start=start, end=end, ticker="QQQ"),
        "60/40": compute_blend_metrics(start=start, end=end),
    }
    if not allow_unequal_coverage:
        _assert_covers_request(out, start, end)
        _assert_equal_coverage(out, start, end)
    return out


GateMode = Literal["strongest", "spy_only"]


def gate_sharpe_vs_benchmark(
    edge_sharpe: float,
    start: str,
    end: str,
    margin: float = 0.2,
    ticker: str = DEFAULT_BENCHMARK_TICKER,
    mode: GateMode = "strongest",
    allow_unequal_coverage: bool = False,
) -> tuple[bool, float]:
    """Return (passed, benchmark_threshold). Edge passes if edge_sharpe >= threshold.

    `mode='strongest'` (default, Phase 0.2): threshold is the strongest
    Sharpe across SPY, QQQ, and 60/40 over the same window, minus margin.
    This is the honest gate — beating SPY alone is the easy version.

    `mode='spy_only'`: legacy behavior — threshold is `ticker` benchmark
    Sharpe minus margin. Use for backward compatibility or A/B with old
    results. Honors the `ticker` parameter.

    Threshold = benchmark_sharpe - margin. Margin default 0.2 means an edge
    must get within 0.2 Sharpe of the benchmark OR beat it to pass.
    """
    if mode == "spy_only":
        bm = compute_benchmark_metrics(start=start, end=end, ticker=ticker)
        threshold = bm.gate_threshold(margin=margin)
        return (edge_sharpe >= threshold, threshold)

    # mode == "strongest"
    multi = compute_multi_benchmark_metrics(
        start=start, end=end, allow_unequal_coverage=allow_unequal_coverage
    )
    # Pick the strongest Sharpe; if all are zero (no coverage), threshold
    # falls back to -margin which is nearly always beatable — we don't
    # want a missing-data window to silently let everything through, so
    # log via the BenchmarkMetrics n_obs field if needed.
    strongest_sharpe = max(bm.sharpe for bm in multi.values())
    threshold = strongest_sharpe - margin
    return (edge_sharpe >= threshold, threshold)


def gate_sharpe_vs_benchmark_with_winner(
    edge_sharpe: float,
    start: str,
    end: str,
    margin: float = 0.2,
) -> tuple[bool, float, str]:
    """Same as `gate_sharpe_vs_benchmark` mode='strongest', plus the name
    of the benchmark that set the threshold. Useful for diagnostic logging.

    Returns (passed, threshold, winner_name).
    """
    multi = compute_multi_benchmark_metrics(start=start, end=end)
    winner = max(multi.items(), key=lambda kv: kv[1].sharpe)
    winner_name, winner_metrics = winner
    threshold = winner_metrics.gate_threshold(margin=margin)
    return (edge_sharpe >= threshold, threshold, winner_name)


__all__ = [
    "BenchmarkMetrics",
    "compute_benchmark_metrics",
    "compute_blend_metrics",
    "compute_multi_benchmark_metrics",
    "gate_sharpe_vs_benchmark",
    "gate_sharpe_vs_benchmark_with_winner",
    "DEFAULT_BENCHMARK_TICKER",
    "DEFAULT_60_40_EQUITY_TICKER",
    "DEFAULT_60_40_BOND_TICKER",
    "DEFAULT_60_40_EQUITY_WEIGHT",
]

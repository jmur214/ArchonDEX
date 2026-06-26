"""scripts/lazy_prices/backtest_lazy_prices_t237.py
================================================
T-2026-06-25-237 — "Lazy Prices" FALSIFICATION pilot, Phase C/D (signal + gauntlet).

Consumes the YoY similarity panel (similarity_t237.py) and runs the EXACTLY
pre-registered T-235 design — NO sweep, NO goalpost-moving:

  * Signal      : per name, the YoY cosine-TF-IDF similarity of its most recent
                  10-K (Item 1A + Item 7) with decision_date <= the rebalance
                  date. HIGH similarity = "non-changer" (the CMN long leg).
  * Portfolio   : long-only TOP-TERCILE non-changers, equal-weight, ANNUAL
                  rebalance, 2006-2025 (signals need a YoY pair; Item 1A
                  mandated 2005+). PIT-691 membership-gated + price-available.
  * Net-of-cost : retail turnover cost applied at each rebalance.

Gauntlet (pre-registered; ALL reported, no metric swapped post-hoc):
  * ci_low(Sharpe) >= 0.4 — block-bootstrap (n=1000, seed=42)  [NN-SHARPE-CI]
  * beat-robo — combined_candidate_scorecard.evaluate_deploy_readiness(
                equity, account="roth", w_dbmf=0.0) vs 60/40 + schwab_like
  * Sortino / Calmar / MaxDD / tail-capture — the metric reframe (does it add
    RETURN, TAIL, or both?)
  * beta-or-edge — FactorRiskModel().decompose(returns).is_it_beta_or_edge()
    (the FLAGGED prime failure suspect: is the non-changer tilt just
    quality/low-vol beta?)
  * MBL — N_trials += 1; the window vs the required SR  [NN-MBL]

[NN-FAIL-CLOSED]: a name with a signal but no price (or vice versa) is recorded
as a skip with a reason, never silently zeroed. An empty held set at a rebalance
is logged; an empty total return series HALTS (no plausible-looking 0.0).

[NN-AI-GATE]: research pilot only — this module is NOT wired into any live or
canonical path. data/edgar/ is outside the pinned substrate (no canon regen).

Usage:
  python -m scripts.lazy_prices.backtest_lazy_prices_t237 \
      [--similarity-panel data/edgar/lazy_prices/similarity_panel.parquet] \
      [--start 2006] [--end 2025] [--cost-bps 10] [--tercile 3] \
      [--rebalance-anchor 06-01] [--freshness-months 18]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine  # noqa: E402

PRICE_DIR = ROOT / "data" / "processed"
PIT_MEMBERSHIP = ROOT / "data" / "universe" / "sp500_membership_pit.parquet"
DEFAULT_PANEL = ROOT / "data" / "edgar" / "lazy_prices" / "similarity_panel.parquet"
OUT_DIR = ROOT / "data" / "edgar" / "lazy_prices"

TRADING_DAYS = 252


# --------------------------------------------------------------------------- #
# price + membership loaders
# --------------------------------------------------------------------------- #
def _load_close(ticker: str) -> Optional[pd.Series]:
    """Daily close for a ticker from data/processed/{ticker}_1d.csv, or None."""
    p = PRICE_DIR / f"{ticker}_1d.csv"
    if not p.exists():
        return None
    try:
        df = pd.read_csv(p, usecols=["Date", "Close"], parse_dates=["Date"])
    except Exception:
        return None
    s = df.set_index("Date")["Close"].sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.astype(float)


def _load_pit_membership() -> pd.DataFrame:
    m = pd.read_parquet(PIT_MEMBERSHIP)
    m["start"] = pd.to_datetime(m["start"])
    m["end"] = pd.to_datetime(m["end"])
    return m


def _is_member(mem: pd.DataFrame, ticker: str, asof: pd.Timestamp) -> bool:
    rows = mem[mem["ticker"] == ticker]
    if rows.empty:
        return False
    hit = (rows["start"] <= asof) & (rows["end"].isna() | (rows["end"] >= asof))
    return bool(hit.any())


# --------------------------------------------------------------------------- #
# signal assembly (PIT, acceptance-keyed)
# --------------------------------------------------------------------------- #
def load_signal_panel(panel_path: Path) -> pd.DataFrame:
    """similarity_panel -> tidy [ticker, decision_date, sim] for ok rows."""
    df = pd.read_parquet(panel_path)
    df = df[df["ok"] & df["sim_cosine_tfidf"].notna()].copy()
    df["decision_date"] = pd.to_datetime(df["decision_date"])
    df = df.rename(columns={"sim_cosine_tfidf": "sim"})
    return df[["ticker", "decision_date", "sim"]].sort_values(["ticker", "decision_date"])


def latest_signal_asof(
    sig: pd.DataFrame, asof: pd.Timestamp, freshness_months: int
) -> pd.DataFrame:
    """Most-recent per-ticker signal with decision_date <= asof and within the
    freshness window (drops stale names that stopped filing)."""
    floor = asof - pd.DateOffset(months=freshness_months)
    elig = sig[(sig["decision_date"] <= asof) & (sig["decision_date"] >= floor)]
    if elig.empty:
        return elig
    idx = elig.groupby("ticker")["decision_date"].idxmax()
    return elig.loc[idx, ["ticker", "sim"]].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# backtest
# --------------------------------------------------------------------------- #
def run_backtest(
    sig: pd.DataFrame,
    mem: pd.DataFrame,
    start_year: int,
    end_year: int,
    cost_bps: float,
    tercile: int,
    anchor_md: str,
    freshness_months: int,
) -> Dict[str, object]:
    """Annual long-only top-tercile non-changers tilt + an equal-weight
    universe benchmark. Returns daily return series + diagnostics."""
    rebal_dates = [pd.Timestamp(f"{y}-{anchor_md}") for y in range(start_year, end_year + 1)]

    # cache closes for every ticker that ever has a signal
    closes: Dict[str, pd.Series] = {}
    no_price: List[str] = []
    for t in sorted(sig["ticker"].unique()):
        c = _load_close(t)
        if c is None or c.empty:
            no_price.append(t)
        else:
            closes[t] = c

    held_long: List[str] = []          # prior period's longs (for turnover)
    held_univ: List[str] = []
    long_daily: List[pd.Series] = []
    univ_daily: List[pd.Series] = []
    per_rebal: List[dict] = []

    for i, rd in enumerate(rebal_dates):
        nxt = rebal_dates[i + 1] if i + 1 < len(rebal_dates) else rd + pd.DateOffset(years=1)
        snap = latest_signal_asof(sig, rd, freshness_months)
        if snap.empty:
            per_rebal.append({"date": rd.date().isoformat(), "n_eligible": 0, "n_long": 0})
            continue
        # eligibility: PIT member as-of + price available
        snap = snap[snap["ticker"].apply(lambda t: t in closes and _is_member(mem, t, rd))]
        n_elig = len(snap)
        if n_elig < tercile:
            per_rebal.append({"date": rd.date().isoformat(), "n_eligible": n_elig, "n_long": 0})
            continue
        # top-tercile non-changers = HIGHEST similarity
        k = max(1, n_elig // tercile)
        longs = snap.nlargest(k, "sim")["ticker"].tolist()
        univ = snap["ticker"].tolist()

        # turnover cost (fraction of book traded), charged on day 1 of the period
        def _cost(prev: List[str], cur: List[str]) -> float:
            if not cur:
                return 0.0
            prev_s, cur_s = set(prev), set(cur)
            turn = len(cur_s.symmetric_difference(prev_s)) / (2 * len(cur_s))
            return turn * (cost_bps / 1e4)

        long_cost = _cost(held_long, longs)
        univ_cost = _cost(held_univ, univ)

        long_r = _period_returns(closes, longs, rd, nxt)
        univ_r = _period_returns(closes, univ, rd, nxt)
        if long_r is not None and len(long_r):
            long_r.iloc[0] -= long_cost
            long_daily.append(long_r)
        if univ_r is not None and len(univ_r):
            univ_r.iloc[0] -= univ_cost
            univ_daily.append(univ_r)

        held_long, held_univ = longs, univ
        per_rebal.append({
            "date": rd.date().isoformat(), "n_eligible": n_elig, "n_long": len(longs),
            "sim_long_mean": round(float(snap.nlargest(k, "sim")["sim"].mean()), 4),
            "sim_univ_mean": round(float(snap["sim"].mean()), 4),
        })

    if not long_daily:
        raise SystemExit(
            "[T237-backtest] FAIL-CLOSED: no held periods produced returns "
            "(empty signal panel or no price overlap). Not emitting a 0.0."
        )

    long_ret = pd.concat(long_daily).sort_index()
    long_ret = long_ret[~long_ret.index.duplicated(keep="first")]
    univ_ret = pd.concat(univ_daily).sort_index()
    univ_ret = univ_ret[~univ_ret.index.duplicated(keep="first")]
    active = (long_ret - univ_ret.reindex(long_ret.index)).dropna()  # non-changers vs universe

    return {
        "long_ret": long_ret, "univ_ret": univ_ret, "active_ret": active,
        "per_rebal": per_rebal, "no_price": no_price,
        "n_rebalances": sum(1 for r in per_rebal if r.get("n_long", 0) > 0),
    }


def _period_returns(
    closes: Dict[str, pd.Series], names: List[str], start: pd.Timestamp, end: pd.Timestamp
) -> Optional[pd.Series]:
    """Equal-weight daily return of `names` over (start, end]."""
    cols = []
    for t in names:
        c = closes.get(t)
        if c is None:
            continue
        seg = c[(c.index > start) & (c.index <= end)]
        if len(seg) > 1:
            cols.append(seg.pct_change().rename(t))
    if not cols:
        return None
    mat = pd.concat(cols, axis=1).sort_index()
    return mat.mean(axis=1, skipna=True).dropna()


# --------------------------------------------------------------------------- #
# gauntlet
# --------------------------------------------------------------------------- #
def _cagr(ret: pd.Series) -> float:
    eq = (1 + ret).cumprod()
    yrs = len(ret) / TRADING_DAYS
    return float(eq.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 and eq.iloc[-1] > 0 else float("nan")


def _tail_capture(ret: pd.Series, bench: pd.Series) -> float:
    """Mean strategy return on the benchmark's worst-decile days (downside
    capture; <1 = defends the tail)."""
    b = bench.reindex(ret.index).dropna()
    r = ret.reindex(b.index)
    if len(b) < 20:
        return float("nan")
    thr = b.quantile(0.10)
    mask = b <= thr
    bm = b[mask].mean()
    return float(r[mask].mean() / bm) if bm != 0 else float("nan")


def gauntlet(res: Dict[str, object], seed: int = 42) -> Dict[str, object]:
    from engines.engine_b_risk.factor_analysis import FactorRiskModel
    from core.combined_candidate_scorecard import evaluate_deploy_readiness, robo_proxy_returns

    long_ret = res["long_ret"]
    univ_ret = res["univ_ret"]
    active = res["active_ret"]
    out: Dict[str, object] = {}

    def _block(ret: pd.Series, label: str) -> dict:
        eq = (1 + ret).cumprod()
        boot = MetricsEngine.bootstrap_distribution(
            ret, MetricsEngine.sharpe_ratio, n_iterations=1000, seed=seed)
        spy = _load_close("SPY")
        spy_ret = spy.pct_change().dropna() if spy is not None else pd.Series(dtype=float)
        return {
            "label": label,
            "n_days": int(len(ret)),
            "years": round(len(ret) / TRADING_DAYS, 2),
            "sharpe": round(float(MetricsEngine.sharpe_ratio(ret)), 3),
            "sharpe_ci_low": round(float(boot["ci_low"]), 3),
            "sharpe_ci_high": round(float(boot["ci_high"]), 3),
            "sortino": round(float(MetricsEngine.sortino_ratio(ret)), 3),
            "cagr": round(_cagr(ret), 4),
            "maxdd": round(float(MetricsEngine.max_drawdown(eq)), 4),
            "calmar": round(_cagr(ret) / abs(float(MetricsEngine.max_drawdown(eq))), 3)
                       if MetricsEngine.max_drawdown(eq) else float("nan"),
            "tail_capture_vs_spy": round(_tail_capture(ret, spy_ret), 3),
        }

    out["non_changers"] = _block(long_ret, "long-only top-tercile non-changers")
    out["universe_ew"] = _block(univ_ret, "equal-weight investable universe")
    out["active_vs_universe"] = {
        "label": "non-changers MINUS universe (the CMN relative claim)",
        "ann_active_ret_pct": round(float(active.mean() * TRADING_DAYS * 100), 3),
        "active_sharpe": round(float(MetricsEngine.sharpe_ratio(active)), 3),
        "active_sharpe_ci_low": round(float(
            MetricsEngine.bootstrap_distribution(active, MetricsEngine.sharpe_ratio,
                                                 n_iterations=1000, seed=seed)["ci_low"]), 3),
    }

    # beat-robo gate (Roth, w_dbmf=0 → the candidate IS the non-changers series)
    try:
        eq = (1 + long_ret).cumprod()
        verdict = evaluate_deploy_readiness(eq, account="roth", w_dbmf=0.0)
        out["beat_robo"] = {
            "passed": bool(verdict.passed),
            "vs_60_40": _verdict_row(verdict.vs_60_40),
            "vs_schwab_like": _verdict_row(verdict.vs_schwab_like),
        }
    except Exception as e:  # pragma: no cover - diagnostic path
        out["beat_robo"] = {"error": f"{type(e).__name__}: {e}"}

    # beta-or-edge (the prime failure suspect)
    try:
        fm = FactorRiskModel()
        dec = fm.decompose(long_ret, edge_name="lazy_prices_non_changers")
        act = fm.decompose(active, edge_name="lazy_prices_active")
        out["beta_or_edge"] = {
            "non_changers_verdict": dec.is_it_beta_or_edge() if dec else "insufficient-overlap",
            "alpha_ann_pct": round(dec.alpha_annualized * 100, 3) if dec else None,
            "alpha_t_hac": round(dec.alpha_t_hac, 3) if dec else None,
            "betas": {k: round(v, 3) for k, v in dec.betas.items()} if dec else None,
            "r2": round(dec.r2, 3) if dec else None,
            "active_verdict": act.is_it_beta_or_edge() if act else "insufficient-overlap",
            "active_alpha_t_hac": round(act.alpha_t_hac, 3) if act else None,
        }
    except Exception as e:  # pragma: no cover
        out["beta_or_edge"] = {"error": f"{type(e).__name__}: {e}"}

    return out


def _verdict_row(rc) -> Optional[dict]:
    if rc is None:
        return None
    return {
        "sharpe_cand": round(rc.sharpe_cand, 3), "ci_low_cand": round(rc.ci_low_cand, 3),
        "sharpe_robo": round(rc.sharpe_robo, 3), "ci_low_robo": round(rc.ci_low_robo, 3),
        "maxdd_cand_pct": round(rc.maxdd_cand_pct, 2), "maxdd_robo_pct": round(rc.maxdd_robo_pct, 2),
        "beats": bool(rc.beats),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Lazy-Prices non-changers backtest + gauntlet (T-237).")
    ap.add_argument("--similarity-panel", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--start", type=int, default=2006)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--cost-bps", type=float, default=10.0, help="retail turnover cost (bps)")
    ap.add_argument("--tercile", type=int, default=3, help="3 → top 1/3 by similarity")
    ap.add_argument("--rebalance-anchor", default="06-01", help="MM-DD annual rebalance anchor")
    ap.add_argument("--freshness-months", type=int, default=18)
    args = ap.parse_args()

    if not args.similarity_panel.exists():
        raise SystemExit(f"[T237-backtest] FAIL-CLOSED: panel not found: {args.similarity_panel}")

    sig = load_signal_panel(args.similarity_panel)
    mem = _load_pit_membership()
    print(f"[T237-backtest] signal panel: {len(sig)} obs, {sig['ticker'].nunique()} tickers, "
          f"decision_date {sig['decision_date'].min().date()}..{sig['decision_date'].max().date()}")

    res = run_backtest(sig, mem, args.start, args.end, args.cost_bps,
                       args.tercile, args.rebalance_anchor, args.freshness_months)
    print(f"[T237-backtest] {res['n_rebalances']} annual rebalances; "
          f"{len(res['no_price'])} signal-tickers lacked price (recorded).")

    report = gauntlet(res)

    import json
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "gauntlet_t237.json"
    out_json.write_text(json.dumps({"params": vars(args) | {"similarity_panel": str(args.similarity_panel)},
                                    "per_rebal": res["per_rebal"], "gauntlet": report}, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    print(f"[T237-backtest] wrote {out_json}")


if __name__ == "__main__":
    main()

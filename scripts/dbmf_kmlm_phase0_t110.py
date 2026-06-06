"""T-110 Phase 0 — DBMF + KMLM managed-futures ETFs diagnostic.

Follow-up to T-108's RECONSIDER verdict: identical Phase-0 analysis,
but on REAL managed-futures ETFs (futures-wrapped products) instead
of the spot-ETF basket. The hypothesis: futures carry/roll/leverage
may deliver the positive-skew convexity that the 8-ETF spot basket
structurally couldn't.

Scope per inbox T-2026-06-05-110:
  - DBMF (iMGP DBi Managed Futures Strategy, inception 2019-05-10)
  - KMLM (KFA Mount Lucas Managed Futures Index, inception 2020-12-08)
  - Make-or-break: realized SKEWNESS positive? (T-108 spot basket failed
    at -0.408; equity-trend reference -0.133.)
  - Crisis-alpha confirmation: 2022 + 2025 (+ COVID for DBMF only) vs SPY.
  - Sharpe/Sortino/MDD with block-bootstrap CI per CLAUDE.md #6.
  - Correlation to SPY (base equity-book proxy).

Honest caveats to surface in audit:
  - Managed products embed manager's discretionary trend model + ER (~0.85-0.95%).
    A positive skew here = "this product delivers it," NOT "trend-following
    structurally delivers it for our self-built path."
  - Short history (DBMF 7yr, KMLM 5.5yr) → thin crisis evidence vs T-108's 17.4yr.
  - KMLM postdates COVID; only 2 testable crises (2022, 2025).

Phase 0 only — NO integration, NO engine touches.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]

STOOQ_PATHS = {
    "DBMF": "data/raw/stooq/daily/us/nyse etfs/1/dbmf.us.txt",
    "KMLM": "data/raw/stooq/daily/us/nyse etfs/1/kmlm.us.txt",
    "SPY":  "data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt",
}

# Crisis windows — SAME definitions as T-108 for direct comparability.
CRISIS_WINDOWS = [
    {"label": "COVID 2020",      "start": "2020-02-19", "end": "2020-04-30"},
    {"label": "2022 bear",       "start": "2022-01-03", "end": "2022-10-12"},
    {"label": "2025 vol-shock",  "start": "2025-02-01", "end": "2025-04-30"},
]


def load_stooq_etf(rel_path: str) -> pd.Series:
    df = pd.read_csv(REPO / rel_path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").sort_index()
    return df["close"].astype(float)


def daily_returns(close: pd.Series) -> pd.Series:
    return (close / close.shift(1) - 1.0).dropna()


def sharpe_ratio(rets: np.ndarray, periods: int = 252) -> float:
    if len(rets) < 2:
        return 0.0
    mu = rets.mean()
    sd = rets.std(ddof=1)
    if sd <= 1e-12:
        return 0.0
    return float(mu / sd * math.sqrt(periods))


def sortino_ratio(rets: np.ndarray, periods: int = 252) -> float:
    if len(rets) < 2:
        return 0.0
    mu = rets.mean()
    downside = rets[rets < 0]
    if len(downside) == 0:
        return float("inf")
    dd = math.sqrt((downside ** 2).mean())
    if dd <= 1e-12:
        return 0.0
    return float(mu / dd * math.sqrt(periods))


def max_drawdown(equity: pd.Series) -> float:
    running_peak = equity.cummax()
    dd = (equity / running_peak) - 1.0
    return float(dd.min())


def politis_white_block(n: int) -> int:
    return max(4, int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))))


def block_bootstrap_ci(
    rets: np.ndarray, metric_fn, n_iter: int = 1000, seed: int = 42,
) -> Tuple[float, float, float]:
    n = len(rets)
    if n < 30:
        return float("nan"), float("nan"), float("nan")
    point = metric_fn(rets)
    block = politis_white_block(n)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_iter):
        idx: List[int] = []
        while len(idx) < n:
            start = rng.randint(0, max(1, n - block))
            idx.extend(range(start, min(start + block, n)))
        idx_arr = np.array(idx[:n])
        boots.append(metric_fn(rets[idx_arr]))
    boots = [b for b in boots if not math.isnan(b) and not math.isinf(b)]
    if not boots:
        return point, float("nan"), float("nan")
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]


def analyze(ticker: str, rets: pd.Series, spy_close: pd.Series) -> Dict:
    print(f"\n{'='*60}\n[T-110] {ticker} — n_obs={len(rets)}, "
          f"first={rets.index.min().date()} last={rets.index.max().date()}, "
          f"~{(rets.index.max() - rets.index.min()).days / 365.25:.1f}yr")

    arr = rets.values
    sharpe_pt, sharpe_lo, sharpe_hi = block_bootstrap_ci(arr, sharpe_ratio)
    sortino_pt, sortino_lo, sortino_hi = block_bootstrap_ci(arr, sortino_ratio)
    skew_pt = float(pd.Series(arr).skew())
    skew_pt2, skew_lo, skew_hi = block_bootstrap_ci(arr, lambda r: float(pd.Series(r).skew()))
    eq = (1.0 + rets).cumprod()
    mdd = max_drawdown(eq)
    ann_ret = float(eq.iloc[-1] ** (252 / len(rets)) - 1.0)

    print(f"   Sharpe:   {sharpe_pt:+.4f}  ci=[{sharpe_lo:+.4f}, {sharpe_hi:+.4f}]")
    print(f"   Sortino:  {sortino_pt:+.4f}  ci=[{sortino_lo:+.4f}, {sortino_hi:+.4f}]")
    print(f"   Skewness: {skew_pt:+.4f}  ci=[{skew_lo:+.4f}, {skew_hi:+.4f}]  (vs T-108 spot basket -0.408; vs equity-trend -0.133)")
    print(f"   MaxDD:    {mdd*100:+.2f}%")
    print(f"   Final equity: {eq.iloc[-1]:.4f} (1.0 = start)")
    print(f"   Annualized return: {ann_ret*100:+.2f}%/yr")

    # Crisis-window returns
    print(f"\n   CRISIS WINDOWS:")
    crisis_rows = []
    for cw in CRISIS_WINDOWS:
        cw_rets = rets.loc[(rets.index >= pd.Timestamp(cw["start"]))
                            & (rets.index <= pd.Timestamp(cw["end"]))]
        if len(cw_rets) < 5:
            print(f"      {cw['label']:20s}  NO COVERAGE (this ETF postdates window)")
            crisis_rows.append({**cw, "n_days": int(len(cw_rets)), "total_return": None})
            continue
        total = float((1.0 + cw_rets).prod() - 1.0)
        spy_window = spy_close.loc[(spy_close.index >= pd.Timestamp(cw["start"]))
                                    & (spy_close.index <= pd.Timestamp(cw["end"]))]
        spy_total = float(spy_window.iloc[-1] / spy_window.iloc[0] - 1.0) if len(spy_window) >= 2 else float("nan")
        delta = total - spy_total
        print(f"      {cw['label']:20s}  n={len(cw_rets):3d}d  {ticker}={total*100:+7.2f}%  SPY={spy_total*100:+7.2f}%  Δ={delta*100:+7.2f}pp")
        crisis_rows.append({
            **cw, "n_days": int(len(cw_rets)),
            "total_return": total, "spy_total_return": spy_total,
            "outperform_spy_pp": delta,
        })

    # Correlation to SPY (proxy for base equity book)
    spy_daily = (spy_close / spy_close.shift(1) - 1.0).dropna()
    aligned = pd.concat([rets.rename("etf"), spy_daily.rename("spy")],
                        axis=1, join="inner").dropna()
    corr = float(aligned["etf"].corr(aligned["spy"]))
    cov = aligned.cov().values
    beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else float("nan")
    print(f"\n   Correlation vs SPY: {corr:+.4f}  (lower = better diversification)")
    print(f"   Beta vs SPY:        {beta:+.4f}")

    return {
        "ticker": ticker,
        "n_obs": int(len(rets)),
        "first_date": str(rets.index.min().date()),
        "last_date": str(rets.index.max().date()),
        "years": float((rets.index.max() - rets.index.min()).days / 365.25),
        "metrics": {
            "sharpe": {"point": sharpe_pt, "ci_low": sharpe_lo, "ci_high": sharpe_hi},
            "sortino": {"point": sortino_pt, "ci_low": sortino_lo, "ci_high": sortino_hi},
            "skewness": {
                "point": skew_pt, "ci_low": skew_lo, "ci_high": skew_hi,
                "t108_spot_basket_reference": -0.408,
                "equity_trend_reference": -0.133,
            },
            "max_drawdown": mdd,
            "final_equity_multiple": float(eq.iloc[-1]),
            "annualized_return": ann_ret,
        },
        "crisis_windows": crisis_rows,
        "diversification": {
            "correlation_to_spy": corr,
            "beta_to_spy": beta,
        },
    }


def verdict_for(result: Dict) -> str:
    """Map ETF result to PROCEED-INTEGRATE / MIXED / DEAD."""
    skew_pt = result["metrics"]["skewness"]["point"]
    skew_lo = result["metrics"]["skewness"]["ci_low"]
    sharpe_lo = result["metrics"]["sharpe"]["ci_low"]
    corr = result["diversification"]["correlation_to_spy"]

    # Crisis-alpha: outperforms SPY in ≥ all covered windows
    crisis_alpha = all(
        r.get("outperform_spy_pp") is not None and r["outperform_spy_pp"] > 0
        for r in result["crisis_windows"]
        if r.get("total_return") is not None
    )

    skew_positive = skew_pt > 0
    skew_strict_positive = skew_lo > 0
    sharpe_positive = sharpe_lo > 0
    low_corr = corr < 0.5

    if skew_positive and crisis_alpha and low_corr and sharpe_positive:
        return "PROCEED-TO-INTEGRATE"
    if crisis_alpha and low_corr:
        return "MIXED (crisis-alpha diversifier; skew flat/negative)"
    return "DEAD"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json",
                    default=str(REPO / "docs/Measurements/2026-06/t110_dbmf_kmlm_phase0.json"))
    args = ap.parse_args()

    dbmf_close = load_stooq_etf(STOOQ_PATHS["DBMF"])
    kmlm_close = load_stooq_etf(STOOQ_PATHS["KMLM"])
    spy_close  = load_stooq_etf(STOOQ_PATHS["SPY"])

    dbmf_rets = daily_returns(dbmf_close)
    kmlm_rets = daily_returns(kmlm_close)

    print(f"[T-110] DATA FLOORS:")
    print(f"   DBMF: {dbmf_close.index.min().date()} → {dbmf_close.index.max().date()}  "
          f"({(dbmf_close.index.max()-dbmf_close.index.min()).days/365.25:.1f}yr)")
    print(f"   KMLM: {kmlm_close.index.min().date()} → {kmlm_close.index.max().date()}  "
          f"({(kmlm_close.index.max()-kmlm_close.index.min()).days/365.25:.1f}yr)")
    print(f"   SPY (reference): {spy_close.index.min().date()} → {spy_close.index.max().date()}")
    print(f"\n[T-110] COVERED CRISES PER ETF:")
    print(f"   COVID 2020:    DBMF=YES  KMLM=NO  (KMLM inception 2020-12-08)")
    print(f"   2022 bear:     DBMF=YES  KMLM=YES")
    print(f"   2025 vol-shock:DBMF=YES  KMLM=YES")

    dbmf_result = analyze("DBMF", dbmf_rets, spy_close)
    kmlm_result = analyze("KMLM", kmlm_rets, spy_close)

    dbmf_verdict = verdict_for(dbmf_result)
    kmlm_verdict = verdict_for(kmlm_result)

    print(f"\n{'='*60}")
    print(f"[T-110] PHASE 0 VERDICTS:")
    print(f"   DBMF: {dbmf_verdict}")
    print(f"   KMLM: {kmlm_verdict}")

    # Combined headline verdict — best of the two
    combined = "DEAD"
    if "PROCEED" in dbmf_verdict or "PROCEED" in kmlm_verdict:
        combined = "PROCEED-TO-INTEGRATE (the ETF that cleared)"
    elif "MIXED" in dbmf_verdict or "MIXED" in kmlm_verdict:
        combined = "MIXED (the ETF that has crisis-alpha + low base-corr)"
    print(f"\n[T-110] COMBINED HEADLINE: {combined}")

    summary = {
        "task": "T-2026-06-05-110",
        "data_floors": {
            "DBMF": str(dbmf_close.index.min().date()),
            "KMLM": str(kmlm_close.index.min().date()),
        },
        "covered_crises": {
            "DBMF": ["COVID 2020", "2022 bear", "2025 vol-shock"],
            "KMLM": ["2022 bear", "2025 vol-shock"],
        },
        "dbmf": dbmf_result,
        "kmlm": kmlm_result,
        "verdicts": {
            "DBMF": dbmf_verdict,
            "KMLM": kmlm_verdict,
            "combined_headline": combined,
        },
        "t108_spot_basket_reference": {
            "skewness": -0.408,
            "skew_ci": [-0.754, -0.039],
            "crisis_2022_pp": 35.68,
            "crisis_covid_pp": 10.99,
            "spy_correlation": 0.289,
            "sharpe": 0.505,
        },
        "honest_caveats": [
            "DBMF/KMLM are MANAGED products — embed manager discretion + ER (~0.85-0.95%).",
            "A positive skew here means 'this product delivers it,' NOT 'self-built futures trend would deliver it.'",
            "KMLM postdates COVID — only 2 testable crises (2022, 2025) vs T-108's 8 windows.",
            "DBMF history 7yr vs T-108's 17.4yr — much thinner crisis evidence.",
        ],
    }

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n[T-110] wrote {out_path}")


if __name__ == "__main__":
    main()

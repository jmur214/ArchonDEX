"""scripts/carry_sleeve_gauntlet_t247.py
=========================================
T-2026-06-26-247 — CROSS-ASSET CARRY sleeve gauntlet.

═══════════════════════════════════════════════════════════════════════════════
PRE-REGISTRATION (committed BEFORE running — `[NN-MBL]`)
═══════════════════════════════════════════════════════════════════════════════
HYPOTHESIS (H1): a cross-asset time-series carry sleeve — long an asset when its
  carry is positive, flat-to-cash when negative — earns a positive risk-adjusted
  return that is NOT explained by equity/bond factor beta (i.e. real carry alpha),
  and complements the trend sleeve (carry = return engine; trend = crash hedge).
H0 (prior LOW-MEDIUM, ~15-25% — the least-bad of the free set): carry-on-bonds is
  duration / term-premium BETA; the sleeve's return is fully explained by FF5+Mom
  PLUS a bond-duration factor → alpha_t_hac ≤ 2 → FAILS as alpha.

PRIME KILL-TEST (the deciding gate): is_it_beta_or_edge. Regress sleeve daily
  returns on FF5 + Mom AND an added bond-DURATION factor (AGG excess return).
  EDGE iff alpha_t_hac > 2.0 AND alpha_annual > 2%; else BETA (fails as alpha).

THRESHOLDS (pre-registered, not tunable post-hoc):
  - ci_low(Sharpe) block-bootstrap; MBL bar = sqrt(2·ln(N)/years), N = 261
    (honest accumulated N_eff ~260 + THIS trial). `[NN-MBL]`: N_trials += 1.
  - beat-robo: evaluate_deploy_readiness(account="roth", w_dbmf=0.0) vs 60_40 +
    schwab_like (net-of-cost, after-tax, window-honesty enforced).
  - Sortino/tail reframe: up/down-capture, per-crisis MaxDD.
  - Carry state: long when carry_t > 0, else cash. Threshold 0 (no sweep).

DATA CONSTRAINT (found at build; material — reported honestly, NOT worked around):
  On-disk asset-class ETF caches for the DIVERSIFIERS (GLD/TLT/IEF/DBC/UUP) start
  2020-04-09 — a 6-yr window with no GFC/dotcom → fails MBL + window-honesty by
  construction. Only SPY/AGG/EFA/VNQ have long histories. And there is NO equity
  earnings/dividend-yield series on disk → equity carry cannot be computed
  honestly (fail-closed → excluded). The one clean, long-history, causal carry
  leg is BOND/DURATION carry (curve slope, traded via AGG 2003+). Therefore:
    PRIMARY (MBL-valid verdict): bond carry, AGG, 2003-2026 (GFC/COVID/2022 in).
    SECONDARY (EXPLORATORY, non-deployment): AGG+GLD carry, 2020-2026 (short).
  The constructor is general (cross-asset ready, fail-closed) so E can extend it
  in Wave 2 once longer diversifier + equity-yield histories are sourced.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.carry_signal import build_carries, carry_sleeve_returns, buy_hold_returns  # noqa: E402
from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.combined_candidate_scorecard import evaluate_deploy_readiness  # noqa: E402
from core.factor_decomposition import (  # noqa: E402
    load_factor_data, regress_returns_on_factors, DEFAULT_FACTOR_COLS,
)

TD = 252
RF = 0.04
N_TRIALS = 261  # honest accumulated N_eff (~260) + this pre-registered trial
MACRO = ROOT / "data" / "macro"
PROC = ROOT / "data" / "processed"


def macro_series(name: str) -> pd.Series:
    d = pd.read_parquet(MACRO / f"{name}.parquet")
    s = d["value"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s.dropna().sort_index()


def etf_close(ticker: str) -> pd.Series:
    d = pd.read_csv(PROC / f"{ticker}_1d.csv")
    s = pd.Series(d["Close"].astype(float).values, index=pd.to_datetime(d["Date"]))
    return s.dropna().sort_index()


# ── metric helpers ────────────────────────────────────────────────────────────
def maxdd(eq: pd.Series) -> float:
    return float((eq / eq.cummax() - 1).min())


def cagr(eq: pd.Series) -> float:
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return float((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1)


def sortino_ci(r: pd.Series) -> tuple[float, float | None]:
    s = ME.sortino_ratio(r, 0.0, TD)
    try:
        ci = ME.bootstrap_distribution(
            r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0
        ).get("ci_low")
    except Exception:
        ci = None
    return float(s), (float(ci) if ci is not None else None)


def sharpe_ci(r: pd.Series) -> tuple[float, float | None]:
    s = ME.sharpe_ratio(r, 0.0, TD)
    try:
        ci = ME.bootstrap_distribution(
            r, lambda x: ME.sharpe_ratio(x, 0.0, TD), n_iterations=1000, seed=0
        ).get("ci_low")
    except Exception:
        ci = None
    return float(s), (float(ci) if ci is not None else None)


def updown(strat: pd.Series, ref: pd.Series) -> tuple[float, float]:
    sm = (1 + strat).resample("ME").prod() - 1
    rm = (1 + ref).resample("ME").prod() - 1
    j = pd.concat({"s": sm, "r": rm}, axis=1).dropna()
    up, dn = j[j.r > 0], j[j.r < 0]
    uc = up.s.mean() / up.r.mean() if len(up) and up.r.mean() else float("nan")
    dc = dn.s.mean() / dn.r.mean() if len(dn) and dn.r.mean() else float("nan")
    return float(uc), float(dc)


def crisis_dd(r: pd.Series, a: str, b: str) -> float | None:
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2:
        return None
    eq = (1 + s).cumprod()
    return float((eq / eq.cummax() - 1).min())


def beta_or_edge(sleeve: pd.Series, agg_ret: pd.Series) -> dict:
    """PRIME KILL-TEST: regress the sleeve on FF5+Mom + a bond-DURATION factor.
    EDGE iff alpha_t_hac > 2 AND alpha_annual > 2%; else BETA (fails as alpha).
    DUR = AGG EXCESS daily return (AGG_ret − RF) — the tradeable duration factor."""
    factors = load_factor_data(auto_download=True)
    dur = (agg_ret.reindex(factors.index) - factors["RF"]).dropna()  # AGG excess
    fac = factors.join(dur.rename("DUR"), how="inner").dropna()
    cols = [c for c in DEFAULT_FACTOR_COLS if c in fac.columns] + ["DUR"]
    d = regress_returns_on_factors(sleeve, fac, factor_cols=cols, edge_name="carry_sleeve")
    if d is None:
        return {"verdict": "insufficient_data"}
    is_edge = d.alpha_tstat > 2.0 and d.alpha_annualized > 0.02
    return {
        "verdict": "edge" if is_edge else "beta",
        "alpha_ann_pct": round(d.alpha_annualized * 100, 3),
        "alpha_t_hac": round(d.alpha_tstat, 3),
        "r2": round(d.r_squared, 4),
        "n_obs": d.n_obs,
        "betas": {k: round(v, 4) for k, v in d.betas.items()},
    }


def report(label: str, sleeve: pd.Series, robo6040: pd.Series, agg_bh: pd.Series,
           crises: list, mbl_valid: bool) -> dict:
    eq = (1 + sleeve).cumprod()
    so, so_ci = sortino_ci(sleeve)
    sh, sh_ci = sharpe_ci(sleeve)
    md, cg = maxdd(eq), cagr(eq)
    uc, dc = updown(sleeve, robo6040.reindex(sleeve.index).dropna())
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    mbl_bar = math.sqrt(2 * math.log(N_TRIALS) / yrs)

    print(f"\n{'='*78}\n{label}\n  window {eq.index[0].date()}..{eq.index[-1].date()} "
          f"({yrs:.1f}y, {len(sleeve)} days)  MBL-valid={mbl_valid}\n{'='*78}")
    print(f"  Sortino {so:.3f} (ci_low {so_ci if so_ci is None else round(so_ci,3)})  "
          f"Sharpe {sh:.3f} (ci_low {sh_ci if sh_ci is None else round(sh_ci,3)})")
    print(f"  CAGR {cg*100:.1f}%  MaxDD {md*100:.1f}%  Calmar {cg/abs(md):.3f}  "
          f"up/down-cap vs 60_40 {uc:.2f}/{dc:.2f}")
    print(f"  MBL bar (N={N_TRIALS}, {yrs:.1f}y) Sharpe≥{mbl_bar:.3f} → "
          f"{'CLEARS' if sh > mbl_bar else 'FAILS'} (point); "
          f"ci_low {'CLEARS' if (sh_ci or -9) > mbl_bar else 'FAILS'}")

    print("  per-crisis MaxDD (sleeve vs AGG buy-hold):")
    for nm, a, b in crises:
        sd, ad = crisis_dd(sleeve, a, b), crisis_dd(agg_bh, a, b)
        if sd is not None:
            print(f"    {nm:8} sleeve {sd*100:6.1f}%  vs  AGG-BH "
                  f"{ad*100:6.1f}%" if ad is not None else f"    {nm:8} sleeve {sd*100:6.1f}%")

    # beat-robo
    dv = evaluate_deploy_readiness((1 + sleeve).cumprod(), account="roth", w_dbmf=0.0)
    print(f"  beat-robo: passed={dv.passed}  ({dv.deploy_verdict})")
    for name, c in dv.comparisons.items():
        print(f"    vs {name:12} cand ci_low {c.ci_low_cand:+.3f} vs robo {c.ci_low_robo:+.3f}"
              f"  MDD {c.maxdd_cand_pct:.1f}% vs {c.maxdd_robo_pct:.1f}%  beats={c.beats}")

    # PRIME KILL-TEST — agg_bh is already AGG daily returns
    boe = beta_or_edge(sleeve, agg_bh)
    print(f"  ★ beta-or-edge (net FF5+Mom+DURATION): {boe.get('verdict','?').upper()}  "
          f"alpha {boe.get('alpha_ann_pct','?')}%/yr  t_hac {boe.get('alpha_t_hac','?')}  "
          f"R² {boe.get('r2','?')}  (DUR β {boe.get('betas',{}).get('DUR','?')})")

    return {
        "label": label, "window": f"{eq.index[0].date()}..{eq.index[-1].date()}",
        "years": round(yrs, 2), "n_days": len(sleeve), "mbl_valid": mbl_valid,
        "sortino": round(so, 3), "sortino_ci_low": None if so_ci is None else round(so_ci, 3),
        "sharpe": round(sh, 3), "sharpe_ci_low": None if sh_ci is None else round(sh_ci, 3),
        "cagr": round(cg, 4), "maxdd": round(md, 4), "calmar": round(cg / abs(md), 3),
        "up_capture": round(uc, 3), "down_capture": round(dc, 3),
        "mbl_bar_sharpe": round(mbl_bar, 3), "mbl_clears_point": bool(sh > mbl_bar),
        "beat_robo_passed": bool(dv.passed),
        "beat_robo": {n: {"ci_low_cand": round(c.ci_low_cand, 3),
                          "ci_low_robo": round(c.ci_low_robo, 3),
                          "maxdd_cand_pct": round(c.maxdd_cand_pct, 2),
                          "beats": bool(c.beats)} for n, c in dv.comparisons.items()},
        "beta_or_edge": boe,
    }


def main() -> int:
    dgs10, dgs3mo, t10yie = macro_series("DGS10"), macro_series("DGS3MO"), macro_series("T10YIE")
    macro = {"DGS10": dgs10, "DGS3MO": dgs3mo, "T10YIE": t10yie}
    agg, gld, spy = etf_close("AGG"), etf_close("GLD"), etf_close("SPY")
    agg_bh = buy_hold_returns(agg)
    # 60_40 daily-rebalanced proxy for up/down capture
    r6040 = (0.6 * buy_hold_returns(spy) + 0.4 * agg_bh).dropna()

    crises = [("GFC", "2007-10-09", "2009-03-09"), ("COVID", "2020-02-19", "2020-03-23"),
              ("2022", "2022-01-03", "2022-10-12")]

    out = {"pre_registration": "see module docstring", "n_trials": N_TRIALS, "results": {}}

    # PRIMARY — bond carry (AGG), long window, MBL-valid
    car_bond = build_carries(["AGG"], macro)
    sleeve_bond = carry_sleeve_returns({"AGG": agg}, car_bond, threshold=0.0)
    out["results"]["primary_bond_carry_AGG"] = report(
        "PRIMARY — BOND CARRY (AGG, curve-slope), MBL-valid",
        sleeve_bond, r6040, agg_bh, crises, mbl_valid=True)

    # SECONDARY — AGG+GLD carry, short window, EXPLORATORY (non-deployment)
    car_multi = build_carries(["AGG", "GLD"], macro)
    sleeve_multi = carry_sleeve_returns({"AGG": agg, "GLD": gld}, car_multi, threshold=0.0)
    out["results"]["secondary_multi_carry_AGG_GLD"] = report(
        "SECONDARY — AGG+GLD CARRY (EXPLORATORY, 2020+, NON-deployment)",
        sleeve_multi, r6040, agg_bh, crises, mbl_valid=False)

    dest = ROOT / "data" / "research" / "carry_gauntlet_t247.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"\n[T247] wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

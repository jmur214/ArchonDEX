"""T-314 (#1) — the bounded regime-conditional adaptation RULE, on the deep substrate.

Pre-registration (director-FROZEN; signal ruling + family addendum appended):
docs/Sources/prereg_adaptation_rule_t314.md. N_trials += 1.

THE QUESTION (the user's contested thesis, made honestly testable): can a BOUNDED
adaptation rule — learned on early decades, FROZEN, tested OOS on held-out decades —
beat the frozen spec? This is NOT the free-parameter fit that killed MetaLearner /
HRP / concentration; it is overfit-proof by construction:

  exposure_adaptive[t] = exposure_frozen[t] · (1 − β · s[t])      # 1 fitted DoF: β

  s[t]  causal vol-STRESS signal, PRE-REGISTERED (not searched), committed 64 min
        BEFORE the T-311 run (a27eef5) — auditable ex-ante provenance:
            rv60  = 60d realized vol of the equity leg, LAGGED 1 day
            s[t]  = clip( (rv60[t-1] − median_expanding(rv60)[t-1]) / median, 0, 1 )
  β ∈ [0,1]  de-risk STRENGTH. β=0 ⇒ adaptive IS the frozen spec exactly.
        The rule can ONLY de-risk (exposure_adaptive ≤ exposure_frozen), matching the
        T-298 "never damp de-risking" asymmetry and the defense-first prior.

  FIT (in-sample ONLY):  β* = argmax_β [ Sortino_IS(β) − τ·β² ]   ridge → β=0
        τ = 0.4, the pre-registered value: τ·(0.5)² = 0.10, i.e. a 10-pp Sortino gain
        is required to move β from 0 to 0.5. The prior CENTER IS THE FROZEN SPEC, so
        "no improvement" is the DEFAULT outcome, not a coincidence.

  WALL: decades 1-3 (first 60%) fit; decades 4-5 (last 40%) NEVER seen by the fit.

  WIN  : OOS Sharpe(adaptive) ≥ OOS Sharpe(frozen) AND paired OOS block-bootstrap
         ci_low > 0.
  NULL : ci_low ≤ 0 ⇒ "the frozen spec is the ceiling; adaptation adds nothing at
         this N" — CONFIRMS the director's prior, REFUTES the thesis WITH EVIDENCE.
         Equally decisive, equally reportable. NOT a failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.deep_reverify_sleeve_t311 import (                          # noqa: E402
    load_substrate, maxdd, cagr, sortino, sharpe, paired, ER, TXN, TD,
)

OUT = ROOT / "data/research/t314_adaptation_rule.json"
SPEEDS = [42, 105, 210]        # the deployed, now-SETTLED frozen spec (T-260-deep)
TAU = 0.4                      # pre-registered ridge prior (10-pp Sortino @ β=0.5)
IS_FRAC = 0.60                 # decades 1-3 fit / 4-5 OOS — one split, pre-declared
RV_WIN = 60                    # realized-vol window (pre-registered)
N_TRIALS = 78


def frozen_exposure(px: pd.Series) -> pd.Series:
    """The deployed ensemble exposure: mean binary long/flat over SPEEDS, lagged."""
    return pd.concat([(px > px.rolling(s).mean()).astype(float) for s in SPEEDS],
                     axis=1).mean(axis=1).shift(1)


def stress_signal(equity_px: pd.Series) -> pd.Series:
    """CAUSAL vol-stress s[t] ∈ [0,1] (T-273 lag discipline): 60d realized vol vs its
    EXPANDING median, both using ONLY data strictly before t."""
    rv = equity_px.pct_change().rolling(RV_WIN).std().shift(1)      # lag → causal
    med = rv.expanding(min_periods=RV_WIN).median()                 # expanding, no look-ahead
    return ((rv - med) / med).clip(lower=0.0, upper=1.0).fillna(0.0)


def sleeve_at(legs: dict, cash: pd.Series, s: pd.Series, beta: float) -> pd.Series:
    """Sleeve returns with exposure scaled by the bounded adaptation rule.
    beta=0 reproduces the frozen sleeve EXACTLY (the shrinkage prior's center)."""
    n = len(legs)
    tot = None
    for name, px in legs.items():
        pos = frozen_exposure(px) * (1.0 - beta * s)      # ONLY de-risks
        r = pos * (px.pct_change() - ER[name] / TD) + (1 - pos) * cash
        r = r - pos.diff().abs().fillna(0) * (1.0 / n) * TXN
        tot = r / n if tot is None else tot + r / n
    return tot.dropna()


def main() -> int:
    legs, cash = load_substrate(["equity", "bond"])          # D-A 2-asset primary
    s = stress_signal(legs["equity"])

    # --- the WALL: one pre-declared split, fit never sees OOS ------------------ #
    base = sleeve_at(legs, cash, s, 0.0)
    split = base.index[int(len(base) * IS_FRAC)]
    # DATE-based slicing (series lengths differ by dropna; a positional/boolean mask
    # would silently misalign the wall — the one thing that must never slip here).
    IS = lambda x: x[x.index < split]                                   # noqa: E731
    OOS = lambda x: x[x.index >= split]                                 # noqa: E731
    print(f"=== T-314 (#1) bounded adaptation rule — deep substrate (2-asset) ===")
    print(f"IS  (fit)  : {base.index[0].date()} .. {split.date()}  ({len(IS(base)):,} bars)")
    print(f"OOS (held) : {split.date()} .. {base.index[-1].date()}  ({len(OOS(base)):,} bars)")
    print(f"signal s[t]: mean {IS(s).mean():.3f} (IS) / {OOS(s).mean():.3f} (OOS); "
          f"frac>0 {(s > 0).mean():.2f}")

    # --- FIT β on IS ONLY, with ridge shrinkage toward the frozen spec --------- #
    grid = np.round(np.arange(0.0, 1.001, 0.02), 3)          # 1-D line search over β
    fit = []
    for b in grid:
        r_is = IS(sleeve_at(legs, cash, s, float(b)))
        so = sortino(r_is)
        fit.append({"beta": float(b), "sortino_is": so, "objective": so - TAU * b * b})
    best = max(fit, key=lambda d: d["objective"])
    beta_star = best["beta"]
    b0 = next(d for d in fit if d["beta"] == 0.0)
    print(f"\n--- FIT (in-sample only; ridge τ={TAU} toward β=0 = the frozen spec) ---")
    print(f"  β*        = {beta_star:.2f}   (Sortino_IS {best['sortino_is']:.4f}, "
          f"objective {best['objective']:.4f})")
    print(f"  β=0 ref   : Sortino_IS {b0['sortino_is']:.4f}, objective {b0['objective']:.4f}")
    print(f"  raw IS gain from adaptation: {best['sortino_is'] - b0['sortino_is']:+.4f} Sortino")
    if beta_star == 0.0:
        print("  ⇒ the shrinkage prior returned β*=0: adaptation did not clear its own "
              "in-sample bar; adaptive == frozen BY CONSTRUCTION.")

    # --- FREEZE β*, apply OOS (never seen by the fit) -------------------------- #
    r_adapt_oos = OOS(sleeve_at(legs, cash, s, beta_star))
    r_frozen_oos = OOS(base)
    res = {}
    print(f"\n--- OOS TEST (β* = {beta_star:.2f} frozen; decades 4-5 unseen by the fit) ---")
    print(f'{"arm":22}{"Sharpe":>9}{"Sortino":>9}{"CAGR":>8}{"MaxDD":>9}')
    for nm, r in [("FROZEN spec", r_frozen_oos), ("ADAPTIVE (β*)", r_adapt_oos)]:
        eq = (1 + r).cumprod()
        res[nm] = {"sharpe": sharpe(r), "sortino": sortino(r), "cagr": cagr(eq),
                   "maxdd": maxdd(eq)}
        print(f'{nm:22}{res[nm]["sharpe"]:>9.3f}{res[nm]["sortino"]:>9.3f}'
              f'{res[nm]["cagr"]*100:>7.2f}%{res[nm]["maxdd"]*100:>8.1f}%')

    p = paired(r_adapt_oos, r_frozen_oos)          # adaptive − frozen, OOS
    d_sharpe = res["ADAPTIVE (β*)"]["sharpe"] - res["FROZEN spec"]["sharpe"]
    # the FROZEN win condition
    ci_lo, ci_hi = p["dSortino_ci"]
    win = (res["ADAPTIVE (β*)"]["sharpe"] >= res["FROZEN spec"]["sharpe"]) and ci_lo > 0
    verdict = ("WIN — bounded adaptation beats the frozen spec OOS"
               if win else
               "NULL — THE FROZEN SPEC IS THE CEILING; adaptation adds nothing at this N")
    print(f"\n  ΔSharpe (adaptive − frozen) = {d_sharpe:+.4f}")
    print(f"  paired OOS ΔSortino 95% CI  = [{ci_lo:+.4f}, {ci_hi:+.4f}]  "
          f"(win requires ci_low > 0)")
    print(f"  ΔMaxDD 95% CI               = [{p['dMaxDD_ci'][0]*100:+.2f}%, "
          f"{p['dMaxDD_ci'][1]*100:+.2f}%]")
    print(f"  Δcompound %/yr 95% CI       = [{p['dLogWealthAnn_ci'][0]*100:+.2f}, "
          f"{p['dLogWealthAnn_ci'][1]*100:+.2f}]")
    print(f"\n  ⇒ VERDICT: {verdict}")

    out = {"beta_star": beta_star, "tau": TAU, "is_frac": IS_FRAC,
           "split": str(split.date()), "n_trials": N_TRIALS,
           "fit_curve": fit, "oos": res, "paired_oos": p,
           "d_sharpe_oos": d_sharpe, "win": bool(win), "verdict": verdict,
           "signal": {"window": RV_WIN, "mean_is": float(IS(s).mean()),
                      "mean_oos": float(OOS(s).mean())}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

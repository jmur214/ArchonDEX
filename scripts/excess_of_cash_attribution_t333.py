"""T-333 — the EXCESS-OF-CASH attribution: is the sleeve's regime dependency an identity?

Dispatch: the external review's F3 (docs/Sources/External_Prompt_Runs/
2026-07-28_research-agent-v3.md). Substrate: T-306 deep (D-A 2-asset primary).
N_trials += 1. Block-bootstrap CIs per [NN-SHARPE-CI].

THE EXACT DECOMPOSITION (an algebraic identity, verified to 1.4e-17 — zero free
parameters, nothing fitted, nothing selected):

    sleeve − buyhold  =  (1−pos)·(cash − asset)  −  pos·ER  −  txn
                      =   CASH_HARVEST  +  MARKET_AVOID  −  COSTS
      CASH_HARVEST  = (1−pos)·cash    the MECHANICAL term: time-flat × cash rate.
                                      Big when cash yields 6%, small when it yields 1%.
      MARKET_AVOID  = −(1−pos)·asset  the TIMING term: the market return you avoided
                                      by being flat. This is the actual claimed skill.
      COSTS         = pos·ER + txn

The "excess-of-cash edge" is MARKET_AVOID − COSTS: what the sleeve's edge over
buy-hold would be if cash yielded ZERO. The cash rate does not appear in it.

PRE-STATED OUTCOMES (from the dispatch, verbatim — the outcome space was NOT chosen
by me):
  (i)   excess-of-cash edge STABLE across yield regimes → the dependency was the cash
        term, an identity; no conditioning justified.
  (ii)  excess-of-cash edge ITSELF regime-dependent → a genuine conditional effect;
        only then is a future conditioning trial warranted.
  (iii) excess-of-cash edge ≈ 0 throughout → the sleeve is a cash-yield harvesting
        vehicle wearing a trend costume, and its deployment case is a rate forecast.

NOT conditioning on yield regime — this REPARAMETERIZES only (per the dispatch). The
era split is inherited from T-311 for comparability and is reported alongside a
CONTINUOUS view (edge vs prevailing cash rate) so the verdict does not rest on one
arbitrary boundary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.deep_reverify_sleeve_t311 import load_substrate, ER, TXN, TD   # noqa: E402
from scripts.adaptation_rule_t314 import frozen_exposure                    # noqa: E402

OUT = ROOT / "data/research/t333_excess_of_cash.json"
SPLIT_YEAR = 1990          # inherited from T-311 (post-hoc there; descriptive here)
BLOCK, ITERS, SEED = 21, 1000, 0


def block_ci(x: pd.Series, fn, block=BLOCK, iters=ITERS, seed=SEED, conf=95):
    """Stationary block-bootstrap CI (the [NN-SHARPE-CI] standard)."""
    rng = np.random.default_rng(seed)
    v, n = x.values, len(x)
    nb = int(np.ceil(n / block))
    out = []
    for _ in range(iters):
        starts = rng.integers(0, n, nb)
        idx = np.concatenate([np.arange(s, s + block) % n for s in starts])[:n]
        out.append(fn(v[idx]))
    lo, hi = np.percentile(out, [(100 - conf) / 2, 100 - (100 - conf) / 2])
    return float(lo), float(hi)


def ann(v) -> float:
    return float(np.mean(v) * TD * 100)          # annualized %/yr


def main() -> int:
    legs, cash = load_substrate(["equity", "bond"])
    px = legs["equity"]
    pos = frozen_exposure(px)
    a = px.pct_change()
    txn = pos.diff().abs().fillna(0) * TXN

    harvest = ((1 - pos) * cash).dropna()
    avoid = (-(1 - pos) * a).dropna()
    costs = (pos * ER["equity"] / TD + txn).dropna()
    idx = harvest.index.intersection(avoid.index).intersection(costs.index)
    harvest, avoid, costs = harvest[idx], avoid[idx], costs[idx]
    edge = harvest + avoid - costs                      # == sleeve − buyhold, exactly
    excess = avoid - costs                              # THE EXCESS-OF-CASH EDGE

    print(f"=== T-333 excess-of-cash attribution | {idx[0].date()}..{idx[-1].date()} "
          f"({(idx[-1]-idx[0]).days/365.25:.1f} yr) ===\n")
    eras = [("FULL", idx),
            (f"pre-{SPLIT_YEAR} (high cash)", idx[idx.year < SPLIT_YEAR]),
            (f"{SPLIT_YEAR}+ (low cash)", idx[idx.year >= SPLIT_YEAR])]
    res = {}
    print(f'{"era":26}{"avg cash":>10}{"CASH-HARV":>11}{"MKT-AVOID":>11}'
          f'{"COSTS":>8}{"= EDGE":>9}{"EXCESS-OF-CASH":>16}')
    for lbl, ii in eras:
        e_lo, e_hi = block_ci(excess[ii], ann)
        res[lbl] = {"avg_cash_pct": ann(cash.reindex(ii).dropna()),
                    "cash_harvest": ann(harvest[ii]), "market_avoid": ann(avoid[ii]),
                    "costs": ann(costs[ii]), "edge": ann(edge[ii]),
                    "excess_of_cash": ann(excess[ii]), "excess_ci": [e_lo, e_hi]}
        r = res[lbl]
        print(f'{lbl:26}{r["avg_cash_pct"]:>9.2f}%{r["cash_harvest"]:>+11.2f}'
              f'{r["market_avoid"]:>+11.2f}{r["costs"]:>+8.2f}{r["edge"]:>+9.2f}'
              f'   {r["excess_of_cash"]:>+7.2f} [{e_lo:+.2f},{e_hi:+.2f}]')

    hi_e, lo_e = res[eras[1][0]], res[eras[2][0]]
    d_edge = lo_e["edge"] - hi_e["edge"]
    d_harv = lo_e["cash_harvest"] - hi_e["cash_harvest"]
    d_excess = lo_e["excess_of_cash"] - hi_e["excess_of_cash"]
    share_cash = 100 * d_harv / d_edge if d_edge else float("nan")
    print(f"\n--- WHAT EXPLAINS THE REGIME SWING? (low-cash era − high-cash era) ---")
    print(f"  total edge swing        : {d_edge:+.2f} pp/yr")
    print(f"  ... from CASH-HARVEST   : {d_harv:+.2f} pp/yr  ({share_cash:.0f}% of the swing)")
    print(f"  ... from EXCESS-OF-CASH : {d_excess:+.2f} pp/yr  ({100-share_cash:.0f}% of the swing)")

    # paired CI on the excess-of-cash edge DIFFERENCE between eras (is it real?)
    lo_x, hi_x = excess[idx[idx.year >= SPLIT_YEAR]], excess[idx[idx.year < SPLIT_YEAR]]
    n = min(len(lo_x), len(hi_x))
    d_ci = block_ci(pd.Series(lo_x.values[:n] - hi_x.values[:n]), ann)
    print(f"  excess-of-cash era difference 95% CI: [{d_ci[0]:+.2f}, {d_ci[1]:+.2f}] pp/yr")

    # CONTINUOUS view — no arbitrary split: excess edge in cash-rate quintiles
    print(f"\n--- CONTINUOUS view (cash-rate quintiles; no arbitrary boundary) ---")
    cr = cash.reindex(idx).rolling(252).mean()
    q = pd.qcut(cr.dropna(), 5, labels=False)
    quint = {}
    for k in range(5):
        m = q[q == k].index
        quint[k] = {"avg_cash": ann(cash.reindex(m).dropna()),
                    "excess": ann(excess.reindex(m).dropna()),
                    "harvest": ann(harvest.reindex(m).dropna())}
        print(f"  Q{k+1} cash {quint[k]['avg_cash']:>5.2f}% → "
              f"harvest {quint[k]['harvest']:>+6.2f}   excess-of-cash {quint[k]['excess']:>+7.2f}")

    # --- mechanical verdict against the PRE-STATED outcomes ------------------- #
    stable = d_ci[0] <= 0 <= d_ci[1]
    near_zero = all(res[l]["excess_ci"][0] <= 0 <= res[l]["excess_ci"][1] for l, _ in eras)
    if near_zero:
        verdict = ("(iii) EXCESS-OF-CASH EDGE ≈ 0 THROUGHOUT — the sleeve is a cash-yield "
                   "harvesting vehicle wearing a trend costume; its deployment case is a rate forecast")
    elif stable:
        verdict = ("(i) EXCESS-OF-CASH EDGE STABLE across yield regimes — the regime "
                   "dependency WAS the cash term, an identity; no conditioning justified")
    else:
        verdict = ("(ii) EXCESS-OF-CASH EDGE ITSELF REGIME-DEPENDENT — a genuine "
                   "conditional effect; only NOW is a future conditioning trial warranted")
    print(f"\n⇒ VERDICT: {verdict}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"eras": res, "swing": {"edge": d_edge, "cash_harvest": d_harv,
                               "excess": d_excess, "cash_share_pct": share_cash},
                               "excess_era_diff_ci": d_ci, "quintiles": quint,
                               "verdict": verdict}, indent=2, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

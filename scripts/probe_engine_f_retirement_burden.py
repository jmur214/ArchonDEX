"""
probe_engine_f_retirement_burden.py — simulate the Engine F retirement gate's
false-retirement rate on edges with a KNOWN positive true Sharpe.

Seeded claim 1A.2 (alpha-frontier review 2026-09-30):
  `lifecycle_manager._check_retirement_gates` retires an edge when the block-
  bootstrap `ci_low` of its per-trade-PnL Sharpe is below benchmark_sharpe − 0.3
  (engines/engine_f_governance/lifecycle_manager.py, Gate 2). Using ci_low on a
  KILL gate inverts the burden of proof: the edge must PROVE it is good at the
  95% level or die. Additionally `_edge_sharpe_from_pnl` annualizes per-trade
  mean/std by sqrt(252) "assuming daily trade frequency" (lifecycle_manager.py
  ~:267-276), and the bootstrap helper uses the same convention (:62-82).

This probe uses the PRODUCTION helpers (`_edge_sharpe_from_pnl`,
`_bootstrap_sharpe_ci_low_from_pnls`) and reproduces Gate 2 + Gate 3 (revival)
verbatim, on synthetic per-trade PnL with true annualized Sharpe ∈ {0.3, 0.6}
at trade frequency ∈ {50/yr, 252/yr}, over N_trades ∈ {100, 250, 500, 1000}.
benchmark_sharpe = 0.8 (SPY-like) → threshold 0.5 (retirement_margin 0.3).

Reports the fraction of simulations in which a TRUE-POSITIVE edge is retired.
Deterministic: seed 0. Prints JSON. Wall time ~5-10 min (real bootstrap).
Run: python scripts/probe_engine_f_retirement_burden.py [--sims 30]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.engine_f_governance.lifecycle_manager import (  # noqa: E402
    _bootstrap_sharpe_ci_low_from_pnls,
    _edge_sharpe_from_pnl,
)

BENCH = 0.8
MARGIN = 0.3
REVIVAL_WINDOW = 15
REVIVAL_SHARPE = 0.3


def gate2_gate3_retire(pnls: np.ndarray) -> bool:
    """Verbatim logic of _check_retirement_gates Gates 2-3 (Gate 1 min-trades assumed met)."""
    threshold = BENCH - MARGIN
    ci_low = _bootstrap_sharpe_ci_low_from_pnls(pnls)
    if ci_low >= threshold:
        return False
    rev = pnls[-REVIVAL_WINDOW:]
    if len(rev) >= 5 and _edge_sharpe_from_pnl(rev) > REVIVAL_SHARPE:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=30)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    rows = []
    for true_sr in (0.3, 0.6):
        for tpy in (50, 252):
            per_trade_sr = true_sr / np.sqrt(tpy)  # honest per-trade SR
            for n in (100, 250, 500, 1000):
                retired = 0
                code_point = []
                code_ci = []
                for _ in range(args.sims):
                    pnls = rng.normal(per_trade_sr * 100.0, 100.0, n)  # $100 std per trade
                    code_point.append(_edge_sharpe_from_pnl(pnls))
                    ci = _bootstrap_sharpe_ci_low_from_pnls(pnls)
                    code_ci.append(ci)
                    if gate2_gate3_retire(pnls):
                        retired += 1
                rows.append({
                    "true_annual_sr": true_sr,
                    "trades_per_year": tpy,
                    "n_trades": n,
                    "years_of_record": round(n / tpy, 1),
                    "code_point_sharpe_mean": round(float(np.mean(code_point)), 3),
                    "code_ci_low_mean": round(float(np.mean(code_ci)), 3),
                    "threshold": BENCH - MARGIN,
                    "retire_rate": round(retired / args.sims, 3),
                })
                print(json.dumps(rows[-1]), file=sys.stderr)
    out = {"sims_per_cell": args.sims, "benchmark_sharpe": BENCH, "margin": MARGIN, "rows": rows,
           "note": ("code_point_sharpe uses sqrt(252) on per-trade PnL regardless of frequency: "
                    "for 50 trades/yr it INFLATES the point estimate ~2.2x; the ci_low is what the gate reads.")}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

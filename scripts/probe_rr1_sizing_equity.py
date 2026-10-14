"""RR-1 probe — does the backtester SIZE from a different equity than it REPORTS?

Pre-registered (alpha_frontier_program_2026_09_30.md §3.1 RR-1): H1 = sizing equity
diverges from true equity after the first fill. REFUTATION: if sizing == cash + MV on
every bar, the finding is wrong — say so and stop.

Drives the REAL golden-master pipeline (identical fixture + edges, imported from the
test module rather than restated) and observes every bar in-process. Mutates nothing:
the only patch is an observer wrapped around _log_snapshot, which reads true equity
(cash + MV) the same way the controller itself does.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))

import backtester.backtest_controller as bc  # noqa: E402
import test_golden_master as gm  # noqa: E402

rows: list = []
_orig_snap, _orig_cap = bc.BacktestController._log_snapshot, bc.BacktestController.get_portfolio_capital


def _observe(self, next_rows, nxt):
    _orig_snap(self, next_rows, nxt)
    px = {t: bc._scalar_close(r) for t, r in next_rows.items()}
    mv = sum(float(p.qty) * float(px[t]) for t, p in self.portfolio.positions.items()
             if p.qty and px.get(t) is not None)
    cash, cap = float(self.portfolio.cash), float(_orig_cap(self))
    rows.append({"date": str(nxt)[:10], "sizing_capital": cap, "cash": cash, "mv": mv,
                 "true_equity": cash + mv, "sizing_equity": cap + mv,
                 "gross": mv / (cash + mv) if (cash + mv) else float("nan")})


bc.BacktestController._log_snapshot = _observe
res = gm._run_pipeline(gm._load_data_map())

import pandas as pd  # noqa: E402

df = pd.DataFrame(rows)
df["ratio"] = df["sizing_equity"] / df["true_equity"]
div = df[(df["sizing_equity"] - df["true_equity"]).abs() > 1e-6]
print(f"bars observed: {len(df)}   bars where sizing != true equity: {len(div)}")
# The SAME count means opposite things on the two sides of the fix, so the verdict says
# which side it is reading. A probe that printed "REFUTED" on the fixed branch would tell a
# reviewer the finding was wrong at the exact moment it was confirmed repaired.
# Decided by EXECUTION, not by reading source: a first version grepped the getter's text
# for `self.portfolio.capital`, found it in the explanatory DOCSTRING, and reported the
# fixed controller as unfixed. Hand the real method a portfolio whose cash and capital
# disagree and see which one it returns.
class _P:  # noqa: D401 - a two-attribute stand-in
    cash, capital = 1.0, 2.0
_c = bc.BacktestController.__new__(bc.BacktestController); _c.portfolio = _P()
_fixed = float(_orig_cap(_c)) == 1.0
if div.empty:
    print("VERDICT: sizing == cash + MV on every bar. " + (
        "This is the FIXED controller — the expected post-repair state (RR-1 repaired)."
        if _fixed else
        "This is the UNFIXED controller — H1 is REFUTED; the finding is wrong. Stop."))
else:
    print("VERDICT: sizing != true equity — H1 CONFIRMED (the frozen-capital bug is live)."
          + ("" if not _fixed else " WARNING: the getter looks fixed yet bars diverge — investigate."))
    print(f"first divergence: {div.iloc[0]['date']}   (first bar with a fill = {df[df['mv'] > 0].iloc[0]['date']})")
print(f"bars with NEGATIVE cash: {(df['cash'] < 0).sum()}   bars with gross > 1.0: {(df['gross'] > 1).sum()}")
print(f"sizing_capital: min {df['sizing_capital'].min():,.0f}  max {df['sizing_capital'].max():,.0f}  (frozen if equal)")
print(f"cash:           min {df['cash'].min():,.0f}  max {df['cash'].max():,.0f}")
print(f"sizing/true equity ratio: median {df['ratio'].median():.3f}  max {df['ratio'].max():.3f}")
print(f"gross (MV/true equity):   median {df['gross'].median():.3f}  max {df['gross'].max():.3f}")
print("\nper-month (last bar of each month):")
m = df.assign(mo=df["date"].str[:7]).groupby("mo").tail(1)
print(m[["date", "sizing_capital", "cash", "mv", "true_equity", "sizing_equity", "ratio", "gross"]]
      .to_string(index=False, float_format=lambda v: f"{v:,.3f}" if abs(v) < 10 else f"{v:,.0f}"))

"""T-291 Deliverable 2 — even_week x is_fomc_week interaction (frozen pre-reg, N_trials+=1).

Is the JF-2019 even-FOMC-cycle-week premium CONCENTRATED in the FOMC decision week (cycle
week 0) vs spread across all even weeks? Groups on SPY daily returns: G1=even&fomc-week,
G2=even&non-fomc-week, G3=odd. Test = G1-G2 block-bootstrap 95% CI (block 5, 1000, seed 0).
Frozen spec: docs/Audit/event_interaction_prereg_t291_2026_07_07.md. Run AFTER the freeze commit.
"""
import csv
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scripts.calendar_flow_probe_t250 import FOMC as _FOMC_RAW      # noqa: E402  (reuse the fixture)

FOMC = sorted(pd.Timestamp(d) for d in _FOMC_RAW)


def spy_returns():
    r = list(csv.DictReader(open(os.path.join(ROOT, "data/processed/SPY_1d.csv"))))
    px = pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()
    return px.pct_change().dropna()


def even_week(dt):
    prev = [f for f in FOMC if f <= dt]
    if not prev:
        return None
    return ((dt - prev[-1]).days // 7) % 2 == 0


def is_fomc_week(dt):
    """dt is in the same ISO calendar week as an FOMC decision (cycle week 0)."""
    iso = dt.isocalendar()
    return any(f.isocalendar()[:2] == (iso[0], iso[1]) for f in FOMC)


def block_ci(a, b, block=5, n=1000, seed=0):
    """95% CI of (mean(a) - mean(b)) via independent block bootstrap of each group."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    diffs = []

    def resample(x):
        nb = int(np.ceil(len(x) / block))
        idx = np.concatenate([np.arange(s, s + block) % len(x) for s in rng.integers(0, len(x), nb)])[:len(x)]
        return x[idx].mean()
    for _ in range(n):
        diffs.append(resample(a) - resample(b))
    return float(a.mean() - b.mean()), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def run(ret, tag):
    idx = ret.index
    ew = pd.Series({d: even_week(d) for d in idx}).dropna().astype(bool)
    fw = pd.Series({d: is_fomc_week(d) for d in idx})
    ew = ew.reindex(idx).fillna(False).astype(bool)   # force bool (else ~ew does int ~ on objects)
    fw = fw.reindex(idx).fillna(False).astype(bool)
    g1 = ret[ew & fw].values          # even & fomc-week (week 0)
    g2 = ret[ew & ~fw].values         # even & non-fomc-week (weeks 2,4,6)
    g3 = ret[~ew].values              # odd weeks (baseline)
    print(f"\n=== {tag}: {idx[0].date()}→{idx[-1].date()} ===")
    for nm, g in [("G1 even&FOMC-week (wk0)", g1), ("G2 even&non-FOMC (wk2,4,6)", g2), ("G3 odd (baseline)", g3)]:
        print(f"  {nm:28} mean {g.mean()*1e4:+6.2f} bps/day  (n={len(g)})")
    pt, lo, hi = block_ci(g1, g2)
    sig = "CONCENTRATED (CI excludes 0, G1>G2)" if (lo > 0) else "not-concentrated (CI straddles 0)"
    print(f"  G1 − G2 = {pt*1e4:+.2f} bps/day  95%CI [{lo*1e4:+.2f}, {hi*1e4:+.2f}] bps  → {sig}")
    _, l13, h13 = block_ci(g1, g3)
    _, l23, h23 = block_ci(g2, g3)
    print(f"  context: G1−G3 [{l13*1e4:+.2f},{h13*1e4:+.2f}]  G2−G3 [{l23*1e4:+.2f},{h23*1e4:+.2f}] bps")
    return lo > 0


def main():
    ret = spy_returns()
    full = run(ret, "FULL 1994-2026 (PRIMARY GATE)")
    run(ret[ret.index >= "2015-01-01"], "POST-2015 (decay read)")
    print(f"\n=== VERDICT (primary = full-sample G1−G2 CI) ===")
    print(f"  {'CONFIRMED — even-week premium is CONCENTRATED in the FOMC week' if full else 'H0 / NOT CONCENTRATED — no FOMC-week-specific mechanism located'}")
    print("  (family-N=2 with T-268; role if confirmed = event-day SIZING modifier, NEVER a timing gate — T-233)")


if __name__ == "__main__":
    main()

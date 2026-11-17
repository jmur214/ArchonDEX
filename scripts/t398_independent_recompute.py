"""T-398 — an INDEPENDENT recomputation of the decision cell from the raw snapshot files.

It shares NO measurement code with scripts/t398_stacked_trend_overlay.py: the calendar, the
membership rule, the excess-return formula, the composite, the arm and the statistics are written
again here, deliberately in a different style (pandas frames, not the harness's arrays). The only
thing taken from the harness is `financing_base()` — B-5's validated H.15 / SOFR parse.

It then compares its numbers with the harness's results.json and exits non-zero if the decision
cell's total differs by more than 1e-9. Its bootstrap uses its OWN seed, so its interval is a
cross-check on the harness's, not a replay of it.

Usage:
    python scripts/t398_independent_recompute.py            # reads data/t398_local/ (run A)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import t398_stacked_trend_overlay as h  # noqa: E402  (financing_base only)

# The decision cell's expense ratios, typed again here from amendments 2 and 3 (percent).
ER_PCT: Dict[str, float] = {
    "RYMFX": 1.99, "AQMIX": 1.25, "ASFYX": 1.45, "WTMF": 0.66, "EVOIX": 1.34, "GMSSX": 0.80, "FMF": 0.98,
    "PQTIX": 1.51, "ABYIX": 1.79, "LOTIX": 1.81, "AHLIX": 1.56, "DBMF": 0.85, "KMLM": 0.90, "CTA": 0.86}
TOL = 1e-9


def main() -> int:
    data = ROOT / "data/t398_local"
    eq = pd.read_csv(ROOT / "data/research/substrate_multidecade/equity_tr_daily.csv",
                     index_col=0, parse_dates=True).iloc[:, 0]
    eq = eq[eq.index <= "2025-12-31"]
    e = eq.pct_change()
    cal = eq.index
    base = h.financing_base()
    rate = pd.Series(base.reindex(base.index.union(cal)).ffill().reindex(cal[:-1]).values, index=cal[1:])
    dcal = pd.Series((cal[1:] - cal[:-1]).days.values, index=cal[1:]).astype(float)
    cash = rate * dcal / 360.0
    xs = {}
    for tk, er in ER_PCT.items():
        px = pd.read_csv(data / "inputs" / f"yf_{tk}.csv", index_col=0, parse_dates=True)["adj_close"]
        span = cal[(cal >= px.index[0]) & (cal <= px.index[-1])]
        r = px.reindex(span).ffill().pct_change()
        r = r[r.index >= (px.index[0] + pd.offsets.MonthBegin(1)).normalize()]
        xs[tk] = r - cash.reindex(r.index) + er / 100.0 / 252.0
    frame = pd.DataFrame(xs)
    count = frame.notna().sum(axis=1)
    x = frame.mean(axis=1)
    start = count[count >= 3].index[0]
    win = cal[cal >= start]
    xw, ew, dw = x.reindex(win), e.reindex(win), dcal.reindex(win)
    bench = ew - 0.0009 / 252
    arm = ew + (xw - 0.01 / 252) - 0.005 * dw / 360.0 - 0.01 / 252
    d = np.log1p(arm) - np.log1p(bench)
    years = (win[-1] - cal[cal.get_loc(start) - 1]).days / 365.25
    wl, wb = (1 + arm).cumprod(), (1 + bench).cumprod()
    roll = d.rolling(756).sum()
    rng = np.random.default_rng(12345)
    n, block = len(d), 21
    dv = d.values
    sums = []
    for _ in range(2000):
        st = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        sums.append(dv[(st[:, None] + np.arange(block)[None, :]).ravel()[:n]].sum())
    lo, hi = np.percentile(sums, [2.5, 97.5])
    mine = {"start": str(start.date()), "n_days": int(n), "years": float(years), "sum_d": float(d.sum()),
            "per_year_pct": float(100 * d.sum() / years),
            "ir": float(d.mean() / d.std(ddof=1) * np.sqrt(252)),
            "composite_vol_pct": float(100 * xw.std(ddof=1) * np.sqrt(252)),
            "composite_gross_excess_pct": float(100 * xw.mean() * 252),
            "arm_maxdd_pct": float(100 * (wl / wl.cummax() - 1).min()),
            "bench_maxdd_pct": float(100 * (wb / wb.cummax() - 1).min()),
            "flat_decade_sum_d": float(d.loc["2011-01-03":"2019-12-31"].sum()),
            "y2022_sum_d": float(d.loc["2022-01-01":"2022-12-31"].sum()),
            "worst_3yr_sum_d": float(roll.min()), "worst_3yr_end": str(roll.idxmin().date()),
            "own_seed_ci_pct_per_year": [float(100 * lo / years), float(100 * hi / years)]}
    res = json.loads((data / "run_A" / "results.json").read_text())
    theirs = {"sum_d": res["H1"]["dlogTW_total"]["point_estimate"], "ir": res["H1"]["ir"],
              "flat_decade_sum_d": res["windows"]["W-L3"]["sit_through"]["w100"]["flat_decade_2011_2019"]["sum_d"],
              "y2022_sum_d": res["windows"]["W-L3"]["sit_through"]["w100"]["y2022"]["sum_d"],
              "worst_3yr_sum_d": res["windows"]["W-L3"]["sit_through"]["w100"]["worst_3yr"]["sum_d"],
              "harness_ci_pct_per_year": [100 * res["H1"]["per_year"]["ci_low"], 100 * res["H1"]["per_year"]["ci_high"]]}
    gaps = {k: abs(mine[k] - theirs[k]) for k in ("sum_d", "ir", "flat_decade_sum_d", "y2022_sum_d", "worst_3yr_sum_d")}
    ok = all(v < TOL for v in gaps.values())
    print(json.dumps({"independent": mine, "harness": theirs, "abs_gaps": gaps, "agree": ok}, indent=1))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

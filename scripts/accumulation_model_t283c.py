"""
scripts/accumulation_model_t283c.py
===================================
T-2026-07-06-283c — the accumulation race on D's CANONICAL T-284 curves.

T-283b built its own gated-2× construction; D delivered the canonical, basis-checked
daily curves to data/research/t284/daily_curves.parquet (primary / secondary /
t282_arm / plain / bh_spy / bh_2x). This swaps them in so the advisor row cites ONE
construction (D's). Runs the same $7K/yr annual DCA race + start-date sensitivity +
worst-dollar-drawdown, and reconciles any drift vs T-283b.

D's PRIMARY = 100% SPY 2×-when-ensemble-trend-on. D's SECONDARY = 3-leg all-2× (NOT
T-282's single-leg arm) — reported EXPLORATORY (its bond/gold 2× synthetics are
un-basis-checked). 0 new N_trials — re-analysis of D's validated curves.

Output: data/research/t283/accumulation_t284.json + tables. Usage:
python -m scripts.accumulation_model_t283c
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.accumulation_model_t283 import accumulate, robo, CONTRIB  # noqa: E402

CURVES = ROOT / "data" / "research" / "t284" / "daily_curves.parquet"
OUT = ROOT / "data" / "research" / "t283" / "accumulation_t284.json"
LABEL = {"primary": "GATED 2× 100%SPY (D primary)", "secondary": "GATED 2× 3-leg all (D secondary, EXPL)",
         "t282_arm": "GATED 2× sleeve (T-282 1-leg)", "plain": "plain ensemble sleeve",
         "bh_spy": "buy-hold SPY (D)", "bh_2x": "naked 2× SPY (D)"}
# T-283b terminals (my construction) for the reconciliation
T283B = {"primary": 1_940_602, "t282_arm": 667_833, "bh_spy": 1_457_567, "plain": 519_224}


def main() -> int:
    if not CURVES.exists():
        print(f"[T283c] FATAL: D's curves absent at {CURVES}"); return 2
    df = pd.read_parquet(CURVES)
    df.index = pd.to_datetime(df.index)
    configs = {c: df[c].dropna() for c in df.columns}
    # continuity context (my construction — flagged): 60_40 on the fair harness
    configs["60_40_ctx"] = robo({"SPY": 0.6, "BOND": 0.4})

    lo = max(c.index[0] for c in configs.values())
    starts = [str(lo.date())] + [s for s in ["2003-01-01", "2006-01-01", "2009-01-01", "2012-01-01"]
                                 if pd.Timestamp(s) >= lo]
    report = {"task": "T-2026-07-06-283c accumulation on D's canonical T-284 curves",
              "contrib_per_yr": CONTRIB, "source": "data/research/t284/daily_curves.parquet",
              "window": [str(lo.date()), str(min(c.index[-1] for c in configs.values()).date())],
              "full": {}, "start_sensitivity": {}, "reconcile_vs_t283b": {}}
    for nm, r in configs.items():
        m, _ = accumulate(r, starts[0])
        report["full"][nm] = m
    for s in starts:
        report["start_sensitivity"][s[:4]] = {nm: accumulate(r, s)[0]["mult_on_contrib"]
                                              for nm, r in configs.items() if accumulate(r, s)}
    for k, v in T283B.items():
        if k in report["full"]:
            d = report["full"][k]["terminal"]
            report["reconcile_vs_t283b"][k] = {"t283b": v, "t283c_D": round(d, 0), "drift_pct": round((d / v - 1) * 100, 1)}

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))
    order = ["primary", "bh_spy", "bh_2x", "secondary", "60_40_ctx", "t282_arm", "plain"]
    f = report["full"]
    print(f"\nT-283c ACCUMULATION on D's canonical T-284 curves — ${CONTRIB:,.0f}/yr DCA, "
          f"{report['window'][0]}..{report['window'][1]} (~{f['bh_spy']['years']:.0f}yr)")
    print(f"{'config':38}{'terminal$':>13}{'×contrib':>10}{'worst $DD':>13}{'%underwater':>12}")
    for nm in order:
        if nm not in f: continue
        m = f[nm]; lbl = LABEL.get(nm, nm)
        print(f"{lbl:38}{m['terminal']:>13,.0f}{m['mult_on_contrib']:>10.2f}{m['worst_dollar_dd']:>13,.0f}{m['frac_underwater']*100:>11.1f}%")
    p, b = f["primary"]["terminal"], f["bh_spy"]["terminal"]
    print(f"\n[T283c] D-PRIMARY (gated 2× 100%SPY) ${p:,.0f} vs buy-hold ${b:,.0f} => "
          f"{'BEATS' if p > b else 'does NOT beat'} (×{p/b:.2f}); worst $DD ${f['primary']['worst_dollar_dd']:,.0f}")
    if "secondary" in f:
        s2 = f["secondary"]
        print(f"[T283c] D-SECONDARY (3-leg all-2×, EXPLORATORY) ${s2['terminal']:,.0f} "
              f"(×{s2['mult_on_contrib']:.2f}); worst $DD ${s2['worst_dollar_dd']:,.0f} — the risk-adjusted candidate")
    print("\nRECONCILE vs T-283b (my construction → D's canonical):")
    for k, v in report["reconcile_vs_t283b"].items():
        print(f"   {LABEL.get(k, k):34}: T-283b ${v['t283b']:,.0f} → D ${v['t283c_D']:,.0f}  ({v['drift_pct']:+.1f}%)")
    print(f"\nSTART-DATE SENSITIVITY (terminal × contributions):")
    cols = ["primary", "bh_spy", "secondary", "t282_arm", "plain"]
    print(f"{'start':>7}" + "".join(f"{LABEL.get(k, k)[:14]:>15}" for k in cols))
    for s, row in report["start_sensitivity"].items():
        print(f"{s:>7}" + "".join(f"{row.get(k, float('nan')):>15.2f}" for k in cols))
    print(f"\n[T283c] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

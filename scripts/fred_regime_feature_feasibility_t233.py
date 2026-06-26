#!/usr/bin/env python
# scripts/fred_regime_feature_feasibility_t233.py
"""T-233 — FRED credit / VIX-term regime-feature FEASIBILITY (measure, do NOT
integrate). Would a free FRED signal de-gross EARLIER than the always-on trend
overlay at the T-221 crisis onsets — especially on the slow bears?

Reuses T-221 crisis windows + overlay de-gross dates (no re-derive); the
canonical regime path's deep panel (T-172/T-222) for SPY. ONE pre-registered
causal de-gross rule (z>+1 over trailing 252d, sustained 3d). Deterministic.
[NN-FAIL-CLOSED] on a degenerate series.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from scripts.regime_oos_loco_t172 import build_deep_panel, _sustained_crossings

ROOT = Path(__file__).resolve().parents[1]
MACRO = ROOT / "data" / "macro"
Z_THRESH = 1.0          # pre-registered: z-score > +1.0 ...
SUSTAIN = 3             # ... sustained 3 consecutive days
ZWIN = 252              # trailing 252-trading-day causal window


def _macro(series: str) -> pd.Series:
    df = pd.read_parquet(MACRO / f"{series}.parquet")
    s = df.iloc[:, 0]
    s.index = pd.to_datetime(s.index)
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def _deep_vix() -> pd.Series:
    s = pd.read_csv(ROOT / "data" / "research" / "vix_deep_t172.csv",
                    index_col=0, parse_dates=True).iloc[:, 0]
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def causal_z(s: pd.Series) -> pd.Series:
    """z-score over the trailing ZWIN days ending at t (causal: the window
    closes at t, value at t is observed at t's close)."""
    mu = s.rolling(ZWIN, min_periods=ZWIN).mean()
    sd = s.rolling(ZWIN, min_periods=ZWIN).std()
    return (s - mu) / sd.replace(0, np.nan)


def first_onset(trigger_series: pd.Series, a: str, b: str, thresh: float) -> Optional[pd.Timestamp]:
    """First date in [a,b] the series is ≥ thresh sustained SUSTAIN days."""
    win = trigger_series.loc[a:b].dropna()
    if len(win) < SUSTAIN:
        return None
    ons = _sustained_crossings(win, thresh, SUSTAIN)
    return win.index[ons[0]] if ons else None


def main() -> int:
    spy = build_deep_panel()["spy_close"]
    gt = json.loads((ROOT / "data" / "research" / "regime_ground_truth_t221.json").read_text())
    crises = {k: tuple(v["window"]) for k, v in gt["crises"].items()}
    overlay = {k: (v["overlay_prespec"]["first_degross"],
                   v["overlay_prespec"]["spy_dd_at_first_degross"])
               for k, v in gt["crises"].items()}

    # --- signals (deep on-disk; PIT-clean) ------------------------------- #
    credit = (_macro("BAA10Y") - _macro("AAA10Y")).dropna()          # deep, all crises
    vix_lvl = _deep_vix()                                            # deep, all crises
    vix3m = _macro("VIX3M"); vixc = _macro("VIX")
    vix_term = (vixc / vix3m).dropna()                              # 2020+ (COVID/2022)
    dxy_mom = _macro("DTWEXBGS").pct_change(20).dropna()           # 2006+ momentum

    for nm, s in (("credit", credit), ("vix_level", vix_lvl), ("dxy_mom", dxy_mom)):
        if s.nunique() < 5:
            raise RuntimeError(f"[NN-FAIL-CLOSED] {nm} series degenerate")

    signals = {
        "credit_BAA-AAA": (causal_z(credit), Z_THRESH),
        "vix_level": (causal_z(vix_lvl), Z_THRESH),
        "vix_term_ratio": (vix_term, 1.0),          # absolute backwardation onset
        "dxy_momentum": (causal_z(dxy_mom), Z_THRESH),
    }

    results = {"crises": {}}
    for cz, (a, b) in crises.items():
        peak = float(spy.loc[a:b].iloc[0])
        ov_date, ov_dd = overlay[cz]
        row = {"window": [a, b], "overlay_degross": ov_date, "overlay_dd": ov_dd, "signals": {}}
        for sname, (trig, th) in signals.items():
            onset = first_onset(trig, a, b, th)
            if onset is None:
                cov = trig.loc[a:b].dropna()
                row["signals"][sname] = {"onset": None,
                                         "note": "no-data" if cov.empty else "no-trigger"}
                continue
            px = spy.loc[:onset]
            dd = round(float(px.iloc[-1] / peak - 1.0), 3)
            lead_td = None
            if ov_date:
                ov_ts = pd.Timestamp(ov_date)
                lead_td = int((spy.loc[a:b].index <= pd.Timestamp(onset)).sum()
                              - (spy.loc[a:b].index <= ov_ts).sum())  # − = signal led
            row["signals"][sname] = {"onset": str(onset.date()), "spy_dd_at_onset": dd,
                                     "lead_td_vs_overlay": lead_td,
                                     "earlier_than_overlay": (dd > ov_dd if ov_dd is not None else None)}
        results["crises"][cz] = row

    # --- print ---------------------------------------------------------- #
    print("=== T-233 FRED regime-feature feasibility | signal first de-gross vs overlay ===")
    print("(SPY dd at trigger; smaller/earlier = leads. overlay dates reused from T-221)\n")
    for cz, r in results["crises"].items():
        slow = "SLOW-BEAR" if cz in ("dotcom_2000", "BEAR_2022") else "fast"
        print(f"  {cz:13s} [{slow:9s}]  overlay {r['overlay_degross']} (dd {r['overlay_dd']:+.0%})")
        for sn, sv in r["signals"].items():
            if sv["onset"] is None:
                print(f"      {sn:16s} {sv['note']}")
            else:
                tag = "LEADS" if sv["earlier_than_overlay"] else "lags"
                print(f"      {sn:16s} {sv['onset']} (dd {sv['spy_dd_at_onset']:+.0%}) "
                      f"lead {sv['lead_td_vs_overlay']:+d}td → {tag}")

    out = ROOT / "data" / "research" / "fred_regime_feature_t233.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

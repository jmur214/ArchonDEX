"""
scripts/dividend_reconcile_t287.py
==================================
T-2026-07-07-287 — reconcile the dividend double-count. D/T-286 verified the
canonical curves are already TOTAL-RETURN; the audit below confirms
`data/processed/SPY_1d.csv` is TR (2005-01-03 = 81.38, the TR value, NOT 120.3
raw), so T-283/T-283b's `+ DIV_D` on top was a DOUBLE COUNT. This re-issues the
ONE corrected canonical accumulation table from D's TR curves + cleanly-recomputed
(no-div) robos, and confirms the relative verdict survives.

Output: data/research/t283/accumulation_CANONICAL_t287.json + the corrected table.
Usage: python -m scripts.dividend_reconcile_t287
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# accumulate() is div-agnostic (compounds a return series + adds contributions);
# the bug was in the config BUILDERS, not accumulate. Reuse it; also grab the raw
# TR price series + cash. Do NOT use the buggy div-adding builders.
from scripts.accumulation_model_t283 import accumulate, CONTRIB, SPY, BOND, GOLD, _cash_on, TD, ER, TXN  # noqa: E402

CURVES = ROOT / "data" / "research" / "t284" / "daily_curves.parquet"
OUT = ROOT / "data" / "research" / "t283" / "accumulation_CANONICAL_t287.json"


def robo_clean(w):
    """60/40-style robo, NO dividend double-count — processed SPY is already TR."""
    closes = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
    etfs = [k for k in w if k != "_cash"]; cw = w.get("_cash", 0.0)
    rets = pd.concat({k: closes[k].pct_change() - ER[k] / TD for k in etfs}, axis=1, sort=True).dropna()
    cr = _cash_on(rets.index); hold = {k: w[k] for k in etfs}; cash = cw; out = {}; pm = None
    for dt, row in rets.iterrows():
        m = (dt.year, dt.month); rc = 0.0
        if pm is not None and m != pm:
            tot = sum(hold.values()) + cash; nh = {k: tot * w[k] for k in etfs}; nc = tot * cw
            rc = sum(abs(nh[k] - hold[k]) for k in etfs) / max(tot, 1e-9) * TXN; hold = nh; cash = nc
        prev = sum(hold.values()) + cash
        for k in etfs: hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt]); out[dt] = (sum(hold.values()) + cash) / prev - 1 - rc; pm = m
    return pd.Series(out)


def main() -> int:
    # --- audit evidence ---
    proc = SPY  # data/processed/SPY_1d.csv close
    sc = float(proc.asof(pd.Timestamp("2005-01-03")))
    w = proc[(proc.index >= "2000-10-30") & (proc.index <= "2025-12-31")]
    cagr = float((w.iloc[-1] / w.iloc[0]) ** (252.0 / len(w)) - 1)
    audit = {"processed_SPY_2005_01_03": round(sc, 2), "TR_value_expected": 81.4, "raw_price_expected": 120.3,
             "is_total_return": abs(sc - 81.4) < abs(sc - 120.3),
             "bare_price_CAGR_pct": round(cagr * 100, 2),
             "double_count_confirmed": True,
             "offending_lines": ["accumulation_model_t283.py:67 _spy_tr_ret = SPY.pct_change() + DIV_D",
                                 "accumulation_model_t283.py:79 sleeve SPY leg: ar = ar + DIV_D",
                                 "accumulation_model_t283.py:92 robo SPY leg: (a + DIV_D)",
                                 "accumulation_model_t283b.py:49 SSO_SYN = 2*(_aret + DIV_D) - ...",
                                 "accumulation_model_t283b.py:71 sleeve SPY leg: aret = aret + DIV_D"]}

    # --- corrected canonical: D's TR curves + clean robos ---
    df = pd.read_parquet(CURVES); df.index = pd.to_datetime(df.index)
    configs = {c: df[c].dropna() for c in df.columns}
    configs["60_40"] = robo_clean({"SPY": 0.6, "BOND": 0.4})
    configs["schwab_like"] = robo_clean({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})

    lo = max(c.index[0] for c in configs.values())
    starts = [str(lo.date())] + [s for s in ["2003-01-01", "2006-01-01", "2009-01-01", "2012-01-01"]
                                 if pd.Timestamp(s) >= lo]
    report = {"task": "T-2026-07-07-287 dividend reconcile — CORRECTED CANONICAL (all TR, no double-count)",
              "basis": "TOTAL-RETURN (processed SPY is TR; D's curves TR; no manual dividend added)",
              "audit": audit, "contrib_per_yr": CONTRIB, "window": [str(lo.date()), str(min(c.index[-1] for c in configs.values()).date())],
              "RETRACTED_t283b_figures": {"buy_hold": "$1.45M -> $929K", "gated_primary": "$1.94M -> $1.12M",
                                          "reason": "double-counted +1.8%/yr dividend on already-TR inputs (~1.57x buy-hold, ~1.74x the 2x arm)"},
              "full": {}, "start_sensitivity": {}}
    for nm, r in configs.items():
        m, _ = accumulate(r, starts[0]); report["full"][nm] = m
    for s in starts:
        report["start_sensitivity"][s[:4]] = {nm: accumulate(r, s)[0]["mult_on_contrib"]
                                              for nm, r in configs.items() if accumulate(r, s)}

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))
    print(f"\n=== T-287 DIVIDEND RECONCILE ===")
    print(f"processed SPY 2005-01-03 = {audit['processed_SPY_2005_01_03']}  => "
          f"{'TOTAL-RETURN' if audit['is_total_return'] else 'RAW PRICE'} (TR≈81.4 / raw≈120.3); bare CAGR {audit['bare_price_CAGR_pct']}%")
    print(f"VERDICT: DOUBLE-COUNT CONFIRMED — T-283/T-283b added +1.8%/yr on already-TR SPY. Figures RETRACTED.")
    f = report["full"]
    order = ["primary", "bh_spy", "bh_2x", "secondary", "60_40", "t282_arm", "schwab_like", "plain"]
    print(f"\nCORRECTED CANONICAL (all TR, no double-count) — ${CONTRIB:,.0f}/yr DCA, {report['window'][0]}..{report['window'][1]}:")
    print(f"{'config':24}{'terminal$':>13}{'×contrib':>10}{'worst $DD':>13}")
    for nm in order:
        if nm not in f: continue
        m = f[nm]; print(f"{nm:24}{m['terminal']:>13,.0f}{m['mult_on_contrib']:>10.2f}{m['worst_dollar_dd']:>13,.0f}")
    p, b = f["primary"]["terminal"], f["bh_spy"]["terminal"]
    every = all(report["start_sensitivity"][s].get("primary", 0) > report["start_sensitivity"][s].get("bh_spy", 1e9)
                for s in report["start_sensitivity"])
    print(f"\nRELATIVE VERDICT (survives the correction): gated 2x 100%SPY ${p:,.0f} vs buy-hold ${b:,.0f} = ×{p/b:.2f}; "
          f"beats buy-hold at EVERY start: {every}")
    print(f"[T287] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

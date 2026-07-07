"""
scripts/accumulation_model_t283b.py
===================================
T-2026-07-06-283b — extend the accumulation model with the TREND-GATED LEVERAGE
arms (D/T-282, merged) under the $7K/yr contributing race. The user's question:
does the GATED 2× config beat buy-hold SPY's $1.45M under accumulation — and what
is its worst contributing-path DRAWDOWN in dollars?

Reuses the T-283 machinery (configs a-d, $7K/yr DCA, SPY TR + 1.8% div) and adds:
  (e) GATED 2× — 100% SPY, 2× when the ensemble trend is ON, cash when off
  (f) GATED 2× SLEEVE — the T-282 3-asset arm (SPY leg 2×-when-on; BOND/GOLD 1×)
Both use T-282's VALIDATED SSO-synthetic (2× SPY TR − borrow[cash+0.60%] −
SSO_ER 0.89%), but with dividends added CONSISTENTLY (2× the div in the SSO
portion) so the comparison vs the div-inclusive buy-hold SPY TR is apples-to-apples
(T-282 itself was price-only). Ensemble trend = T-260 multi-speed [42,105,210].

0 new N_trials — a re-analysis of the T-282-validated leverage arms under the
contribution schedule. (T-284's formal full-equity validation is D's; this is the
accumulation-race preview using the validated machinery.)
Output: data/research/t283/accumulation_levered.json + tables.
Usage: python -m scripts.accumulation_model_t283b
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.trend_overlay import TrendOverlay  # noqa: E402
from scripts.accumulation_model_t283 import (  # noqa: E402  (reuse — imports run module load, not main)
    SPY, CLOSES, DIV_D, TD, ER, TXN, CONTRIB, _cash_on,
    spy_buyhold, sleeve, robo, accumulate,
)

SSO_ER, BORROW_SPREAD = 0.0089, 0.0060      # T-282 validated LETF ER + financing spread
OUT = ROOT / "data" / "research" / "t283" / "accumulation_levered.json"

# SSO synthetic — 2× SPY index TR (incl. dividends) − financing − LETF ER.
# T-282 basis-checked the price-only version vs real SSO; adding the 2× dividend
# makes it consistent with the div-inclusive buy-hold SPY TR (and more accurate —
# a real 2× LETF earns 2× the total return).
_aret = SPY.pct_change()
_borrow = _cash_on(SPY.index) + BORROW_SPREAD / TD
SSO_SYN = (2 * (_aret + DIV_D) - _borrow - SSO_ER / TD).rename("sso_syn")


def _ens_pos(c):
    ens = pd.concat([TrendOverlay(s, enabled=True).exposure(c) for s in [42, 105, 210]], axis=1).mean(axis=1)
    return ens.shift(1)


def gated_2x_spy():
    """(e) 100% SPY, 2× when the ensemble trend is on, cash (short rate) when off."""
    pos = _ens_pos(SPY).reindex(SPY.index)
    ch = _cash_on(SPY.index)
    r = pos * SSO_SYN + (1 - pos) * ch - pos.diff().abs().fillna(0.0) * TXN
    return r.dropna()


def gated_2x_sleeve():
    """(f) T-282 3-asset arm: SPY leg 2×-when-on (SPY+SSO blend), BOND/GOLD 1×."""
    parts = []
    for k, c in CLOSES.items():
        aret = c.pct_change()
        if k == "SPY":
            aret = aret + DIV_D
        pos = _ens_pos(c); ch = _cash_on(aret.index)
        if k == "SPY":
            e = (2.0 * pos).clip(upper=2.0)
            lo = e * (aret - ER["SPY"] / TD) + (1 - e) * ch
            hi = (2 - e) * (aret - ER["SPY"] / TD) + (e - 1) * SSO_SYN.reindex(aret.index)
            r = lo.where(e <= 1, hi) - e.diff().abs().fillna(0.0) * (1 / 3) * TXN
        else:
            r = pos * (aret - ER[k] / TD) + (1 - pos) * ch - pos.diff().abs().fillna(0.0) * (1 / 3) * TXN
        parts.append((r * (1 / 3)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="any").sum(axis=1).dropna()


def main() -> int:
    configs = {
        "SPY_buyhold_TR": spy_buyhold(),
        "GATED_2x_100SPY": gated_2x_spy(),
        "GATED_2x_sleeve_T282": gated_2x_sleeve(),
        "trend_sleeve": sleeve(),
        "60_40": robo({"SPY": 0.6, "BOND": 0.4}),
        "schwab_like": robo({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20}),
    }
    lo = max(c.index[0] for c in configs.values())
    starts = [str(lo.date())] + [s for s in ["2003-01-01", "2006-01-01", "2009-01-01", "2012-01-01"]
                                 if pd.Timestamp(s) >= lo]

    report = {"task": "T-2026-07-06-283b accumulation + trend-gated leverage",
              "contrib_per_yr": CONTRIB, "sso_er": SSO_ER, "borrow_spread": BORROW_SPREAD,
              "window": [str(lo.date()), str(min(c.index[-1] for c in configs.values()).date())],
              "note": "GATED arms use T-282's validated SSO-synthetic + ensemble trend, dividends added for consistency vs T-283's div-inclusive SPY TR. 0 new N_trials.",
              "full": {}, "start_sensitivity": {}}
    for nm, r in configs.items():
        m, _ = accumulate(r, starts[0])
        report["full"][nm] = m
    for s in starts:
        row = {}
        for nm, r in configs.items():
            res = accumulate(r, s)
            if res: row[nm] = res[0]["mult_on_contrib"]
        report["start_sensitivity"][s[:4]] = row

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))

    f = report["full"]
    order = ["GATED_2x_100SPY", "SPY_buyhold_TR", "GATED_2x_sleeve_T282", "60_40", "schwab_like", "trend_sleeve"]
    print(f"\nT-283b ACCUMULATION + GATED LEVERAGE — ${CONTRIB:,.0f}/yr DCA, {report['window'][0]}..{report['window'][1]} "
          f"(~{f['SPY_buyhold_TR']['years']:.0f}yr)")
    print(f"{'config':22}{'terminal$':>13}{'×contrib':>10}{'worst $DD':>13}{'%underwater':>12}")
    for nm in order:
        m = f[nm]
        print(f"{nm:22}{m['terminal']:>13,.0f}{m['mult_on_contrib']:>10.2f}{m['worst_dollar_dd']:>13,.0f}{m['frac_underwater']*100:>11.1f}%")
    bh = f["SPY_buyhold_TR"]["terminal"]; g = f["GATED_2x_100SPY"]["terminal"]
    print(f"\n[T283b] GATED-2x-100%SPY terminal ${g:,.0f} vs buy-hold SPY ${bh:,.0f}  "
          f"=> {'BEATS' if g > bh else 'does NOT beat'} the bar (×{g/bh:.2f}); "
          f"worst contributing-path drawdown ${f['GATED_2x_100SPY']['worst_dollar_dd']:,.0f}")
    print(f"\nSTART-DATE SENSITIVITY (terminal × contributions):")
    print(f"{'start':>7}" + "".join(f"{k[:13]:>14}" for k in order))
    for s, row in report["start_sensitivity"].items():
        print(f"{s:>7}" + "".join(f"{row.get(k, float('nan')):>14.2f}" for k in order))
    print(f"\n[T283b] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

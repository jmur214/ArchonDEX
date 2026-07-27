"""T-312 + T-315 — the offense campaign (ONE family, jointly reported), FROZEN terms.

T-312: deep re-verify the T-298 asymmetric-damped GATED config (equity-only, per the freeze) — does the
       2000-2026 directional edge become CI-significant over ~10 crises?
T-315: the STATIC un-gated arms {1.25,1.35,1.5,1.75,2.0}x held forever (amended grid) + an age-glide —
       the config a confirmed won't-sell holder actually wants, where the gate's turnover cost is absent.

Reuses T-311's substrate loaders verbatim (calendar_guard asserted, reindex_onto convention).
Costs are MEASURED data: 2.2bps SSO-leg (E), 0.51bps 1x-equity leg.
"""
from __future__ import annotations
import sys, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from core.metrics_engine import MetricsEngine as ME                      # noqa: E402
from scripts.deep_reverify_sleeve_t311 import (load_substrate, ensemble_pos, maxdd, cagr,  # noqa: E402
                                               sortino, CRISES, TD, ER)

SSO_ER, SPREAD = 0.0089, 0.0060
SLIP_SSO, SLIP_EQ = 2.2 / 1e4, 0.51 / 1e4      # E's measured numbers
REGIMES = {"1962-1989": ("1900-01-01", "1989-12-31"), "1990-2026": ("1990-01-01", "2100-01-01")}


# ---------------- vehicles ----------------
def lev_daily(eq_ret: pd.Series, cash: pd.Series, L: float) -> pd.Series:
    """Daily-reset L-x LETF (the honest SSO mechanic): L*gross - (L-1)*(cash+spread) - ER."""
    gross = eq_ret + ER["equity"] / TD                     # the LETF doesn't pay the 1x fund's ER
    return L * gross - (L - 1.0) * (cash + SPREAD / TD) - (SSO_ER / TD if L > 1.0 else 0.0)


def static_arm(eq_ret, cash, L: float, rebal_per_yr: int = 1) -> pd.Series:
    """Held FOREVER: no gate, no turnover except the annual rebalance (0.51bps on that only)."""
    r = lev_daily(eq_ret, cash, L)
    if L > 1.0:
        cost = pd.Series(0.0, index=r.index)
        yr = r.index.to_period("Y")
        cost[yr != yr.shift(1)] = SLIP_EQ * rebal_per_yr    # ~nothing
        r = r - cost
    return r.dropna()


def glide_arm(eq_ret, cash, L0: float, taper_yrs: int = 12) -> pd.Series:
    """Age-glide: hold L0, then de-lever linearly to 1x over the FINAL taper_yrs."""
    idx = eq_ret.index; end = idx[-1]; start_taper = end - pd.Timedelta(days=int(365.25 * taper_yrs))
    frac = pd.Series(1.0, index=idx)
    m = idx >= start_taper
    if m.any():
        prog = (idx[m] - start_taper).days / max((end - start_taper).days, 1)
        frac[m] = 1.0 - np.clip(prog, 0, 1)
    Lt = 1.0 + (L0 - 1.0) * frac
    gross = eq_ret + ER["equity"] / TD
    r = Lt * gross - (Lt - 1.0) * (cash + SPREAD / TD) - np.where(Lt > 1.0, SSO_ER / TD, 0.0)
    return pd.Series(r, index=idx).dropna() - (Lt.diff().abs().fillna(0) * SLIP_EQ)


def gated_t298(eq_px: pd.Series, eq_ret: pd.Series, cash: pd.Series) -> tuple[pd.Series, float, float]:
    """T-298: e = min(2*ensemble,2); damp re-entry (band 2/3 on e2), NEVER damp de-risking."""
    e_t = (2.0 * ensemble_pos(eq_px)).clip(upper=2.0).reindex(eq_ret.index).shift(1)
    held, out, B, TOL = np.nan, [], 2.0 / 3.0, 1e-9
    for v in e_t.values:
        if np.isnan(v):
            out.append(np.nan); continue
        if np.isnan(held): held = v
        elif v < held - TOL: held = v                       # de-risk: immediate (exit-lag == 0)
        elif v - held > B + TOL: held = v                   # re-entry: only >= 2 increments
        out.append(held)
    e = pd.Series(out, index=eq_ret.index)
    viol = int((e > e_t + TOL).sum())                       # invariant check
    sso = lev_daily(eq_ret, cash, 2.0)
    lo = e * (eq_ret - ER["equity"] / TD) + (1 - e) * cash
    hi = (2 - e) * (eq_ret - ER["equity"] / TD) + (e - 1) * sso
    r = lo.where(e <= 1, hi)
    sso_w = (e - 1).clip(lower=0); ts = sso_w.diff().abs().fillna(0)
    tot = e.diff().abs().fillna(0); teq = (tot - ts).clip(lower=0)
    return (r - ts * SLIP_SSO - teq * SLIP_EQ).dropna(), viol, float(e.mean())


# ---------------- stats ----------------
def eqc(r): return (1 + r).cumprod()
def wealth(r, start=10_000): return float(start * eqc(r).iloc[-1])
def paired_dw(a, b, L=21, n=1000, seed=0):
    j = pd.concat({"a": a, "b": b}, axis=1).dropna(); A, B_ = j["a"].values, j["b"].values; N = len(A)
    rng = np.random.default_rng(seed); nb = int(np.ceil(N / L)); out = []
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb)
        ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        out.append(np.prod(1 + A[ix]) - np.prod(1 + B_[ix]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def win_stats(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 5: return None
    e = eqc(s); return {"ret": float(e.iloc[-1] - 1), "dd": maxdd(e)}


def years_to_recover(r, crisis_end):
    """From the post-crisis trough, how long to regain the prior peak (the 'what's left to compound' test)."""
    e = eqc(r); pk = e.cummax(); under = e < pk * (1 - 1e-9)
    seg = under[under.index >= pd.Timestamp(crisis_end)]
    if not len(seg) or not seg.iloc[0]: return 0.0
    rec = seg[~seg]
    if not len(rec): return float("inf")
    return float((rec.index[0] - pd.Timestamp(crisis_end)).days / 365.25)


def report(name, r, bar, extra=""):
    e = eqc(r); lo, hi = paired_dw(r, bar)
    sig = "SIGNIFICANT" if lo > 0 else ("LOSES" if hi < 0 else "straddles-0")
    print(f"  {name:34}{wealth(r):>13,.0f}{cagr(e)*100:>8.2f}%{maxdd(e)*100:>8.1f}%{sortino(r):>8.2f}"
          f"  [{lo:+8.2f},{hi:+8.2f}] {sig}{extra}")
    return {"wealth": wealth(r), "cagr": cagr(e), "dd": maxdd(e), "ci": (lo, hi), "sig": sig}


def erp_haircut(eq_ret: pd.Series, bps_per_yr: float) -> pd.Series:
    """Forward-ERP sensitivity: subtract a constant annualized haircut from the equity return."""
    return eq_ret - bps_per_yr / TD


def main():
    legs, cash = load_substrate(["equity"])                 # equity-only per the T-312 freeze
    eq_px = legs["equity"]; eq_ret = eq_px.pct_change().dropna()
    cash = cash.reindex(eq_ret.index).ffill().fillna(0.0)
    print(f"=== T-312 + T-315 OFFENSE CAMPAIGN | equity-only | {eq_ret.index[0].date()}..{eq_ret.index[-1].date()} ===")
    e99, c99 = eq_ret, cash
    m58 = eq_ret.index >= pd.Timestamp("1968-01-01"); e58, c58 = eq_ret[m58], cash[m58]
    m64 = eq_ret.index >= pd.Timestamp("1962-01-01"); e64, c64 = eq_ret[m64], cash[m64]

    for wl, (er, cr) in [("D-B ~58yr (1968+)", (e58, c58)), ("D-A ~64yr (1962+)", (e64, c64)),
                         ("~99yr (1926+, secondary)", (e99, c99))]:
        bar = (er - ER["equity"] / TD).dropna()
        print(f"\n--- {wl} | ERP {((1+er).prod()**(252/len(er))-1 - ((1+cr).prod()**(252/len(cr))-1))*100:.2f}% "
              f"| sigma {er.std()*np.sqrt(TD)*100:.1f}% ---")
        print(f"  {'arm':34}{'$10k→':>13}{'CAGR':>9}{'MaxDD':>8}{'Sortino':>8}  paired Δwealth 95% CI vs buy-hold")
        report("BUY-HOLD 1x (THE BAR)", bar, bar)
        g, viol, mexp = gated_t298(eq_px, er, cr)
        report("T-312 gated T-298 (damped)", g, bar, f"  [invariant viol={viol}, mean-exp {mexp:.2f}]")
        for L in (1.25, 1.35, 1.5, 1.75, 2.0):
            report(f"T-315 static {L:.2f}x (held fwd)", static_arm(er, cr, L), bar)
        report("T-315 glide 2.0x→1x (final 12y)", glide_arm(er, cr, 2.0), bar)

    # ---- the frontier under forward-ERP haircuts (the whole question) ----
    print("\n=== ERP HAIRCUT SENSITIVITY (D-B ~58yr) — where does each L's edge cross zero? ===")
    bar58 = (e58 - ER["equity"] / TD).dropna()
    print(f"  {'haircut':10}" + "".join(f"{f'{L:.2f}x':>13}" for L in (1.0, 1.25, 1.35, 1.5, 1.75, 2.0)))
    for hc, lab in [(0.0, "none"), (0.02, "-2%"), (0.03, "-3%")]:
        eh = erp_haircut(e58, hc); bh = (eh - ER["equity"] / TD).dropna()
        row = f"  {lab:10}{wealth(bh):>13,.0f}"
        for L in (1.25, 1.35, 1.5, 1.75, 2.0):
            row += f"{wealth(static_arm(eh, c58, L)):>13,.0f}"
        print(row)
    print("  (row = terminal $10k; the L whose column peaks is the wealth-optimal leverage at that ERP)")
    sig = float(e58.std() * np.sqrt(TD))
    print("\n  Kelly-optimal L (= ERP/sigma^2) at each scenario:")
    erp58 = float((1 + e58).prod() ** (252 / len(e58)) - 1 - ((1 + c58).prod() ** (252 / len(c58)) - 1))
    for hc, lab in [(0.0, "none"), (0.02, "-2%"), (0.03, "-3%")]:
        print(f"    {lab:6} ERP {erp58-hc:.2%} -> L* = {(erp58-hc)/sig**2:.2f}")

    # ---- the 1929 ruin test in DOLLARS + years-to-recover ----
    print("\n=== THE 1929 RUIN TEST (~99yr window) — trough in DOLLARS from $10k, and years to recover ===")
    bar99 = (e99 - ER["equity"] / TD).dropna()
    arms99 = {"buy-hold 1x": bar99, "gated T-298": gated_t298(eq_px, e99, c99)[0]}
    for L in (1.25, 1.5, 1.75, 2.0): arms99[f"static {L:.2f}x"] = static_arm(e99, c99, L)
    for nm, r in arms99.items():
        s = r[(r.index >= "1929-09-01") & (r.index <= "1932-07-31")]
        if len(s) < 5: continue
        e = eqc(s); trough = float(10_000 * e.min()); dd = maxdd(e)
        print(f"  {nm:18} 1929-32 dd {dd*100:7.1f}%  trough ${trough:>9,.0f} from $10,000  "
              f"years-to-recover {years_to_recover(r, '1932-07-31'):.1f}")

    # ---- regime split (B/T-311 convention) ----
    print("\n=== CASH-RATE REGIME SPLIT (mirrors B/T-311) — is the static edge regime-concentrated? ===")
    for lab, (a, b) in REGIMES.items():
        m = (e64.index >= pd.Timestamp(a)) & (e64.index <= pd.Timestamp(b))
        er_, cr_ = e64[m], c64[m]
        if len(er_) < 500: continue
        bar_ = (er_ - ER["equity"] / TD).dropna()
        row = f"  {lab:10} avg cash {float((1+cr_).prod()**(252/len(cr_))-1)*100:4.1f}%  bar {cagr(eqc(bar_))*100:5.2f}%"
        for L in (1.5, 2.0):
            row += f" | {L:.1f}x {cagr(eqc(static_arm(er_, cr_, L)))*100:5.2f}%"
        row += f" | gated {cagr(eqc(gated_t298(eq_px, er_, cr_)[0]))*100:5.2f}%"
        print(row)

    # ---- lost-decades (Japan-style) tail overlay ----
    print("\n=== LOST-DECADES OVERLAY (Japan-style: a 20yr flat-to-down path grafted on) ===")
    jp = e58.copy(); n20 = int(20 * 252)
    jp.iloc[-n20:] = jp.iloc[-n20:] - (0.02 / TD)           # -2%/yr drift for the final 20yr
    bj = (jp - ER["equity"] / TD).dropna()
    print(f"  {'arm':22}{'$10k→':>13}{'CAGR':>9}")
    print(f"  {'buy-hold 1x':22}{wealth(bj):>13,.0f}{cagr(eqc(bj))*100:>8.2f}%")
    for L in (1.25, 1.5, 2.0):
        r = static_arm(jp, c58, L); print(f"  {f'static {L:.2f}x':22}{wealth(r):>13,.0f}{cagr(eqc(r))*100:>8.2f}%")

    # ---- the $7k/yr accumulation race ----
    print("\n=== $7k/yr ACCUMULATION RACE (dollar-weighted — the glide de-levers when the balance is biggest) ===")
    def accumulate(r, contrib=7000.0):
        bal = 0.0; yr = None
        for t, x in r.items():
            if yr != t.year: bal += contrib; yr = t.year
            bal *= (1 + x)
        return bal
    print(f"  {'arm':26}{'final $':>15}")
    print(f"  {'buy-hold 1x':26}{accumulate(bar58):>15,.0f}")
    for L in (1.25, 1.5, 2.0):
        print(f"  {f'static {L:.2f}x':26}{accumulate(static_arm(e58, c58, L)):>15,.0f}")
    print(f"  {'glide 2.0x→1x (12y)':26}{accumulate(glide_arm(e58, c58, 2.0)):>15,.0f}")
    print(f"  {'gated T-298':26}{accumulate(gated_t298(eq_px, e58, c58)[0]):>15,.0f}")


if __name__ == "__main__":
    main()

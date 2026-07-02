"""scripts/offleg_ab_t259.py — RUN the FROZEN T-258 off-leg pre-registration.
================================================================================
Executes docs/Audit/offleg_ab_preregistration_t258_2026_07_02.md EXACTLY on the
T-255 fair harness + T-256 deep TR-reconciled substrate. NO spec changes, NO sweep.

Control  = the T-255 fair sleeve (EW SPY/BOND/GOLD long-flat; FLAT leg = cash@DGS3MO;
           ER+txn both sides). Reproduced verbatim from fair_t236_rerun_t255.py.
Candidate= identical sleeve, but the FLAT leg holds the frozen off-leg:
           argmax trailing-12mo(252d) total return of {BIL, IEF} if that instrument's
           own 12mo return > 0, else BIL (T-bills). GLD excluded (long-leg asset).
           Off-leg instruments from data/processed/tr_reconciled/ (TR-reconciled).

Gates (frozen): paired ΔSortino ci_low>0 AND Δterminal-wealth ci_low>0 vs control;
2022 = named must-not-degrade HARD gate (cand 2022 MaxDD ≥ ctrl − 0.5pp AND 2022
ret ≥ ctrl − 0.5pp); MBL (N_trials += 1). Fail-closed: A/B window restricted to
where the off-leg is fully defined (both BIL & IEF have 252d momentum) — no silent
cash fallback. Duration BETA reclaimed, honestly labeled (not alpha; cf T-247).
"""
import csv, math, sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = "/Users/jacksonmurphy/Dev/trading_machine-agent-a"
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.trend_overlay import TrendOverlay  # noqa: E402

TD = 252
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
TXN = 0.00015  # 1.5 bps/side


def spy_close():
    r = list(csv.DictReader(open(f"{ROOT}/data/processed/SPY_1d.csv")))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def csv_ser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


def macro(s):
    d = pd.read_parquet(f"{ROOT}/data/macro/{s}.parquet")["value"].astype(float)
    d.index = pd.to_datetime(d.index); return d.dropna().sort_index()


def tr_close(t):
    d = pd.read_csv(f"{ROOT}/data/processed/tr_reconciled/{t}_1d.csv")
    return pd.Series(d["Close"].astype(float).values, index=pd.to_datetime(d["Date"])).sort_index()


SPY = spy_close()
BOND = csv_ser(f"{ROOT}/data/research/bond_synth_dgs10_t255.csv")
GOLD = csv_ser(f"{ROOT}/data/research/gold_gcf_t255.csv")
closes = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
dgs3 = macro("DGS3MO")
cash_daily = (dgs3 / 100.0 / TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq="D")).ffill()


def build_offleg():
    """Frozen off-leg: hold IEF iff (mom_IEF > mom_BIL AND mom_IEF > 0), else BIL.
    Returns (offleg_daily_return, switch_indicator, hold_is_ief) on the causal
    (shifted) decision, defined only where both 252d momenta exist."""
    bil, ief = tr_close("BIL"), tr_close("IEF")
    idx = bil.index.union(ief.index)
    bil = bil.reindex(idx).ffill(); ief = ief.reindex(idx).ffill()
    rb, ri = bil.pct_change(), ief.pct_change()
    mom_b, mom_i = bil / bil.shift(TD) - 1, ief / ief.shift(TD) - 1
    hold_ief = ((mom_i > mom_b) & (mom_i > 0))          # as-of day t (causal)
    hold_ief = hold_ief.where(mom_b.notna() & mom_i.notna())  # NaN until both defined
    pos_ief = hold_ief.shift(1)                          # act on yesterday's decision
    offleg = pos_ief * ri + (1 - pos_ief) * rb           # selected instrument's return
    switch = pos_ief.fillna(0).diff().abs().fillna(0)    # BIL<->IEF rotation
    # valid only where the decision was defined (both momenta existed the prior day)
    valid = pos_ief.notna()
    return offleg.where(valid), switch.where(valid, 0.0), hold_ief


def sleeve(offleg_ret, offleg_switch):
    """EW SPY/BOND/GOLD long-flat; flat leg earns offleg_ret; ER when long; txn on
    trend flips AND on off-leg rotations (flat weight). offleg_switch=0 series →
    reproduces the T-255 fair control when offleg_ret=cash."""
    parts = []
    for k, c in closes.items():
        c = c.astype(float); aret = c.pct_change()
        pos = TrendOverlay(105, enabled=True).exposure(c).shift(1)
        oflg = offleg_ret.reindex(aret.index).ffill()
        sw = offleg_switch.reindex(aret.index).fillna(0.0)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * oflg
        flip = pos.diff().abs().fillna(0)
        r = r - flip * (1.0 / 3.0) * TXN                 # trend flip cost (harness-exact)
        r = r - (1 - pos) * sw * TXN                     # off-leg rotation cost (flat weight)
        parts.append((r * (1.0 / 3.0)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()


def robo_fair(weights, cash_rate):
    etfs = [k for k in weights if k != "_cash"]; cw = weights.get("_cash", 0.0)
    rets = pd.concat({k: closes[k].pct_change() - ER[k] / TD for k in etfs}, axis=1, sort=True).dropna()
    cr = cash_rate.reindex(rets.index).ffill().fillna(0.0)
    hold = {k: weights[k] for k in etfs}; cash = cw; out = {}; pm = None
    for dt, row in rets.iterrows():
        m = (dt.year, dt.month); rc = 0.0
        if pm is not None and m != pm:
            tot = sum(hold.values()) + cash
            nh = {k: tot * weights[k] for k in etfs}; ncash = tot * cw
            rc = sum(abs(nh[k] - hold[k]) for k in etfs) / max(tot, 1e-9) * TXN
            hold = nh; cash = ncash
        prev = sum(hold.values()) + cash
        for k in etfs: hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt])
        out[dt] = (sum(hold.values()) + cash) / prev - 1 - rc; pm = m
    return pd.Series(out)


# ── build control + candidate ─────────────────────────────────────────────────
offleg_ret, offleg_switch, hold_ief = build_offleg()
zero_sw = pd.Series(0.0, index=cash_daily.index)
control = sleeve(cash_daily, zero_sw)                    # cash flat leg (= T-255 fair sleeve)
candidate = sleeve(offleg_ret, offleg_switch)            # momentum {BIL,IEF} flat leg
r6040 = robo_fair({"SPY": 0.60, "BOND": 0.40}, cash_daily)
rschwab = robo_fair({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20}, cash_daily)

# validation: control on ITS full window must reproduce the T-255 harness sleeve
cf = control.dropna()
print(f"[validate control vs T-255] full-window {cf.index[0].date()}..{cf.index[-1].date()} "
      f"Sortino {ME.sortino_ratio(cf,0.0,TD):.3f} Sharpe {ME.sharpe_ratio(cf,0.0,TD):.3f} "
      f"$10k→{10000*(1+cf).prod():,.0f}  (harness: 1.163 / 0.904 / 39,931)")

# A/B window = where the off-leg is fully defined (fail-closed; no cash fallback)
start = max(control.index[0], candidate.index[0], r6040.index[0], rschwab.index[0])
end = min(control.index[-1], candidate.index[-1])
def win(s): return s[(s.index >= start) & (s.index <= end)].dropna()
def maxdd(eq): return float((eq / eq.cummax() - 1).min())
def cagr(eq): return float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1)
def so(r): return ME.sortino_ratio(r, 0.0, TD)
def so_ci(r):
    try: return ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get("ci_low")
    except Exception: return float("nan")

print(f"\n=== T-259 OFF-LEG A/B — off-leg-defined window {start.date()}..{end.date()} "
      f"({(end-start).days/365.25:.1f}y) ===")
print(f'{"strategy":34}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"CAGR":>7}{"MaxDD":>8}{"$10k→":>10}')
rows = {"cash-off-leg (control)": control, "momentum-off-leg (candidate)": candidate,
        "60_40": r6040, "schwab_like": rschwab}
res = {}
for nm, r in rows.items():
    rw = win(r); eq = (1 + rw).cumprod(); res[nm] = (rw, eq)
    print(f'{nm:34}{so(rw):>9.3f}{so_ci(rw):>8.3f}{ME.sharpe_ratio(rw,0.0,TD):>8.3f}'
          f'{cagr(eq)*100:>6.1f}%{maxdd(eq)*100:>7.1f}%{10000*eq.iloc[-1]/eq.iloc[0]:>10,.0f}')


def paired(a, b, L=21, n=1000):
    """block-bootstrap paired diff (a − b): ΔSortino CI, Δterminal-wealth CI, P(Δ>0)."""
    j = pd.concat({"a": a, "b": b}, axis=1, sort=True).dropna(); x, y = j["a"].values, j["b"].values; N = len(x)
    rng = np.random.default_rng(0); dso = []; dtw = []; nb = int(np.ceil(N / L))
    def sortino(v):
        d = v[v < 0]; dd = np.sqrt((d**2).mean()) if len(d) else 1e-9; return (v.mean() / dd) * np.sqrt(TD)
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb); ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        xs, ys = x[ix], y[ix]
        dso.append(sortino(xs) - sortino(ys)); dtw.append(np.prod(1 + xs) - np.prod(1 + ys))
    return ((np.percentile(dso, 2.5), np.percentile(dso, 97.5)),
            (np.percentile(dtw, 2.5), np.percentile(dtw, 97.5)), float(np.mean(np.array(dso) > 0)))


print("\n=== PRIMARY GATE — paired diff (candidate − control), 21d blocks, 1000 iter ===")
(dlo, dhi), (tlo, thi), pw = paired(win(candidate), win(control))
g_sortino = dlo > 0; g_wealth = tlo > 0
print(f"  ΔSortino 95%CI [{dlo:+.3f},{dhi:+.3f}]  → ci_low>0: {'PASS' if g_sortino else 'FAIL'}")
print(f"  Δterminal(×start) 95%CI [{tlo:+.3f},{thi:+.3f}]  → ci_low>0: {'PASS' if g_wealth else 'FAIL'}")
print(f"  P(candidate Sortino > control) = {pw:.0%}")

print("\n=== HARD GATE — 2022 must-not-degrade ===")
def yr(r, y): return r[(r.index >= pd.Timestamp(f"{y}-01-01")) & (r.index <= pd.Timestamp(f"{y}-12-31"))]
c22, k22 = yr(win(control), 2022), yr(win(candidate), 2022)
c_ret, k_ret = (1 + c22).prod() - 1, (1 + k22).prod() - 1
c_dd, k_dd = maxdd((1 + c22).cumprod()), maxdd((1 + k22).cumprod())
g_2022 = (k_dd >= c_dd - 0.005) and (k_ret >= c_ret - 0.005)
print(f"  2022 return : control {c_ret*100:+.2f}%  candidate {k_ret*100:+.2f}%  (Δ {(k_ret-c_ret)*100:+.2f}pp)")
print(f"  2022 MaxDD  : control {c_dd*100:+.2f}%  candidate {k_dd*100:+.2f}%  (Δ {(k_dd-c_dd)*100:+.2f}pp)")
print(f"  → must-not-degrade (both ≥ control − 0.5pp): {'PASS' if g_2022 else 'FAIL'}")

# MBL — N_trials += 1 (sleeve lineage 16 → 17); relative A/B is the primary bar
N = 17; yrs = (end - start).days / 365.25; mbl = math.sqrt(2 * math.log(N) / yrs)
kw = win(candidate); ksh = ME.sharpe_ratio(kw, 0.0, TD)
print(f"\n=== MBL (N={N}, {yrs:.1f}y): Sharpe bar {mbl:.3f}; candidate Sharpe {ksh:.3f} "
      f"→ {'CLEARS' if ksh > mbl else 'FAILS'} ===")

verdict = "PASS — off-leg improves the sleeve" if (g_sortino and g_wealth and g_2022) else \
          "REFUTED — off-leg does not clear the frozen gates"
print(f"\n=== VERDICT: {verdict} ===")
print(f"  gates: ΔSortino ci_low>0 {g_sortino} | Δwealth ci_low>0 {g_wealth} | 2022 no-degrade {g_2022}")

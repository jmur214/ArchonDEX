"""scripts/offleg_rescue_t266.py — RUN the FROZEN T-266 off-leg RESCUE (family N=2, FINAL).
================================================================================
Executes docs/Audit/offleg_rescue_preregistration_t266_2026_07_02.md EXACTLY.
Identical to the T-259 A/B (scripts/offleg_ab_t259.py) EXCEPT build_offleg adds one
eligibility gate: IEF is held only when the T-259 base 12mo selection picks it AND
IEF > its 63-day (3-month) SMA — the fast duration-trend gate that fixes the 2022
failure (12mo momentum held IEF into the bond crash). ONE spec, no sweep.
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
TXN = 0.00015


def spy_close():
    r = list(csv.DictReader(open(f"{ROOT}/data/processed/SPY_1d.csv")))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()
def csv_ser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index); return d.iloc[:, 0].astype(float).sort_index()
def macro(s):
    d = pd.read_parquet(f"{ROOT}/data/macro/{s}.parquet")["value"].astype(float); d.index = pd.to_datetime(d.index)
    return d.dropna().sort_index()
def tr_close(t):
    d = pd.read_csv(f"{ROOT}/data/processed/tr_reconciled/{t}_1d.csv")
    return pd.Series(d["Close"].astype(float).values, index=pd.to_datetime(d["Date"])).sort_index()


SPY = spy_close()
BOND = csv_ser(f"{ROOT}/data/research/bond_synth_dgs10_t255.csv")
GOLD = csv_ser(f"{ROOT}/data/research/gold_gcf_t255.csv")
closes = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
dgs3 = macro("DGS3MO")
cash_daily = (dgs3 / 100.0 / TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq="D")).ffill()


def build_offleg_rescue():
    """T-259 base selection + the RESCUE 63d IEF fast-trend eligibility gate.
    IEF held iff (mom_IEF>mom_BIL AND mom_IEF>0) AND (IEF > IEF 63d SMA); else BIL."""
    bil, ief = tr_close("BIL"), tr_close("IEF")
    idx = bil.index.union(ief.index)
    bil = bil.reindex(idx).ffill(); ief = ief.reindex(idx).ffill()
    rb, ri = bil.pct_change(), ief.pct_change()
    mom_b, mom_i = bil / bil.shift(TD) - 1, ief / ief.shift(TD) - 1
    base_ief = (mom_i > mom_b) & (mom_i > 0)                      # T-259 base selection
    fast_sma = ief.rolling(63, min_periods=63).mean()            # 63d (3mo) fast trend
    ief_uptrend = ief > fast_sma                                 # duration trending up (fast)
    hold_ief = (base_ief & ief_uptrend).where(mom_b.notna() & mom_i.notna() & fast_sma.notna())
    pos_ief = hold_ief.shift(1)                                   # causal
    offleg = pos_ief * ri + (1 - pos_ief) * rb
    switch = pos_ief.fillna(0).diff().abs().fillna(0)
    valid = pos_ief.notna()
    return offleg.where(valid), switch.where(valid, 0.0)


def sleeve(offleg_ret, offleg_switch):
    """T-255 fair sleeve; flat leg earns offleg_ret; ER when long; txn on flips +
    off-leg rotations. offleg_ret=cash & switch=0 reproduces the fair control."""
    parts = []
    for k, c in closes.items():
        c = c.astype(float); aret = c.pct_change()
        pos = TrendOverlay(105, enabled=True).exposure(c).shift(1)
        oflg = offleg_ret.reindex(aret.index).ffill()
        sw = offleg_switch.reindex(aret.index).fillna(0.0)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * oflg
        r = r - pos.diff().abs().fillna(0) * (1.0 / 3.0) * TXN
        r = r - (1 - pos) * sw * TXN
        parts.append((r * (1.0 / 3.0)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()


def robo_fair(weights):
    etfs = [k for k in weights if k != "_cash"]; cw = weights.get("_cash", 0.0)
    rets = pd.concat({k: closes[k].pct_change() - ER[k] / TD for k in etfs}, axis=1, sort=True).dropna()
    cr = cash_daily.reindex(rets.index).ffill().fillna(0.0)
    hold = {k: weights[k] for k in etfs}; cash = cw; out = {}; pm = None
    for dt, row in rets.iterrows():
        m = (dt.year, dt.month); rc = 0.0
        if pm is not None and m != pm:
            tot = sum(hold.values()) + cash; nh = {k: tot * weights[k] for k in etfs}; ncash = tot * cw
            rc = sum(abs(nh[k] - hold[k]) for k in etfs) / max(tot, 1e-9) * TXN; hold = nh; cash = ncash
        prev = sum(hold.values()) + cash
        for k in etfs: hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt]); out[dt] = (sum(hold.values()) + cash) / prev - 1 - rc; pm = m
    return pd.Series(out)


offleg_ret, offleg_switch = build_offleg_rescue()
control = sleeve(cash_daily, pd.Series(0.0, index=cash_daily.index))
candidate = sleeve(offleg_ret, offleg_switch)
r6040 = robo_fair({"SPY": 0.60, "BOND": 0.40}); rschwab = robo_fair({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})

start = max(control.index[0], candidate.index[0], r6040.index[0], rschwab.index[0]); end = min(control.index[-1], candidate.index[-1])
def win(s): return s[(s.index >= start) & (s.index <= end)].dropna()
def maxdd(eq): return float((eq / eq.cummax() - 1).min())
def cagr(eq): return float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1)
def so(r): return ME.sortino_ratio(r, 0.0, TD)
def so_ci(r):
    try: return ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get("ci_low")
    except Exception: return float("nan")

print(f"=== T-266 OFF-LEG RESCUE A/B (family N=2, FINAL) — window {start.date()}..{end.date()} ({(end-start).days/365.25:.1f}y) ===")
print(f'{"strategy":34}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"CAGR":>7}{"MaxDD":>8}{"$10k→":>10}')
for nm, r in {"cash-off-leg (control)": control, "rescue-off-leg (candidate)": candidate, "60_40": r6040, "schwab_like": rschwab}.items():
    rw = win(r); eq = (1 + rw).cumprod()
    print(f'{nm:34}{so(rw):>9.3f}{so_ci(rw):>8.3f}{ME.sharpe_ratio(rw,0.0,TD):>8.3f}{cagr(eq)*100:>6.1f}%{maxdd(eq)*100:>7.1f}%{10000*eq.iloc[-1]/eq.iloc[0]:>10,.0f}')


def paired(a, b, L=21, n=1000):
    j = pd.concat({"a": a, "b": b}, axis=1, sort=True).dropna(); x, y = j["a"].values, j["b"].values; N = len(x)
    rng = np.random.default_rng(0); dso = []; dtw = []; nb = int(np.ceil(N / L))
    def sortino(v):
        d = v[v < 0]; dd = np.sqrt((d**2).mean()) if len(d) else 1e-9; return (v.mean() / dd) * np.sqrt(TD)
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb); ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        dso.append(sortino(x[ix]) - sortino(y[ix])); dtw.append(np.prod(1 + x[ix]) - np.prod(1 + y[ix]))
    return ((np.percentile(dso, 2.5), np.percentile(dso, 97.5)), (np.percentile(dtw, 2.5), np.percentile(dtw, 97.5)), float(np.mean(np.array(dso) > 0)))


print("\n=== PRIMARY GATE — paired diff (candidate − control) ===")
(dlo, dhi), (tlo, thi), pw = paired(win(candidate), win(control))
g_sortino = dlo > 0; g_wealth = tlo > 0
print(f"  ΔSortino 95%CI [{dlo:+.3f},{dhi:+.3f}] → ci_low>0: {'PASS' if g_sortino else 'FAIL'}")
print(f"  Δterminal(×start) 95%CI [{tlo:+.3f},{thi:+.3f}] → ci_low>0: {'PASS' if g_wealth else 'FAIL'}")
print(f"  P(candidate Sortino > control) = {pw:.0%}")

print("\n=== HARD GATE — 2022 must-not-degrade ===")
def yr(r, y): return r[(r.index >= pd.Timestamp(f"{y}-01-01")) & (r.index <= pd.Timestamp(f"{y}-12-31"))]
c22, k22 = yr(win(control), 2022), yr(win(candidate), 2022)
c_ret, k_ret = (1 + c22).prod() - 1, (1 + k22).prod() - 1
c_dd, k_dd = maxdd((1 + c22).cumprod()), maxdd((1 + k22).cumprod())
g_2022 = (k_dd >= c_dd - 0.005) and (k_ret >= c_ret - 0.005)
print(f"  2022 return : control {c_ret*100:+.2f}%  candidate {k_ret*100:+.2f}%  (Δ {(k_ret-c_ret)*100:+.2f}pp)")
print(f"  2022 MaxDD  : control {c_dd*100:+.2f}%  candidate {k_dd*100:+.2f}%  (Δ {(k_dd-c_dd)*100:+.2f}pp)")
print(f"  → must-not-degrade: {'PASS' if g_2022 else 'FAIL'}")

N = 18; yrs = (end - start).days / 365.25; mbl = math.sqrt(2 * math.log(N) / yrs); ksh = ME.sharpe_ratio(win(candidate), 0.0, TD)
print(f"\n=== MBL (N={N}, {yrs:.1f}y): Sharpe bar {mbl:.3f}; candidate Sharpe {ksh:.3f} → {'CLEARS' if ksh > mbl else 'FAILS'} ===")

passed = g_sortino and g_wealth and g_2022
print(f"\n=== VERDICT: {'PASS — rescue clears all frozen gates (user-decision spec-change candidate)' if passed else 'REFUTED — family closes with evidence (N=2 exhausted)'} ===")
print(f"  ΔSortino ci_low>0 {g_sortino} | Δwealth ci_low>0 {g_wealth} | 2022 no-degrade {g_2022}")

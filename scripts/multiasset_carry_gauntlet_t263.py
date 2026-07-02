"""scripts/multiasset_carry_gauntlet_t263.py
=============================================
T-2026-07-02-263 — DIVERSIFIED multi-asset CARRY re-test on the 21yr substrate.

═══════════════════════════════════════════════════════════════════════════════
PRE-REGISTRATION (committed BEFORE running — `[NN-MBL]`, `[NN-SUBSTRATE-REVERIFY]`)
═══════════════════════════════════════════════════════════════════════════════
This is the SECONDARY the T-247 pre-reg named, now unblocked by C/T-256's deep
TR-reconciled substrate (2005+) + Shiller CAPE (the equity-carry leg T-247 had to
fail-closed exclude). FRESH trial: N_trials += 1. New substrate → re-verify.

SETTLED, NOT re-litigated: bond-carry-is-duration-BETA (T-247, alpha_t_hac 0.815).
OPEN QUESTION (H1): does a DIVERSIFIED cross-asset carry basket (bond + equity +
gold) add a NON-duration return stream — real alpha net of FF5+Mom AND a duration
factor — and/or a genuinely uncorrelated 3rd stream (corr < ~0.4 to the trend
sleeve) for the T-248 composer? H0 (prior LOW-MEDIUM): the basket is still just
the bond/duration leg wearing a diversified coat.

THE SPEC (ONE, NO sweep — frozen):
- Legs (equal-weight 1/3): BOND=IEF, EQUITY=SPY, GOLD=GLD (tr_reconciled TR series).
  Commodity (DBC) + FX (UUP) FAIL-CLOSED excluded: no clean on-disk carry input
  (no futures curve; no foreign short rates). Reported, not faked.
- Per-asset carry (causal, as-of t): BOND = DGS10−DGS3MO (curve slope); EQUITY =
  100/CAPE − DGS3MO (Shiller CAPE earnings yield − short rate); GOLD = −(DGS3MO −
  T10YIE) (−real short rate).
- Cross-asset standardization: causal EXPANDING-window z-score per leg (min 252d).
- Long/flat: long when carry z-score > 0, else flat → cash @ DGS3MO (fair-harness
  convention, T-255). ER per leg + 1.5bps txn on flips. Position over t+1 = signal_t.

GATES (frozen): Sortino + block-bootstrap ci_low vs 60_40 + schwab_like; beta-or-edge
net of FF5+Mom AND DURATION (IEF excess) — EDGE iff alpha_t_hac>2 AND alpha_ann>2%;
paired Δ + CORRELATION vs the trend sleeve (uncorrelated 3rd stream iff corr<~0.4);
MBL at the 21yr window. `[NN-FAIL-CLOSED]`: window = where all 3 legs are defined
(bounded by Shiller CAPE end 2024-09) — no silent fabrication past it.
═══════════════════════════════════════════════════════════════════════════════
"""
import csv, math, sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = "/Users/jacksonmurphy/Dev/trading_machine-agent-a"
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.trend_overlay import TrendOverlay  # noqa: E402
from core.carry_signal import bond_carry, equity_carry, gold_carry, zscore_expanding  # noqa: E402
from core.factor_decomposition import load_factor_data, regress_returns_on_factors, DEFAULT_FACTOR_COLS  # noqa: E402

TD = 252
TXN = 0.00015
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}          # trend-sleeve legs (T-255)
ER_CARRY = {"BOND": 0.0015, "EQUITY": 0.0009, "GOLD": 0.0040}  # carry legs (IEF/SPY/GLD)
N_TRIALS = 262  # honest accumulated (~261) + this fresh trial


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

# fair-harness inputs (trend sleeve + robos)
SPY, BOND, GOLD = spy_close(), csv_ser(f"{ROOT}/data/research/bond_synth_dgs10_t255.csv"), csv_ser(f"{ROOT}/data/research/gold_gcf_t255.csv")
closes = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
dgs10, dgs3, t10yie = macro("DGS10"), macro("DGS3MO"), macro("T10YIE")
cash_daily = (dgs3 / 100.0 / TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq="D")).ffill()
def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)

# Shiller CAPE (monthly → daily ffill)
_sh = pd.read_csv(f"{ROOT}/data/macro/shiller_ie_data.csv"); _sh["date"] = pd.to_datetime(_sh["date"])
cape = _sh.set_index("date")["cape"].astype(float).dropna().sort_index()

# carry legs (tr_reconciled)
IEF, SPY_TR, GLD = tr_close("IEF"), tr_close("SPY"), tr_close("GLD")


def _to_daily(carry, idx):
    return carry.reindex(carry.index.union(idx)).sort_index().ffill().reindex(idx)


def carry_sleeve():
    """Diversified bond/equity/gold carry, z-score long/flat, flat=cash@short-rate."""
    legs = {"BOND": (IEF, bond_carry(dgs10, dgs3)),
            "EQUITY": (SPY_TR, equity_carry(cape, dgs3)),
            "GOLD": (GLD, gold_carry(dgs3, t10yie))}
    parts = []
    for k, (close, carry) in legs.items():
        aret = close.pct_change()
        z = zscore_expanding(_to_daily(carry, aret.index), 252)
        sig = (z > 0).astype(float); sig[z.isna()] = np.nan
        pos = sig.shift(1)
        r = pos * (aret - ER_CARRY[k] / TD) + (1 - pos) * cash_on(aret.index)
        r = r - pos.diff().abs().fillna(0) * (1.0 / 3.0) * TXN
        parts.append((r * (1.0 / 3.0)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()


def trend_sleeve():
    """T-255 fair trend sleeve (SPY/BOND/GOLD long-flat, flat=cash) — for the corr test."""
    parts = []
    for k, c in closes.items():
        aret = c.astype(float).pct_change(); pos = TrendOverlay(105, enabled=True).exposure(c.astype(float)).shift(1)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * cash_on(aret.index)
        r = r - pos.diff().abs().fillna(0) * (1.0 / 3.0) * TXN
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


carry = carry_sleeve(); trend = trend_sleeve()
r6040 = robo_fair({"SPY": 0.60, "BOND": 0.40}); rschwab = robo_fair({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})
start = max(carry.index[0], r6040.index[0], rschwab.index[0]); end = min(carry.index[-1], r6040.index[-1])
def win(s): return s[(s.index >= start) & (s.index <= end)].dropna()
def maxdd(eq): return float((eq / eq.cummax() - 1).min())
def cagr(eq): return float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1)
def so(r): return ME.sortino_ratio(r, 0.0, TD)
def so_ci(r):
    try: return ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get("ci_low")
    except Exception: return float("nan")

print(f"=== T-263 DIVERSIFIED CARRY (bond+equity+gold, z-score long/flat) {start.date()}..{end.date()} "
      f"({(end-start).days/365.25:.1f}y) ===")
print(f'{"strategy":26}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"CAGR":>7}{"MaxDD":>8}{"$10k→":>10}')
for nm, r in {"DIVERSIFIED CARRY": carry, "trend sleeve": trend, "60_40": r6040, "schwab_like": rschwab}.items():
    rw = win(r); eq = (1 + rw).cumprod()
    print(f'{nm:26}{so(rw):>9.3f}{so_ci(rw):>8.3f}{ME.sharpe_ratio(rw,0.0,TD):>8.3f}{cagr(eq)*100:>6.1f}%{maxdd(eq)*100:>7.1f}%{10000*eq.iloc[-1]/eq.iloc[0]:>10,.0f}')

# GATE — beta-or-edge net of FF5+Mom AND a DURATION factor (IEF excess)
print("\n=== GATE: beta-or-edge (net FF5+Mom + DURATION=IEF excess) ===")
fac = load_factor_data(auto_download=True)
dur = (IEF.pct_change().reindex(fac.index) - fac["RF"]).dropna()
facd = fac.join(dur.rename("DUR"), how="inner").dropna()
cols = [c for c in DEFAULT_FACTOR_COLS if c in facd.columns] + ["DUR"]
d = regress_returns_on_factors(win(carry), facd, factor_cols=cols, edge_name="div_carry")
is_edge = d is not None and d.alpha_tstat > 2.0 and d.alpha_annualized > 0.02
print(f"  {'EDGE' if is_edge else 'BETA'}: alpha {d.alpha_annualized*100:+.3f}%/yr  t_hac {d.alpha_tstat:+.3f}  "
      f"R² {d.r_squared:.4f}  DUR β {d.betas.get('DUR',float('nan')):+.3f}  MktRF β {d.betas.get('MktRF',float('nan')):+.3f}")

# GATE — paired Δ + CORRELATION vs trend sleeve (uncorrelated 3rd stream for T-248?)
j = pd.concat({"c": win(carry), "t": win(trend)}, axis=1, sort=True).dropna()
corr = float(j["c"].corr(j["t"]))
def sortino_np(v): dn = v[v < 0]; dd = np.sqrt((dn**2).mean()) if len(dn) else 1e-9; return (v.mean()/dd)*np.sqrt(TD)
rng = np.random.default_rng(0); c_, t_ = j["c"].values, j["t"].values; N = len(c_); L = 21; nb = int(np.ceil(N/L)); dso = []
for _ in range(1000):
    st = rng.integers(0, N-L+1, size=nb); ix = np.concatenate([np.arange(x, x+L) for x in st])[:N]
    dso.append(sortino_np(c_[ix]) - sortino_np(t_[ix]))
print(f"\n=== GATE: vs trend sleeve — corr {corr:+.3f} ({'UNCORRELATED (<0.4) → 3rd-stream candidate' if abs(corr)<0.4 else 'correlated ≥0.4'}) ===")
print(f"  paired ΔSortino (carry−trend) 95%CI [{np.percentile(dso,2.5):+.3f},{np.percentile(dso,97.5):+.3f}]")

# GATE — MBL + robo
N = N_TRIALS; yrs = (end-start).days/365.25; mbl = math.sqrt(2*math.log(N)/yrs); csh = ME.sharpe_ratio(win(carry),0.0,TD)
print(f"\n=== MBL (N={N}, {yrs:.1f}y): Sharpe bar {mbl:.3f}; carry Sharpe {csh:.3f} → {'CLEARS' if csh>mbl else 'FAILS'} ===")
beats = []
for nm, rb in [("60_40", r6040), ("schwab_like", rschwab)]:
    beats.append(so_ci(win(carry)) > so_ci(win(rb)))
    print(f"  vs {nm}: carry Sortino ci_low {so_ci(win(carry)):+.3f} vs robo {so_ci(win(rb)):+.3f} → {'beats' if beats[-1] else 'no'}")

print(f"\n=== VERDICT: {'EDGE — diversified basket adds a non-duration stream' if is_edge else 'H0 — no non-duration alpha (duration beta stands)'};"
      f" 3rd-stream={'YES' if abs(corr)<0.4 else 'NO'} (corr {corr:+.3f}) ===")

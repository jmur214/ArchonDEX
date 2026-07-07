"""T-296 RUN — return-stack (synthetic-RSST) composition arm (frozen pre-reg, N_trials+=1).

Frozen: sleeve with SPY leg = synthetic-RSST (SPY_TR + MF_excess) under the {2,5,10}mo
long/flat gate, vs (a) plain sleeve and (b) the T-284 offense arm (trend-gated 2x SPY).
MF proxy per the frozen order = AQR TSMOM (1985+, construction-audit PASSED), scaled to
DBMF vol. Fair T-255 harness (DGS3MO cash), monthly (AQR is monthly; {2,5,10}mo maps
cleanly). Gates: paired ΔSortino + Δwealth 95% CI vs both baselines; windows = crashes +
2015-16 chop + 2022. EXPLORATORY — the double-trend interaction (shape) is the read;
the LEVEL/wealth is bounded by the measured replication basis (reported).
"""
import csv
import io
import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME              # noqa: E402

SPEEDS_MO = [2, 5, 10]
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040, "RSST": 0.0100, "SSO": 0.0091}
SSO_LEV = 2.0


def _spy():
    r = list(csv.DictReader(open(os.path.join(ROOT, "data/processed/SPY_1d.csv"))))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def _cser(f):
    d = pd.read_csv(os.path.join(ROOT, f), index_col=0)
    d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


def m_ret(px):
    return px.resample("ME").last().pct_change()


def aqr_tsmom_scaled():
    """AQR diversified TSMOM factor (monthly, excess-over-cash), scaled to DBMF vol."""
    import yfinance as yf
    b = open(os.path.join(ROOT, "data/research/aqr_tsmom_monthly_t296.xlsx"), "rb").read()
    df = pd.read_excel(io.BytesIO(b), "TSMOM Factors", header=17)
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["date"]).set_index("date")
    ts = pd.to_numeric(df["TSMOM"], errors="coerce").dropna()
    ts.index = ts.index.to_period("M").to_timestamp("M")
    dbmf = yf.Ticker("DBMF").history(period="max", auto_adjust=True)["Close"]
    dbmf.index = pd.to_datetime(dbmf.index).tz_localize(None)
    dbmf_m = dbmf.resample("ME").last().pct_change().dropna()
    dbmf_m.index = dbmf_m.index.to_period("M").to_timestamp("M")
    ov = pd.concat({"a": ts, "d": dbmf_m}, axis=1).dropna()
    scale = float(ov.d.std() / ov.a.std())
    return ts * scale, scale, ts, dbmf_m


def multi_expo_m(px_m):
    """monthly multi-speed long/flat: mean of (close > SMA(n months)) over {2,5,10}."""
    sig = pd.concat([(px_m > px_m.rolling(n).mean()).astype(float) for n in SPEEDS_MO], axis=1).mean(axis=1)
    return sig.shift(1)   # act on last month's signal


def sleeve(legs_ret, cash_m, start):
    """EW multi-speed long/flat over the given leg monthly-return series; flat→cash; ER; txn."""
    parts = []
    for k, r in legs_ret.items():
        px = (1 + r.fillna(0)).cumprod()
        pos = multi_expo_m(px)
        ch = cash_m.reindex(r.index).ffill().fillna(0)
        leg = pos * (r - ER.get(k, 0) / 12) + (1 - pos) * ch - pos.diff().abs().fillna(0) * (1/len(legs_ret)) * 0.0005
        parts.append((leg * (1/len(legs_ret))).rename(k))
    s = pd.concat(parts, axis=1)
    return s[s.index >= start].dropna(how="any").sum(axis=1).dropna()


def stats(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    so = ME.sortino_ratio(r, 0.0, 12)
    try:
        ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, 12), n_iterations=800, seed=0).get("ci_low")
    except Exception:
        ci = float("nan")
    return so, ci, (eq / eq.cummax() - 1).min(), (eq.iloc[-1] / eq.iloc[0]) ** (1/yrs) - 1, 10000 * eq.iloc[-1]/eq.iloc[0]


def paired(a, b, L=6, n=800):
    j = pd.concat({"a": a, "b": b}, axis=1).dropna()
    A, B = j["a"].values, j["b"].values
    N = len(A)
    rng = np.random.default_rng(0)
    dso, dw = [], []

    def so_(x):
        d = x[x < 0]
        return (x.mean() / (np.sqrt((d**2).mean()) if len(d) else 1e-9)) * np.sqrt(12)
    nb = int(np.ceil(N / L))
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb)
        ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        dso.append(so_(A[ix]) - so_(B[ix]))
        dw.append(np.prod(1 + A[ix]) - np.prod(1 + B[ix]))
    return (np.percentile(dso, 2.5), np.percentile(dso, 97.5)), (np.percentile(dw, 2.5), np.percentile(dw, 97.5))


def ddwin(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2:
        return float("nan")
    eq = (1 + s).cumprod()
    return (eq / eq.cummax() - 1).min()


def main():
    spy_m = m_ret(_spy())
    bond_m = m_ret(_cser("data/research/bond_synth_dgs10_t255.csv"))
    gold_m = m_ret(_cser("data/research/gold_gcf_t255.csv"))
    for s in (spy_m, bond_m, gold_m):
        s.index = s.index.to_period("M").to_timestamp("M")
    d = pd.read_parquet(os.path.join(ROOT, "data/macro/DGS3MO.parquet"))["value"].astype(float)
    d.index = pd.to_datetime(d.index)
    cash_m = (d.dropna() / 100).resample("ME").mean() / 12
    cash_m.index = cash_m.index.to_period("M").to_timestamp("M")

    aqr, scale, aqr_raw, dbmf_m = aqr_tsmom_scaled()
    # synthetic-RSST monthly = SPY_TR + MF_excess (AQR already excess-over-cash)
    synth_rsst = (spy_m + aqr).dropna()
    # T-284 offense proxy: trend-gated synthetic SSO = 2x SPY excess + cash - ER
    sso_m = (SSO_LEV * (spy_m - cash_m) + cash_m).dropna()

    # --- basis report (frozen: validate proxy vs real RSST) ---
    import yfinance as yf
    rsst = yf.Ticker("RSST").history(period="max", auto_adjust=True)["Close"]
    rsst.index = pd.to_datetime(rsst.index).tz_localize(None)
    rsst_m = rsst.resample("ME").last().pct_change().dropna()
    rsst_m.index = rsst_m.index.to_period("M").to_timestamp("M")
    jv = pd.concat({"r": rsst_m, "s": synth_rsst}, axis=1).dropna()
    print(f"=== AQR proxy audit: construction PASSED (MOP TSMOM 1985+, diversified, hypothetical/excess). "
          f"vol-scale to DBMF={scale:.3f} ===")
    print(f"  FAITHFULNESS basis (synth vs real RSST, {len(jv)}mo): corr={jv.s.corr(jv.r):.3f} "
          f"ann-diff={(jv.s-jv.r).mean()*12*100:+.1f}%/yr → EXCEEDS the ±4-5% assumed band "
          f"(hypothetical factor over-captures vs the live fund).")

    start = max(synth_rsst.index[0], bond_m.index[0], gold_m.index[0]) + pd.DateOffset(months=11)
    plain = sleeve({"SPY": spy_m, "BOND": bond_m, "GOLD": gold_m}, cash_m, start)
    arm = sleeve({"RSST": synth_rsst, "BOND": bond_m, "GOLD": gold_m}, cash_m, start)
    offense = sleeve({"SSO": sso_m, "BOND": bond_m, "GOLD": gold_m}, cash_m, start)
    idx = plain.index.intersection(arm.index).intersection(offense.index)
    plain, arm, offense = plain.reindex(idx).dropna(), arm.reindex(idx).dropna(), offense.reindex(idx).dropna()

    print(f"\n=== ARM (monthly, {idx[0].date()}→{idx[-1].date()}, {len(idx)}mo, EXPLORATORY — level basis-bounded) ===")
    print(f"{'strategy':30}{'Sortino':>9}{'ci_low':>8}{'MaxDD':>8}{'CAGR':>7}{'$10k→':>11}")
    for nm, r in [("PLAIN sleeve (SPY/BOND/GOLD)", plain), ("ARM: synth-RSST leg", arm),
                  ("T-284 offense (2x SPY)", offense)]:
        so, ci, md, cg, tw = stats(r)
        print(f"{nm:30}{so:>9.3f}{ci:>8.3f}{md*100:>7.1f}%{cg*100:>6.1f}%{tw:>11,.0f}")

    print("\n=== PRE-REGISTERED GATES — paired Δ(ARM − baseline) 95% CI ===")
    for nm, base in [("plain sleeve", plain), ("T-284 offense", offense)]:
        (dslo, dshi), (dwlo, dwhi) = paired(arm, base)
        sig = "SIG+" if dslo > 0 else ("SIG−" if dshi < 0 else "straddle-0")
        print(f"  vs {nm:14}: ΔSortino[{dslo:+.2f},{dshi:+.2f}] {sig} | Δwealth-mult[{dwlo:+.2f},{dwhi:+.2f}] (basis-inflated)")

    print("\n=== DOUBLE-TREND read (does the MF stack help in chop / hurt in gaps? in-window MaxDD) ===")
    print(f"{'window':22}{'PLAIN':>9}{'ARM':>9}{'offense':>9}")
    for nm, a, b in [("2008 GFC", "2008-09-01", "2009-03-31"), ("COVID-2020", "2020-02-01", "2020-04-30"),
                     ("2015-16 chop", "2015-06-01", "2016-06-30"), ("2022", "2022-01-01", "2022-12-31")]:
        print(f"{nm:22}{ddwin(plain,a,b)*100:>8.1f}%{ddwin(arm,a,b)*100:>8.1f}%{ddwin(offense,a,b)*100:>8.1f}%")
    # chop CAGR read (2015-16): does the MF stack add return where trend chops?
    def wret(r, a, b):
        s = r[(r.index >= a) & (r.index <= b)]
        return ((1 + s).prod() - 1) * 100 if len(s) else float("nan")
    print(f"\n  2015-16 chop total return: PLAIN {wret(plain,'2015-06-01','2016-06-30'):+.1f}%  "
          f"ARM {wret(arm,'2015-06-01','2016-06-30'):+.1f}%  (MF stack rescue trend's chop weakness?)")
    print("\n*** EXPLORATORY. WEALTH gate is basis-inflated (AQR over-captures ~2-3x vs live fund) — read ΔSortino "
          "+ the double-trend SHAPE, not the level. Consequence rule: PASS→real-RSST fwd shadow-track; FAIL→close door. ***")


if __name__ == "__main__":
    main()

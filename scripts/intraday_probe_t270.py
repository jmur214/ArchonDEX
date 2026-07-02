"""scripts/intraday_probe_t270.py — the ONE intraday probe (FROZEN pre-reg T-270).
================================================================================
Executes docs/Audit/intraday_probe_preregistration_t270_2026_07_02.md EXACTLY.
PRIMARY: Gao intraday momentum (long-only). SECONDARY: ORB long-only 1x. SPY SIP
minute 2016-2026 → daily aggregates (cached). Frictions: 2.5bps/side, cash-account
~50% deployment, post-2018 OOS. Gates vs both robos AND the trend sleeve + MBL.
Reuses the T-150 minute-aggregation approach (SIP feed, not IEX).
"""
import csv, math, sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/jacksonmurphy/Dev/trading_machine-agent-a")
sys.path.insert(0, str(ROOT))
from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.trend_overlay import TrendOverlay  # noqa: E402

TD = 252
MAIN_ENV = "/Users/jacksonmurphy/Dev/trading_machine-2/.env"
CACHE = ROOT / "data" / "research" / "intraday_t270" / "SPY_daily.parquet"
COST = 0.00025          # 2.5 bps/side (frozen)
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
TXN = 0.00015


def _keys():
    from dotenv import dotenv_values
    v = dotenv_values(MAIN_ENV)
    return (v.get("APCA_API_KEY_ID") or v.get("ALPACA_API_KEY"),
            v.get("APCA_API_SECRET_KEY") or v.get("ALPACA_SECRET_KEY"))


def _orb_day(g, or_hi, or_lo):
    """Long-only 1x ORB return for one day's post-10:00 bars (sorted). Enter long at
    or_hi on the first bar whose high≥or_hi; stop at or_lo; else exit 16:00 close."""
    post = g[g["t"] >= 600]
    if post.empty or not np.isfinite(or_hi):
        return 0.0
    entered = False
    for _, b in post.iterrows():
        if not entered and b["high"] >= or_hi:
            entered = True
            continue                       # entered at or_hi; check stop on later bars
        if entered and b["low"] <= or_lo:
            return or_lo / or_hi - 1.0      # stopped
    if entered:
        return float(post.iloc[-1]["close"]) / or_hi - 1.0   # exit 16:00 close
    return 0.0


def fetch_daily() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import DataFeed
    key, sec = _keys(); client = StockHistoricalDataClient(key, sec)
    rows = []
    for y in range(2016, 2027):
        try:
            req = StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Minute,
                                   start=datetime(y, 1, 1), end=datetime(y, 12, 31),
                                   feed=DataFeed.SIP)
            df = client.get_stock_bars(req).df
        except Exception as e:
            print(f"[T270] WARN {y}: {type(e).__name__}: {e}", flush=True); continue
        if df is None or df.empty:
            continue
        df = df.reset_index()
        ts = pd.to_datetime(df["timestamp"]).dt.tz_convert("America/New_York")
        df["d"] = ts.dt.normalize().dt.tz_localize(None); df["t"] = ts.dt.hour * 60 + ts.dt.minute
        for d, g in df.groupby("d"):
            g = g.sort_values("t"); f30 = g[(g["t"] >= 570) & (g["t"] < 600)]
            reg = g[(g["t"] >= 570) & (g["t"] < 960)]
            if f30.empty or reg.empty:
                continue
            b1000 = g[g["t"] >= 600]; b1530 = g[g["t"] >= 930]
            or_hi, or_lo = f30["high"].max(), f30["low"].min()
            rows.append({"d": d, "day_close": reg.iloc[-1]["close"],
                         "p_1000": b1000.iloc[0]["open"] if not b1000.empty else np.nan,
                         "p_1530": b1530.iloc[0]["open"] if not b1530.empty else np.nan,
                         "p_1600": reg.iloc[-1]["close"],
                         "or_hi": or_hi, "or_lo": or_lo,
                         "orb_ret": _orb_day(g, or_hi, or_lo)})
        print(f"[T270] {y}: {len([r for r in rows if r['d'].year==y])} days", flush=True)
    out = pd.DataFrame(rows).set_index("d").sort_index()
    out["prev_close"] = out["day_close"].shift(1)
    out["r_first"] = out["p_1000"] / out["prev_close"] - 1.0          # Gao predictor (vs prior close)
    out["last30"] = out["p_1600"] / out["p_1530"] - 1.0              # Gao target (15:30→16:00)
    CACHE.parent.mkdir(parents=True, exist_ok=True); out.to_parquet(CACHE)
    return out


def cross_check(daily):
    """Sanity-bound the SIP first-30min extremes vs Stooq daily H/L on a sample."""
    try:
        sp = pd.read_csv(ROOT / "data" / "processed" / "SPY_1d.csv"); sp["Date"] = pd.to_datetime(sp["Date"])
        sp = sp.set_index("Date")
        rng = np.random.default_rng(0); samp = daily.dropna(subset=["or_hi", "or_lo"]).sample(min(15, len(daily)), random_state=0)
        bad = 0
        for d, r in samp.iterrows():
            if d in sp.index:
                dh, dl = sp.loc[d, "High"], sp.loc[d, "Low"]
                if r["or_hi"] > dh * 1.005 or r["or_lo"] < dl * 0.995:  # OR must sit within the day's range
                    bad += 1
        print(f"[cross-check] {len(samp)}-day sample: {bad} OR-extremes outside daily H/L bound "
              f"→ {'PASS' if bad == 0 else 'FLAG'}")
    except Exception as e:
        print(f"[cross-check] skipped: {e}")


# ── fair-harness robos + trend sleeve (for the gauntlet) ──────────────────────
def _csv(f): d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index); return d.iloc[:, 0].astype(float).sort_index()
def _macro(s): d = pd.read_parquet(ROOT / "data" / "macro" / f"{s}.parquet")["value"].astype(float); d.index = pd.to_datetime(d.index); return d.dropna().sort_index()
SPY = pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in csv.DictReader(open(ROOT / "data/processed/SPY_1d.csv"))}).sort_index()
BOND, GOLD = _csv(ROOT / "data/research/bond_synth_dgs10_t255.csv"), _csv(ROOT / "data/research/gold_gcf_t255.csv")
closes = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
dgs3 = _macro("DGS3MO"); cash_daily = (dgs3 / 100.0 / TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq="D")).ffill()
def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)

def trend_sleeve():
    parts = []
    for k, c in closes.items():
        aret = c.astype(float).pct_change(); pos = TrendOverlay(105, enabled=True).exposure(c.astype(float)).shift(1)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * cash_on(aret.index) - pos.diff().abs().fillna(0) * (1 / 3) * TXN
        parts.append((r * (1 / 3)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()

def robo(weights):
    etfs = [k for k in weights if k != "_cash"]; cw = weights.get("_cash", 0.0)
    rets = pd.concat({k: closes[k].pct_change() - ER[k] / TD for k in etfs}, axis=1, sort=True).dropna()
    cr = cash_daily.reindex(rets.index).ffill().fillna(0.0); hold = {k: weights[k] for k in etfs}; cash = cw; out = {}; pm = None
    for dt, row in rets.iterrows():
        m = (dt.year, dt.month); rc = 0.0
        if pm is not None and m != pm:
            tot = sum(hold.values()) + cash; nh = {k: tot * weights[k] for k in etfs}; nc = tot * cw
            rc = sum(abs(nh[k] - hold[k]) for k in etfs) / max(tot, 1e-9) * TXN; hold = nh; cash = nc
        prev = sum(hold.values()) + cash
        for k in etfs: hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt]); out[dt] = (sum(hold.values()) + cash) / prev - 1 - rc; pm = m
    return pd.Series(out)


def realized(active_gross, active_mask, idx):
    """Frozen frictions: active day → 0.5·(gross−cost) + 0.5·cash; flat day → cash."""
    ch = cash_on(idx)
    net = active_gross - active_mask * COST * 2          # round-trip cost on active days
    return (active_mask * (0.5 * net + 0.5 * ch) + (1 - active_mask) * ch)


def stats(r):
    rw = r.dropna(); eq = (1 + rw).cumprod()
    try: ci = ME.bootstrap_distribution(rw, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get("ci_low")
    except Exception: ci = float("nan")
    return (ME.sortino_ratio(rw, 0.0, TD), ci, ME.sharpe_ratio(rw, 0.0, TD),
            float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1),
            float((eq / eq.cummax() - 1).min()))


def main():
    daily = fetch_daily()
    print(f"[T270] SPY daily intraday features: {len(daily)} days {daily.index.min().date()}..{daily.index.max().date()}")
    cross_check(daily)
    dd = daily.dropna(subset=["r_first", "last30", "orb_ret"]).copy()

    # PRIMARY Gao: active when r_first>0, gross = last30 (15:30→16:00)
    gao_active = (dd["r_first"] > 0).astype(float)
    gao = realized(dd["last30"].fillna(0.0), gao_active, dd.index)
    # SECONDARY ORB: active when a breakout return != 0 (upside breakout occurred)
    orb_active = (dd["orb_ret"] != 0).astype(float)
    orb = realized(dd["orb_ret"].fillna(0.0), orb_active, dd.index)

    trend = trend_sleeve(); r6040 = robo({"SPY": 0.60, "BOND": 0.40}); rsch = robo({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})
    for label, lo in [("FULL 2016-2026", dd.index.min()), ("POST-2018 OOS", pd.Timestamp("2018-01-01"))]:
        w = lambda s: s[(s.index >= lo) & (s.index <= dd.index.max())].dropna()
        print(f"\n=== {label} ({(dd.index.max()-lo).days/365.25:.1f}y, gao active {gao_active[gao_active.index>=lo].mean():.0%} of days) ===")
        print(f'{"strategy":26}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"CAGR":>7}{"MaxDD":>8}')
        rows = {"Gao momentum (net,cash-acct)": gao, "ORB 1x (net,cash-acct)": orb,
                "trend sleeve": trend, "60_40": r6040, "schwab_like": rsch}
        S = {}
        for nm, r in rows.items():
            so, ci, sh, cg, md = stats(w(r)); S[nm] = (so, ci)
            print(f'{nm:26}{so:>9.3f}{ci:>8.3f}{sh:>8.3f}{cg*100:>6.1f}%{md*100:>7.1f}%')
        if label == "POST-2018 OOS":
            g_so, g_ci = S["Gao momentum (net,cash-acct)"]
            beats = g_ci > S["trend sleeve"][1] and g_ci > S["60_40"][1] and g_ci > S["schwab_like"][1]
            yrs = (dd.index.max() - lo).days / 365.25; mbl = math.sqrt(2 * math.log(263) / yrs)
            gsh = ME.sharpe_ratio(w(gao), 0.0, TD)
            print(f"  MBL (N=263, {yrs:.1f}y): bar {mbl:.3f}; Gao Sharpe {gsh:.3f} → {'CLEARS' if gsh > mbl else 'FAILS'}")
            print(f"\n=== VERDICT: {'SOMETHING SURVIVES — escalate' if (g_ci > 0 and beats) else 'INTRADAY CLOSES WITH EVIDENCE (H0)'} "
                  f"(Gao ci_low {g_ci:+.3f}, beats robos+sleeve={beats}) ===")


if __name__ == "__main__":
    main()

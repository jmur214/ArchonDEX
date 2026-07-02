"""
scripts/asymmetric_exits_gauntlet_t269.py
=========================================
T-2026-07-02-269 — asymmetric EXITS gauntlet (the "when to sell" trader skill).
Runs the FROZEN pre-registration (docs/Audit/asymmetric_exits_prereg_t269...md).

Entry (a boring trigger): new 252d-high breakout on PIT S&P 500 members (survivor-
free). Exit (THE HYPOTHESIS): Chandelier trailing stop = highest-close-since-entry
− 3·ATR(22), no profit target; force-exit on PIT removal. 5%/position, max 20
concurrent, cash @ short rate, 3bps/side. FROZEN — no sweep.

Gates: per-trade + daily SKEW; Sortino + block-bootstrap ci_low vs both robos;
is_it_beta_or_edge (FF5+Mom HAC kill-test); paired vs the fair trend sleeve; MBL.

Output: data/research/t269/exits_gauntlet.json + table.
Usage: python -m scripts.asymmetric_exits_gauntlet_t269
"""
from __future__ import annotations

import csv
import glob
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.trend_overlay import TrendOverlay  # noqa: E402
from engines.data_manager.membership import load_membership  # noqa: E402
from engines.engine_b_risk.factor_analysis import FactorRiskModel  # noqa: E402

TD = 252
HIGH_N, ATR_N, K = 252, 22, 3.0     # FROZEN
POS_W, MAX_POS = 0.05, 20           # FROZEN
COST = 0.0003                       # 3 bps/side
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
TXN_SLV = 0.00015
OUT = ROOT / "data" / "research" / "t269" / "exits_gauntlet.json"


def _load_close_hlc(tkr):
    try:
        d = pd.read_csv(ROOT / f"data/processed/{tkr}_1d.csv", index_col=0, parse_dates=True)
        if not {"Close", "High", "Low"} <= set(d.columns) or len(d) < HIGH_N + ATR_N + 5:
            return None
        return d[["Close", "High", "Low"]].astype(float)
    except Exception:
        return None


def _name_trades(d: pd.DataFrame, member: pd.Series):
    """State machine → list of (entry_i, exit_i) integer index positions + a
    per-bar in-position mask. Causal: signal at t → act at t+1; stop level from t−1."""
    c = d["Close"]; h = d["High"]; low = d["Low"]
    prevc = c.shift(1)
    tr = pd.concat([h - low, (h - prevc).abs(), (low - prevc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(ATR_N).mean()
    hi252 = c.rolling(HIGH_N).max().shift(1)          # prior-252 max (excludes t)
    breakout = (c > hi252) & atr.notna() & hi252.notna()
    mem = member.reindex(d.index).fillna(False).values
    C = c.values; A = atr.values; BO = breakout.values
    n = len(C)
    trades = []
    i = 0
    while i < n - 1:
        # enter at i+1 if breakout at i AND member at i AND (i+1) valid
        if BO[i] and mem[i]:
            e = i + 1
            hi_since = C[e]; trail_prev = C[e] - K * A[e]
            j = e
            while j < n - 1:
                hi_since = max(hi_since, C[j])
                trail = hi_since - K * A[j]
                # exit at j+1 if today's close breaks YESTERDAY's trail, or PIT-removed
                if C[j] < trail_prev or not mem[j]:
                    break
                trail_prev = trail
                j += 1
            trades.append((e, j))          # held from e..j (inclusive), exit at close j
            i = j + 1
        else:
            i += 1
    return trades


# ---- fair robos + sleeve (D's T-255 conventions; committed data) ----------- #
def _spy_close():
    r = list(csv.DictReader(open(ROOT / "data/processed/SPY_1d.csv")))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def _csv_ser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


def main() -> int:
    dgs3 = _csv_ser_macro = pd.read_parquet(ROOT / "data/macro/DGS3MO.parquet")["value"].astype(float)
    dgs3.index = pd.to_datetime(dgs3.index)
    cash_daily = (dgs3.dropna().sort_index() / 100.0 / TD)
    cash_daily = cash_daily.reindex(pd.date_range(cash_daily.index[0], cash_daily.index[-1], freq="D")).ffill()
    def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)

    # universe: PIT members ∩ have OHLC
    mem_df = load_membership()
    pit_tickers = set(mem_df["ticker"])
    have = {Path(f).name.replace("_1d.csv", "") for f in glob.glob(str(ROOT / "data/processed/*_1d.csv"))}
    names = sorted(pit_tickers & have)
    print(f"[T269] universe: {len(names)} PIT∩OHLC names")

    # per-name membership mask helper (interval → bool series on the name's index)
    by_t = mem_df.groupby("ticker")
    def member_mask(tkr, idx):
        s = pd.Series(False, index=idx)
        if tkr in by_t.groups:
            for _, row in by_t.get_group(tkr).iterrows():
                end = row["end"] if pd.notna(row["end"]) else idx[-1]
                s.loc[(idx >= row["start"]) & (idx <= end)] = True
        return s

    # collect per-name trades → global daily return contributions + per-trade returns
    trade_rets = []          # per-trade total return (for skew)
    # per-name: (entry_ts, exit_ts, daily_ret Series during hold incl. entry/exit costs)
    name_trade_streams = []
    for k, tkr in enumerate(names):
        d = _load_close_hlc(tkr)
        if d is None:
            continue
        mm = member_mask(tkr, d.index)
        for (e, j) in _name_trades(d, mm):
            seg = d["Close"].iloc[e:j + 1]
            if len(seg) < 2:
                continue
            r = seg.pct_change().dropna()          # daily returns while held (entry+1..exit)
            # entry cost on first held day, exit cost on last
            r.iloc[0] -= COST
            r.iloc[-1] -= COST
            name_trade_streams.append(r)
            trade_rets.append(float(seg.iloc[-1] / seg.iloc[0] - 1.0) - 2 * COST)

    # portfolio walk with the 20-cap (admit in chronological entry order)
    name_trade_streams.sort(key=lambda s: s.index[0])
    all_days = pd.DatetimeIndex(sorted(set().union(*[s.index for s in name_trade_streams])))
    active = []          # list of (end_ts, iterator over daily rets)
    contrib = pd.Series(0.0, index=all_days)
    nactive = pd.Series(0, index=all_days)
    # build a per-day map: date -> list of (return) for positions live that day, capped at 20 by entry order
    live = {}            # id -> Series
    admitted, nid = [], 0
    streams_by_start = {}
    for s in name_trade_streams:
        streams_by_start.setdefault(s.index[0], []).append(s)
    open_positions = []  # (end_ts, series)
    for day in all_days:
        # drop finished
        open_positions = [(end, s) for (end, s) in open_positions if end >= day]
        # admit new (entry == day) up to cap
        for s in streams_by_start.get(day, []):
            if len(open_positions) < MAX_POS:
                open_positions.append((s.index[-1], s))
        # today's contribution: 5% each active
        tot = 0.0; cnt = 0
        for (end, s) in open_positions:
            if day in s.index:
                tot += POS_W * float(s.loc[day]); cnt += 1
        contrib.loc[day] = tot; nactive.loc[day] = cnt
    cashfrac = (1.0 - POS_W * nactive).clip(lower=0.0)
    strat = (contrib + cashfrac * cash_on(all_days)).dropna()

    # ---- fair sleeve + robos ---- #
    SPY = _spy_close(); BOND = _csv_ser(ROOT / "data/research/bond_synth_dgs10_t255.csv"); GOLD = _csv_ser(ROOT / "data/research/gold_gcf_t255.csv")
    closes = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
    def sleeve():
        parts = []
        for kk, cc in closes.items():
            cc = cc.astype(float); ar = cc.pct_change(); pos = TrendOverlay(105, enabled=True).exposure(cc).shift(1)
            ch = cash_on(ar.index); r = pos * (ar - ER[kk] / TD) + (1 - pos) * ch
            r = r - pos.diff().abs().fillna(0) * (1 / 3) * TXN_SLV
            parts.append((r * (1 / 3)).rename(kk))
        return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()
    def robo(w):
        etfs = [k for k in w if k != "_cash"]; cw = w.get("_cash", 0.0)
        rets = pd.concat({k: closes[k].pct_change() - ER[k] / TD for k in etfs}, axis=1, sort=True).dropna()
        cr = cash_on(rets.index); hold = {k: w[k] for k in etfs}; cash = cw; out = {}; pm = None
        for dt, row in rets.iterrows():
            m = (dt.year, dt.month); rc = 0.0
            if pm is not None and m != pm:
                tot = sum(hold.values()) + cash; nh = {k: tot * w[k] for k in etfs}; nc = tot * cw
                rc = sum(abs(nh[k] - hold[k]) for k in etfs) / max(tot, 1e-9) * TXN_SLV; hold = nh; cash = nc
            prev = sum(hold.values()) + cash
            for k in etfs: hold[k] *= (1 + row[k])
            cash *= (1 + cr.loc[dt]); out[dt] = (sum(hold.values()) + cash) / prev - 1 - rc; pm = m
        return pd.Series(out)
    slv = sleeve(); r6040 = robo({"SPY": 0.6, "BOND": 0.4}); rsch = robo({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})

    # align window
    lo = max(strat.index[0], r6040.index[0]); hi = min(strat.index[-1], r6040.index[-1])
    W = lambda s: s[(s.index >= lo) & (s.index <= hi)].dropna()
    strat_w = W(strat)

    def maxdd(r): eq = (1 + r).cumprod(); return float((eq / eq.cummax() - 1).min())
    def so(r): return float(ME.sortino_ratio(r, 0.0, TD))
    def so_ci(r):
        try: return float(ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get("ci_low"))
        except Exception: return float("nan")
    def sk(a): a = np.asarray(a, float); a = a[np.isfinite(a)]; m = a.mean(); s = a.std(); return float(((a - m) ** 3).mean() / s ** 3) if s > 0 and len(a) > 2 else 0.0

    tr = np.array(trade_rets, float)
    report = {"task": "T-2026-07-02-269 asymmetric exits gauntlet",
              "frozen": {"high_n": HIGH_N, "atr_n": ATR_N, "k": K, "pos_w": POS_W, "max_pos": MAX_POS, "cost_bps": 3},
              "window": [str(lo.date()), str(hi.date())], "n_days": int(len(strat_w)),
              "n_trades": int(len(tr)),
              "skew": {"per_trade": round(sk(tr), 3), "daily": round(sk(strat_w.values), 3),
                       "trade_win_rate": round(float((tr > 0).mean()), 3),
                       "avg_win": round(float(tr[tr > 0].mean()) if (tr > 0).any() else 0.0, 4),
                       "avg_loss": round(float(tr[tr < 0].mean()) if (tr < 0).any() else 0.0, 4),
                       "best": round(float(tr.max()), 3), "worst": round(float(tr.min()), 3)},
              "strategies": {}}
    for nm, r in [("ASYM_EXITS", strat_w), ("trend_sleeve", W(slv)), ("60_40", W(r6040)), ("schwab_like", W(rsch))]:
        eq = (1 + r).cumprod()
        report["strategies"][nm] = {"sortino": round(so(r), 3), "sortino_ci_low": round(so_ci(r), 3),
                                    "sharpe": round(float(ME.sharpe_ratio(r, 0.0, TD)), 3),
                                    "cagr_pct": round((eq.iloc[-1] ** (365.25 / (r.index[-1] - r.index[0]).days) - 1) * 100, 2),
                                    "maxdd_pct": round(maxdd(r) * 100, 2)}

    # kill-test: is_it_beta_or_edge (FF5+Mom HAC)
    try:
        dec = FactorRiskModel().decompose(strat_w.rename("exits"), edge_name="asym_exits")
        report["beta_or_edge"] = {"verdict": dec.is_it_beta_or_edge() if dec else "n/a",
                                  "alpha_ann": round(dec.alpha_annualized, 4) if dec else None,
                                  "alpha_t_hac": round(dec.alpha_t_hac, 3) if dec else None,
                                  "market_beta": round(dec.betas.get("market", float("nan")), 3) if dec else None,
                                  "mom_beta": round(dec.betas.get("momentum", float("nan")), 3) if dec else None,
                                  "r2": round(dec.r2, 3) if dec else None}
    except Exception as e:
        report["beta_or_edge"] = {"error": f"{type(e).__name__}: {e}"}

    # paired vs sleeve
    def paired(a, b, L=21, n=1000):
        j = pd.concat({"a": a, "b": b}, axis=1, sort=True).dropna(); x, y = j["a"].values, j["b"].values; N = len(x)
        rng = np.random.default_rng(0); nb = int(np.ceil(N / L)); ds = []
        def sortino(v): d = v[v < 0]; dd = np.sqrt((d ** 2).mean()) if len(d) else 1e-9; return v.mean() / dd * np.sqrt(TD)
        for _ in range(n):
            st = rng.integers(0, N - L + 1, size=nb); ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
            ds.append(sortino(x[ix]) - sortino(y[ix]))
        return [round(float(np.percentile(ds, 2.5)), 3), round(float(np.percentile(ds, 97.5)), 3)], round(float(np.mean(np.array(ds) > 0)), 3)
    ci, pwin = paired(strat_w, W(slv))
    report["paired_vs_sleeve"] = {"dSortino_ci": ci, "P_exits_gt_sleeve": pwin}

    yrs = (hi - lo).days / 365.25; N_eff = 16
    report["mbl"] = {"years": round(yrs, 1), "n_eff": N_eff,
                     "sharpe_bar": round(math.sqrt(2 * math.log(N_eff) / yrs), 3),
                     "exits_sharpe": report["strategies"]["ASYM_EXITS"]["sharpe"]}

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))
    s = report["skew"]
    print(f"\nT-269 asymmetric exits — {report['window'][0]}..{report['window'][1]} ({report['n_days']}d, {report['n_trades']} trades)")
    print(f"SKEW: per-trade {s['per_trade']}  daily {s['daily']}  win-rate {s['trade_win_rate']}  "
          f"avgW {s['avg_win']} avgL {s['avg_loss']}  best {s['best']} worst {s['worst']}")
    print(f"{'strategy':16}{'Sortino':>9}{'ci_low':>8}{'Sharpe':>8}{'CAGR':>7}{'MaxDD':>8}")
    for nm, m in report["strategies"].items():
        print(f"{nm:16}{m['sortino']:>9.3f}{m['sortino_ci_low']:>8.3f}{m['sharpe']:>8.3f}{m['cagr_pct']:>6.1f}%{m['maxdd_pct']:>7.1f}%")
    boe = report["beta_or_edge"]
    print(f"beta_or_edge: {boe.get('verdict')}  alpha_ann {boe.get('alpha_ann')} (t_HAC {boe.get('alpha_t_hac')})  "
          f"mkt-β {boe.get('market_beta')} mom-β {boe.get('mom_beta')} R² {boe.get('r2')}")
    print(f"paired vs sleeve: ΔSortino 95%CI {report['paired_vs_sleeve']['dSortino_ci']}  P(exits>sleeve)={report['paired_vs_sleeve']['P_exits_gt_sleeve']:.0%}")
    print(f"MBL: {yrs:.0f}yr Sharpe bar {report['mbl']['sharpe_bar']}  exits Sharpe {report['mbl']['exits_sharpe']}")
    print(f"[T269] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

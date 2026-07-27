"""T-2026-07-27-311 — DEEP re-verify the trend sleeve on the T-306 multi-decade substrate.

Pre-registration (director-FROZEN 2026-07-27, caveats accepted-as-disclosed):
docs/Sources/prereg_deep_reverify_sleeve_t311.md. N_trials += 1 (ONE family).

Re-MEASURES the FROZEN deploying config — ensemble {42,105,210}, equal-weight,
long/flat, T-255 fair conventions — on the deep substrate. NOTHING is tuned.

  PRIMARY   D-A 2-asset (equity+bond), ~64yr — the honest deepest window.
  SECONDARY D-B 3-asset (equity+bond+gold), ~58yr — the deployed shape.

Baselines: schwab_like A (cash@mkt) / B (below-mkt sweep), 60/40, BUY-HOLD EQUITY.
Director ruling: report the paired Δwealth vs BUY-HOLD prominently — for a
confirmed won't-sell max-wealth user that column IS the verdict (the September
question is "robo → WHAT?", not "robo → sleeve?").

Fair conventions (verbatim T-255): ER charged when long AND on robo legs; 1.5bps
txn both sides; flat leg + robo _cash earn the short rate (FF RF daily).
Disclosed caveats (frozen-accepted): ETF-equivalent ERs on the pre-ETF segment are
anachronistic but CONSERVATIVE + symmetric; pre-1993 equity is broad-market TR
(not S&P-500) per T-306.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.metrics_engine import MetricsEngine as ME          # noqa: E402
from core.calendar_guard import assert_no_calendar_holes     # noqa: E402

SUB = ROOT / "data/research/substrate_multidecade"
OUT = ROOT / "data/research/t311_deep_reverify.json"
TD = 252
TXN = 0.00015                                   # 1.5 bps/side
ER = {"equity": 0.0009, "bond": 0.0003, "gold": 0.0040}      # T-255 ETF-equivalent
SPEEDS = [42, 105, 210]                         # the deployed ensemble — FROZEN
N_TRIALS = 76                                   # honest-N after this trial
# The independent crises the deep window spans (for the drawdown-structural test).
CRISES = {
    "1970": ("1969-11-01", "1970-07-01"), "1973-74 stagflation": ("1973-01-01", "1974-12-31"),
    "1980-82 Volcker": ("1980-11-01", "1982-08-31"), "1987 crash": ("1987-08-01", "1987-12-31"),
    "1990": ("1990-07-01", "1990-10-31"), "dotcom": ("2000-03-01", "2002-10-31"),
    "GFC": ("2007-10-01", "2009-03-31"), "COVID": ("2020-02-01", "2020-04-30"),
    "2022": ("2022-01-01", "2022-10-31"),
}


def _leg(name: str) -> pd.Series:
    s = pd.read_csv(SUB / f"{name}_tr_daily.csv", parse_dates=[0], index_col=0).iloc[:, 0]
    return s.sort_index()


def load_substrate(assets: list[str]) -> tuple[dict, pd.Series]:
    """TR index per leg + the daily cash rate, aligned onto the EQUITY calendar
    (legs carry native US-market/London calendars — reindex_onto is the T-255
    pattern; a forced common index would ffill-corrupt one leg on the other's
    holidays). calendar_guard asserted on the aligned frame."""
    legs = {a: _leg(a) for a in assets}
    cash = pd.read_csv(SUB / "cash_daily.csv", parse_dates=[0], index_col=0).iloc[:, 0].sort_index()
    cal = legs["equity"].index
    start = max(s.index.min() for s in legs.values())
    cal = cal[cal >= start]
    aligned = {a: s.reindex(cal).ffill() for a, s in legs.items()}
    frame = pd.DataFrame(aligned).dropna()
    assert_no_calendar_holes(frame.index, frame.index, benchmark_name="equity_calendar")
    return {a: frame[a] for a in assets}, cash.reindex(frame.index).ffill().fillna(0.0)


def ensemble_pos(px: pd.Series) -> pd.Series:
    """Mean of binary long/flat signals across the FROZEN speeds, lagged 1 day
    (causal — T-273). Long when price > its trailing mean over `speed` days."""
    sig = [(px > px.rolling(s).mean()).astype(float) for s in SPEEDS]
    return pd.concat(sig, axis=1).mean(axis=1).shift(1)


def sleeve_returns(legs: dict, cash: pd.Series) -> pd.Series:
    """EW long/flat sleeve; flat leg earns the short rate; ER when long; txn on flips."""
    n = len(legs)
    tot = None
    for name, px in legs.items():
        aret = px.pct_change()
        pos = ensemble_pos(px)
        r = pos * (aret - ER[name] / TD) + (1 - pos) * cash
        r = r - pos.diff().abs().fillna(0) * (1.0 / n) * TXN
        tot = r / n if tot is None else tot + r / n
    return tot.dropna()


def robo_returns(legs: dict, weights: dict, cash_rate: pd.Series) -> pd.Series:
    """Monthly-rebal; legs net of ER; _cash earns cash_rate; 1.5bps rebal cost."""
    etfs = [k for k in weights if k != "_cash"]
    cw = weights.get("_cash", 0.0)
    rets = pd.concat({k: legs[k].pct_change() - ER[k] / TD for k in etfs}, axis=1).dropna()
    cr = cash_rate.reindex(rets.index).ffill().fillna(0.0)
    hold = {k: weights[k] for k in etfs}
    cash, out, pm = cw, {}, None
    for dt, row in rets.iterrows():
        m, rebal_cost = (dt.year, dt.month), 0.0
        if pm is not None and m != pm:
            t = sum(hold.values()) + cash
            nh = {k: t * weights[k] for k in etfs}
            rebal_cost = sum(abs(nh[k] - hold[k]) for k in etfs) / max(t, 1e-9) * TXN
            hold, cash = nh, t * cw
        prev = sum(hold.values()) + cash
        for k in etfs:
            hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt])
        out[dt] = (sum(hold.values()) + cash) / prev - 1 - rebal_cost
        pm = m
    return pd.Series(out)


def buyhold_equity(legs: dict) -> pd.Series:
    return (legs["equity"].pct_change() - ER["equity"] / TD).dropna()


# --- metrics ---------------------------------------------------------------- #
def maxdd(eq): return float((eq / eq.cummax() - 1).min())
def cagr(eq): return float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1)
def sortino(r): return float(ME.sortino_ratio(r, 0.0, TD))
def sharpe(r): return float(ME.sharpe_ratio(r, 0.0, TD))


def ci_low_sortino(r):
    try:
        return float(ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD),
                                               n_iterations=1000, seed=0).get("ci_low"))
    except Exception:
        return float("nan")


def paired(sl: pd.Series, bl: pd.Series, L: int = 21, n: int = 1000) -> dict:
    """Paired block-bootstrap of sleeve − baseline: ΔSortino, Δwealth, ΔMaxDD."""
    j = pd.concat({"s": sl, "b": bl}, axis=1).dropna()
    s, b = j["s"].values, j["b"].values
    N = len(s)
    rng = np.random.default_rng(0)
    nb = int(np.ceil(N / L))
    dso, dtw, dmd = [], [], []

    def _sortino(x):
        d = x[x < 0]
        dd = np.sqrt((d ** 2).mean()) if len(d) else 1e-9
        return (x.mean() / dd) * np.sqrt(TD)

    def _mdd(x):
        eq = np.cumprod(1 + x)
        return float((eq / np.maximum.accumulate(eq) - 1).min())

    dcagr = []
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb)
        ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        ss, bb = s[ix], b[ix]
        dso.append(_sortino(ss) - _sortino(bb))
        dtw.append(np.prod(1 + ss) - np.prod(1 + bb))
        dmd.append(_mdd(ss) - _mdd(bb))
        # Δ COMPOUNDING RATE (annualized log-wealth) — the well-behaved wealth stat.
        # The raw Δterminal-wealth bootstrap is numerically DEGENERATE over a 60+yr
        # compounding window (terminal-multiple variance explodes → an uninformative
        # CI that must NOT be read as "a tie"). Mean log-return × 252 is the same
        # economic question (who compounds faster) with a stable sampling distribution.
        dcagr.append((np.log1p(ss).mean() - np.log1p(bb).mean()) * TD)
    q = lambda a, p: float(np.percentile(a, p))                      # noqa: E731
    return {
        "dSortino_ci": [q(dso, 2.5), q(dso, 97.5)], "dSortino_mean": float(np.mean(dso)),
        "dWealth_ci": [q(dtw, 2.5), q(dtw, 97.5)], "dWealth_mean": float(np.mean(dtw)),
        "dLogWealthAnn_ci": [q(dcagr, 2.5), q(dcagr, 97.5)],
        "dLogWealthAnn_mean": float(np.mean(dcagr)),
        "dMaxDD_ci": [q(dmd, 2.5), q(dmd, 97.5)], "dMaxDD_mean": float(np.mean(dmd)),
        "p_sortino_win": float(np.mean(np.array(dso) > 0)),
        "p_compound_win": float(np.mean(np.array(dcagr) > 0)),
    }


def run(label: str, assets: list[str], schwab_w: dict, w6040: dict) -> dict:
    legs, cash = load_substrate(assets)
    arms = {
        "TREND SLEEVE": sleeve_returns(legs, cash),
        "buy-hold EQUITY": buyhold_equity(legs),
        "60_40": robo_returns(legs, w6040, cash),
        "schwab_like (cash@mkt)": robo_returns(legs, schwab_w, cash),
        "schwab_like (below-mkt sweep)": robo_returns(
            legs, schwab_w, (cash - 0.0125 / TD).clip(lower=0.0)),
    }
    start = max(s.dropna().index.min() for s in arms.values())
    end = min(s.dropna().index.max() for s in arms.values())
    w = {k: v[(v.index >= start) & (v.index <= end)].dropna() for k, v in arms.items()}
    yrs = (end - start).days / 365.25

    rows = {}
    print(f"\n=== {label}: {start.date()} .. {end.date()} ({yrs:.1f} yr) ===")
    print(f'{"strategy":32}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"CAGR":>7}{"MaxDD":>8}{"$10k→":>13}')
    for nm, r in w.items():
        eq = (1 + r).cumprod()
        rows[nm] = {"sortino": sortino(r), "sortino_ci_low": ci_low_sortino(r),
                    "sharpe": sharpe(r), "cagr": cagr(eq), "maxdd": maxdd(eq),
                    "terminal_10k": float(10000 * eq.iloc[-1] / eq.iloc[0])}
        print(f'{nm:32}{rows[nm]["sortino"]:>9.3f}{rows[nm]["sortino_ci_low"]:>8.3f}'
              f'{rows[nm]["sharpe"]:>8.3f}{rows[nm]["cagr"]*100:>6.1f}%'
              f'{rows[nm]["maxdd"]*100:>7.1f}%{rows[nm]["terminal_10k"]:>13,.0f}')

    print(f"\n--- PAIRED block-bootstrap (sleeve − baseline; 21d blocks, 1000 iter) ---")
    pairs = {}
    for nm in ["buy-hold EQUITY", "60_40", "schwab_like (cash@mkt)", "schwab_like (below-mkt sweep)"]:
        p = paired(w["TREND SLEEVE"], w[nm])
        pairs[nm] = p
        star = "  <<< THE VERDICT ROW" if nm == "buy-hold EQUITY" else ""
        print(f'  vs {nm:31} ΔSortino [{p["dSortino_ci"][0]:+.3f},{p["dSortino_ci"][1]:+.3f}]'
              f'  Δcompound%/yr [{p["dLogWealthAnn_ci"][0]*100:+.2f},{p["dLogWealthAnn_ci"][1]*100:+.2f}]'
              f'  ΔMaxDD [{p["dMaxDD_ci"][0]*100:+.1f}%,{p["dMaxDD_ci"][1]*100:+.1f}%]{star}')

    # per-crisis drawdown (the structural-win test across the deep window's crises)
    print(f"\n--- per-crisis MaxDD: sleeve vs buy-hold equity ---")
    crisis = {}
    for cname, (a, b) in CRISES.items():
        seg_s = w["TREND SLEEVE"][(w["TREND SLEEVE"].index >= a) & (w["TREND SLEEVE"].index <= b)]
        seg_b = w["buy-hold EQUITY"][(w["buy-hold EQUITY"].index >= a) & (w["buy-hold EQUITY"].index <= b)]
        if len(seg_s) < 20:
            continue
        ds, db = maxdd((1 + seg_s).cumprod()), maxdd((1 + seg_b).cumprod())
        crisis[cname] = {"sleeve_mdd": ds, "buyhold_mdd": db, "shallower": bool(ds > db)}
        print(f'  {cname:22} sleeve {ds*100:>6.1f}%   buy-hold {db*100:>6.1f}%   '
              f'{"SHALLOWER ✓" if ds > db else "deeper ✗"}')

    mbl_sr = math.sqrt(2 * math.log(N_TRIALS) / yrs)
    print(f"\nMBL/DSR: N={N_TRIALS}, {yrs:.0f}yr → required Sharpe {mbl_sr:.3f}; "
          f"sleeve Sharpe {rows['TREND SLEEVE']['sharpe']:.3f} "
          f"({'CLEARS' if rows['TREND SLEEVE']['sharpe'] > mbl_sr else 'FAILS'})")
    return {"label": label, "window": [str(start.date()), str(end.date())], "years": yrs,
            "arms": rows, "paired": pairs, "crisis_mdd": crisis,
            "mbl_required_sharpe": mbl_sr, "n_trials": N_TRIALS}


def main() -> int:
    out = {}
    # PRIMARY: 2-asset (gold-free) — schwab_like gold weight renormalized away.
    out["primary_2asset"] = run(
        "PRIMARY — D-A 2-asset (equity+bond)", ["equity", "bond"],
        schwab_w={"equity": 0.474, "bond": 0.316, "_cash": 0.211},
        w6040={"equity": 0.60, "bond": 0.40})
    # SECONDARY: 3-asset (the deployed shape).
    out["secondary_3asset"] = run(
        "SECONDARY — D-B 3-asset (equity+bond+gold)", ["equity", "bond", "gold"],
        schwab_w={"equity": 0.45, "bond": 0.30, "gold": 0.05, "_cash": 0.20},
        w6040={"equity": 0.60, "bond": 0.40})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

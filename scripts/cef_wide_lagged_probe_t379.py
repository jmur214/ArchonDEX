"""T-379 — CEF discount reversion, WIDE survivor universe, one-day execution skip.

Runs the frozen pre-registration `docs/Sources/prereg_cef_wide_lagged_t379_2026-11-10.md`.
The T-267 signal unchanged (own trailing-12-month-end discount z-score, cheapest quintile,
equal weight, monthly) on every fund of the archived CEFConnect roster that has an
`X<TKR>X` NAV ticker, with point-in-time liquidity / staleness eligibility, and two
execution arms: SKIP (enter at the close AFTER the signal day — the gated arm) and
NO-SKIP (enter at the signal close, as T-267 did — decomposition only).

Survivor-only. Exploratory. N_trials consumed: 2. Never deployment evidence.

Usage:
    python scripts/cef_wide_lagged_probe_t379.py --roster <cef_daily.parquet> [--smoke]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME  # noqa: E402

CACHE = os.path.join(ROOT, "data/research/cef_panel_t379.parquet")
COST_PER_SIDE = 0.0015
QUINTILE = 0.20
MIN_NAMES = 10
Z_WINDOW = 12
ADV_FLOOR = 500_000.0
ADV_WINDOW = 63
STALE_WINDOW = 5
DISC_LO, DISC_HI = -0.60, 1.00
ERR_HI, ERR_LO, ERR_NAV = 1.00, -0.70, 0.25
NW_LAGS = 6
BOOT_BLOCK, BOOT_N, BOOT_SEED = 6, 2000, 0
SAT_W = 0.15


def tr_close(ticker: str) -> pd.Series:
    # ticker-exclusions: bypassed — three named ETF control series (SPY, HYG, LQD) for the regression; never a universe read
    df = pd.read_csv(os.path.join(ROOT, f"data/processed/tr_reconciled/{ticker}_1d.csv"),
                     parse_dates=["Date"]).set_index("Date")
    return df["Close"].astype(float).sort_index()


def build_panel(roster_path: str) -> pd.DataFrame:
    """Daily raw Close, Adj Close, Volume and NAV per fund → cached parquet (columns: field|ticker)."""
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    import logging
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    roster = sorted(pd.read_parquet(roster_path)["Ticker"].unique())
    nav = yf.download([f"X{t}X" for t in roster], period="max", auto_adjust=False,
                      progress=False, threads=True)["Close"].dropna(axis=1, how="all")
    have = [c[1:-1] for c in nav.columns]
    if not have:
        raise RuntimeError("no NAV ticker returned data — refusing to build an empty panel")
    px = yf.download(have, period="max", auto_adjust=False, progress=False, threads=True)
    frames: Dict[str, pd.Series] = {}
    for t in have:
        raw = px["Close"][t] if t in px["Close"].columns else None
        if raw is None or raw.dropna().empty:
            continue
        frames[f"raw|{t}"] = raw
        frames[f"adj|{t}"] = px["Adj Close"][t]
        frames[f"vol|{t}"] = px["Volume"][t]
        frames[f"nav|{t}"] = nav[f"X{t}X"]
    panel = pd.DataFrame(frames)
    panel.index = pd.to_datetime(panel.index).tz_localize(None).normalize()
    panel = panel.sort_index()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    panel.to_parquet(CACHE)
    return panel


def field(panel: pd.DataFrame, name: str) -> pd.DataFrame:
    cols = [c for c in panel.columns if c.startswith(name + "|")]
    out = panel[cols].copy()
    out.columns = [c.split("|", 1)[1] for c in cols]
    return out


def newey_west_t(y: np.ndarray, X: np.ndarray, lags: int = NW_LAGS) -> Tuple[np.ndarray, np.ndarray]:
    """T-267's estimator, unchanged."""
    X = np.column_stack([np.ones(len(y)), X])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    S = (X * resid[:, None]).T @ (X * resid[:, None])
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
        S += w * (G + G.T)
    XtX_inv = np.linalg.inv(X.T @ X)
    cov = XtX_inv @ S @ XtX_inv
    return beta, beta / np.sqrt(np.diag(cov))


def signal_days(index: pd.DatetimeIndex) -> List[pd.Timestamp]:
    s = pd.Series(index, index=index)
    return list(s.groupby([index.year, index.month]).last())


def run_arm(panel: pd.DataFrame, skip: bool, smoke: bool = False) -> pd.DataFrame:
    raw, adj, vol, nav = (field(panel, k) for k in ("raw", "adj", "vol", "nav"))
    days = raw.index
    pos = {d: i for i, d in enumerate(days)}
    sig = [d for d in signal_days(days)]
    # month-end discount panel and the T-267 z-score (window includes the current month-end)
    disc_me = (raw.loc[sig] / nav.loc[sig] - 1.0)
    z_me = (disc_me - disc_me.rolling(Z_WINDOW, min_periods=Z_WINDOW).mean()) / \
        disc_me.rolling(Z_WINDOW, min_periods=Z_WINDOW).std()
    dollar = (raw * vol).rolling(ADV_WINDOW, min_periods=ADV_WINDOW // 2).median()
    nav_moved = (nav.diff().abs() > 0).rolling(STALE_WINDOW, min_periods=1).max().astype(bool)
    spy, hyg, lqd = tr_close("SPY"), tr_close("HYG"), tr_close("LQD")

    rows = []
    held_prev: set = set()
    last_ctrl = min(spy.index[-1], hyg.index[-1], lqd.index[-1])
    for i in range(len(sig) - 1):
        s, s_next = sig[i], sig[i + 1]
        e_i, x_i = pos[s] + (1 if skip else 0), pos[s_next] + (1 if skip else 0)
        if x_i >= len(days):
            break
        e, x = days[e_i], days[x_i]
        zi = z_me.loc[s].dropna()
        d_s = disc_me.loc[s]
        elig = [t for t in zi.index
                if DISC_LO <= d_s[t] <= DISC_HI
                and dollar.at[s, t] >= ADV_FLOOR
                and bool(nav_moved.at[s, t])]
        if len(elig) < MIN_NAMES:
            continue
        fwd = adj.loc[x, elig] / adj.loc[e, elig] - 1.0
        nav_chg = (nav.loc[x, elig] / nav.loc[e, elig] - 1.0).abs()
        err = ((fwd > ERR_HI) | (fwd < ERR_LO)) & (nav_chg < ERR_NAV)
        fwd = fwd[~err].dropna()
        elig_ok = list(fwd.index)
        if len(elig_ok) < MIN_NAMES:
            continue
        k = max(2, int(round(len(elig_ok) * QUINTILE)))
        held = set(zi[elig_ok].nsmallest(k).index)
        turn = len(held.symmetric_difference(held_prev)) / max(len(held), 1)
        row = {"signal": s, "entry": e, "exit": x, "n_elig": len(elig_ok), "k": k,
               "n_err": int(err.sum()), "turn": turn}
        if not smoke:
            row["strat"] = float(fwd[list(held)].mean() - turn * COST_PER_SIDE)
            row["univ"] = float(fwd.mean())
            if x <= last_ctrl and e >= hyg.index[0]:
                def _r(c: pd.Series) -> float:
                    return float(c.asof(x) / c.asof(e) - 1.0)
                row["spy"], row["credit"] = _r(spy), _r(hyg) - _r(lqd)
        rows.append(row)
        held_prev = held
    return pd.DataFrame(rows).set_index("entry")


def boot_ci_low(x: np.ndarray, block: int = BOOT_BLOCK, n: int = BOOT_N, seed: int = BOOT_SEED) -> float:
    rng = np.random.default_rng(seed)
    m = len(x)
    out = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s0, s0 + block) % m
                              for s0 in rng.integers(0, m, int(np.ceil(m / block)))])[:m]
        out.append(x[idx].mean())
    return float(np.percentile(out, 2.5))


def ratio_ci(r: pd.Series, fn) -> Tuple[float, Optional[float]]:
    pt = float(fn(r, 0.0, 12))
    ci = ME.bootstrap_distribution(r, lambda v: fn(v, 0.0, 12), n_iterations=1000, seed=0).get("ci_low")
    return pt, (None if ci is None else float(ci))


def report(tag: str, df: pd.DataFrame) -> Dict[str, object]:
    out: Dict[str, object] = {"window": tag, "months": int(len(df))}
    if len(df) < 36:
        raise RuntimeError(f"{tag}: only {len(df)} months — refusing to report a statistic")
    s = df["strat"]
    eq = (1 + s).cumprod()
    out["cagr"] = float(eq.iloc[-1] ** (12 / len(s)) - 1)
    out["maxdd"] = float((eq / eq.cummax() - 1).min())
    out["sharpe"], out["sharpe_ci_low"] = ratio_ci(s, ME.sharpe_ratio)
    out["sortino"], out["sortino_ci_low"] = ratio_ci(s, ME.sortino_ratio)
    reg = df[["strat", "spy", "credit", "univ"]].dropna()
    if len(reg) < 36:
        raise RuntimeError(f"{tag}: regression sample {len(reg)} months — halt")
    beta, t = newey_west_t(reg["strat"].values, reg[["spy", "credit", "univ"]].values)
    out.update(reg_months=int(len(reg)), alpha_pct_mo=float(beta[0] * 100), alpha_t_hac=float(t[0]),
               beta_spy=float(beta[1]), beta_credit=float(beta[2]), beta_univ=float(beta[3]))
    sat = reg.assign(comb=(1 - SAT_W) * reg["spy"] + SAT_W * reg["strat"])
    d = (np.log1p(sat["comb"]) - np.log1p(sat["spy"])).values
    out["sat_dlogwealth_ann"] = float(d.mean() * 12)
    out["sat_dlogwealth_ann_ci_low"] = boot_ci_low(d) * 12
    out["spy_cagr_same_months"] = float((1 + reg["spy"]).prod() ** (12 / len(reg)) - 1)
    out["strat_cagr_same_months"] = float((1 + reg["strat"]).prod() ** (12 / len(reg)) - 1)
    out["univ_cagr_same_months"] = float((1 + reg["univ"]).prod() ** (12 / len(reg)) - 1)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", required=True)
    ap.add_argument("--smoke", action="store_true", help="first 12 signal months, counts only")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    panel = build_panel(a.roster)
    funds = sorted({c.split("|", 1)[1] for c in panel.columns})
    print(f"panel: {len(funds)} funds, {panel.index[0].date()} → {panel.index[-1].date()}")
    if a.smoke:
        df = run_arm(panel, skip=True, smoke=True).head(12)
        print(df[["signal", "exit", "n_elig", "k", "n_err", "turn"]].to_string())
        return 0
    results = {"n_funds": len(funds), "arms": {}}
    for name, skip in (("SKIP", True), ("NO_SKIP", False)):
        df = run_arm(panel, skip=skip)
        res = [report("FULL", df), report("POST-2011", df[df.index >= "2011-01-01"])]
        results["arms"][name] = {"first_entry": str(df.index[0].date()), "last_entry": str(df.index[-1].date()),
                                 "median_n_elig": float(df["n_elig"].median()), "median_k": float(df["k"].median()),
                                 "n_err_total": int(df["n_err"].sum()), "mean_turn": float(df["turn"].mean()),
                                 "windows": res}
        if a.out:
            df.to_csv(a.out.replace(".json", f"_{name}.csv"))
    print(json.dumps(results, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(results, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""scripts/raw_signal_decile_b1.py — B-1 raw-signal decile harness (IC, Arms L/LS, wealth leg).

Implements steps 4–6 of the FROZEN B-1 pre-registration
(`docs/Sources/prereg_b1_raw_signal_decile_2026-09-30.md` §11.1 SPEC, the choices the frozen
text leaves open recorded in §11.4 BEFORE any output existed). A standalone harness: it never
touches `BacktestController`.

    PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    OMP_DYNAMIC=FALSE python -m scripts.raw_signal_decile_b1 \
        --panel data/research/b1/full_2a/signal_panel_<md5>.parquet \
        --out data/research/b1/run1/ --seed 0 --boot-iter 1000 --boot-block-months 6

Exit codes: 0 ok · 2 HALT (`[NN-FAIL-CLOSED]`: panel/census mismatch, a calendar census
failure, a window too short to bootstrap, a missing benchmark month) · 3 env pins wrong
(refused, never re-exec'd) · 4 disk below the floor · 5 cwd/code provenance outside this
worktree.

Design laws (each tested in tests/test_raw_signal_decile_b1.py):
  * NO SIGN FLIPPING (§2.1). Every statistic is computed on sign × raw value; a BH rejection
    in the wrong direction is reported as NOT clearing, with its statistic shown.
  * ONE bootstrap draw per window. The project-standard moving-block bootstrap
    (`MetricsEngine.bootstrap_distribution`) is run on the MONTH INDICES with one seed, so
    the arm, SPY and the EW sleeve, and every signal in a window, see the same resampled
    months (paired).
  * Missing is counted, never filled: an Arm L month without >= 10 eligible names takes the
    EW-universe return and is COUNTED (§4.2); a NaN forward return is never filled.
"""
from __future__ import annotations

import os
import sys

# ONE definition of the pins (the builder's). Importing it loads numpy before this check runs;
# that is harmless because a wrong pin is REFUSED (exit 3) — the process never computes and
# is never re-exec'd.
from scripts.build_signal_panel_b1 import ENV_PINS, env_pin_violations  # noqa: E402

if __name__ == "__main__":
    _bad = env_pin_violations()
    if _bad:
        print("[B1-HARNESS] REFUSING: determinism env pins wrong — " + "; ".join(_bad) +
              ". Export them BEFORE python starts (prereg §11.1 step 1). Never re-exec'd.",
              file=sys.stderr)
        sys.exit(3)

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Dict, List, Optional, Tuple  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts import build_signal_panel_b1 as panel_mod  # noqa: E402

ROOT = panel_mod.ROOT
FWD = "__fwd_ret_1m"
MIN_NAMES = panel_mod.MIN_NAMES          # an Arm L / LS leg needs >= 10 names
MIN_WINDOW_MONTHS = 24                   # fewer months than this cannot be block-bootstrapped
COST_PER_SIDE = 0.0005                   # 10 bps round trip (§2.5) = 5 bps per unit traded
BORROW_PER_MONTH = 0.0050 / 12.0         # 50 bps/yr on the LS short leg (§2.5)
SATELLITE = 0.25                         # 75% SPY + 25% Arm L (§5.1)
BH_Q = 0.05
IC_NW_LAGS = 6                           # §5.1
MAIN_START = "2000-01"

# §4.1 declared signs on the RAW computed value; Engine A edges in native orientation (+).
SIGN = {"mom_12_1": +1, "mom_6_1": +1, "reversal_1m": -1, "dist_52w_high": +1,
        "realized_vol_60d": -1, "beta_252d": -1, "skew_60d": -1, "high_minus_low_60d": -1,
        "drawdown_60d": +1, "ma_cross_50_200": +1, "moving_avg_distance_50d": +1,
        "vol_regime_5_60": -1, "overnight_intraday_v1": +1, "volume_anomaly_v1": +1}
SIGN.update({s: +1 for s in panel_mod.SENSITIVITY_EDGES})
SIGN.update({s: +1 for s in panel_mod.SHORT_EDGES})

# §5.3 calendar sub-family: daily dummy regression, T-196 sign (+ on the raw value).
CALENDAR = ["fomc_drift", "pre_fomc_reduce", "pre_holiday", "sell_in_may_halloween",
            "january_effect", "triple_witching_premium", "tax_loss_season",
            "month_of_year_dummy", "weekday_dummy", "days_to_quarter_end"]
CALENDAR_EXCLUDED_BY_RULING: Dict[str, str] = {}
CALENDAR_UNUSABLE_HALT_SHARE = 0.10      # a constant feature-year is unusable (§3.4, daily form)


# ============================================================ statistics
def nw_mean_t(x: np.ndarray, lags: int, min_n: int = MIN_WINDOW_MONTHS) -> Tuple[float, float, float]:
    """Mean, Newey-West (Bartlett) t and two-sided p of a series' mean — OLS on a constant
    with statsmodels' HAC covariance. NaNs are dropped (and counted by the caller)."""
    import statsmodels.api as sm
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < min_n:
        return float("nan"), float("nan"), float("nan")
    res = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0]), float(res.pvalues[0])


def nw_slope(y: np.ndarray, x: np.ndarray, lags: int) -> Tuple[float, float, float]:
    """Slope, Newey-West t and two-sided p of y on [1, x]."""
    import statsmodels.api as sm
    res = sm.OLS(y, sm.add_constant(x, has_constant="add")).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[1]), float(res.tvalues[1]), float(res.pvalues[1])


def nw_auto_lags(n: int) -> int:
    """Newey-West (1994) rule of thumb: floor(4 (T/100)^(2/9))."""
    return int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))


def bh_adjust(p: List[float], q: float = BH_Q) -> Tuple[List[float], List[bool]]:
    """Benjamini-Hochberg within one family; NaN p-values never reject and are not counted
    in m (a signal with no computable IC is reported, not silently given a slot)."""
    from statsmodels.stats.multitest import multipletests
    p = np.asarray(p, dtype=float)
    ok = np.isfinite(p)
    adj = np.full(len(p), np.nan)
    rej = np.zeros(len(p), dtype=bool)
    if ok.any():
        r, a, _, _ = multipletests(p[ok], alpha=q, method="fdr_bh")
        adj[ok], rej[ok] = a, r
    return [float(v) for v in adj], [bool(v) for v in rej]


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson on average ranks (ties averaged — §4.2: IC is Spearman on the tied values)."""
    ra = pd.Series(a).rank(method="average").to_numpy()
    rb = pd.Series(b).rank(method="average").to_numpy()
    if np.std(ra) < 1e-12 or np.std(rb) < 1e-12:       # [NN-FP-GUARDS]
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


# ============================================================ portfolios
def select_legs(signed: pd.Series, sparse: bool) -> Tuple[Optional[pd.Index], Optional[pd.Index]]:
    """(top, bottom) names for one month from the SIGNED values of the eligible names.
    Non-sparse: deciles that never SPLIT or DROP a tie group — top = rank(max) > 0.9 n,
    bottom = rank(min) <= 0.1 n. Names at a structural extreme (drawdown_60d = 0 at a 60-day
    high) are equally most-favorable: under average ranks a tie group above 20% of names
    would sink below 0.9 n and empty the top decile, silently turning Arm L into the EW
    sleeve. An oversized leg is counted by the caller.
    Sparse (§4.2): top = names strictly favorable (signed > 0, the native long side);
    bottom = the lowest tie group. A leg with < MIN_NAMES names is None (counted)."""
    if sparse:
        top = signed.index[signed.to_numpy() > 0]
        bottom = signed.index[np.isclose(signed.to_numpy(), signed.min(), rtol=0, atol=1e-12)]
    else:
        n = len(signed)
        top = signed.index[signed.rank(method="max").to_numpy() > 0.9 * n]
        bottom = signed.index[signed.rank(method="min").to_numpy() <= 0.1 * n]
    return (top if len(top) >= MIN_NAMES else None,
            bottom if len(bottom) >= MIN_NAMES else None)


def leg_series(legs: List[Optional[pd.Index]], fwd: List[pd.Series]) -> pd.DataFrame:
    """Gross return, turnover (sum |w - w_drifted|) and cost of an equal-weight leg rebalanced
    every month. The previous weights DRIFT with their realised returns before the trade; a
    None month holds nothing (gross NaN, the leg is fully traded out)."""
    rows, prev = [], {}
    for names, f in zip(legs, fwd):
        if names is None:
            w = {}
            gross = float("nan")
        else:
            w = {t: 1.0 / len(names) for t in names}
            gross = float(f.reindex(names).mean())
        turnover = sum(abs(w.get(t, 0.0) - prev.get(t, 0.0)) for t in set(w) | set(prev))
        rows.append({"gross": gross, "turnover": turnover, "cost": COST_PER_SIDE * turnover})
        if names is None:
            prev = {}
        else:
            r = f.reindex(names).fillna(0.0)
            g = 1.0 + gross
            prev = {t: w[t] * (1.0 + float(r[t])) / g for t in names} if abs(g) > 1e-12 else {}
    return pd.DataFrame(rows)


def max_drawdown(r: np.ndarray) -> float:
    from core.metrics_engine import MetricsEngine
    return float(MetricsEngine.max_drawdown(pd.Series(np.cumprod(1.0 + np.asarray(r)))))


def boot(n: int, fn, seed: int, iters: int, block: int) -> Dict[str, float]:
    """The project-standard moving-block bootstrap on the MONTH INDICES: the same seed and
    n draw the same months for every call, so every metric in a window is paired."""
    from core.metrics_engine import MetricsEngine
    idx = pd.Series(np.arange(n, dtype=float))
    out = MetricsEngine.bootstrap_distribution(
        idx, lambda s: fn(s.to_numpy().astype(int)), n_iterations=iters,
        block_length=block, seed=seed)
    return {"point": out["point_estimate"], "ci_low": out["ci_low"], "ci_high": out["ci_high"],
            "p_above_zero": out["p_above_zero"]}


def dlogw(arm: np.ndarray, spy: np.ndarray, bench_sat: Optional[np.ndarray] = None):
    """Δ log terminal wealth of (75% SPY + 25% arm) vs 100% SPY, or vs (75% SPY + 25% bench)."""
    a = SATELLITE * arm + (1.0 - SATELLITE) * spy
    b = spy if bench_sat is None else SATELLITE * bench_sat + (1.0 - SATELLITE) * spy

    def f(i):
        return float(np.sum(np.log1p(a[i])) - np.sum(np.log1p(b[i])))
    return f


# ============================================================ the monthly engine
def window_frames(panel: pd.DataFrame, start: str, end: pd.Timestamp,
                  first_n: Optional[int] = None) -> Tuple[List[pd.Timestamp], List[pd.DataFrame]]:
    months = [m for m in sorted(panel.index.get_level_values("month_end").unique())
              if pd.Timestamp(start + "-01") <= m <= end]
    if first_n is not None:                               # the smoke: a window's FIRST n months
        months = months[:first_n]
    return months, [panel.xs(m, level="month_end") for m in months]


def evaluate_signal(sig: str, sparse: bool, frames: List[pd.DataFrame],
                    spy: np.ndarray, ew: np.ndarray, ew_legs: List[pd.Index],
                    seed: int, iters: int, block: int,
                    min_months: int = MIN_WINDOW_MONTHS) -> dict:
    sign = SIGN[sig]
    n = len(frames)
    ics, top_legs, bot_legs = [], [], []
    n_ic_skipped = n_l_fallback = n_ls_missing = n_l_oversized = 0
    for k, fr in enumerate(frames):
        elig = fr[[sig, FWD]].dropna()
        signed = sign * elig[sig]
        if len(elig) and panel_mod.month_usable(elig[sig].to_numpy(dtype=float)):
            ic = spearman(signed.to_numpy(), elig[FWD].to_numpy())
            top, bot = select_legs(signed, sparse)
        else:
            ic, top, bot = float("nan"), None, None
        n_ic_skipped += int(not np.isfinite(ic))
        if top is None:                                   # §4.2: EW-universe, COUNTED
            n_l_fallback += 1
        elif not sparse and len(top) > 0.15 * len(elig):  # a tie group made the decile > 15%
            n_l_oversized += 1
        n_ls_missing += int(top is None or bot is None)
        ics.append(ic)
        top_legs.append(top if top is not None else ew_legs[k])
        bot_legs.append(bot if (top is not None and bot is not None) else None)

    fwd = [fr[FWD] for fr in frames]
    L = leg_series(top_legs, fwd)
    l_net = (L["gross"] - L["cost"]).to_numpy()
    S = leg_series(bot_legs, fwd)
    ls_net = (L["gross"] - L["cost"] - S["gross"] - S["cost"] - BORROW_PER_MONTH).to_numpy()
    ls_ok = np.isfinite(ls_net)

    from core.metrics_engine import MetricsEngine as ME
    ic_mean, ic_t, ic_p = nw_mean_t(np.asarray(ics), IC_NW_LAGS, min_months)
    row = {"signal": sig, "family": panel_mod.FAMILY[sig], "sign": sign, "sparse": sparse,
           "n_months": n, "n_ic_months": int(np.isfinite(ics).sum()),
           "n_ic_months_skipped": n_ic_skipped, "ic_mean": ic_mean, "ic_t_nw": ic_t,
           "ic_p": ic_p,
           "L_ann_mean": float(np.mean(l_net) * 12), "L_maxdd": max_drawdown(l_net),
           "L_turnover_ann_oneway": float(L["turnover"].mean() / 2.0 * 12),
           "L_cost_drag_bps_yr": float(L["cost"].mean() * 12 * 1e4),
           "L_n_fallback_months": n_l_fallback, "L_n_oversized_top_months": n_l_oversized,
           "L_sharpe": boot(n, lambda i: ME.sharpe_ratio(pd.Series(l_net[i]), periods=12),
                            seed, iters, block),
           "L_sortino": boot(n, lambda i: ME.sortino_ratio(pd.Series(l_net[i]), periods=12),
                             seed, iters, block),
           "dlogw_vs_spy": boot(n, dlogw(l_net, spy), seed, iters, block),
           "dlogw_vs_ew": boot(n, dlogw(l_net, spy, ew), seed, iters, block),
           "LS_n_missing_months": n_ls_missing}
    if ls_ok.sum() >= min_months:
        x = ls_net[ls_ok]
        row.update({"LS_ann_mean": float(np.mean(x) * 12), "LS_maxdd": max_drawdown(x),
                    "LS_sharpe": boot(len(x), lambda i: ME.sharpe_ratio(pd.Series(x[i]), periods=12),
                                      seed, iters, block),
                    "LS_sortino": boot(len(x), lambda i: ME.sortino_ratio(pd.Series(x[i]), periods=12),
                                       seed, iters, block)})
    else:
        row["LS_note"] = f"LS computable in {int(ls_ok.sum())} months — not evaluated (diagnostic only)"
    return row


def classify(row: dict) -> dict:
    """Clears IC = BH rejects AND the statistic is in the declared direction (§2.1).
    Wealth = BOTH ci_lows > 0 (H1 as ruled). EW tilt = beats SPY but not the EW sleeve."""
    rej = row.get("ic_bh_reject", False)
    pos = np.isfinite(row["ic_t_nw"]) and row["ic_t_nw"] > 0
    row["clears_ic"] = bool(rej and pos)
    row["wrong_sign_reject"] = bool(rej and not pos)
    spy_ok = row["dlogw_vs_spy"]["ci_low"] > 0
    ew_ok = row["dlogw_vs_ew"]["ci_low"] > 0
    row["wealth_clears_both"] = bool(spy_ok and ew_ok)
    row["ew_tilt_not_signal"] = bool(spy_ok and not ew_ok)
    row["meets_h1"] = bool(row["family"] == "main" and row["clears_ic"]
                           and row["wealth_clears_both"])
    return row


# ============================================================ calendar (daily)
def calendar_values(days: pd.DatetimeIndex, features: List[str]) -> pd.DataFrame:
    from core.feature_foundry.feature import get_feature_registry
    reg = get_feature_registry()
    out = {}
    for fid in features:
        f = reg.get(fid)
        if f is None:
            raise RuntimeError(f"[NN-FAIL-CLOSED] calendar feature {fid!r} not registered")
        out[fid] = [(lambda v: float(v) if v is not None else float("nan"))(f("SPY", d.date()))
                    for d in days]
    return pd.DataFrame(out, index=days)


def calendar_census(vals: pd.DataFrame) -> Tuple[dict, List[str]]:
    """A feature-YEAR is unusable when the feature is NaN or takes ONE value on every trading
    day of that year (the daily form of §3.4's three spellings of missing). HALT a feature
    unusable in > 10% of its years."""
    cen, halts = {}, []
    for fid in vals.columns:
        bad = []
        for y, s in vals[fid].groupby(vals.index.year):
            v = s.dropna().to_numpy()
            if len(v) == 0 or np.std(v) < 1e-12:
                bad.append(int(y))
        years = vals.index.year.unique()
        share = len(bad) / max(1, len(years))
        cen[fid] = {"n_years": int(len(years)), "unusable_years": bad,
                    "unusable_share": round(share, 4)}
        if share > CALENDAR_UNUSABLE_HALT_SHARE:
            halts.append(f"calendar {fid}: constant/NaN in {len(bad)} of {len(years)} years "
                         f"({share:.1%} > 10%): {bad[0]}–{bad[-1]}")
    return cen, halts


def ew_daily(panel: pd.DataFrame, closes: pd.DataFrame) -> pd.Series:
    """Equal-weight daily return of the PIT universe: on day t, the names in the panel at the
    LAST month-end strictly before t, with closes on both t-1 and t. < 10 names → NaN."""
    rets = closes.pct_change(fill_method=None)
    mes = sorted(panel.index.get_level_values("month_end").unique())
    mask = pd.DataFrame(False, index=rets.index, columns=rets.columns)
    for i, m in enumerate(mes):
        nxt = mes[i + 1] if i + 1 < len(mes) else rets.index[-1] + pd.Timedelta(days=1)
        names = [t for t in panel.xs(m, level="month_end").index if t in mask.columns]
        rows = (rets.index > m) & (rets.index <= nxt)
        mask.loc[rows, names] = True
    r = rets.where(mask)
    n = r.notna().sum(axis=1)
    out = r.mean(axis=1)
    out[n < MIN_NAMES] = np.nan
    return out


def evaluate_calendar(vals: pd.DataFrame, ew: pd.Series) -> List[dict]:
    """Daily dummy regression: EW return from t to t+1 on the feature value at t (the
    position the signal sets at t's close), Newey-West t, T-196 sign (+)."""
    y = ew.shift(-1)
    rows = []
    for fid in vals.columns:
        d = pd.concat([vals[fid], y], axis=1, keys=["x", "y"]).dropna()
        lags = nw_auto_lags(len(d))
        b, t, p = nw_slope(d["y"].to_numpy(), d["x"].to_numpy(), lags)
        rows.append({"signal": fid, "family": "calendar", "sign": +1, "n_days": int(len(d)),
                     "nw_lags": lags, "slope": b, "t_nw": t, "p": p})
    return rows


# ============================================================ io / identity
def canonical_results_md5(results: dict) -> str:
    """Rows sorted by (family, signal); floats to 12 significant digits; JSON sort_keys."""
    import hashlib

    def r12(o):
        if isinstance(o, float):
            return float(f"{o:.12g}") if np.isfinite(o) else str(o)
        if isinstance(o, dict):
            return {k: r12(v) for k, v in o.items()}
        if isinstance(o, list):
            return [r12(v) for v in o]
        return o
    body = {k: results[k] for k in ("rows", "calendar", "benchmarks", "h1", "families")}
    body["rows"] = sorted(body["rows"], key=lambda r: (r["family"], r["signal"]))
    body["calendar"] = sorted(body["calendar"], key=lambda r: r["signal"])
    return hashlib.md5(json.dumps(r12(body), sort_keys=True).encode()).hexdigest()


def load_panel_checked(panel_path: Path) -> Tuple[pd.DataFrame, dict, List[str]]:
    """The panel must be the content its name claims and its census must have passed."""
    halts = []
    panel = pd.read_parquet(panel_path)
    digest = panel_mod.canonical_md5(panel)
    stem = panel_path.stem.replace("signal_panel_", "")
    if digest[:12] != stem:
        halts.append(f"panel content md5 {digest[:12]} != its filename {stem}")
    cpath = panel_path.with_name(f"census_{stem}.json")
    census = json.loads(cpath.read_text()) if cpath.is_file() else {}
    if not census:
        halts.append(f"no census beside the panel ({cpath.name})")
    elif census.get("halt_reasons"):
        halts.append(f"census carries HALT reasons: {census['halt_reasons']}")
    elif census.get("panel_canonical_md5") != digest:
        halts.append("census panel_canonical_md5 != the panel's content md5")
    return panel, census, halts


def run(panel: pd.DataFrame, census: dict, start: str, seed: int, iters: int, block: int,
        price_root: Path, with_calendar: bool = True,
        smoke_months: Optional[int] = None) -> Tuple[dict, List[str]]:
    halts: List[str] = []
    min_months = smoke_months or MIN_WINDOW_MONTHS
    end = max(panel.index.get_level_values("month_end"))
    spy_df = panel_mod.load_ohlcv("SPY", price_root)
    if spy_df is None:
        return {}, ["SPY_1d.csv missing — no benchmark"]
    all_me = panel_mod.month_ends(spy_df.index, MAIN_START,
                                  (end + pd.offsets.MonthBegin(1)).strftime("%Y-%m"))

    def spy_returns(months):
        out = []
        for m in months:
            r, how = panel_mod.forward_return(spy_df, m, all_me[all_me.index(m) + 1])
            if how != "full":
                halts.append(f"SPY forward return at {m.date()} is {how}")
            out.append(r)
        return np.asarray(out)

    signals = [s for s in panel.columns if s != FWD]
    sparse = {s: census.get("signals", {}).get(s, {}).get("sparse") for s in signals}
    halts += [f"census has no sparse flag for {s}" for s, v in sparse.items() if v is None]
    if halts:
        return {}, halts
    windows = {"main": max(start, MAIN_START),
               "short_window": max(start, panel_mod.SHORT_WINDOW_START)}
    rows, benchmarks = [], {}
    for wname, wstart in windows.items():
        fams = ("main", "sensitivity") if wname == "main" else ("short_window",)
        if not any(panel_mod.FAMILY.get(s) in fams for s in signals):
            continue                                      # no member of this window in the panel
        months, frames = window_frames(panel, wstart, end, smoke_months)
        if len(months) < min_months:
            halts.append(f"window {wname} from {wstart}: {len(months)} months < {min_months}")
            continue
        spy = spy_returns(months)
        ew_legs = [fr.index[fr[FWD].notna()] for fr in frames]
        E = leg_series(ew_legs, [fr[FWD] for fr in frames])
        ew = (E["gross"] - E["cost"]).to_numpy()
        from core.metrics_engine import MetricsEngine as ME
        benchmarks[wname] = {
            "start": wstart, "n_months": len(months),
            "spy_ann_mean": float(np.mean(spy) * 12), "spy_maxdd": max_drawdown(spy),
            "spy_sharpe": boot(len(months), lambda i: ME.sharpe_ratio(pd.Series(spy[i]), periods=12),
                               seed, iters, block),
            "ew_ann_mean": float(np.mean(ew) * 12), "ew_maxdd": max_drawdown(ew),
            "ew_cost_drag_bps_yr": float(E["cost"].mean() * 12 * 1e4),
            "ew_sleeve_dlogw_vs_spy": boot(len(months), dlogw(ew, spy), seed, iters, block)}
        for s in signals:
            if panel_mod.FAMILY[s] in fams:
                rows.append(evaluate_signal(s, bool(sparse[s]), frames, spy, ew, ew_legs,
                                            seed, iters, block, min_months))
    families = {}
    for fam in ("main", "short_window"):
        members = [r for r in rows if r["family"] == fam]
        adj, rej = bh_adjust([r["ic_p"] for r in members])
        for r, a, j in zip(members, adj, rej):
            r["ic_p_bh"], r["ic_bh_reject"] = a, j
        families[fam] = {"m": len(members)}
    for r in rows:
        if r["family"] == "sensitivity":                  # reported, NOT in any BH count
            r["ic_p_bh"], r["ic_bh_reject"] = None, False
        classify(r)
        if r["family"] == "sensitivity":
            r["clears_ic"] = r["wrong_sign_reject"] = r["meets_h1"] = None
    for fam in families:
        families[fam]["n_clear_ic"] = sum(bool(r["clears_ic"]) for r in rows if r["family"] == fam)

    cal_rows, cal_census = [], {}
    if with_calendar:
        feats = [f for f in CALENDAR if f not in CALENDAR_EXCLUDED_BY_RULING]
        first = min(panel.index.get_level_values("month_end"))
        days = spy_df.loc[max(first, pd.Timestamp(windows["main"] + "-01")):end].index
        if smoke_months:
            days = days[days <= days[0] + pd.DateOffset(months=smoke_months)]
        vals = calendar_values(days, feats)
        cal_census, ch = calendar_census(vals)
        halts += ch
        if not ch:
            tickers = sorted(panel.index.get_level_values("ticker").unique())
            closes = pd.DataFrame({t: df["Close"] for t in tickers
                                   if (df := panel_mod.load_ohlcv(t, price_root)) is not None})
            # On SPY's trading calendar BEFORE differencing: one file's stray off-calendar row
            # would otherwise make the next day's return NaN for every other name.
            closes = closes.reindex(spy_df.index)
            closes = closes.loc[(closes.index >= days[0]) & (closes.index <= end)]
            ew_d = ew_daily(panel, closes).reindex(days)
            cal_rows = evaluate_calendar(vals, ew_d)
            adj, rej = bh_adjust([r["p"] for r in cal_rows])
            for r, a, j in zip(cal_rows, adj, rej):
                r["p_bh"], r["bh_reject"] = a, j
                r["clears"] = bool(j and r["t_nw"] > 0)
                r["wrong_sign_reject"] = bool(j and not r["t_nw"] > 0)
            families["calendar"] = {"m": len(cal_rows),
                                    "n_clear": sum(r["clears"] for r in cal_rows)}
    h1 = {"met": any(r.get("meets_h1") for r in rows),
          "signals_meeting": sorted(r["signal"] for r in rows if r.get("meets_h1")),
          "ew_tilt_not_signal": sorted(r["signal"] for r in rows
                                       if r["family"] == "main" and r["ew_tilt_not_signal"]),
          "n_trials_consumed": 4}
    return {"rows": rows, "calendar": cal_rows, "calendar_census": cal_census,
            "calendar_excluded_by_ruling": CALENDAR_EXCLUDED_BY_RULING,
            "benchmarks": benchmarks, "families": families, "h1": h1}, halts


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--boot-iter", type=int, default=1000)
    ap.add_argument("--boot-block-months", type=int, default=6)
    ap.add_argument("--start", default=MAIN_START, help="YYYY-MM (2012-01 = the §7 sensitivity window)")
    ap.add_argument("--no-calendar", action="store_true", help="skip the daily calendar family")
    ap.add_argument("--smoke-months", type=int, default=None,
                    help="SMOKE ONLY: each window's FIRST n months (§11.1 Step 2); output is "
                         "labelled smoke_*.json and is never a measurement")
    a = ap.parse_args(argv)

    if Path.cwd().resolve() != ROOT:
        print(f"[B1-HARNESS] REFUSING: cwd {Path.cwd()} is not the worktree root {ROOT}",
              file=sys.stderr)
        return 5
    import core.metrics_engine as me_mod
    import core.feature_foundry as cff
    prov = panel_mod.provenance([me_mod, cff, panel_mod])
    prov["harness"] = str(Path(__file__).resolve())
    print("[B1-HARNESS] provenance: " + json.dumps(prov))
    bad = panel_mod.provenance_violations(prov)
    if bad:
        print(f"[B1-HARNESS] REFUSING: code from outside this worktree: {bad}", file=sys.stderr)
        return 5
    import importlib
    import pkgutil
    import core.feature_foundry.features as fpkg
    for m in pkgutil.iter_modules(fpkg.__path__):
        importlib.import_module(f"{fpkg.__name__}.{m.name}")

    t0 = time.time()
    panel, census, halts = load_panel_checked(Path(a.panel))
    results: dict = {}
    if not halts:
        results, halts = run(panel, census, a.start, a.seed, a.boot_iter, a.boot_block_months,
                             ROOT / "data" / "processed", with_calendar=not a.no_calendar,
                             smoke_months=a.smoke_months)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    panel_mod.assert_disk_floor(out)
    meta = {"panel": str(a.panel), "panel_canonical_md5": census.get("panel_canonical_md5"),
            "start": a.start, "seed": a.seed, "boot_iter": a.boot_iter,
            "boot_block_months": a.boot_block_months, "with_calendar": not a.no_calendar,
            "smoke_months": a.smoke_months,
            "provenance": prov, "env_pins": {k: os.environ.get(k) for k in ENV_PINS},
            "halt_reasons": halts, "wall_seconds": round(time.time() - t0, 1)}
    if halts:
        (out / "halt.json").write_text(json.dumps(meta, indent=2, default=str))
        print("[B1-HARNESS] HALT ([NN-FAIL-CLOSED]) — no results written:\n  " +
              "\n  ".join(halts), file=sys.stderr)
        return 2
    digest = canonical_results_md5(results)
    results["meta"] = {**meta, "results_canonical_md5": digest}
    name = (f"smoke_{a.smoke_months}m_{digest[:12]}.json" if a.smoke_months
            else f"results_{digest[:12]}.json")
    if a.smoke_months:
        results["meta"]["label"] = "SMOKE — NOT A MEASUREMENT (first months of each window only)"
    (out / name).write_text(json.dumps(results, indent=2, default=str))
    print(f"[B1-HARNESS] results -> {out / name}  "
          f"canonical md5 {digest}  ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

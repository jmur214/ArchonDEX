"""T-087 — Engine E regime re-diagnosis on 12-yr extended substrate.

Companion of scripts/validate_regime_signals.py (which is the 2021-2025
5-yr diagnostic that produced the 2026-05-06 refutation). This script:

  1) Extends the SPY price history to 2014 using the Stooq mirror at
     data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt (already on disk,
     5,344 trading days back to 2005). The processed SPY_1d.csv only
     covers 2020-04+ which is why the prior diagnostic was 5-yr.
  2) Re-uses build_feature_panel + HMMRegimeClassifier.predict_proba_sequence
     to label every day 2014-01-01 → 2025-12-31 with the HMM's
     filtered regime probabilities.
  3) Computes:
       - AUC of p_crisis / p_stressed / (p_crisis + p_stressed) vs forward
         {5,10,20}-day SPY drawdown ≤ -5%, with bootstrap CI on AUC.
       - Lead/lag: corr(p_crisis_t, dd_{t-k:t}) vs corr(p_crisis_t, dd_{t:t+k}).
       - Per-stress-event TPR (2015-08, 2018-Q4, 2020-03, 2022, 2025).
       - VVIX-z (z-score of compute_vvix_proxy over trailing 252d) AUC
         + bootstrap CI — the T-055f go/no-go.

Outputs:
  - stdout report
  - docs/Measurements/2026-05/regime_signal_validation_t087_2026_05_30.json

Read-only diagnostic. No engine code touched.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier  # noqa: E402
from engines.engine_e_regime import macro_features as _mf  # noqa: E402


STOOQ_SPY = REPO / "data" / "raw" / "stooq" / "daily" / "us" / "nyse etfs" / "2" / "spy.us.txt"
STOOQ_TLT = REPO / "data" / "raw" / "stooq" / "daily" / "us" / "nasdaq etfs" / "tlt.us.txt"


# ----------------------------------------------------------------------
# Data loaders
# ----------------------------------------------------------------------
def _load_stooq_close(path: Path, start: str, end: str) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").sort_index()
    s = df["close"].astype(float)
    s = s.loc[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    s.index.name = "date"
    return s


def load_spy_extended(start: str = "2013-01-01", end: str = "2026-12-31") -> pd.Series:
    """Load SPY close from Stooq (covers 2005+). Returns tz-naive daily series."""
    return _load_stooq_close(STOOQ_SPY, start, end)


def load_tlt_extended(start: str = "2013-01-01", end: str = "2026-12-31") -> pd.Series:
    """Load TLT close from Stooq (covers 2005+). Returns tz-naive daily series."""
    return _load_stooq_close(STOOQ_TLT, start, end)


def load_fred(series_id: str) -> Optional[pd.Series]:
    p = REPO / "data" / "macro" / f"{series_id}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if "value" in df.columns:
        s = df["value"].dropna()
    else:
        numeric = df.select_dtypes(include=[np.number]).columns
        if len(numeric) == 0:
            return None
        s = df[numeric[0]].dropna()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def compute_vvix_proxy(daily_idx: pd.DatetimeIndex) -> pd.Series:
    """30d rolling annualized std of log(VIX) — same as production script."""
    s = load_fred("VIXCLS")
    s = s.dropna()
    log_ret = np.log(s).diff()
    rolling_std = log_ret.rolling(30, min_periods=30).std(ddof=1) * np.sqrt(252.0)
    return rolling_std.reindex(daily_idx, method="ffill")


def vvix_z_score(daily_idx: pd.DatetimeIndex, window: int = 252) -> pd.Series:
    """Trailing z-score of VVIX-proxy over `window` business days."""
    vvix = compute_vvix_proxy(daily_idx)
    mean = vvix.rolling(window, min_periods=window).mean()
    std = vvix.rolling(window, min_periods=window).std(ddof=1)
    z = (vvix - mean) / std.replace(0.0, np.nan)
    return z


# ----------------------------------------------------------------------
# Feature panel — extended-substrate variant
# ----------------------------------------------------------------------
def build_extended_panel(spy: pd.Series, start: str, end: str) -> pd.DataFrame:
    """Build the HMM feature panel using extended-substrate SPY.

    Replicates engines.engine_e_regime.macro_features.build_feature_panel
    but bypasses the SPY/TLT loaders (which read data/processed/*_1d.csv
    that only covers 2020-04+).

    Returns DataFrame indexed by daily date with FEATURE_COLUMNS in the
    same order as the production builder.
    """
    daily_idx = spy.index
    daily_idx = daily_idx[(daily_idx >= pd.Timestamp(start)) & (daily_idx <= pd.Timestamp(end))]

    # Load TLT from Stooq (extended substrate) — falls back to processed CSV
    # if Stooq file missing. This is critical: processed/TLT_1d.csv only
    # covers 2020-04+, which would NaN-out the 2014-2019 panel rows and
    # force the HMM into its uniform-prior fallback for that range.
    if STOOQ_TLT.exists():
        tlt = load_tlt_extended(start="2013-06-01", end=end)
    else:
        tlt_csv = REPO / "data" / "processed" / "TLT_1d.csv"
        if tlt_csv.exists():
            tlt_df = pd.read_csv(tlt_csv, index_col=0, parse_dates=True)
            tlt = tlt_df["Close"].astype(float).sort_index()
            if tlt.index.tz is not None:
                tlt.index = tlt.index.tz_localize(None)
        else:
            tlt = None

    vix = load_fred("VIXCLS")
    t10y2y = load_fred("T10Y2Y")
    baa = load_fred("BAA10Y")
    aaa = load_fred("AAA10Y")
    dollar = load_fred("DTWEXBGS")

    out = pd.DataFrame(index=daily_idx)
    spy_log = np.log(spy).diff()
    out["spy_log_return"] = spy_log.reindex(daily_idx)
    out["spy_ret_5d"] = spy_log.rolling(5).sum().reindex(daily_idx)
    out["spy_vol_20d"] = spy_log.rolling(20).std(ddof=0).reindex(daily_idx)

    if tlt is not None and not tlt.empty:
        tlt_log = np.log(tlt).diff()
        out["tlt_log_return"] = tlt_log.reindex(daily_idx)
        out["tlt_ret_20d"] = tlt_log.rolling(20).sum().reindex(daily_idx)
    else:
        out["tlt_log_return"] = np.nan
        out["tlt_ret_20d"] = np.nan

    out["vix_level"] = vix.reindex(daily_idx, method="ffill") if vix is not None else np.nan
    out["yield_curve_spread"] = (
        t10y2y.reindex(daily_idx, method="ffill") if t10y2y is not None else np.nan
    )

    if baa is not None and aaa is not None:
        joined = pd.concat([baa.rename("baa"), aaa.rename("aaa")], axis=1, join="inner").dropna()
        spread = (joined["baa"] - joined["aaa"]).sort_index()
        out["credit_spread_baa_aaa"] = spread.reindex(daily_idx, method="ffill")
    else:
        out["credit_spread_baa_aaa"] = np.nan

    if dollar is not None and not dollar.empty:
        dollar_aligned = dollar.reindex(daily_idx, method="ffill")
        out["dollar_ret_63d"] = np.log(dollar_aligned).diff(63)
    else:
        out["dollar_ret_63d"] = np.nan

    # Reorder to FEATURE_COLUMNS (same order the HMM expects)
    feature_cols = [c for c in _mf.FEATURE_COLUMNS if c in out.columns]
    out = out[feature_cols]
    return out


# ----------------------------------------------------------------------
# Targets
# ----------------------------------------------------------------------
def forward_drawdown(price: pd.Series, horizon: int) -> pd.Series:
    rolling_min = price.shift(-1).rolling(horizon, min_periods=1).min()
    out = (rolling_min - price) / price
    out.iloc[-horizon:] = np.nan
    return out


# ----------------------------------------------------------------------
# AUC + bootstrap CI
# ----------------------------------------------------------------------
def auc_score(scores: np.ndarray, labels: np.ndarray) -> float:
    mask = ~(np.isnan(scores) | np.isnan(labels))
    s = scores[mask]
    y = labels[mask].astype(int)
    if len(s) == 0 or y.sum() == 0 or y.sum() == len(y):
        return float("nan")
    order = np.argsort(s)
    ranks = np.empty(len(s), dtype=np.float64)
    sorted_s = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    n_pos = y.sum()
    n_neg = len(y) - n_pos
    sum_pos_ranks = ranks[y == 1].sum()
    return float((sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def auc_block_bootstrap_ci(
    scores: np.ndarray, labels: np.ndarray, n_iter: int = 1000, block: int = 8, seed: int = 0
) -> Tuple[float, float, float]:
    """Block-bootstrap CI for AUC. Block respects serial correlation
    in the daily target series. Returns (point, ci_low, ci_high)."""
    mask = ~(np.isnan(scores) | np.isnan(labels))
    s = scores[mask]
    y = labels[mask]
    n = len(s)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    point = auc_score(s, y)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_iter):
        idx = []
        while len(idx) < n:
            start = rng.randint(0, max(1, n - block))
            idx.extend(range(start, min(start + block, n)))
        idx = np.array(idx[:n])
        boots.append(auc_score(s[idx], y[idx]))
    boots = [b for b in boots if not math.isnan(b)]
    if not boots:
        return point, float("nan"), float("nan")
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]


# ----------------------------------------------------------------------
# Lead/lag analysis
# ----------------------------------------------------------------------
def lead_vs_lag_corr(signal: pd.Series, price: pd.Series, lags: List[int]) -> Dict[str, Dict[int, float]]:
    """For each lag k:
       - 'lag' = corr(signal_t, trailing dd over (t-k, t])    — past
       - 'lead' = corr(signal_t, forward dd over (t, t+k])    — future
    Returns dict {lag: {k: corr}, lead: {k: corr}}.
    A 'predictive' signal has lead > lag; coincident has lag ≥ lead.
    """
    out = {"lag": {}, "lead": {}}
    for k in lags:
        forward_dd = forward_drawdown(price, k)
        rolling_min_past = price.rolling(k, min_periods=1).min()
        past_dd = (rolling_min_past - price) / price  # min over (t-k+1, t]; negative when past drop
        common = signal.dropna().index.intersection(forward_dd.dropna().index)
        if len(common) > 30:
            out["lead"][k] = float(signal.loc[common].corr(forward_dd.loc[common]))
        else:
            out["lead"][k] = float("nan")
        common2 = signal.dropna().index.intersection(past_dd.dropna().index)
        if len(common2) > 30:
            out["lag"][k] = float(signal.loc[common2].corr(past_dd.loc[common2]))
        else:
            out["lag"][k] = float("nan")
    return out


# ----------------------------------------------------------------------
# Per-stress-event TPR
# ----------------------------------------------------------------------
STRESS_EVENTS = [
    {"label": "2015-08 China-vol", "trough": "2015-08-25", "start": "2015-08-01", "end": "2015-09-30"},
    {"label": "2018-Q4 selloff",   "trough": "2018-12-24", "start": "2018-10-01", "end": "2018-12-31"},
    {"label": "2020-03 COVID",     "trough": "2020-03-23", "start": "2020-02-01", "end": "2020-04-30"},
    {"label": "2022 bear (full)",  "trough": "2022-10-12", "start": "2022-01-01", "end": "2022-12-31"},
    {"label": "2025 vol-shock",    "trough": "2025-04-08", "start": "2025-03-01", "end": "2025-05-31"},
]


def per_event_tpr(
    signal: pd.Series,
    threshold: float,
    events: List[Dict],
    lookback_window_days: int = 60,
) -> List[Dict]:
    """Did `signal >= threshold` fire at any point in (trough - lookback, trough]?
    'fire-on-time' means it fired LEADING the trough (≤ lookback_window_days before)."""
    out = []
    for ev in events:
        trough = pd.Timestamp(ev["trough"])
        window_start = trough - pd.Timedelta(days=lookback_window_days)
        sig_in_window = signal.loc[
            (signal.index >= window_start) & (signal.index <= trough)
        ].dropna()
        if len(sig_in_window) == 0:
            out.append({
                "label": ev["label"], "trough": ev["trough"],
                "fired": False, "lead_days": None,
                "max_signal_in_window": None, "n_obs_in_window": 0,
            })
            continue
        fired = (sig_in_window >= threshold).any()
        if fired:
            first_fire = sig_in_window[sig_in_window >= threshold].index[0]
            lead_days = (trough - first_fire).days
        else:
            lead_days = None
        out.append({
            "label": ev["label"], "trough": ev["trough"],
            "fired": bool(fired), "lead_days": lead_days,
            "max_signal_in_window": float(sig_in_window.max()),
            "n_obs_in_window": int(len(sig_in_window)),
        })
    return out


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2014-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--hmm-pkl", default=str(REPO / "engines" / "engine_e_regime" / "models" / "hmm_3state_v1.pkl"))
    ap.add_argument("--dd-threshold", type=float, default=-0.05)
    ap.add_argument("--out-json", default=str(REPO / "docs" / "Measurements" / "2026-05" / "regime_signal_validation_t087_2026_05_30.json"))
    args = ap.parse_args()

    print(f"[T-087] window: {args.start} → {args.end}")
    print(f"[T-087] dd threshold: {args.dd_threshold:+.0%}")

    # ---- SPY from Stooq (12-yr capable) ----
    spy = load_spy_extended(start="2013-06-01", end=args.end)
    print(f"[T-087] SPY (Stooq): rows={len(spy)} {spy.index.min().date()} → {spy.index.max().date()}")

    # ---- Build feature panel + HMM proba ----
    hmm = HMMRegimeClassifier.load(args.hmm_pkl)
    print(f"[T-087] HMM trained {hmm._artifact_metadata['train_start']} → {hmm._artifact_metadata['train_end']}")
    print(f"[T-087] HMM label_for_idx: {hmm._state_label_for_idx}")
    print(f"[T-087] CAVEAT: 2014-2020 is OUT OF SAMPLE relative to HMM training (2021-2024)")

    panel = build_extended_panel(spy, start="2013-06-01", end=args.end)
    print(f"[T-087] panel rows={len(panel)} cols={list(panel.columns)}")
    print(f"[T-087] panel non-null head:")
    print(panel.dropna().head(3).to_string())

    # CRITICAL: predict_proba_sequence uses forward-BACKWARD smoothing
    # (non-causal — each row's posterior includes future evidence). For a
    # predictive-validity test (AUC of signal_t vs forward dd_t→t+k), we
    # need the FILTERED (forward-only) posterior. Build it by calling
    # predict_proba on growing prefixes Z[:t+1] and taking the last row.
    feature_names = list(hmm.feature_names)
    valid = panel[feature_names].dropna()
    Z = (valid.values - hmm._feature_means) / hmm._feature_stds
    n_rows = len(Z)
    print(f"[T-087] computing CAUSAL (filtered) HMM posteriors over {n_rows} rows...")
    proba_arr = np.empty((n_rows, hmm.n_states), dtype=np.float64)
    for t in range(n_rows):
        # Use up to 252 trailing bars (matches per-row API window default
        # range — keeps each filter step bounded and yields a true online
        # signal, while preventing distant pre-2014 burn-in from dominating).
        start_t = max(0, t - 252 + 1)
        proba_arr[t] = hmm._hmm.predict_proba(Z[start_t:t + 1])[-1]
    state_cols = list(hmm._state_label_for_idx)
    proba_df_full = pd.DataFrame(proba_arr, index=valid.index, columns=state_cols)
    # Reindex to all panel rows; NaN-row positions become uniform.
    proba_df = proba_df_full.reindex(panel.index)
    for c in state_cols:
        proba_df[c] = proba_df[c].fillna(1.0 / hmm.n_states)

    mask = (proba_df.index >= pd.Timestamp(args.start)) & (proba_df.index <= pd.Timestamp(args.end))
    proba_df = proba_df.loc[mask]
    print(f"[T-087] HMM filtered proba in window rows={len(proba_df)} cols={list(proba_df.columns)}")
    for c in proba_df.columns:
        print(f"        mean({c}) = {proba_df[c].mean():.4f}")

    spy_window = spy.loc[(spy.index >= pd.Timestamp(args.start)) & (spy.index <= pd.Timestamp(args.end))]
    common = proba_df.index.intersection(spy_window.index)
    proba_df = proba_df.loc[common]
    spy_window = spy_window.loc[common]
    print(f"[T-087] aligned rows: {len(common)} ({common.min().date()} → {common.max().date()})")

    # ---- VVIX-z ----
    vvix_proxy = compute_vvix_proxy(common)
    vvix_z = vvix_z_score(common, window=252)
    print(f"[T-087] VVIX-proxy coverage: {(~vvix_proxy.isna()).sum()}/{len(common)} non-null")
    print(f"[T-087] VVIX-z (252d trailing) coverage: {(~vvix_z.isna()).sum()}/{len(common)} non-null")

    # ---- Unconditional fire rates (context for stress-event TPR) ----
    p_crisis_full = proba_df.get("crisis", pd.Series(np.nan, index=common))
    p_stressed_full = proba_df.get("stressed", pd.Series(np.nan, index=common))
    p_combined = p_crisis_full.fillna(0.0) + p_stressed_full.fillna(0.0)
    vvix_z_252_full = vvix_z_score(common, window=252)
    fire_rates = {
        "hmm_p_crisis@0.5": float((p_crisis_full >= 0.5).mean()),
        "hmm_p_stressed@0.5": float((p_stressed_full >= 0.5).mean()),
        "hmm_crisis_or_stressed@0.5": float((p_combined >= 0.5).mean()),
        "vvix_z_252d@1.0": float((vvix_z_252_full >= 1.0).mean()),
        "vvix_z_252d@1.5": float((vvix_z_252_full >= 1.5).mean()),
        "vvix_z_252d@2.0": float((vvix_z_252_full >= 2.0).mean()),
    }
    print(f"\n[T-087] Unconditional fire rates over full window:")
    for k, v in fire_rates.items():
        print(f"   {k:30s}  {v:.3f}")

    # ---- AUC vs forward dd ≤ threshold ----
    results: Dict = {
        "args": vars(args),
        "window": {
            "start": str(common.min().date()),
            "end": str(common.max().date()),
            "n_days": int(len(common)),
            "years": float((common.max() - common.min()).days / 365.25),
        },
        "hmm_metadata": dict(hmm._artifact_metadata),
        "hmm_state_label_for_idx": list(hmm._state_label_for_idx),
        "unconditional_fire_rates": fire_rates,
        "auc": {},
        "auc_sub_windows": {},
        "lead_vs_lag": {},
        "per_event_tpr": {},
    }

    for horizon in [5, 10, 20]:
        fdd = forward_drawdown(spy_window, horizon)
        target = (fdd <= args.dd_threshold).astype(float)
        target[fdd.isna()] = np.nan
        base_rate = float(np.nanmean(target.values))
        print(f"\n[T-087] horizon={horizon}d, dd≤{args.dd_threshold:+.0%}: base rate = {base_rate:.4f}")

        signals = {
            "hmm_p_crisis": proba_df.get("crisis", pd.Series(np.nan, index=common)).values,
            "hmm_p_stressed": proba_df.get("stressed", pd.Series(np.nan, index=common)).values,
            "hmm_p_crisis_or_stressed": (
                proba_df.get("crisis", pd.Series(0.0, index=common)).values
                + proba_df.get("stressed", pd.Series(0.0, index=common)).values
            ),
            "vvix_proxy": vvix_proxy.values,
            "vvix_z_252d": vvix_z.values,
        }
        results["auc"][f"horizon_{horizon}d"] = {"base_rate": base_rate, "signals": {}}
        for name, sig in signals.items():
            point, lo, hi = auc_block_bootstrap_ci(np.asarray(sig), target.values, n_iter=1000, block=8, seed=42)
            results["auc"][f"horizon_{horizon}d"]["signals"][name] = {
                "auc_point": point, "auc_ci_low": lo, "auc_ci_high": hi,
            }
            print(f"        {name:30s} AUC = {point:.4f}  ci=[{lo:.4f}, {hi:.4f}]")

    # ---- Sub-window AUC: OOS pre-2021 vs in-sample 2021-2024 vs post-train 2025 ----
    sub_windows = [
        ("oos_2014_2020", "2014-01-01", "2020-12-31"),
        ("train_2021_2024", "2021-01-01", "2024-12-31"),
        ("post_train_2025", "2025-01-01", "2025-12-31"),
    ]
    print(f"\n[T-087] Sub-window AUC decomposition (horizon=10d, dd≤-5%):")
    print(f"        Critical question: does the 12-yr AUC come from OOS (2014-2020),")
    print(f"        or is it dominated by the in-sample 2021-2024 training period?")
    for name, sub_start, sub_end in sub_windows:
        mask = (common >= pd.Timestamp(sub_start)) & (common <= pd.Timestamp(sub_end))
        idx = common[mask]
        if len(idx) < 100:
            print(f"   {name}: rows={len(idx)} (skipped)")
            continue
        spy_sub = spy_window.loc[idx]
        fdd_sub = forward_drawdown(spy_sub, 10)
        target_sub = (fdd_sub <= args.dd_threshold).astype(float)
        target_sub[fdd_sub.isna()] = np.nan
        base = float(np.nanmean(target_sub.values))
        sub_results = {"n_days": int(len(idx)), "base_rate": base, "signals": {}}
        for sname, sig in [
            ("hmm_p_crisis", p_crisis_full.loc[idx]),
            ("hmm_p_stressed", p_stressed_full.loc[idx]),
            ("hmm_p_crisis_or_stressed", p_combined.loc[idx]),
            ("vvix_proxy", vvix_proxy.loc[idx]),
            ("vvix_z_252d", vvix_z_252_full.loc[idx]),
        ]:
            point, lo, hi = auc_block_bootstrap_ci(
                np.asarray(sig.values), target_sub.values, n_iter=1000, block=8, seed=42
            )
            sub_results["signals"][sname] = {"auc_point": point, "auc_ci_low": lo, "auc_ci_high": hi}
        results["auc_sub_windows"][name] = sub_results
        print(f"   {name} (n={len(idx)}, base={base:.4f}):")
        for sname, sres in sub_results["signals"].items():
            print(f"      {sname:30s}  AUC={sres['auc_point']:.4f}  ci=[{sres['auc_ci_low']:.4f}, {sres['auc_ci_high']:.4f}]")

    # ---- Lead/lag analysis ----
    lags_to_test = [5, 10, 20, 40, 60]
    print(f"\n[T-087] Lead-vs-lag correlation (positive lead == predictive, more-negative lag == coincident):")
    print(f"        corr(signal_t, forward dd over k days) vs corr(signal_t, trailing dd over k days)")
    print(f"        forward dd is NEGATIVE during selloffs; correlation should be NEGATIVE if signal predicts.")

    for name, sig in [
        ("hmm_p_crisis", proba_df.get("crisis", pd.Series(np.nan, index=common))),
        ("hmm_p_stressed", proba_df.get("stressed", pd.Series(np.nan, index=common))),
        ("vvix_proxy", vvix_proxy),
        ("vvix_z_252d", vvix_z),
    ]:
        ll = lead_vs_lag_corr(sig, spy_window, lags_to_test)
        results["lead_vs_lag"][name] = ll
        print(f"   {name}:")
        for k in lags_to_test:
            lead, lag = ll["lead"].get(k, float("nan")), ll["lag"].get(k, float("nan"))
            ratio = abs(lag) / abs(lead) if lead and not math.isnan(lead) and lead != 0 else float("nan")
            print(f"      k={k:3d}d  lead={lead:+.4f}  lag={lag:+.4f}  |lag|/|lead|={ratio:.2f}")

    # ---- Per-stress-event TPR ----
    print(f"\n[T-087] Per-stress-event TPR at canonical thresholds:")
    p_crisis = proba_df.get("crisis", pd.Series(np.nan, index=common))
    p_stressed = proba_df.get("stressed", pd.Series(np.nan, index=common))
    p_crisis_or_stressed = p_crisis.fillna(0.0) + p_stressed.fillna(0.0)

    canonical_signals = {
        "hmm_p_crisis @ 0.5": (p_crisis, 0.5),
        "hmm_p_stressed @ 0.5": (p_stressed, 0.5),
        "hmm_crisis_or_stressed @ 0.5": (p_crisis_or_stressed, 0.5),
        "vvix_z_252d @ 1.0": (vvix_z, 1.0),
        "vvix_z_252d @ 1.5": (vvix_z, 1.5),
        "vvix_z_252d @ 2.0": (vvix_z, 2.0),
    }
    for name, (sig, thr) in canonical_signals.items():
        ev_rows = per_event_tpr(sig, thr, STRESS_EVENTS, lookback_window_days=60)
        results["per_event_tpr"][name] = ev_rows
        fired_count = sum(1 for r in ev_rows if r["fired"])
        n_have_data = sum(1 for r in ev_rows if r["n_obs_in_window"] > 0)
        print(f"   {name}:  fired={fired_count}/{n_have_data} of stress events (where signal has coverage)")
        for r in ev_rows:
            lead_str = f"{r['lead_days']}d lead" if r["lead_days"] is not None else "no fire"
            max_sig = r["max_signal_in_window"]
            max_str = f"max={max_sig:.3f}" if max_sig is not None else "no coverage"
            print(f"      {r['label']:25s} trough={r['trough']}  fired={str(r['fired']):5s}  {lead_str:14s}  {max_str}")

    # ---- Write JSON ----
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n[T-087] wrote {out_path}")


if __name__ == "__main__":
    main()

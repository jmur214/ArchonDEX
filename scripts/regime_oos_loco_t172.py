#!/usr/bin/env python
# scripts/regime_oos_loco_t172.py
"""T-172 — regime-detector leave-one-crisis-out OOS generalization test.

Implements the LOCKED pre-registration
(docs/Audit/regime_oos_preregistration_t172_2026_06_16.md): train a
Gaussian HMM on the deep reduced feature panel EXCLUDING a held-out
crisis, then test whether it FIRES on that held-out crisis with lead and
within the false-alarm budget. The deployable bar is dotcom (the crisis
TYPE the production model is blind to).

MEASUREMENT ONLY — does not touch the production regime model. Reduced
base feature set (no VIX term structure — it didn't exist in 2000; no
dollar — 2006 floor): spy_ret_5d, spy_vol_20d, bond_ret_20d (DGS10
proxy), vix_level, yield_curve_spread, credit_spread. Causal p_crisis
(forward filter, no lookahead). Seed-pinned.

Run:  python -m scripts.regime_oos_loco_t172
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp

ROOT = Path(__file__).resolve().parents[1]
SEED = 0
N_STATES = 3
N_INIT = 10
FIRE_THRESH = 0.50
FIRE_SUSTAIN = 3          # trading days
FA_BUDGET_PER_YR = 1.0
BUFFER_DAYS = 90         # calendar buffer around the held-out crisis

# Crisis windows (peak → trough), the T-118b/v3 anchors.
CRISES = {
    "dotcom": ("2000-03-01", "2002-10-09"),
    "GFC":    ("2007-10-09", "2009-03-09"),
    "COVID":  ("2020-02-19", "2020-03-23"),
    "2022":   ("2022-01-03", "2022-10-12"),
}
FEATURES = ["spy_ret_5d", "spy_vol_20d", "bond_ret_20d",
            "vix_level", "yield_curve_spread", "credit_spread"]


# --------------------------------------------------------------------- #
def _load_macro(series: str) -> pd.Series:
    df = pd.read_parquet(ROOT / "data" / "macro" / f"{series}.parquet")
    s = df.iloc[:, 0] if df.shape[1] >= 1 else df.squeeze()
    s.index = pd.to_datetime(s.index)
    return pd.to_numeric(s, errors="coerce").dropna()


def _deep_vix() -> pd.Series:
    """^VIX back to 1995 (covers dotcom + GFC). Cached locally."""
    cache = ROOT / "data" / "research" / "vix_deep_t172.csv"
    if cache.exists():
        s = pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
        return pd.to_numeric(s, errors="coerce").dropna()
    import yfinance as yf
    d = yf.download("^VIX", start="1995-01-01", end="2026-06-01",
                    progress=False, auto_adjust=False)
    close = d["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    s = pd.Series(close.values, index=pd.to_datetime(d.index)).dropna()
    cache.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(cache)
    return s


def build_deep_panel() -> pd.DataFrame:
    spy = pd.read_csv(ROOT / "data" / "processed" / "SPY_1d.csv",
                      parse_dates=["Date"]).set_index("Date")["Close"]
    spy = pd.to_numeric(spy, errors="coerce").dropna().sort_index()
    idx = spy.index[spy.index >= "1999-06-01"]   # warm-up before 2000

    vix = _deep_vix().reindex(idx, method="ffill")
    dgs10 = _load_macro("DGS10").reindex(idx, method="ffill")
    dgs3mo = _load_macro("DGS3MO").reindex(idx, method="ffill")
    baa = _load_macro("BAA10Y").reindex(idx, method="ffill")
    aaa = _load_macro("AAA10Y").reindex(idx, method="ffill")

    s = spy.reindex(idx)
    panel = pd.DataFrame(index=idx)
    panel["spy_ret_5d"] = s.pct_change(5)
    panel["spy_vol_20d"] = s.pct_change().rolling(20).std() * np.sqrt(252)
    # bond total-return proxy: ~ -duration * Δyield (10y duration ≈ 8.5)
    panel["bond_ret_20d"] = -8.5 * (dgs10 - dgs10.shift(20)) / 100.0
    panel["vix_level"] = vix
    panel["yield_curve_spread"] = dgs10 - dgs3mo
    panel["credit_spread"] = baa - aaa
    panel["spy_close"] = s
    panel = panel.dropna()
    panel = panel[panel.index >= "2000-01-01"]
    return panel


# --------------------------------------------------------------------- #
def _standardize(train: pd.DataFrame, full: pd.DataFrame):
    """z-score features using TRAIN-only mean/std (no leakage)."""
    mu = train[FEATURES].mean()
    sd = train[FEATURES].std().replace(0, 1.0)
    return ((full[FEATURES] - mu) / sd).values, mu, sd


def _causal_filtered_posterior(model, X: np.ndarray) -> np.ndarray:
    """Forward-filter posterior P(state_t | obs_1..t) — causal, no
    backward smoothing (the T-089 lookahead guard). Returns (T x n)."""
    framelogprob = model._compute_log_likelihood(X)
    log_start = np.log(model.startprob_ + 1e-300)
    log_trans = np.log(model.transmat_ + 1e-300)
    T, n = framelogprob.shape
    log_alpha = np.zeros((T, n))
    log_alpha[0] = log_start + framelogprob[0]
    for t in range(1, T):
        for j in range(n):
            log_alpha[t, j] = framelogprob[t, j] + logsumexp(
                log_alpha[t - 1] + log_trans[:, j])
    post = np.exp(log_alpha - logsumexp(log_alpha, axis=1, keepdims=True))
    return post


def _sustained_crossings(p: pd.Series, thresh: float, sustain: int) -> list:
    """Indices where p first reaches thresh and stays ≥thresh for
    `sustain` consecutive days (each such onset counted once)."""
    above = (p >= thresh).values
    onsets = []
    i = 0
    n = len(above)
    while i < n:
        if above[i] and all(above[i:i + sustain]) and (i == 0 or not above[i - 1]):
            onsets.append(i)
            # skip to end of this above-run
            while i < n and above[i]:
                i += 1
        else:
            i += 1
    return onsets


def loco_fold(panel: pd.DataFrame, name: str, start: str, end: str) -> dict:
    from hmmlearn.hmm import GaussianHMM
    cstart, cend = pd.Timestamp(start), pd.Timestamp(end)
    buf = pd.Timedelta(days=BUFFER_DAYS)
    held = (panel.index >= cstart - buf) & (panel.index <= cend + buf)
    train = panel.loc[~held]

    Xtrain, mu, sd = _standardize(train, train)
    Xfull, _, _ = _standardize(train, panel)

    model = GaussianHMM(n_components=N_STATES, covariance_type="diag",
                        n_iter=200, random_state=SEED, init_params="stmc")
    # multiple inits — keep the best by training log-likelihood.
    best, best_ll = None, -np.inf
    for k in range(N_INIT):
        m = GaussianHMM(n_components=N_STATES, covariance_type="diag",
                        n_iter=200, random_state=SEED + k)
        try:
            m.fit(Xtrain)
            ll = m.score(Xtrain)
        except Exception:
            continue
        if ll > best_ll:
            best, best_ll = m, ll
    model = best

    # crisis state = highest mean spy_vol_20d (z) among training-assigned states.
    train_states = model.predict(Xtrain)
    vol_idx = FEATURES.index("spy_vol_20d")
    means = [Xtrain[train_states == s, vol_idx].mean() if (train_states == s).any()
             else -np.inf for s in range(N_STATES)]
    crisis_state = int(np.argmax(means))

    post = _causal_filtered_posterior(model, Xfull)
    p_crisis = pd.Series(post[:, crisis_state], index=panel.index)

    # --- firing on the held-out crisis window ---
    win = (panel.index >= cstart) & (panel.index <= cend)
    pwin = p_crisis[win]
    spy_win = panel["spy_close"][win]
    trough_date = spy_win.idxmin()
    onsets = _sustained_crossings(pwin, FIRE_THRESH, FIRE_SUSTAIN)
    fired, lead_td, first_cross = False, None, None
    if onsets:
        first_cross = pwin.index[onsets[0]]
        # lead = trading days from first sustained crossing to trough
        if first_cross <= trough_date:
            lead_td = int((spy_win.index <= trough_date).sum()
                          - (spy_win.index <= first_cross).sum())
            fired = lead_td > 0

    # --- false-alarm rate on CALM days (not in ANY crisis window) ---
    calm = pd.Series(True, index=panel.index)
    for _, (s0, s1) in CRISES.items():
        calm &= ~((panel.index >= pd.Timestamp(s0) - buf)
                  & (panel.index <= pd.Timestamp(s1) + buf))
    p_calm = p_crisis[calm]
    fa_onsets = _sustained_crossings(p_calm, FIRE_THRESH, FIRE_SUSTAIN)
    calm_years = max(len(p_calm) / 252.0, 1e-9)
    fa_per_yr = len(fa_onsets) / calm_years

    return {
        "crisis": name,
        "fired": bool(fired),
        "lead_trading_days": lead_td,
        "first_crossing": str(first_cross.date()) if first_cross is not None else None,
        "trough": str(trough_date.date()),
        "max_p_crisis_in_window": round(float(pwin.max()), 3),
        "false_alarms_per_yr": round(float(fa_per_yr), 2),
        "fa_within_budget": bool(fa_per_yr <= FA_BUDGET_PER_YR),
        "crisis_state": crisis_state,
        "n_train": int(len(train)),
        "train_ll": round(float(best_ll), 1),
    }


def main() -> None:
    panel = build_deep_panel()
    print(f"deep panel: {panel.index.min().date()} → {panel.index.max().date()} "
          f"({len(panel)} obs); features: {FEATURES}\n")
    results = []
    for name, (s0, s1) in CRISES.items():
        r = loco_fold(panel, name, s0, s1)
        results.append(r)
        verdict = "FIRES ✓" if (r["fired"] and r["fa_within_budget"]) else (
            "fires but FA over budget" if r["fired"] else "NO FIRE")
        print(f"  [{name:7}] {verdict:24} lead={r['lead_trading_days']}td "
              f"first={r['first_crossing']} trough={r['trough']} "
              f"max_p={r['max_p_crisis_in_window']} FA/yr={r['false_alarms_per_yr']}")

    dotcom = next(r for r in results if r["crisis"] == "dotcom")
    passed = dotcom["fired"] and dotcom["fa_within_budget"]
    print(f"\n  PRE-REGISTERED VERDICT: dotcom (the untrained TYPE) "
          f"{'PASSES' if passed else 'FAILS'} the OOS bar "
          f"→ Step 2 (dynamic-sizing amplifier) "
          f"{'GATED OPEN' if passed else 'STAYS CLOSED; always-on 20% is the ceiling'}")
    out = ROOT / "data" / "research" / "regime_oos_loco_t172.json"
    out.write_text(json.dumps({"results": results, "pass_dotcom": passed}, indent=2))
    print(f"  written: {out}")


if __name__ == "__main__":
    main()

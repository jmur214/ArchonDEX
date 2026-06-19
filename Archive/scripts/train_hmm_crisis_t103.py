"""T-103 — Retrain Engine E's HMM on a crisis-inclusive span.

Companion of scripts/train_hmm_regime.py (which trained 2021-2024 only —
the in-sample-era model that motivated this dispatch).

Design (per inbox T-2026-06-04-103):
- Train span: 2006-04-01 → 2019-12-31  (effective binding floor: FRED
  DTWEXBGS starts 2006-01-02; dollar_ret_63d needs 63 business-day
  warmup → 2006-04-01).
- Held-out crises: COVID (2020), 2022 bear, 2025 vol-shock — NEVER
  seen during training.
- In-sample crisis: 2008 GFC, 2011 EU sovereign-debt, 2015-08 China
  vol-spike, 2018-Q4 selloff — IN train span.
- Loses dotcom 2000-02 (acceptable per director: 2008 is load-bearing).

Data path:
- SPY + TLT pulled from Stooq mirror (covers 2005-02-25 → 2026; we
  bypass data/processed/{SPY,TLT}_1d.csv which is Alpaca-only 2020+).
- VIXCLS, T10Y2Y, BAA10Y, AAA10Y from FRED parquet cache (back to 2000).
- DTWEXBGS from FRED parquet (binding floor: 2006-01-02).

Training:
- 3-state Gaussian HMM via HMMRegimeClassifier (random_state=42,
  matches T-087 in-sample model).
- Output: engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl
  (NEW; existing hmm_3state_v1.pkl PRESERVED).

This script TRAINS ONLY. Validation lives in
scripts/validate_hmm_crisis_t103.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier  # noqa: E402
from engines.engine_e_regime import macro_features as _mf  # noqa: E402


STOOQ_SPY = REPO / "data" / "raw" / "stooq" / "daily" / "us" / "nyse etfs" / "2" / "spy.us.txt"
STOOQ_TLT = REPO / "data" / "raw" / "stooq" / "daily" / "us" / "nasdaq etfs" / "tlt.us.txt"


def _load_stooq_close(path: Path, start: str, end: str) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").sort_index()
    s = df["close"].astype(float)
    s = s.loc[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    s.index.name = "date"
    return s


def load_fred(series_id: str) -> pd.Series:
    p = REPO / "data" / "macro" / f"{series_id}.parquet"
    if not p.exists():
        raise FileNotFoundError(f"FRED cache missing: {p}")
    df = pd.read_parquet(p)
    if "value" in df.columns:
        s = df["value"].dropna()
    else:
        numeric = df.select_dtypes(include=[np.number]).columns
        s = df[numeric[0]].dropna()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def build_crisis_panel(start: str, end: str) -> pd.DataFrame:
    """Build the 7-feature HMM panel from Stooq SPY/TLT + FRED.
    Mirrors engines.engine_e_regime.macro_features.build_feature_panel
    but bypasses the data/processed CSV loaders (which only cover
    2020-04+). Identical FEATURE_COLUMNS order so the trained model
    can be loaded back via HMMRegimeClassifier.load().
    """
    spy = _load_stooq_close(STOOQ_SPY, start, end)
    tlt = _load_stooq_close(STOOQ_TLT, start, end)

    daily_idx = spy.index
    daily_idx = daily_idx[(daily_idx >= pd.Timestamp(start)) & (daily_idx <= pd.Timestamp(end))]

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

    tlt_log = np.log(tlt).diff()
    out["tlt_log_return"] = tlt_log.reindex(daily_idx)
    out["tlt_ret_20d"] = tlt_log.rolling(20).sum().reindex(daily_idx)

    out["vix_level"] = vix.reindex(daily_idx, method="ffill")
    out["yield_curve_spread"] = t10y2y.reindex(daily_idx, method="ffill")

    joined = pd.concat([baa.rename("baa"), aaa.rename("aaa")], axis=1, join="inner").dropna()
    spread = (joined["baa"] - joined["aaa"]).sort_index()
    out["credit_spread_baa_aaa"] = spread.reindex(daily_idx, method="ffill")

    dollar_aligned = dollar.reindex(daily_idx, method="ffill")
    out["dollar_ret_63d"] = np.log(dollar_aligned).diff(63)

    # Match FEATURE_COLUMNS order from production builder.
    cols = [c for c in _mf.FEATURE_COLUMNS if c in out.columns]
    out = out[cols]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-start", default="2006-04-01")
    ap.add_argument("--train-end", default="2019-12-31")
    # Panel start: matches the binding floor evidence below.
    ap.add_argument("--panel-start", default="2005-02-25")
    ap.add_argument("--panel-end", default="2025-12-31")
    ap.add_argument(
        "--out-pickle",
        default=str(REPO / "engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl"),
    )
    ap.add_argument(
        "--out-json",
        default=str(REPO / "data/research/hmm_crisis_train_t103.json"),
    )
    args = ap.parse_args()

    print(f"[T-103-train] panel: {args.panel_start} → {args.panel_end}")
    print(f"[T-103-train] train: {args.train_start} → {args.train_end}")
    print(f"[T-103-train] held-out crises: COVID Feb-May 2020, 2022 bear, 2025 vol-shock")

    panel = build_crisis_panel(args.panel_start, args.panel_end)
    print(f"[T-103-train] panel rows={len(panel)} cols={list(panel.columns)}")
    panel_valid = panel.dropna()
    print(f"[T-103-train] panel non-null rows={len(panel_valid)} "
          f"first={panel_valid.index.min().date()} last={panel_valid.index.max().date()}")

    train_panel = panel.loc[args.train_start:args.train_end].dropna()
    print(f"[T-103-train] train_panel rows={len(train_panel)} "
          f"first={train_panel.index.min().date()} last={train_panel.index.max().date()}")
    assert len(train_panel) > 1000, f"insufficient training data: {len(train_panel)}"

    clf = HMMRegimeClassifier(n_states=3, random_state=42)
    print(f"[T-103-train] fitting 3-state HMM (random_state=42)...")
    artifact = clf.fit(
        train_panel,
        train_start=args.train_start,
        train_end=args.train_end,
    )

    print(f"[T-103-train] train_log_likelihood={artifact.train_log_likelihood:.2f}")
    print(f"[T-103-train] state_label_for_idx={clf._state_label_for_idx}")

    out_pkl = Path(args.out_pickle)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    import pickle
    with open(out_pkl, "wb") as f:
        pickle.dump(artifact, f)
    print(f"[T-103-train] wrote {out_pkl}")

    # Distribution check on train set
    train_proba = clf.predict_proba_sequence(train_panel)
    counts = train_proba.idxmax(axis=1).value_counts().to_dict()
    print(f"[T-103-train] train state distribution: {counts}")

    summary = {
        "task": "T-2026-06-04-103",
        "train_start": args.train_start,
        "train_end": args.train_end,
        "panel_start": args.panel_start,
        "panel_end": args.panel_end,
        "n_train_obs": int(len(train_panel)),
        "n_panel_obs": int(len(panel_valid)),
        "feature_columns": list(panel.columns),
        "binding_floor": {
            "DTWEXBGS_first_date": "2006-01-02",
            "stooq_SPY_TLT_first_date": "2005-02-25",
            "dollar_ret_63d_warmup_days": 63,
            "effective_panel_start": str(panel_valid.index.min().date()),
        },
        "train_log_likelihood": float(artifact.train_log_likelihood),
        "state_label_for_idx": list(clf._state_label_for_idx),
        "train_state_distribution": {k: int(v) for k, v in counts.items()},
        "out_pickle": str(out_pkl),
        "preserved_existing_model": "engines/engine_e_regime/models/hmm_3state_v1.pkl (NOT overwritten)",
        "random_state": 42,
        "reproducible": True,
    }
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, default=str))
    print(f"[T-103-train] wrote {out_json}")


if __name__ == "__main__":
    main()

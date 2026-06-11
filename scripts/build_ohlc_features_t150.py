"""
scripts/build_ohlc_features_t150.py
===================================
T-2026-06-11-150 Part A — OHLC-derived intraday-information features
(zero new data; the research's ranking: range-based vol estimators capture
most of intraday's value without minute bars).

FEATURES (per ticker, per day; the pre-registered Part-A set):
  yz_vol_21         Yang-Zhang (2000) annualized vol, 21d window — combines
                    overnight variance, open-to-close variance, and the
                    Rogers-Satchell range term; the minimum-variance unbiased
                    member of the range-estimator family.
  gk_vol_21         Garman-Klass (1980) annualized vol, 21d window.
  on_mean_21        trailing 21d mean overnight log return (T-135's signal,
                    repurposed as a conditioning FEATURE).
  on_share_21       trailing 21d sum|r_on| / (sum|r_on| + sum|r_id|) — where
                    a name's variance lives (the LPS composition feature).
  gap_abs_z         today's |r_on| / trailing 63d std of r_on (gap shock).
  gap_freq_21       fraction of last 21d with |r_on| > 1%.

CORRUPT-OPENS FILTER (MANDATORY — T-135's finding, 83 snap-back prints):
rows where |r_on|>25% AND |r_id|>25% with opposite signs have the open
treated as untrusted (open := prev close) BEFORE any feature computation.
Same repair as scripts/analyze_overnight_intraday_t135.py.

Output: data/research/ohlc_features_t150/features.parquet
        (long: ticker, date, <features>; vintage-stamped sidecar meta)
Loader: load_ohlc_features() in this module.

Usage: python -m scripts.build_ohlc_features_t150
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "research" / "ohlc_features_t150"
OUT_PARQUET = OUT_DIR / "features.parquet"

START, END = "1999-01-01", "2025-12-31"
W = 21
GAP_STD_W = 63


def load_ohlc_features() -> pd.DataFrame:
    """Loader for the Part-A feature panel (long format)."""
    return pd.read_parquet(OUT_PARQUET)


def _features_one(df: pd.DataFrame) -> pd.DataFrame | None:
    if not {"Open", "High", "Low", "Close"} <= set(df.columns) or len(df) < 300:
        return None
    o = df["Open"].astype(float)
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    c = df["Close"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_on = np.log(o / c.shift(1))
        r_id = np.log(c / o)
    # corrupt-opens repair (T-135): snap-back rows -> open untrusted
    snap = (r_on.abs() > 0.25) & (r_id.abs() > 0.25) & (np.sign(r_on) != np.sign(r_id))
    o = o.where(~snap, c.shift(1))
    with np.errstate(divide="ignore", invalid="ignore"):
        r_on = np.log(o / c.shift(1))
        r_id = np.log(c / o)
        log_ho = np.log(h / o)
        log_lo = np.log(l / o)
        log_co = r_id

    # Yang-Zhang: sigma^2 = var(on) + k*var(oc) + (1-k)*RS ; k per YZ(2000)
    var_on = r_on.rolling(W).var()
    var_oc = log_co.rolling(W).var()
    rs = (log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)).rolling(W).mean()
    k = 0.34 / (1.34 + (W + 1) / (W - 1))
    yz_var = var_on + k * var_oc + (1 - k) * rs
    yz_vol = np.sqrt(yz_var.clip(lower=0) * 252)

    log_hl = np.log(h / l)
    gk_var = (0.5 * log_hl ** 2 - (2 * np.log(2) - 1) * log_co ** 2).rolling(W).mean()
    gk_vol = np.sqrt(gk_var.clip(lower=0) * 252)

    abs_on = r_on.abs()
    abs_id = r_id.abs()
    denom = abs_on.rolling(W).sum() + abs_id.rolling(W).sum()
    on_share = abs_on.rolling(W).sum() / denom.replace(0, np.nan)

    out = pd.DataFrame({
        "yz_vol_21": yz_vol,
        "gk_vol_21": gk_vol,
        "on_mean_21": r_on.rolling(W).mean(),
        "on_share_21": on_share,
        "gap_abs_z": abs_on / r_on.rolling(GAP_STD_W).std().replace(0, np.nan),
        "gap_freq_21": (abs_on > 0.01).rolling(W).mean(),
    })
    out["n_snap_repaired"] = int(snap.sum())
    return out.dropna(how="all")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    n_snap_total = 0
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        df = df[(df.index >= START) & (df.index <= END)]
        feat = _features_one(df)
        if feat is None or feat.empty:
            continue
        t = f.split("/")[-1].replace("_1d.csv", "")
        n_snap_total += int(feat["n_snap_repaired"].iloc[0])
        feat = feat.drop(columns=["n_snap_repaired"])
        feat["ticker"] = t
        frames.append(feat.reset_index(names="date"))
    panel = pd.concat(frames, ignore_index=True)
    panel.to_parquet(OUT_PARQUET, index=False)
    (OUT_DIR / "meta.json").write_text(json.dumps({
        "task": "T-2026-06-11-150 PartA",
        "features": ["yz_vol_21", "gk_vol_21", "on_mean_21", "on_share_21",
                     "gap_abs_z", "gap_freq_21"],
        "corrupt_opens_filter": "T-135 snap-back repair applied pre-compute",
        "n_snap_rows_repaired_total": n_snap_total,
        "window": [START, END],
    }, indent=2))
    print(f"[T150-A] panel: {len(panel)} rows, {panel.ticker.nunique()} tickers, "
          f"{panel.date.min().date()}..{panel.date.max().date()} | "
          f"snap-repaired rows: {n_snap_total}")
    print(f"[T150-A] wrote {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

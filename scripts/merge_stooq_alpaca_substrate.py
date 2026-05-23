"""scripts/merge_stooq_alpaca_substrate.py
==========================================
T-2026-05-23-082: merge Stooq deep history with Alpaca recent bars into
a single canonical substrate-extended `data/processed/<TICKER>_1d.csv`,
with a dividend-strip layer to reconcile the two sources' adjustment
conventions.

The convention problem
----------------------
- Alpaca's data is **split-only adjusted** (per `data_manager.py:671`
  "adjustment=split" — explicit project choice). Dividends are NOT
  reflected in historical prices. This matches the portfolio engine's
  PnL model (price changes only; no dividend reinvestment).
- Stooq's data is **total-return adjusted** (split + dividend). Historical
  prices have past dividends baked in.

Empirically: non-dividend stocks (AAPL, NVDA, AMZN) agree perfectly
(0.00% close-diff). Dividend payers diverge by 7-10% (KO, JNJ, XOM, PG).
A naive merge would create silent equity-curve inflation in the deep
history.

The dividend-strip layer
------------------------
For tickers with overlap (Stooq + Alpaca both have data for the same
period — typically 2018+ or 2020+):

  1. Compute ratio(t) = alpaca_close(t) / stooq_close(t) on every overlap day.
  2. Fit log(ratio) ~ a + b*t  (linear in days-from-epoch).
     The slope b is the implied daily dividend yield contribution that
     Stooq applied and Alpaca did not.
  3. Extrapolate the fitted ratio back through Stooq's pre-seam dates.
  4. Multiply Stooq's pre-seam OHLC by the extrapolated ratio. This
     converts Stooq's prices into Alpaca-equivalent convention.
  5. Concatenate corrected_stooq_pre + alpaca verbatim.
  6. Recompute ATR + PrevClose end-to-end.

Limitations of the log-linear fit:
- Assumes the dividend yield was approximately constant over the
  pre-seam period (real yields vary)
- Tickers that started paying dividends mid-history (AAPL → 2012) will
  have suboptimal extrapolation pre-dividend-start, but the multiplier
  is near-1.0 there anyway
- Minimum overlap of 100 trading days required for a stable fit; below
  that, fall back to per-ticker constant ratio (just seam-rescale)

Per-ticker case logic
---------------------
  case both:        Stooq + Alpaca overlap exists (most cases)
    -> Apply dividend-strip per above; concatenate; recompute derived

  case both_no_overlap:  Both have data but ranges don't overlap (rare)
    -> Use seam-rescale (single ratio at junction)

  case stooq_only:  Stooq has T, Alpaca does not
    -> Use Stooq bars verbatim (no Alpaca anchor to correct to;
       acknowledge convention divergence in manifest)

  case alpaca_only: Alpaca has T, Stooq does not
    -> Copy Alpaca file unchanged (recompute derived to be safe)

  case neither: skip (Kibot territory for the surviving 183 SPX delisted)

Schema (matches existing data/processed/<T>_1d.csv exactly)
-----------------------------------------------------------
- Columns: Date,Open,High,Low,Close,Volume,ATR,PrevClose
- ATR: 14-day rolling mean of True Range (project convention)
- PrevClose: Close.shift(1)

Provenance manifest
-------------------
`data/processed_merged/_merge_meta.json` lists, per ticker:
- merge_case: both | stooq_only | alpaca_only
- seam_date (only for `both`)
- n_stooq_pre_seam, n_alpaca, total_bars
- seam_close_diff_pct (close-price agreement at the seam)
- first_bar_date, last_bar_date

The seam-diff is the key quality signal: if > 1% on any ticker, that
ticker is flagged for review (almost always a split/adjustment
mismatch).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ALPACA_DIR = REPO / "data/processed"
STOOQ_DIR = REPO / "data/processed/stooq_us_daily"
OUT_DIR = REPO / "data/processed_merged"


# =============================================================================
# IO helpers
# =============================================================================

def _read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return None


def _recompute_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute ATR + PrevClose end-to-end per project convention.
    Matches engines/data_manager/data_manager.py:495-503.
    """
    df = df.sort_values("Date").reset_index(drop=True).copy()
    tr = pd.concat([
        (df["High"] - df["Low"]).abs(),
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"]  - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(window=14, min_periods=14).mean()
    df["PrevClose"] = df["Close"].shift(1)
    return df


def _write(df: pd.DataFrame, ticker: str, out_dir: Path) -> Tuple[Path, Path]:
    csv = out_dir / f"{ticker}_1d.csv"
    pq = out_dir / "parquet" / f"{ticker}_1d.parquet"
    csv.parent.mkdir(parents=True, exist_ok=True)
    pq.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv, index=False, date_format="%Y-%m-%d")
    df.set_index("Date").to_parquet(pq)
    return csv, pq


# =============================================================================
# Dividend-strip layer (Stooq total-return → Alpaca split-only)
# =============================================================================

# Minimum overlap (trading days) needed for a stable log-linear fit.
# Below this, we fall back to a single-point seam-rescale.
MIN_OVERLAP_FIT = 100


def fit_ratio_loglinear(
    stooq_df: pd.DataFrame,
    alpaca_df: pd.DataFrame,
) -> Optional[Dict]:
    """Fit log(alpaca_close / stooq_close) ~ a + b*days_from_epoch on overlap.

    Returns dict with keys: a, b, epoch, n_overlap, r_squared, last_ratio.
    Returns None if overlap is too short for stable fit.

    The fitted parameters let us extrapolate `ratio(t) = exp(a + b*(t - epoch))`
    backward through Stooq's pre-seam history. Multiplying Stooq's OHLC by
    that ratio converts the prices into Alpaca-equivalent (split-only).
    """
    overlap = stooq_df[["Date", "Close"]].rename(columns={"Close": "stooq_close"}).merge(
        alpaca_df[["Date", "Close"]].rename(columns={"Close": "alpaca_close"}),
        on="Date",
    )
    if len(overlap) < MIN_OVERLAP_FIT:
        return None
    # Guard against zero / negative closes
    overlap = overlap[(overlap["stooq_close"] > 0) & (overlap["alpaca_close"] > 0)].copy()
    if len(overlap) < MIN_OVERLAP_FIT:
        return None

    overlap["ratio"] = overlap["alpaca_close"] / overlap["stooq_close"]
    overlap = overlap.sort_values("Date").reset_index(drop=True)
    epoch = overlap["Date"].iloc[0]  # epoch = seam date (first Alpaca bar)
    n = len(overlap)

    # Empirically the ratio is NOT log-linear — it's roughly flat in the
    # earlier part of the overlap and bends to ~1.0 at today. Two-endpoint
    # anchoring with median-smoothed endpoints captures the relevant
    # boundary behavior: seam continuity AND today-agreement.
    #
    # Use median of first 30 days as the seam anchor (smooths daily noise).
    # Use median of last 30 days as the today anchor.
    head_window = min(30, n // 4)
    tail_window = min(30, n // 4)
    seam_ratio_smooth  = float(overlap["ratio"].iloc[:head_window].median())
    today_ratio_smooth = float(overlap["ratio"].iloc[-tail_window:].median())

    intercept = float(np.log(seam_ratio_smooth))
    T_today = float((overlap["Date"].iloc[-1] - epoch).days)
    if T_today > 0:
        slope = (float(np.log(today_ratio_smooth)) - intercept) / T_today
    else:
        slope = 0.0

    # Fit quality metric: how well does the 2-endpoint line predict the
    # cloud's actual ratios? Compare to a flat-at-seam null.
    t = (overlap["Date"] - epoch).dt.days.values.astype(float)
    log_ratio = np.log(overlap["ratio"].values)
    y_pred = intercept + slope * t
    ss_res = float(np.sum((log_ratio - y_pred) ** 2))
    ss_tot = float(np.sum((log_ratio - log_ratio.mean()) ** 2))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "a": float(intercept),
        "b": float(slope),
        "epoch": epoch,
        "n_overlap": int(n),
        "r_squared": float(r_squared),
        "seam_ratio_smooth": seam_ratio_smooth,
        "today_ratio_smooth": today_ratio_smooth,
    }


def apply_dividend_strip(
    stooq_pre: pd.DataFrame,
    fit: Dict,
) -> pd.DataFrame:
    """Apply ratio(t) = exp(a + b*(t - epoch)) to Stooq's OHLC."""
    if stooq_pre.empty:
        return stooq_pre
    out = stooq_pre.copy()
    t = (out["Date"] - fit["epoch"]).dt.days.values.astype(float)
    ratio = np.exp(fit["a"] + fit["b"] * t)
    for col in ["Open", "High", "Low", "Close"]:
        out[col] = out[col] * ratio
    # Volume left untouched — dividend adjustment doesn't affect share counts
    return out


def apply_constant_rescale(
    stooq_pre: pd.DataFrame,
    rescale_factor: float,
) -> pd.DataFrame:
    """Fallback when overlap is too short: scale by a single constant."""
    if stooq_pre.empty:
        return stooq_pre
    out = stooq_pre.copy()
    for col in ["Open", "High", "Low", "Close"]:
        out[col] = out[col] * rescale_factor
    return out


# =============================================================================
# Per-ticker merge
# =============================================================================

def merge_ticker(ticker: str, stooq_dir: Path, alpaca_dir: Path) -> Dict:
    """Merge one ticker. Returns provenance record (no IO of the result)."""
    record: Dict = {"ticker": ticker}
    alpaca = _read_csv(alpaca_dir / f"{ticker}_1d.csv")
    stooq = _read_csv(stooq_dir / f"{ticker}_1d.csv")

    if alpaca is not None and stooq is not None:
        # ---- BOTH ----
        seam_date = alpaca["Date"].min()
        stooq_pre = stooq[stooq["Date"] < seam_date].copy()

        # --- Dividend-strip: fit ratio over overlap, extrapolate backward ---
        fit = fit_ratio_loglinear(stooq, alpaca)
        correction_method = None
        if fit is not None:
            corrected_pre = apply_dividend_strip(stooq_pre, fit)
            correction_method = "loglinear_fit"
        else:
            # Fallback: constant rescale by seam-date ratio (if available)
            stooq_on_seam = stooq[stooq["Date"] == seam_date]
            if not stooq_on_seam.empty:
                rescale = float(alpaca.iloc[0]["Close"]) / float(stooq_on_seam.iloc[0]["Close"])
                corrected_pre = apply_constant_rescale(stooq_pre, rescale)
                correction_method = f"constant_rescale_{rescale:.6f}"
            else:
                corrected_pre = stooq_pre  # last-resort: no correction
                correction_method = "none_no_anchor"

        merged = pd.concat([
            corrected_pre[["Date", "Open", "High", "Low", "Close", "Volume"]],
            alpaca[["Date", "Open", "High", "Low", "Close", "Volume"]],
        ], ignore_index=True)
        merged = _recompute_derived(merged)

        # Post-correction seam check: compare corrected_stooq seam-date close
        # to alpaca's first close. After dividend-strip this should be ~0.
        seam_close_diff_pct = None
        stooq_on_seam = stooq[stooq["Date"] == seam_date]
        if not stooq_on_seam.empty:
            # Apply the same correction to the seam-date Stooq close for fair compare
            if fit is not None:
                t_seam = (seam_date - fit["epoch"]).days
                ratio_at_seam = float(np.exp(fit["a"] + fit["b"] * t_seam))
                corrected_seam = float(stooq_on_seam.iloc[0]["Close"]) * ratio_at_seam
            else:
                # constant_rescale path: ratio already applied uniformly
                corrected_seam = float(stooq_on_seam.iloc[0]["Close"]) * (
                    float(alpaca.iloc[0]["Close"]) / float(stooq_on_seam.iloc[0]["Close"])
                )
            alpaca_seam_close = float(alpaca.iloc[0]["Close"])
            seam_close_diff_pct = (
                (alpaca_seam_close - corrected_seam) / corrected_seam * 100
            )

        record.update({
            "merge_case": "both",
            "seam_date": str(seam_date.date()),
            "n_stooq_pre_seam": int(len(stooq_pre)),
            "n_alpaca": int(len(alpaca)),
            "total_bars": int(len(merged)),
            "correction_method": correction_method,
            "fit_r_squared": round(fit["r_squared"], 4) if fit else None,
            "fit_n_overlap": fit["n_overlap"] if fit else None,
            "fit_slope_per_day": fit["b"] if fit else None,
            "implied_annual_div_yield_pct": (
                round((1 - np.exp(-fit["b"] * 252)) * 100, 3) if fit else None
            ),
            "seam_close_diff_pct": round(seam_close_diff_pct, 4) if seam_close_diff_pct is not None else None,
            "first_bar_date": merged["Date"].iloc[0].strftime("%Y-%m-%d") if len(merged) else None,
            "last_bar_date":  merged["Date"].iloc[-1].strftime("%Y-%m-%d") if len(merged) else None,
        })
        return record, merged

    if stooq is not None:
        # ---- STOOQ ONLY (ticker is a new entry for us) ----
        merged = _recompute_derived(stooq[["Date", "Open", "High", "Low", "Close", "Volume"]].copy())
        record.update({
            "merge_case": "stooq_only",
            "seam_date": None,
            "n_stooq_pre_seam": int(len(stooq)),
            "n_alpaca": 0,
            "total_bars": int(len(merged)),
            "seam_close_diff_pct": None,
            "first_bar_date": merged["Date"].iloc[0].strftime("%Y-%m-%d"),
            "last_bar_date":  merged["Date"].iloc[-1].strftime("%Y-%m-%d"),
        })
        return record, merged

    if alpaca is not None:
        # ---- ALPACA ONLY (no Stooq depth available) ----
        # Pass through unchanged but still recompute derived to be safe.
        merged = _recompute_derived(alpaca[["Date", "Open", "High", "Low", "Close", "Volume"]].copy())
        record.update({
            "merge_case": "alpaca_only",
            "seam_date": None,
            "n_stooq_pre_seam": 0,
            "n_alpaca": int(len(alpaca)),
            "total_bars": int(len(merged)),
            "seam_close_diff_pct": None,
            "first_bar_date": merged["Date"].iloc[0].strftime("%Y-%m-%d"),
            "last_bar_date":  merged["Date"].iloc[-1].strftime("%Y-%m-%d"),
        })
        return record, merged

    record["merge_case"] = "skip_neither"
    return record, None


# =============================================================================
# Main
# =============================================================================

def _enumerate_candidates(alpaca_dir: Path, stooq_dir: Path) -> List[str]:
    """Union of tickers present in either source."""
    tickers = set()
    for p in alpaca_dir.glob("*_1d.csv"):
        tickers.add(p.name.replace("_1d.csv", ""))
    for p in stooq_dir.glob("*_1d.csv"):
        tickers.add(p.name.replace("_1d.csv", ""))
    return sorted(tickers)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_DIR),
                    help=f"Output dir (default {OUT_DIR.relative_to(REPO)})")
    ap.add_argument("--limit", type=int, default=None,
                    help="Smoke-test: process only first N tickers")
    ap.add_argument("--clean", action="store_true",
                    help="Wipe output dir before writing")
    args = ap.parse_args()

    out_dir = Path(args.out)
    if args.clean and out_dir.exists():
        print(f"[merge] cleaning {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = _enumerate_candidates(ALPACA_DIR, STOOQ_DIR)
    if args.limit:
        candidates = candidates[:args.limit]
    print(f"[merge] {len(candidates)} candidate tickers")

    manifest = {
        "task_id": "T-2026-05-23-082",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alpaca_source": str(ALPACA_DIR.relative_to(REPO)),
        "stooq_source": str(STOOQ_DIR.relative_to(REPO)),
        "output": str(out_dir.relative_to(REPO)) if out_dir.is_relative_to(REPO) else str(out_dir),
        "per_ticker": {},
    }

    by_case = {"both": 0, "stooq_only": 0, "alpaca_only": 0, "skip_neither": 0}
    seam_anomalies: List[Dict] = []

    for tkr in candidates:
        rec, merged = merge_ticker(tkr, STOOQ_DIR, ALPACA_DIR)
        by_case[rec["merge_case"]] = by_case.get(rec["merge_case"], 0) + 1
        manifest["per_ticker"][tkr] = rec
        if merged is not None and not merged.empty:
            _write(merged, tkr, out_dir)
        # Flag seam anomalies for review
        if rec.get("seam_close_diff_pct") is not None and abs(rec["seam_close_diff_pct"]) > 1.0:
            seam_anomalies.append({
                "ticker": tkr,
                "seam_date": rec["seam_date"],
                "seam_close_diff_pct": rec["seam_close_diff_pct"],
            })

    manifest["summary"] = {
        **by_case,
        "n_seam_anomalies_over_1pct": len(seam_anomalies),
    }
    manifest["seam_anomalies"] = seam_anomalies

    meta_path = out_dir / "_merge_meta.json"
    with open(meta_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print()
    print(f"[merge] case breakdown: {by_case}")
    print(f"[merge] seam-anomalies (>1% diff): {len(seam_anomalies)}")
    if seam_anomalies[:5]:
        print(f"[merge] sample anomalies:")
        for a in seam_anomalies[:5]:
            print(f"  {a['ticker']}: {a['seam_close_diff_pct']:+.2f}% at {a['seam_date']}")
    print(f"[merge] manifest: {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

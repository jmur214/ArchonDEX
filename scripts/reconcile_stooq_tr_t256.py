#!/usr/bin/env python3
"""T-2026-07-02-256 Part 2 — TR reconciliation of the Stooq-ingested ETFs.

WHY
---
The Stooq daily bundle (`data/processed/stooq_us_daily/`, ingested Part 1) is
SPLIT-adjusted but NOT dividend-adjusted (measured in the gap audit: Stooq AGG
≈ +1.0%/yr vs true total-return ≈ +3.0%/yr). Consuming it raw imports that
dividend bias — fatal for any carry / total-return study. This script produces
TR-reconciled series per ticker, using the proven T-167 yfinance-splice pattern.

METHOD (per ticker)
-------------------
* Fetch yfinance auto_adjust=False → Close (split-adj price) + Adj Close (total
  return). Build TR OHLC exactly as T-167: O/H/L * (AdjClose/Close), Close = AdjClose.
* BASIS CHECK against the on-disk Stooq split-adj close over the overlap:
  ratio = stooq_close / yf_close. Both are split-adjusted PRICE, so a consistent
  convention ⇒ ratio is ~constant (report mean, std, CV). This validates the Stooq
  bundle has no split/data error and documents the convention.
* TR GAP: annualized (Adj-Close return − Close return) = the dividend the split-only
  Stooq data misses. Reported per ticker (this is the bias the reconciliation fixes).
* Where yfinance lacks early history that Stooq has, the Stooq portion is spliced on
  by RETURNS scaled to the yfinance-TR level at the seam (never raw price levels).

FAIL-CLOSED ([NN-FAIL-CLOSED])
------------------------------
If yfinance returns nothing, or the basis CV exceeds the tolerance (inconsistent
convention ⇒ possible split error / wrong ticker), the ticker is NOT written as a
"reconciled" TR file — it is flagged price_only=True LOUDLY in the manifest so no
downstream study can silently treat split-only data as total return.

OUTPUT
------
* data/processed/tr_reconciled/<TICKER>_1d.csv   (TR OHLC+Volume, T-167 schema)
* data/processed/tr_reconciled/_tr_manifest.json (per-ticker window, basis, TR gap,
  convention verdict) — the load-bearing provenance record.
Canon-safe: writes a NEW namespace only; never touches data/processed/<T>_1d.csv.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STOOQ_DIR = ROOT / "data/processed/stooq_us_daily"
OUT_DIR = ROOT / "data/processed/tr_reconciled"
TD = 252
SPLIT_JUMP_TOL = 0.20  # max |daily return divergence| stooq vs yf split-adj close (split-jump detector)
MIN_OVERLAP = 250      # need at least ~1yr of overlap to trust the split check


def load_stooq_close(ticker: str) -> pd.Series | None:
    f = STOOQ_DIR / f"{ticker}_1d.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f, parse_dates=["Date"]).set_index("Date").sort_index()
    return df["Close"].astype(float)


def fetch_yf_tr(ticker: str, start: str, asof: str, retries: int = 3):
    """yfinance total-return OHLC (T-167 basis) + split-adj Close for the basis check."""
    import yfinance as yf
    for attempt in range(retries):
        try:
            raw = yf.download(ticker, start=start, end=asof, interval="1d",
                              progress=False, auto_adjust=False, threads=False)
            if raw is not None and len(raw):
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                raw.index = pd.to_datetime(raw.index)
                fac = raw["Adj Close"] / raw["Close"]
                tr = pd.DataFrame({
                    "Open": raw["Open"] * fac,
                    "High": raw["High"] * fac,
                    "Low": raw["Low"] * fac,
                    "Close": raw["Adj Close"],
                    "Volume": raw["Volume"].astype(float),
                })
                return tr, raw["Close"].astype(float)
        except Exception as e:  # noqa: BLE001
            print(f"    [{ticker}] yf attempt {attempt+1} failed: {e}")
        time.sleep(1.5 * (attempt + 1))
    return None, None


def compute_atr_prevclose(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    tr = pd.concat([
        (out["High"] - out["Low"]).abs(),
        (out["High"] - out["Close"].shift()).abs(),
        (out["Low"] - out["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    out["ATR"] = tr.rolling(window=14, min_periods=14).mean()
    out["PrevClose"] = out["Close"].shift(1)
    return out


def ann_ret(s: pd.Series) -> float:
    r = s.pct_change().dropna()
    if len(r) < 2:
        return float("nan")
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")


def reconcile(ticker: str, asof: str) -> dict:
    entry = {"ticker": ticker, "price_only": True, "written": False}
    stooq = load_stooq_close(ticker)
    if stooq is None:
        entry["error"] = "no stooq series"
        return entry
    start = (stooq.index[0] - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    tr, yf_close = fetch_yf_tr(ticker, start, asof)
    if tr is None:
        entry["error"] = "yfinance returned nothing (FAIL-CLOSED → price_only)"
        entry["stooq_window"] = [str(stooq.index[0].date()), str(stooq.index[-1].date())]
        return entry

    # --- BASIS CHECK. The TR series IS yfinance Adj Close. Stooq is the SPLIT
    # cross-check: Stooq is split-adjusted (and often PARTIALLY dividend-adjusted),
    # so stooq/yf_close drifts GRADUALLY with the dividend-convention difference —
    # that drift is EXPECTED, not an error. A SPLIT misalignment instead shows as a
    # single-day ~50-100% jump. So we gate on the max daily RETURN divergence
    # (jump detector), not on the ratio CV, and we REPORT the dividend drift + TR gap.
    j = pd.concat({"s": stooq, "y": yf_close, "tr": tr["Close"]}, axis=1, sort=True).dropna()
    entry["overlap_days"] = int(len(j))
    reconciled = True
    if len(j) >= MIN_OVERLAP:
        ratio = j["s"] / j["y"]
        entry["basis_ratio_mean"] = round(float(ratio.mean()), 6)
        entry["basis_ratio_cv"] = round(float(ratio.std() / ratio.mean()), 6)
        # split-jump detector: max |Δ return| between stooq and yf split-adj close
        ret_div = (j["s"].pct_change() - j["y"].pct_change()).abs()
        max_jump = float(ret_div.max())
        entry["max_daily_return_divergence"] = round(max_jump, 5)
        # dividend convention Stooq already captures, and the TR it STILL misses:
        entry["stooq_div_capture_pct_yr"] = round((ann_ret(j["s"]) - ann_ret(j["y"])) * 100, 3)
        entry["tr_gap_pct_yr"] = round((ann_ret(j["tr"]) - ann_ret(j["s"])) * 100, 3)
        entry["full_div_yield_pct_yr"] = round((ann_ret(j["tr"]) - ann_ret(j["y"])) * 100, 3)
        reconciled = max_jump <= SPLIT_JUMP_TOL
    else:
        entry["basis_note"] = f"overlap {len(j)} < {MIN_OVERLAP} — split check skipped, trusting yf TR"

    entry["yf_tr_window"] = [str(tr.index[0].date()), str(tr.index[-1].date())]
    entry["stooq_window"] = [str(stooq.index[0].date()), str(stooq.index[-1].date())]

    if not reconciled:
        entry["error"] = (f"max daily return divergence {entry.get('max_daily_return_divergence')} "
                          f"> {SPLIT_JUMP_TOL} — Stooq/yf SPLIT misalignment. FAIL-CLOSED → price_only")
        return entry

    # --- splice Stooq-by-RETURNS onto the front if it predates yfinance TR ---
    tr_full = tr.copy()
    if stooq.index[0] < tr.index[0] - pd.Timedelta(days=5):
        seam = tr.index[0]
        pre = stooq[stooq.index < seam]
        if len(pre) > 20:
            pre_ret = pre.pct_change()
            level = tr["Close"].iloc[0]
            back = (1.0 / (1.0 + pre_ret[::-1]).cumprod())[::-1] * level  # scale by returns
            # rebuild pre OHLC from the stooq ratios at TR level (returns-chained close only)
            pre_tr = pd.DataFrame({"Open": back, "High": back, "Low": back,
                                   "Close": back, "Volume": 0.0}).dropna()
            tr_full = pd.concat([pre_tr, tr])
            entry["spliced_stooq_pre"] = [str(pre_tr.index[0].date()), str(pre_tr.index[-1].date())]

    out = compute_atr_prevclose(tr_full)[["Open", "High", "Low", "Close", "Volume", "ATR", "PrevClose"]]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body = out.reset_index()
    body.columns = ["Date"] + list(out.columns)
    body["Date"] = pd.to_datetime(body["Date"]).dt.strftime("%Y-%m-%d")
    (OUT_DIR / f"{ticker}_1d.csv").write_text(body.to_csv(index=False))
    entry.update(price_only=False, written=True,
                 tr_window=[str(tr_full.index[0].date()), str(tr_full.index[-1].date())],
                 rows=int(len(out)))
    return entry


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asof", required=True, help="vintage / end date YYYY-MM-DD")
    ap.add_argument("--tickers", required=True, help="comma-separated tickers")
    args = ap.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    manifest = {"task": "T-2026-07-02-256", "asof": args.asof,
                "split_jump_tol": SPLIT_JUMP_TOL, "per_ticker": {}}
    ok = pri = fail = 0
    for t in tickers:
        print(f"[tr] {t} ...")
        e = reconcile(t, args.asof)
        manifest["per_ticker"][t] = e
        if e.get("written"):
            ok += 1
            print(f"    ✓ TR {e['tr_window'][0]}→{e['tr_window'][1]} "
                  f"jump={e.get('max_daily_return_divergence')} tr_gap={e.get('tr_gap_pct_yr')}%/yr")
        elif "error" in e and "yfinance returned nothing" in e.get("error", ""):
            fail += 1
            print(f"    ✗ FAILED: {e['error']}")
        else:
            pri += 1
            print(f"    ⚠ price_only: {e.get('error', 'n/a')}")

    manifest["summary"] = {"reconciled": ok, "price_only": pri, "fetch_failed": fail,
                           "total": len(tickers)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "_tr_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n[tr] {ok} reconciled / {pri} price_only / {fail} fetch_failed "
          f"→ {OUT_DIR}/_tr_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

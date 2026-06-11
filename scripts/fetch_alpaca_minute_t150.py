"""
scripts/fetch_alpaca_minute_t150.py
===================================
T-2026-06-11-150 Part B — index-level minute-bar features from Alpaca's free
tier (IEX feed, 2016+), aggregated to DAILY features at pull time (raw minutes
are NOT retained — disk + we only need the daily aggregates).

PRICE-SHAPE FEATURES ONLY (the research's explicit caveat: IEX is ~3% of
consolidated volume — volume/imbalance features are unreliable on this feed
and are deliberately NOT computed; price-shape features are tolerable):
  fhh_ret       first-half-hour log return (09:30 open -> 10:00 ET)
  or_frac       opening-range fraction: (H-L of first 30min) / prev close
  last30_ret    last-half-hour log return (15:30 -> 16:00 close)

Symbols: SPY, QQQ, IWM, DIA, TLT, GLD (index level — the regime-conditioning
consumers want market state, not single names).

Keys: read from the MAIN worktree .env (worktrees don't carry it); never
echoed. Incremental: per-symbol parquet + last-date state; re-runs append.
Cache: data/research/minute_features_t150/ — NOT a baked substrate dir
(image bakes processed/raw/governor only) -> no manifest regen (T-131 checked).

Usage: python -m scripts.fetch_alpaca_minute_t150 [--symbols SPY,QQQ] [--start 2016-01-01]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "research" / "minute_features_t150"
MAIN_ENV = Path("/Users/jacksonmurphy/Dev/trading_machine-2/.env")
SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "TLT", "GLD"]


def _load_keys() -> tuple[str, str]:
    from dotenv import dotenv_values
    vals = dotenv_values(MAIN_ENV)
    key = vals.get("APCA_API_KEY_ID") or vals.get("ALPACA_API_KEY")
    sec = vals.get("APCA_API_SECRET_KEY") or vals.get("ALPACA_SECRET_KEY")
    if not key or not sec:
        raise RuntimeError("Alpaca keys not found in main .env")
    return key, sec


def fetch_symbol(sym: str, start: str, end: str) -> pd.DataFrame | None:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import DataFeed

    key, sec = _load_keys()
    client = StockHistoricalDataClient(key, sec)
    feats = []
    years = pd.date_range(start, end, freq="YS").tolist() or [pd.Timestamp(start)]
    for y0 in years:
        y1 = min(y0 + pd.DateOffset(years=1), pd.Timestamp(end))
        try:
            req = StockBarsRequest(symbol_or_symbols=sym, timeframe=TimeFrame.Minute,
                                   start=y0.to_pydatetime(), end=y1.to_pydatetime(),
                                   feed=DataFeed.IEX)
            bars = client.get_stock_bars(req).df
        except Exception as e:
            print(f"[T150-B] WARN {sym} {y0.year}: {type(e).__name__}: {e}", flush=True)
            continue
        if bars is None or bars.empty:
            continue
        df = bars.reset_index()
        ts = pd.to_datetime(df["timestamp"]).dt.tz_convert("America/New_York")
        df["d"] = ts.dt.normalize().dt.tz_localize(None)
        df["t"] = ts.dt.hour * 60 + ts.dt.minute
        first30 = df[(df["t"] >= 570) & (df["t"] < 600)]   # 09:30-09:59
        last30 = df[(df["t"] >= 930) & (df["t"] < 960)]    # 15:30-15:59
        close_bar = df[df["t"] < 960].groupby("d").last()

        f30 = first30.groupby("d").agg(
            o_open=("open", "first"), o_close=("close", "last"),
            o_high=("high", "max"), o_low=("low", "min"))
        l30 = last30.groupby("d").agg(l_open=("open", "first"),
                                      l_close=("close", "last"))
        day = f30.join(l30, how="left").join(
            close_bar[["close"]].rename(columns={"close": "day_close"}), how="left")
        import numpy as np
        day["fhh_ret"] = np.log(day["o_close"] / day["o_open"])
        day["prev_close"] = day["day_close"].shift(1)
        day["or_frac"] = (day["o_high"] - day["o_low"]) / day["prev_close"]
        day["last30_ret"] = np.log(day["l_close"] / day["l_open"])
        feats.append(day[["fhh_ret", "or_frac", "last30_ret"]].dropna(how="all"))
        print(f"[T150-B] {sym} {y0.year}: {len(day)} days", flush=True)
    if not feats:
        return None
    out = pd.concat(feats).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out["symbol"] = sym
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2025-12-31")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sym in [s.strip().upper() for s in args.symbols.split(",")]:
        dest = OUT_DIR / f"{sym}.parquet"
        start = args.start
        if dest.exists():
            old = pd.read_parquet(dest)
            start = str((old.index.max() + pd.Timedelta(days=1)).date())
            if start > args.end:
                print(f"[T150-B] {sym}: up to date")
                continue
        df = fetch_symbol(sym, start, args.end)
        if df is None:
            print(f"[T150-B] {sym}: NO DATA (entitlement/feed?)")
            continue
        if dest.exists():
            df = pd.concat([pd.read_parquet(dest), df])
            df = df[~df.index.duplicated(keep="last")].sort_index()
        df.to_parquet(dest)
        print(f"[T150-B] {sym}: wrote {len(df)} days "
              f"({df.index.min().date()}..{df.index.max().date()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

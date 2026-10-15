"""ARCHIVED 2026-10-15 from engines/data_manager/tr_writer.py — the total-return writer's Alpaca provider.

Retired by the director's ruling: ONE provider for the whole universe (yfinance). Measured on a
copy of the processed cache: the project's Alpaca feed is IEX, whose daily history starts
2020-07-27; of the 172 files the per-span rule sent to Alpaca, 69 came back empty, 69 of the 103
that returned could not cover the cached span, and 99 of the 103 read DIFFERENT_CONVENTION against
the cache. Kept verbatim, never deleted ([NN-ARCHIVE]). Not importable as a writer provider: the
writer's DEFAULT_PROVIDERS no longer names it.
"""
from __future__ import annotations

import os

import pandas as pd

COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


class WriterRefusal(RuntimeError):
    """Local copy so this archived module stands alone."""


def alpaca_provider(ticker: str, start: pd.Timestamp, end: pd.Timestamp, adjusted: bool) -> pd.DataFrame:
    """Alpaca, same feed as DataManager (IEX): adjustment="all" -> total return; "split" otherwise."""
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    key = os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY")
    if not (key and secret):
        raise WriterRefusal("no Alpaca keys — the writer will not substitute another provider")
    client = StockHistoricalDataClient(key, secret)
    req = StockBarsRequest(symbol_or_symbols=ticker, timeframe=TimeFrame.Day,
                           start=pd.Timestamp(start).tz_localize("UTC"),
                           end=pd.Timestamp(end).tz_localize("UTC"),
                           adjustment="all" if adjusted else "split", feed="iex", limit=10000)
    df = client.get_stock_bars(req).df
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index().set_index("timestamp")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                            "close": "Close", "volume": "Volume"})
    return df[COLUMNS].sort_index()

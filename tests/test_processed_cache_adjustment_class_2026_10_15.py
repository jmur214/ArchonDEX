"""The processed price cache's ADJUSTMENT CLASS, asserted from the DATA — not a docstring.

R's B-1 read (R-5), re-derived 2026-10-15: `engines/data_manager/data_manager.py`'s comments,
the Alpaca fetch (`adjustment="split"`), and the T-082b merge design all say the cache is
SPLIT-ONLY ("price changes only; no dividend reinvestment"). The files are DIVIDEND
BACK-ADJUSTED: against the split-only Alpaca bars in data/raw/, processed/raw drifts at each
name's dividend yield (XOM +3.51, KO +3.06, SPY +1.33 %/yr over 2023-01-03..2025-12-30), and
the pre-merge backup (`data/processed_alpaca_backup_2026_05_23`) already held the same
values — the merge's premise "Alpaca is split-only" was false when it ran.

Which convention the program WANTS is an open ruling (it is a substrate change either way,
[NN-SUBSTRATE-REVERIFY]). Until then this lock pins what IS true. If the cache is rebuilt to
either convention, this test fails BY DESIGN: update it together with the health_check row,
never quietly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
PROCESSED = REPO / "data" / "processed"
RAW = REPO / "data" / "raw"

# A floor well under each name's measured drift: dividend back-adjustment is unmistakable
# above it, and a split-only cache sits at ~0 (no splits in the 2023-2025 window).
DIVIDEND_FLOOR = {"XOM": 0.020, "KO": 0.020, "SPY": 0.008}


def _annual_drift(processed: pd.Series, raw: pd.Series) -> float:
    """Annualised drift of processed/raw over their common dates. ~0 when both carry the
    same adjustment; ~ +yield when `processed` is dividend back-adjusted and `raw` is not."""
    j = pd.concat([processed.rename("p"), raw.rename("r")], axis=1, join="inner").dropna()
    if len(j) < 100:
        raise ValueError(f"only {len(j)} common days — too few to classify")
    ratio = j["p"] / j["r"]
    years = (j.index[-1] - j.index[0]).days / 365.25
    return float((ratio.iloc[-1] / ratio.iloc[0]) ** (1 / years) - 1)


def _load(ticker: str) -> tuple:
    p, r = PROCESSED / f"{ticker}_1d.csv", RAW / f"{ticker}_1d.csv"
    if not (p.exists() and r.exists()):
        pytest.skip(f"{ticker}: processed or raw bars not on disk in this environment "
                    f"(CI / a fresh clone) — the class cannot be measured honestly here")
    proc = pd.read_csv(p, parse_dates=["Date"]).set_index("Date")["Close"]
    raw = pd.read_csv(r)
    raw.index = pd.to_datetime(raw["timestamp"], utc=True).dt.tz_convert(None).dt.normalize()
    return proc, raw["close"]


# ── the measure itself, on synthetic series (runs everywhere) ───────────────────

def _synthetic(yield_pa: float) -> tuple:
    idx = pd.bdate_range("2023-01-02", periods=750)
    raw = pd.Series(100.0 * (1 + 0.0002) ** np.arange(len(idx)), index=idx)
    years = (idx - idx[-1]).days / 365.25              # <= 0: back-adjust toward the past
    back_adjusted = raw * (1 + yield_pa) ** years
    return back_adjusted, raw


def test_the_measure_reads_a_back_adjusted_series_at_its_yield():
    proc, raw = _synthetic(0.035)
    assert _annual_drift(proc, raw) == pytest.approx(0.035, abs=0.002)


def test_the_measure_reads_identical_conventions_as_zero():
    _, raw = _synthetic(0.0)
    assert abs(_annual_drift(raw, raw)) < 1e-12


# ── the lock, on the real cache ─────────────────────────────────────────────────

@pytest.mark.parametrize("ticker", sorted(DIVIDEND_FLOOR))
def test_the_processed_cache_is_DIVIDEND_back_adjusted_not_split_only_as_documented(ticker):
    proc, raw = _load(ticker)
    drift = _annual_drift(proc, raw)
    assert drift > DIVIDEND_FLOOR[ticker], (
        f"{ticker}: processed/raw drift {drift*100:+.2f}%/yr — the cache no longer reads as "
        f"dividend back-adjusted. If it was rebuilt to a ruled convention, update this lock "
        f"AND the health_check row together; if not, something rewrote the substrate.")

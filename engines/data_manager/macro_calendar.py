"""Macro event calendar — FOMC decision dates (T-2026-07-07-290, deliverable 3).

Single source of truth for FOMC decision dates: `config/fomc_calendar.json`
(1994-2025 carried byte-for-byte from the old hardcoded list in
`scripts/calendar_flow_probe_t250.py`; 2026 transcribed from federalreserve.gov,
never from model memory). C's T-291 detector consumes the two functions below.

CONTRACT (stable):
    config path : config/fomc_calendar.json  (key "decision_dates": list[YYYY-MM-DD])
    is_fomc_week(date) -> bool
    days_to_next_decision(date) -> Optional[int]
"""
from __future__ import annotations

import json
from datetime import date as _date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
FOMC_CALENDAR_PATH = _ROOT / "config" / "fomc_calendar.json"

DateLike = Union[str, _date, datetime, pd.Timestamp]

_CACHE: dict = {}


def load_fomc_dates(path: Optional[Union[str, Path]] = None) -> List[pd.Timestamp]:
    """Sorted FOMC decision dates (normalized to midnight). Cached per path."""
    p = Path(path) if path else FOMC_CALENDAR_PATH
    key = str(p)
    if key not in _CACHE:
        if not p.exists():
            raise FileNotFoundError(f"FOMC calendar missing: {p}")
        raw = json.loads(p.read_text())["decision_dates"]
        _CACHE[key] = sorted(pd.Timestamp(d).normalize() for d in raw)
    return _CACHE[key]


def _monday(d: pd.Timestamp) -> pd.Timestamp:
    d = pd.Timestamp(d).normalize()
    return d - timedelta(days=int(d.weekday()))   # Monday of d's week


def is_fomc_week(date: DateLike, path: Optional[Union[str, Path]] = None) -> bool:
    """True if `date` falls in the same Mon-Sun week as an FOMC decision date
    (weekly-resolution — the convention the T-250 even-week probe uses)."""
    dates = load_fomc_dates(path)
    wk = _monday(pd.Timestamp(date))
    weeks = {_monday(f) for f in dates}
    return wk in weeks


def days_to_next_decision(date: DateLike, path: Optional[Union[str, Path]] = None) -> Optional[int]:
    """Calendar days from `date` to the NEXT FOMC decision on/after it (0 if
    `date` IS a decision day). None if `date` is past the last known decision
    (calendar exhausted — the caller should extend the config)."""
    d = pd.Timestamp(date).normalize()
    future = [f for f in load_fomc_dates(path) if f >= d]
    return int((future[0] - d).days) if future else None


__all__ = ["load_fomc_dates", "is_fomc_week", "days_to_next_decision", "FOMC_CALENDAR_PATH"]

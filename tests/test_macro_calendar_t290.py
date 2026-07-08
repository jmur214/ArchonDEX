"""T-2026-07-07-290 d3 — FOMC macro calendar loader + the C/T-291 contract."""
import subprocess
import re

import pandas as pd
import pytest

from engines.data_manager.macro_calendar import (
    load_fomc_dates, is_fomc_week, days_to_next_decision, FOMC_CALENDAR_PATH,
)


def test_config_exists_and_loads():
    dates = load_fomc_dates()
    assert FOMC_CALENDAR_PATH.exists()
    assert len(dates) == 265                       # 257 historical + 8 (2026)
    assert dates == sorted(dates)                  # sorted
    assert str(dates[0].date()) == "1994-02-04"
    assert str(dates[-1].date()) == "2026-12-09"


def test_regression_le2025_byte_identical_to_hardcoded():
    """The loader must reproduce the OLD hardcoded 1994-2025 list byte-for-byte
    (the retrofit regression: it faithfully carries the prior source of truth)."""
    # Pinned to the LAST commit carrying the hardcoded list — origin/main no
    # longer has it after the retrofit merged, so a moving ref self-invalidates.
    PRE_RETROFIT = "5ce87820d25f661b0d0286026252ac6517811a9b"
    src = subprocess.run(["git", "show", f"{PRE_RETROFIT}:scripts/calendar_flow_probe_t250.py"],
                         capture_output=True, text=True).stdout
    hard = re.findall(r'"(\d{4}-\d{2}-\d{2})"', re.search(r"FOMC=\[(.*?)\]", src, re.S).group(1))
    loaded_le2025 = [d.strftime("%Y-%m-%d") for d in load_fomc_dates() if d <= pd.Timestamp("2025-12-31")]
    assert loaded_le2025 == hard                   # byte-for-byte historical identity


def test_is_fomc_week():
    assert is_fomc_week("2026-01-28") is True       # a decision day
    assert is_fomc_week("2026-01-26") is True        # Mon of the decision week
    assert is_fomc_week("2026-02-10") is False       # an off-week
    assert is_fomc_week("2025-12-10") is True         # historical decision day


def test_days_to_next_decision():
    assert days_to_next_decision("2026-01-28") == 0   # on a decision day
    assert days_to_next_decision("2026-02-01") == 45  # → 2026-03-18
    assert days_to_next_decision("2026-12-09") == 0
    assert days_to_next_decision("2027-01-01") is None  # calendar exhausted → extend config


def test_accepts_multiple_datelike_types():
    for d in ["2026-03-18", pd.Timestamp("2026-03-18"), pd.Timestamp("2026-03-18").date()]:
        assert is_fomc_week(d) is True
        assert days_to_next_decision(d) == 0

"""tests/test_mbl_gate.py
========================
Regression tests for T-083 MBL Gate-0 (core/measurement/mbl_gate.py).
"""
from __future__ import annotations

import math
import pytest

from core.measurement.mbl_gate import (
    check_mbl_gate,
    compute_mbl_min,
    compute_n_effective,
    years_from_window,
)


# ---------------- compute_mbl_min ----------------

def test_compute_mbl_min_at_n_eq_1_is_zero():
    """No multiple-testing accumulation → MBL = 0."""
    assert compute_mbl_min(n_effective=1, sr_target=1.0) == 0.0
    assert compute_mbl_min(n_effective=1, sr_target=1.55) == 0.0


def test_compute_mbl_min_at_n_100_sr_1_matches_dev_spec():
    """Dev's 2026-05-16 metrics dive: N=100, SR=1.0 → ~9.2 years."""
    result = compute_mbl_min(n_effective=100, sr_target=1.0)
    assert math.isclose(result, 9.21, abs_tol=0.01)


def test_compute_mbl_min_at_n_1000_sr_1_matches_dev_spec():
    """Dev: N=1000, SR=1.0 → ~13.8 years."""
    result = compute_mbl_min(n_effective=1000, sr_target=1.0)
    assert math.isclose(result, 13.82, abs_tol=0.01)


def test_compute_mbl_min_sr_target_scaling():
    """Higher SR_target reduces required T (quadratic relationship)."""
    n = 100
    mbl_at_1 = compute_mbl_min(n, sr_target=1.0)
    mbl_at_2 = compute_mbl_min(n, sr_target=2.0)
    # SR doubles → MBL quarters
    assert math.isclose(mbl_at_2, mbl_at_1 / 4, abs_tol=0.001)


def test_compute_mbl_min_rejects_invalid_n():
    with pytest.raises(ValueError, match="n_effective must be >= 1"):
        compute_mbl_min(n_effective=0, sr_target=1.0)
    with pytest.raises(ValueError, match="n_effective must be >= 1"):
        compute_mbl_min(n_effective=-5, sr_target=1.0)


def test_compute_mbl_min_rejects_invalid_sr():
    with pytest.raises(ValueError, match="sr_target must be > 0"):
        compute_mbl_min(n_effective=100, sr_target=0.0)
    with pytest.raises(ValueError, match="sr_target must be > 0"):
        compute_mbl_min(n_effective=100, sr_target=-1.0)


# ---------------- check_mbl_gate ----------------

def test_check_passes_when_window_exceeds_min():
    """35 years comfortably clears the 13.8yr MBL at N=1000, SR=1.0."""
    result = check_mbl_gate(t_years=35.0, n_effective=1000, sr_target=1.0)
    assert result["passed"] is True
    assert result["margin_years"] > 20.0
    assert "PASS" in result["reason"]


def test_check_fails_at_5yr_n100_sr1():
    """The dev's load-bearing example: 5yr can't clear DSR at N=100,SR=1.0."""
    result = check_mbl_gate(t_years=5.0, n_effective=100, sr_target=1.0)
    assert result["passed"] is False
    assert result["margin_years"] < 0
    assert result["mbl_min"] > 9.0
    assert "FAIL" in result["reason"]
    assert "under-powered" in result["reason"]


def test_check_passes_at_5yr_n100_sr155():
    """The dev's high-SR-target case: with SR=1.55, 5yr is enough at N=100."""
    result = check_mbl_gate(t_years=5.0, n_effective=100, sr_target=1.55)
    assert result["passed"] is True
    assert result["mbl_min"] < 5.0


def test_check_at_boundary_passes():
    """T_years exactly == MBL_min counts as PASS (>=, not >)."""
    mbl = compute_mbl_min(n_effective=50, sr_target=1.0)
    result = check_mbl_gate(t_years=mbl, n_effective=50, sr_target=1.0)
    assert result["passed"] is True
    assert math.isclose(result["margin_years"], 0.0, abs_tol=1e-9)


def test_check_reason_contains_diagnostic_numbers():
    """The reason string should help a human diagnose why."""
    result = check_mbl_gate(t_years=4.0, n_effective=100, sr_target=1.0)
    assert "4.00" in result["reason"]    # the t_years
    assert "9.21" in result["reason"]    # the mbl_min
    assert "100" in result["reason"]     # n_effective
    assert "1.0" in result["reason"]     # sr_target


# ---------------- years_from_window ----------------

def test_years_from_window_5year():
    y = years_from_window("2021-01-01", "2026-01-01")
    assert math.isclose(y, 5.0, abs_tol=0.01)


def test_years_from_window_substrate_extension():
    """1970-2026 should give ~56 years (extended-substrate depth)."""
    y = years_from_window("1970-01-01", "2026-01-01")
    assert math.isclose(y, 56.0, abs_tol=0.1)


# ---------------- compute_n_effective ----------------

def test_compute_n_effective_returns_at_least_1_when_db_missing(tmp_path):
    """Bootstrap safety: no registry file → return 1 (no prior trials)."""
    nonexistent = tmp_path / "no_such_db.sqlite"
    assert compute_n_effective(db_path=nonexistent) == 1


def test_compute_n_effective_counts_real_rows(tmp_path):
    """Functional test against a tiny in-memory-ish sqlite."""
    import sqlite3
    db = tmp_path / "test_registry.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, snapshot_at TEXT)")
    conn.execute("INSERT INTO runs VALUES ('a', '2026-01-01')")
    conn.execute("INSERT INTO runs VALUES ('b', '2026-02-01')")
    conn.execute("INSERT INTO runs VALUES ('c', '2026-03-01')")
    conn.commit()
    conn.close()

    assert compute_n_effective(db_path=db) == 3
    # since-filter should also work
    assert compute_n_effective(db_path=db, since_iso="2026-02-15") == 1

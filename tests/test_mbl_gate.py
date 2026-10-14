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


def test_compute_mbl_min_upper_bound_reproduces_dev_spec():
    """The 2026-05-16 metrics dive's figures (N=100 → 9.21yr, N=1000 → 13.82yr at SR=1)
    are the 2·ln(N) UPPER BOUND. RR-3: the bound stays available for comparison; it is
    no longer the gate."""
    assert math.isclose(compute_mbl_min(100, 1.0, upper_bound=True), 9.21, abs_tol=0.01)
    assert math.isclose(compute_mbl_min(1000, 1.0, upper_bound=True), 13.82, abs_tol=0.01)


def test_compute_mbl_min_default_is_the_exact_form():
    """RR-3: MinBTL = E[max_N]^2 / SR^2 (Bailey et al. 2014). The bound overstates the
    required window by ~44% at N=100 and ~30% at N=1000."""
    assert math.isclose(compute_mbl_min(100, 1.0), 6.404, abs_tol=0.01)
    assert math.isclose(compute_mbl_min(1000, 1.0), 10.596, abs_tol=0.01)
    for n in (10, 100, 260, 1000):
        assert compute_mbl_min(n, 1.0) < compute_mbl_min(n, 1.0, upper_bound=True)


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
    """The dev's load-bearing example still holds under the exact form: 5yr cannot clear
    DSR at N=100, SR=1.0 (MinBTL 6.40yr exact; 9.21yr was the bound)."""
    result = check_mbl_gate(t_years=5.0, n_effective=100, sr_target=1.0)
    assert result["passed"] is False
    assert result["margin_years"] < 0
    assert result["mbl_min"] > 6.0
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
    assert "6.40" in result["reason"]    # the mbl_min (exact form)
    assert "exact" in result["reason"]   # RR-3: the formula is named, never implied
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

def test_compute_n_effective_fails_closed_when_db_missing(tmp_path):
    """RR-3. A missing registry is not evidence of zero prior trials: it must RAISE.
    (This test previously required the opposite, and N=1 makes Gate 0 vacuous — the
    registry is absent in every cloud container, so the lock was on the defect.)"""
    from core.measurement.mbl_gate import HonestNUnavailableError
    with pytest.raises(HonestNUnavailableError):
        compute_n_effective(db_path=tmp_path / "no_such_db.sqlite")


def test_compute_n_effective_fails_closed_on_empty_or_unreadable_registry(tmp_path):
    """The same door by other routes: an empty `runs` table (was `max(1, 0)`), and a
    0-byte file (a real one sits beside the registry: data/observability/run_registry.db)."""
    import sqlite3
    from core.measurement.mbl_gate import HonestNUnavailableError
    empty = tmp_path / "empty.sqlite"
    c = sqlite3.connect(empty); c.execute("CREATE TABLE runs (run_id TEXT)"); c.commit(); c.close()
    with pytest.raises(HonestNUnavailableError):
        compute_n_effective(db_path=empty)
    zero = tmp_path / "zero.db"; zero.write_bytes(b"")
    with pytest.raises(HonestNUnavailableError):
        compute_n_effective(db_path=zero)


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

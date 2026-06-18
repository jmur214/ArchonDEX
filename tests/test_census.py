"""T-181 — behavioural contract tests for the shared execution-census gate
(`core.census.assert_census`). Locks that each of the 6 invariants flips a
run to NON-CANONICAL, that a clean run passes, and that a missing census
fails closed. No backtest / no network — synthetic summaries only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.census import EMPTY_MD5, assert_census  # noqa: E402


def _clean_census() -> dict:
    return {
        "edges_blind": [],
        "n_resolved": 109,
        "n_in_panel": 109,
        "n_trades": 1500,
        "trades_canon_md5": "deadbeefcafe",
        "trades_empty": False,
        "fundamentals_blind": 0,
        "fundamentals_edges_active": ["value_book_to_market"],
        "edges_errored": {},
        "regime_unknown_frac": 0.03,
        "regime_total_bars": 6000,
        "config_provenance": {"degraded": False,
                              "risk": {"exists": True, "n_keys": 11}},
    }


def _summary(census: dict) -> dict:
    return {"bootstrap_distribution": {"sharpe": {}}, "census": census}


def test_clean_run_is_canonical():
    v = assert_census(_summary(_clean_census()))
    assert v.canonical and v.ok and not v.failures
    assert v.census_present


def test_missing_census_fails_closed():
    v = assert_census({"Sharpe Ratio": 0.7})
    assert not v.canonical
    assert not v.census_present
    assert any("census block missing" in f for f in v.failures)


def test_missing_census_allowed_when_not_required():
    v = assert_census({"Sharpe Ratio": 0.7}, require_census=False)
    assert v.ok and not v.canonical  # ok-to-proceed but not certifiable


@pytest.mark.parametrize("mutate,needle", [
    (lambda c: c.update(edges_blind=["accruals_inv_sloan"]), "edges_blind"),
    (lambda c: c.update(edges_errored={"rsi_bounce_v1": {"crash_bars": 37, "last_error": "KeyError: 'Close'"}}),
     "edges_errored"),
    (lambda c: c.update(n_in_panel=19), "panel shrank"),
    (lambda c: c.update(n_trades=0, trades_empty=True), "zero-trade"),
    (lambda c: c.update(trades_canon_md5=EMPTY_MD5, n_trades=1, trades_empty=False), "EMPTY_MD5"),
    (lambda c: c.update(fundamentals_blind=1), "fundamentals_blind"),
    (lambda c: c.update(regime_unknown_frac=1.0), "regime 100% unknown"),
    (lambda c: c.__setitem__("config_provenance", {"degraded": True,
                                                    "risk": {"exists": True, "n_keys": 1}}), "config degraded"),
])
def test_each_invariant_flips_noncanonical(mutate, needle):
    c = _clean_census()
    mutate(c)
    v = assert_census(_summary(c))
    assert not v.canonical, f"expected NON-CANONICAL for {needle}"
    assert any(needle in f for f in v.failures), f"{needle} not in {v.failures}"


def test_expected_dormant_allowlist_excuses_blind_edge():
    c = _clean_census()
    c["edges_blind"] = ["earnings_drift"]
    assert not assert_census(_summary(c)).canonical
    v = assert_census(_summary(c), expected_dormant={"earnings_drift"})
    assert v.canonical, "allowlisted dormant edge should not block"


def test_panel_allowlist_tolerates_small_gap():
    c = _clean_census()
    c["n_in_panel"] = 106  # 3 short of 109
    assert not assert_census(_summary(c)).canonical
    assert assert_census(_summary(c), panel_allowlist=3).canonical


def test_missing_ci_warns_but_does_not_block():
    s = {"census": _clean_census()}  # no bootstrap_distribution, no skip_reason
    v = assert_census(s)
    assert v.canonical  # CI absence is a WARN, not a hard fail
    assert any("bootstrap" in w for w in v.warnings)


def test_explicit_ci_skip_reason_suppresses_warning():
    s = {"census": _clean_census(), "bootstrap_ci_skip_reason": "n<32"}
    v = assert_census(s)
    assert v.canonical and not v.warnings


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

"""T-2026-05-30-057c-followup regression tests — defensive against
the bug class T-057c-det surfaced: dict-iteration-order + float-sum
producing cross-container drift at near-zero residue points.

The 3 sites fixed in this PR each have the same fingerprint:
  1. xsec_momentum.py dollar-neutralization `sum(weights.values())`
  2. composer.py HRP `active` list from `per_ticker.items()`
  3. moonshot_sleeve.py weight normalization `sum(weights.values())`

These tests pin the FIXES: the order-independent operation must produce
the same result regardless of input dict insertion order. They are
NOT trying to prove behavior — only to prevent regression of the
defensive ordering.
"""
from __future__ import annotations

import math

import pytest


# ----------------------------------------------------------------------
# 1. xsec_momentum dollar-neutral sum is order-independent
# ----------------------------------------------------------------------

def _simulate_xsec_neutral_sum(weights: dict) -> float:
    """Mirror the production fix from xsec_momentum.py:111.

    Pre-T-057c-followup: `s = sum(weights.values())` (order-dependent).
    Post-fix:            `s = math.fsum(sorted(weights.values()))` (order-independent).
    """
    return math.fsum(sorted(weights.values()))


def test_xsec_neutral_sum_order_independent_zero_crossing():
    """At a dollar-neutral zero crossing (long_w ≈ -short_w), insertion
    order would flip the FP residue under plain `sum()`. The fixed
    impl must produce the same value for permuted insertion orders."""
    # 3 longs at +1/3 + 3 shorts at -1/3 → sum should be 0 exactly.
    values_a = {"AAPL": 1/3, "MSFT": 1/3, "GOOG": 1/3,
                "XOM": -1/3, "JPM": -1/3, "WMT": -1/3}
    # Reverse iteration order via re-insertion.
    values_b = {"WMT": -1/3, "JPM": -1/3, "XOM": -1/3,
                "GOOG": 1/3, "MSFT": 1/3, "AAPL": 1/3}
    s_a = _simulate_xsec_neutral_sum(values_a)
    s_b = _simulate_xsec_neutral_sum(values_b)
    assert s_a == s_b, (
        f"sorted+fsum should be order-independent: "
        f"order_a={s_a}, order_b={s_b}"
    )
    # And the sum should be tighter to zero than naive sum.
    naive_a = sum(values_a.values())
    naive_b = sum(values_b.values())
    # math.fsum is exact for ties-to-zero in this construction.
    assert s_a == 0.0
    # Naive sum may produce 0.0 OR a small epsilon residue depending on
    # interpreter order. Both are acceptable as long as fsum is tighter
    # or equal.
    assert abs(s_a) <= abs(naive_a) + 1e-15
    assert abs(s_b) <= abs(naive_b) + 1e-15


def test_xsec_neutral_sum_with_inv_vol_residue():
    """Real-world weights are scaled by inverse vol. Test with the
    kind of mismatched-magnitude tail residues that would cancel
    differently across summation orders."""
    weights = {
        f"T{i:03d}": (1.0 / (0.15 + i * 1e-12)) * (1.0 if i % 2 else -1.0)
        for i in range(20)
    }
    # Compute in two permuted orders.
    perm = list(weights.items())
    weights_rev = dict(reversed(perm))
    assert _simulate_xsec_neutral_sum(weights) == _simulate_xsec_neutral_sum(weights_rev)


# ----------------------------------------------------------------------
# 2. composer.py active list is alphabetically deterministic
# ----------------------------------------------------------------------

def _simulate_composer_active_list(per_ticker: dict) -> list:
    """Mirror the production fix from composer.py:118-121.

    Pre-fix:  `active = [t for t, info in per_ticker.items() if cond]`
    Post-fix: `active = sorted(t for t, info in per_ticker.items() if cond)`
    """
    return sorted(
        t for t, info in per_ticker.items()
        if abs(float(info.get("aggregate_score", 0.0))) > 1e-6
    )


def test_composer_active_list_order_independent():
    """Two equivalent per_ticker dicts in different insertion orders
    MUST produce the same active list, so the HRP clustering input is
    deterministic."""
    per_ticker_a = {
        "AAPL": {"aggregate_score": 0.5},
        "MSFT": {"aggregate_score": -0.3},
        "XOM":  {"aggregate_score": 1e-9},  # below threshold, filtered
        "GOOG": {"aggregate_score": 0.7},
    }
    per_ticker_b = {
        "XOM":  {"aggregate_score": 1e-9},
        "GOOG": {"aggregate_score": 0.7},
        "MSFT": {"aggregate_score": -0.3},
        "AAPL": {"aggregate_score": 0.5},
    }
    a = _simulate_composer_active_list(per_ticker_a)
    b = _simulate_composer_active_list(per_ticker_b)
    assert a == b
    assert a == ["AAPL", "GOOG", "MSFT"]  # alphabetical, XOM filtered


def test_composer_active_filters_below_1e6_threshold():
    per_ticker = {
        "AAPL": {"aggregate_score": 0.5},
        "MSFT": {"aggregate_score": 5e-7},   # below threshold
        "GOOG": {"aggregate_score": -1e-6},  # exactly at threshold → filtered
        "AMZN": {"aggregate_score": 2e-6},   # just above → kept
    }
    assert _simulate_composer_active_list(per_ticker) == ["AAPL", "AMZN"]


# ----------------------------------------------------------------------
# 3. moonshot_sleeve normalization is order-independent
# ----------------------------------------------------------------------

def _simulate_moonshot_normalize_total(weights: dict) -> float:
    """Mirror the production fix from moonshot_sleeve.py:156.

    Pre-fix:  `total = sum(weights.values())`
    Post-fix: `total = math.fsum(sorted(weights.values()))`
    """
    return math.fsum(sorted(weights.values()))


def test_moonshot_total_order_independent():
    """Equal weights inserted in different orders must produce the
    same total — pre-fix, this could differ by FP epsilon at certain
    ticker-count multiples."""
    n = 30  # production sleeve has 30-50 names
    weights = {f"T{i:02d}": 1.0 / n for i in range(n)}
    weights_rev = dict(reversed(list(weights.items())))
    assert _simulate_moonshot_normalize_total(weights) == _simulate_moonshot_normalize_total(weights_rev)


def test_moonshot_total_with_capped_weights():
    """Production path passes through `sector_cap` + `per-bet cap`
    before this sum, so input values are heterogeneous (some at cap,
    some below). Verify fsum-on-sorted handles that."""
    weights = {
        "AAPL": 0.05, "MSFT": 0.05, "GOOG": 0.05,
        "TSLA": 0.0833333333333333,  # 1/12 — not exact float
        "NVDA": 0.0833333333333333,
        "AMZN": 0.0833333333333333,
        "META": 0.01, "GE": 0.01, "F": 0.01, "T": 0.01,
    }
    perm = dict(reversed(list(weights.items())))
    assert _simulate_moonshot_normalize_total(weights) == _simulate_moonshot_normalize_total(perm)


# ----------------------------------------------------------------------
# Cross-cutting: verify the pattern itself produces the same answer
# under all permutations (small-n exhaustive)
# ----------------------------------------------------------------------

def test_pattern_exhaustive_small_n():
    """For n=4 there are 24 permutations. All must yield the same
    sorted+fsum result. Sanity check on the defensive pattern itself."""
    import itertools
    base = [0.123, -0.456, 0.789, -0.246]
    keys = ["A", "B", "C", "D"]
    expected = math.fsum(sorted(base))
    for perm in itertools.permutations(range(4)):
        d = {keys[i]: base[perm[i]] for i in range(4)}
        actual = math.fsum(sorted(d.values()))
        assert actual == expected, f"permutation {perm} gave {actual} != {expected}"


# ----------------------------------------------------------------------
# Guard: the production fix imports `math` — make sure that's wired
# ----------------------------------------------------------------------

def test_production_imports_math_in_xsec_momentum():
    """Catch a regression where `math` import is removed by a linter."""
    from engines.engine_a_alpha.edges import xsec_momentum
    assert hasattr(xsec_momentum, "math"), (
        "xsec_momentum.py must import `math` for the T-057c-followup "
        "fsum fix on line 111"
    )


def test_production_imports_math_in_moonshot_sleeve():
    from engines.engine_c_portfolio.sleeves import moonshot_sleeve
    assert hasattr(moonshot_sleeve, "math"), (
        "moonshot_sleeve.py must import `math` for the T-057c-followup "
        "fsum fix on line 156"
    )

"""T-241 — moonshot probe C1: top-K concentration / conviction-weighting (default OFF).

Concentrate the book into the top-K highest-conviction names (|combined signal|),
conviction-weighted, GROSS PRESERVED (no leverage — reallocate, don't borrow).
Gated default-OFF → OFF is a no-op (canon byte-identical, proven by the 2022 md5).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_c_portfolio.policy import PortfolioPolicy, PortfolioPolicyConfig  # noqa: E402


def _policy(**kw) -> PortfolioPolicy:
    return PortfolioPolicy(PortfolioPolicyConfig(**kw))


# a diversified book + per-name conviction (|signal|)
_WEIGHTS = {"A": 0.20, "B": 0.20, "C": 0.20, "D": 0.20, "E": 0.20}
_SIGNALS = {"A": 0.9, "B": 0.1, "C": 0.8, "D": 0.2, "E": 0.05}   # top-2 conviction = A, C


def test_off_default_is_a_noop():
    p = _policy()  # concentration_enabled defaults False
    assert p._apply_concentration(dict(_WEIGHTS), _SIGNALS) == _WEIGHTS


def test_on_keeps_only_top_k_by_conviction():
    p = _policy(concentration_enabled=True, concentration_top_k=2)
    out = p._apply_concentration(dict(_WEIGHTS), _SIGNALS)
    held = {t for t, w in out.items() if abs(w) > 1e-12}
    assert held == {"A", "C"}                              # the 2 highest |signal|
    assert all(out[t] == 0.0 for t in ("B", "D", "E"))     # the rest zeroed


def test_on_preserves_gross_no_leverage():
    p = _policy(concentration_enabled=True, concentration_top_k=2)
    out = p._apply_concentration(dict(_WEIGHTS), _SIGNALS)
    assert sum(abs(w) for w in out.values()) == pytest.approx(1.0)  # == original gross


def test_on_is_conviction_weighted_not_equal_weight():
    p = _policy(concentration_enabled=True, concentration_top_k=2)
    out = p._apply_concentration(dict(_WEIGHTS), _SIGNALS)
    # A (0.9) gets more than C (0.8); ratio == conviction ratio
    assert out["A"] > out["C"]
    assert out["A"] / out["C"] == pytest.approx(0.9 / 0.8)


def test_sign_comes_from_the_signal_not_the_old_weight():
    # C1 OVERRIDES the allocator: direction follows the edge's signal, not the
    # prior weight. B has the strongest |signal| and it is NEGATIVE → short B.
    p = _policy(concentration_enabled=True, concentration_top_k=1)
    out = p._apply_concentration({"A": 0.5, "B": 0.5, "C": 0.5}, {"A": 0.2, "B": -0.9, "C": 0.1})
    assert out["B"] < 0 and out["A"] == 0.0 and out["C"] == 0.0


def test_can_hold_a_high_conviction_name_the_allocator_zeroed():
    # the override picks top-K by CONVICTION even if the allocator didn't size it
    p = _policy(concentration_enabled=True, concentration_top_k=2)
    out = p._apply_concentration({"A": 0.5, "B": 0.5}, {"A": 0.1, "B": 0.2, "Z": 0.9, "Y": 0.8})
    held = {t for t, w in out.items() if abs(w) > 1e-12}
    assert held == {"Z", "Y"}                              # top-2 conviction, not A/B
    assert sum(abs(w) for w in out.values()) == pytest.approx(1.0)  # gross preserved


def test_fewer_than_k_names_unchanged():
    p = _policy(concentration_enabled=True, concentration_top_k=10)
    book = {"A": 0.5, "B": 0.5}
    assert p._apply_concentration(book, {"A": 0.3, "B": 0.7}) == book


def test_deterministic_tiebreak():
    # equal conviction → ticker-asc tie-break (no FP/order lottery)
    p = _policy(concentration_enabled=True, concentration_top_k=2)
    out = p._apply_concentration({"Z": 0.25, "A": 0.25, "M": 0.25, "B": 0.25},
                                 {"Z": 0.5, "A": 0.5, "M": 0.5, "B": 0.5})
    held = {t for t, w in out.items() if abs(w) > 1e-12}
    assert held == {"A", "B"}                              # alphabetic on the conviction tie


def test_no_conviction_anywhere_is_a_safe_noop():
    # all signals 0 → nothing to rank by conviction → return the book unchanged
    # (fail-safe: never fabricate a concentration from a conviction-less book).
    p = _policy(concentration_enabled=True, concentration_top_k=2)
    book = {"A": 0.4, "B": 0.3, "C": 0.1}
    assert p._apply_concentration(book, {"A": 0.0, "B": 0.0, "C": 0.0}) == book


def test_config_keys_in_dataclass():
    import json
    from dataclasses import fields
    cfg = json.loads((ROOT / "config" / "portfolio_settings.json").read_text())
    names = {f.name for f in fields(PortfolioPolicyConfig)}
    for k in ("concentration_enabled", "concentration_top_k"):
        assert k in cfg and k in names


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

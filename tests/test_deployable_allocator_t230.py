"""T-230 — DEPLOYABLE cash-account allocator mode (default OFF, canon-safe).

D's T-215 found the mean_variance book runs to ~2.32x gross (borrowing) and can
hold shorts — neither executable in a $5-15K CASH Roth. The deployable mode
projects the allocator output onto the executable cone: long-only, per-name
[0, max], gross Σw ≤ max_gross. Gated default-OFF → OFF is a no-op (canon
byte-identical, proven separately by the 2022 md5).
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


# the kind of book D diagnosed: 2.32x gross, includes a short
_LEVERED = {"AAPL": 0.30, "MSFT": 0.30, "NVDA": 0.30, "AMZN": 0.30,
            "GOOGL": 0.30, "META": 0.30, "TSLA": 0.32, "XOM": -0.10}  # Σ|w|=2.32, gross(Σw)=2.22


def test_off_default_is_a_noop():
    p = _policy()  # deployable_cash_account defaults False
    assert p._apply_deployable_constraints(dict(_LEVERED)) == _LEVERED


def test_on_zeros_shorts_long_only():
    p = _policy(deployable_cash_account=True)
    out = p._apply_deployable_constraints(dict(_LEVERED))
    assert all(w >= 0.0 for w in out.values())            # no shorts
    assert out["XOM"] == 0.0                                # the short → 0


def test_on_clamps_each_name_to_max_weight():
    p = _policy(deployable_cash_account=True, deployable_max_weight=0.25)
    out = p._apply_deployable_constraints({"A": 0.40, "B": 0.10})
    assert out["A"] <= 0.25 + 1e-12                         # per-name cap applied pre-renorm


def test_on_caps_gross_at_max_gross_no_leverage():
    p = _policy(deployable_cash_account=True, deployable_max_gross=1.0, deployable_max_weight=0.25)
    out = p._apply_deployable_constraints(dict(_LEVERED))
    assert sum(out.values()) <= 1.0 + 1e-9                  # de-levered to ≤ 1x
    assert sum(out.values()) == pytest.approx(1.0, abs=1e-9)  # was > 1 → scaled to exactly the cap


def test_on_leaves_an_already_executable_book_untouched_modulo_clamp():
    # long, per-name ≤ 0.25, Σw = 0.6 < 1 → cash residual allowed, weights unchanged
    p = _policy(deployable_cash_account=True, deployable_max_gross=1.0, deployable_max_weight=0.25)
    book = {"A": 0.20, "B": 0.25, "C": 0.15}
    out = p._apply_deployable_constraints(book)
    assert out == book                                     # under cap → no de-lever, no short to zero


def test_on_preserves_relative_long_proportions_when_delevering():
    # inputs BELOW the per-name clamp so the de-lever scaling (not the clamp)
    # governs → relative proportions preserved.
    p = _policy(deployable_cash_account=True, deployable_max_gross=1.0, deployable_max_weight=2.0)
    out = p._apply_deployable_constraints({"A": 1.0, "B": 2.0})  # gross 3 → /3
    assert out["B"] == pytest.approx(2 * out["A"])         # 2:1 ratio preserved
    assert sum(out.values()) == pytest.approx(1.0)


def test_empty_weights_safe():
    assert _policy(deployable_cash_account=True)._apply_deployable_constraints({}) == {}


def test_config_keys_in_dataclass():
    # Layer-1 contract: the new JSON keys must be real dataclass fields
    import json
    from dataclasses import fields
    cfg = json.loads((ROOT / "config" / "portfolio_settings.json").read_text())
    names = {f.name for f in fields(PortfolioPolicyConfig)}
    for k in ("deployable_cash_account", "deployable_max_weight", "deployable_max_gross"):
        assert k in cfg and k in names


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))

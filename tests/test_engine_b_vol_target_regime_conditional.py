"""T-2026-05-23-055e regression suite — regime-conditional vol-target
multiplier on top of the EWMA / rolling estimators.

Validates per the T-055e dispatch acceptance:

1. test_regime_aware_default_is_false        — config default preserves T-055d
2. test_regime_aware_false_advisory_ignored  — even with advisory passed, regime_aware=False is a no-op
3. test_regime_aware_true_advisory_none      — regime_aware=True + advisory=None still no-op (safe)
4. test_regime_summary_to_multiplier_dispatch — each summary value picks the right multiplier
5. test_unknown_regime_summary_falls_back_to_unity — schema-drift safety
6. test_advisory_missing_regime_summary_key  — partial advisory dict → no-op
7. test_regime_aware_with_ewma_estimator     — composes with EWMA (acceptance: scale moves vs no-advisory baseline)
8. test_regime_aware_with_rolling_estimator  — composes with rolling
9. test_regime_aware_determinism             — repeated calls bit-identical
10. test_regime_aware_no_lookahead           — adding future advisory doesn't change past result
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from engines.engine_b_risk.vol_target import (
    VolTargetConfig,
    compute_portfolio_vol_scale,
    _regime_target_multiplier,
    _REGIME_SUMMARY_TO_MULTIPLIER_FIELD,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _build_history(returns: np.ndarray,
                   start: datetime = datetime(2024, 1, 2),
                   initial_equity: float = 100.0) -> list[dict]:
    eq = [initial_equity]
    for r in returns:
        eq.append(eq[-1] * (1.0 + float(r)))
    return [
        {"timestamp": start + timedelta(days=i), "equity": eq[i]}
        for i in range(len(eq))
    ]


# ----------------------------------------------------------------------
# 1. Default behavior preserved
# ----------------------------------------------------------------------

def test_regime_aware_default_is_false():
    """A VolTargetConfig with no regime_aware field set MUST default
    to False — preserves T-055 / T-055c / T-055d on-main behavior."""
    cfg = VolTargetConfig(enabled=True)
    assert cfg.regime_aware is False
    # Default multipliers also frozen at the dispatch-recommended values.
    assert cfg.benign_target_multiplier == 1.0
    assert cfg.cautious_target_multiplier == 0.85
    assert cfg.stressed_target_multiplier == 0.60
    assert cfg.crisis_target_multiplier == 0.40


# ----------------------------------------------------------------------
# 2. regime_aware=False short-circuits even when advisory is supplied
# ----------------------------------------------------------------------

def test_regime_aware_false_advisory_ignored():
    """When regime_aware=False, the advisory dict MUST be ignored —
    the multiplier helper returns 1.0 regardless of advisory content."""
    cfg = VolTargetConfig(enabled=True, regime_aware=False)
    for summary in ("benign", "cautious", "stressed", "crisis"):
        m = _regime_target_multiplier(cfg, {"regime_summary": summary})
        assert m == 1.0, f"regime_aware=False but multiplier={m} for {summary}"


# ----------------------------------------------------------------------
# 3. regime_aware=True with advisory=None falls back safely
# ----------------------------------------------------------------------

def test_regime_aware_true_advisory_none():
    """regime_aware=True but advisory=None must still produce 1.0 —
    can't pick a multiplier without a regime signal."""
    cfg = VolTargetConfig(enabled=True, regime_aware=True)
    assert _regime_target_multiplier(cfg, None) == 1.0
    assert _regime_target_multiplier(cfg, {}) == 1.0


# ----------------------------------------------------------------------
# 4. Dispatch table — each summary maps to the configured multiplier
# ----------------------------------------------------------------------

def test_regime_summary_to_multiplier_dispatch():
    """Each of the 4 known regime_summary values maps to the
    corresponding config field."""
    cfg = VolTargetConfig(
        enabled=True, regime_aware=True,
        benign_target_multiplier=1.10,    # custom to detect mis-mapping
        cautious_target_multiplier=0.90,
        stressed_target_multiplier=0.55,
        crisis_target_multiplier=0.35,
    )
    cases = {
        "benign": 1.10,
        "cautious": 0.90,
        "stressed": 0.55,
        "crisis": 0.35,
    }
    for summary, expected in cases.items():
        m = _regime_target_multiplier(cfg, {"regime_summary": summary})
        assert m == expected, (
            f"summary={summary}: expected multiplier {expected}, got {m}"
        )
    # And confirm the dispatch table itself covers exactly these 4
    # keys (Engine E advisory contract).
    assert set(_REGIME_SUMMARY_TO_MULTIPLIER_FIELD.keys()) == set(cases.keys())


# ----------------------------------------------------------------------
# 5. Unknown summary value → safe fallback to 1.0
# ----------------------------------------------------------------------

def test_unknown_regime_summary_falls_back_to_unity():
    """If Engine E's schema ever drifts (new label, typo, etc.), the
    multiplier MUST default to 1.0 — never break sizing on schema drift."""
    cfg = VolTargetConfig(enabled=True, regime_aware=True)
    for bad in ("euphoria", "RECESSION", "", None, 0, 1, True):
        m = _regime_target_multiplier(cfg, {"regime_summary": bad})
        assert m == 1.0, f"bad summary {bad!r} produced multiplier {m}"


# ----------------------------------------------------------------------
# 6. Partial advisory dict (missing regime_summary) → no-op
# ----------------------------------------------------------------------

def test_advisory_missing_regime_summary_key():
    """If advisory dict is non-empty but lacks regime_summary, still
    fall back to 1.0."""
    cfg = VolTargetConfig(enabled=True, regime_aware=True)
    assert _regime_target_multiplier(
        cfg,
        {"risk_scalar": 0.7, "suggested_max_positions": 5},
    ) == 1.0


# ----------------------------------------------------------------------
# 7. End-to-end with EWMA — regime-conditional multiplier moves the scale
# ----------------------------------------------------------------------

def test_regime_aware_with_ewma_estimator():
    """`compute_portfolio_vol_scale` with EWMA estimator AND
    regime_aware=True must produce a scale DIFFERENT from the
    regime_aware=False baseline on the same history. Specifically:
    under "crisis" (multiplier 0.40), the effective target_vol is
    0.04 → target/realized ratio shrinks → scale drops toward floor.
    Under "benign" (multiplier 1.0), behavior matches T-055d EWMA.
    """
    rng = np.random.default_rng(seed=99)
    # 200 days of moderate vol (≈ 14% annualized) — realized vol
    # sits ABOVE the 0.10 target so baseline scale < 1.0.
    history = _build_history(rng.normal(0.0, 0.009, 200))

    cfg_base = VolTargetConfig(
        enabled=True, estimator_type="ewma", ewma_lambda=0.94,
        target_annual_vol=0.10, leverage_floor=0.3, leverage_ceiling=2.0,
        regime_aware=False,
    )
    cfg_regime = VolTargetConfig(
        enabled=True, estimator_type="ewma", ewma_lambda=0.94,
        target_annual_vol=0.10, leverage_floor=0.3, leverage_ceiling=2.0,
        regime_aware=True,
        crisis_target_multiplier=0.40,
        stressed_target_multiplier=0.60,
        cautious_target_multiplier=0.85,
        benign_target_multiplier=1.0,
    )

    s_base = compute_portfolio_vol_scale(history, cfg_base)
    s_benign = compute_portfolio_vol_scale(
        history, cfg_regime, advisory={"regime_summary": "benign"},
    )
    s_crisis = compute_portfolio_vol_scale(
        history, cfg_regime, advisory={"regime_summary": "crisis"},
    )

    # Benign multiplier = 1.0 → should match baseline exactly.
    assert s_benign == s_base, (
        f"benign multiplier=1.0 should match baseline; "
        f"got benign={s_benign} vs base={s_base}"
    )
    # Crisis multiplier = 0.40 → effective target is 0.04 → ratio
    # drops by 0.4× → scale drops materially vs benign.
    assert s_crisis < s_benign - 0.05, (
        f"crisis multiplier should produce a noticeably smaller scale: "
        f"benign={s_benign:.3f} vs crisis={s_crisis:.3f}"
    )
    # Crisis scale should respect the floor.
    assert s_crisis >= 0.3 - 1e-9, f"crisis scale {s_crisis} violates floor"


# ----------------------------------------------------------------------
# 8. End-to-end with rolling estimator — same composition logic
# ----------------------------------------------------------------------

def test_regime_aware_with_rolling_estimator():
    """Same composition test against the rolling-60d estimator."""
    rng = np.random.default_rng(seed=17)
    history = _build_history(rng.normal(0.0, 0.009, 200))

    cfg_base = VolTargetConfig(
        enabled=True, estimator_type="rolling",
        realized_vol_window_days=60, min_returns_required=60,
        target_annual_vol=0.10, leverage_floor=0.3, leverage_ceiling=2.0,
        regime_aware=False,
    )
    cfg_regime = VolTargetConfig(
        enabled=True, estimator_type="rolling",
        realized_vol_window_days=60, min_returns_required=60,
        target_annual_vol=0.10, leverage_floor=0.3, leverage_ceiling=2.0,
        regime_aware=True,
        stressed_target_multiplier=0.50,
    )

    s_base = compute_portfolio_vol_scale(history, cfg_base)
    s_stressed = compute_portfolio_vol_scale(
        history, cfg_regime, advisory={"regime_summary": "stressed"},
    )
    assert s_stressed < s_base, (
        f"stressed (0.50× target) should produce smaller scale than "
        f"baseline: base={s_base:.3f}, stressed={s_stressed:.3f}"
    )


# ----------------------------------------------------------------------
# 9. Determinism
# ----------------------------------------------------------------------

def test_regime_aware_determinism():
    """Repeated calls on the same (history, cfg, advisory) tuple
    produce bit-identical scales."""
    rng = np.random.default_rng(seed=42)
    history = _build_history(rng.normal(0.0, 0.01, 150))
    cfg = VolTargetConfig(
        enabled=True, estimator_type="ewma", ewma_lambda=0.94,
        regime_aware=True,
    )
    advisory = {"regime_summary": "stressed"}
    scales = [compute_portfolio_vol_scale(history, cfg, advisory=advisory)
              for _ in range(10)]
    first = scales[0]
    for s in scales[1:]:
        assert s == first, f"non-deterministic: {scales}"


# ----------------------------------------------------------------------
# 10. No look-ahead — advisory snapshot is consumed at call-time only
# ----------------------------------------------------------------------

def test_regime_aware_no_lookahead():
    """The advisory dict passed at call time is the ONLY input — there's
    no out-of-band state that could leak forward. Confirm by mutating
    the advisory dict AFTER the call: result must NOT change for prior
    calls (Python dict mutation can't retroactively affect a returned
    float)."""
    rng = np.random.default_rng(seed=3)
    history = _build_history(rng.normal(0.0, 0.01, 150))
    cfg = VolTargetConfig(
        enabled=True, estimator_type="ewma", regime_aware=True,
    )
    advisory_mutable = {"regime_summary": "benign"}
    s_benign = compute_portfolio_vol_scale(history, cfg, advisory=advisory_mutable)
    # Now flip the advisory to crisis and re-call; new value differs.
    advisory_mutable["regime_summary"] = "crisis"
    s_crisis = compute_portfolio_vol_scale(history, cfg, advisory=advisory_mutable)
    # Original `s_benign` must NOT be affected by the post-call mutation.
    # (Sanity check on Python value semantics; the real point is to
    # confirm advisory is consumed synchronously per call, not cached.)
    assert s_benign != s_crisis, (
        "expected benign vs crisis to produce different scales; "
        f"benign={s_benign}, crisis={s_crisis}"
    )
    # Re-call with benign restored MUST return the original benign scale.
    advisory_mutable["regime_summary"] = "benign"
    s_benign_re = compute_portfolio_vol_scale(history, cfg, advisory=advisory_mutable)
    assert s_benign_re == s_benign, (
        f"re-evaluation with the same input should match: "
        f"first={s_benign}, retry={s_benign_re}"
    )

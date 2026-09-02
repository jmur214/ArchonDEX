"""tests/test_buyhold_spread_lattice_t349.py — T-349.

The pre-registration's load-bearing claim is an ENUMERATION: the buy/hold-spread family on
the gated-offense signal is finite, and only one member was ever untested. A table in prose
is an assertion; this makes it a receipt anyone can re-run.

The classifier is validated against the two members whose outcomes are already known —
T-298 (constructible, ran) and T-297 Arm 1 (gate-(b) violating, and it failed exactly that
way with a 225-day exit lag). A classifier that could not reproduce those is describing a
model of the strategy rather than the strategy.
"""
from __future__ import annotations

import itertools

import pytest

TOL = 1e-9
STATES = (0.0, 1 / 3, 2 / 3, 1.0)      # ensemble fraction: three speeds, quantized in 1/3
BANDS = (0.0, 1 / 3, 2 / 3, 1.0)       # any band below the quantum cannot bind (T-297)


def held_step(h: float, t: float, b_up: float, b_dn: float) -> float:
    """One day of a two-threshold buy/hold spread on the exposure gate."""
    if t > h and (t - h) > b_up + TOL:
        return t
    if t < h and (h - t) > b_dn + TOL:
        return t
    return h


def full_exposure_reachable(b_up: float, b_dn: float) -> bool:
    """Can full exposure be reached from flat under SOME signal path?

    Reachability, not a monotone ramp: the signal may jump several speeds in one day, and a
    ramp-only test wrongly condemns T-298 (whose whole design is to re-enter on multi-speed
    jumps while suppressing single-increment whipsaws)."""
    seen, frontier = {0.0}, [0.0]
    while frontier:
        h = frontier.pop()
        for t in STATES:
            n = held_step(h, t, b_up, b_dn)
            if n not in seen:
                seen.add(n)
                frontier.append(n)
    return abs(max(seen) - 1.0) < TOL


def exit_lag_zero(b_up: float, b_dn: float) -> bool:
    """Frozen gate (b): a collapse must be followed the SAME day, from any held state."""
    return all(held_step(h, 1 / 3, b_up, b_dn) <= 1 / 3 + TOL
               and held_step(h, 0.0, b_up, b_dn) <= TOL
               for h in STATES)


def classify(b_up: float, b_dn: float) -> str:
    if not full_exposure_reachable(b_up, b_dn):
        return "DEGENERATE"
    if not exit_lag_zero(b_up, b_dn):
        return "VIOLATES_GATE_B"
    if b_up == 0.0 and b_dn == 0.0:
        return "UNDAMPED"
    return "CONSTRUCTIBLE"


# ---------- the classifier reproduces what already happened ----------
def test_t298_classifies_constructible_because_it_ran():
    assert classify(1 / 3, 0.0) == "CONSTRUCTIBLE"


def test_t297_arm1_classifies_as_a_gate_b_violation_because_that_is_how_it_failed():
    """T-297 Arm 1 cut turnover 4x and beat SPY at 5bps — and was rejected for a 225-day
    crash exit lag. The classifier must find that, or it is not modelling this gate."""
    assert classify(1 / 3, 1 / 3) == "VIOLATES_GATE_B"


def test_the_undamped_baseline_is_not_flagged_as_damping():
    assert classify(0.0, 0.0) == "UNDAMPED"


# ---------- the structural results the pre-registration rests on ----------
def test_every_nonzero_maintain_band_violates_the_frozen_exit_gate():
    """THE structural finding: the 'loose to maintain' half of a buy/hold spread is
    unavailable to this strategy on principle. Any nonzero decrease band delays the crash
    exit by construction, and gate (b) is frozen — so the spread can only ever be one-sided
    here. No measurement can overturn this; it is arithmetic on a quantized signal."""
    for b_up, b_dn in itertools.product(BANDS, BANDS):
        if b_dn > TOL:
            assert not exit_lag_zero(b_up, b_dn), f"B_dn={b_dn} unexpectedly preserved the exit"


def test_exactly_one_constructible_member_is_untested():
    """The family is finite and exhausted: undamped, T-298, one untested rung, and
    degenerate cells. There is nothing to sweep."""
    constructible = {(u, d) for u, d in itertools.product(BANDS, BANDS)
                     if classify(u, d) == "CONSTRUCTIBLE"}
    assert constructible == {(1 / 3, 0.0), (2 / 3, 0.0)}
    untested = constructible - {(1 / 3, 0.0)}          # T-298 ran
    assert untested == {(2 / 3, 0.0)}, "the pre-registration's single arm"


def test_the_widest_band_is_degenerate_not_merely_worse():
    """B_up = 1 cannot reach full exposure at all — it is excluded by construction, so it
    is not a 'more conservative' option someone can propose later."""
    assert classify(1.0, 0.0) == "DEGENERATE"


def test_arm_U_can_only_increase_exposure_from_flat():
    """Arm U's mechanism, pre-stated so the result cannot explain it afterwards: exposure
    rises only from zero and only to full; between visits to flat it is monotonically
    non-increasing. That is the cost side of the turnover cut."""
    b_up, b_dn = 2 / 3, 0.0
    for h in (1 / 3, 2 / 3):
        assert all(held_step(h, t, b_up, b_dn) <= h + TOL for t in STATES), \
            "no increase may fire from a partial position"
    assert held_step(0.0, 1.0, b_up, b_dn) == pytest.approx(1.0)   # flat -> full only
    assert held_step(0.0, 2 / 3, b_up, b_dn) == pytest.approx(0.0)


def test_arm_U_preserves_the_exit_invariant():
    assert exit_lag_zero(2 / 3, 0.0)

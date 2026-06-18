"""Measured-mode HALT semantics — fail-closed at the data-load SOURCE.

T-2026-06-17-194 (implements D's T-189 design). The complement to T-181's
post-run execution census: census CATCHES a clouded run after the fact and marks
it non-canonical; this module makes a missing **load-bearing** input for an
**active** consumer HALT at the exact load site, the instant it is detected, in an
explicit MEASURED run (cloud / anchor / hermetic-strict). Outside measured mode
(local dev, paper, tests) the existing graceful degradation is preserved
byte-for-byte — the loader returns its usual empty/None/fallback and the run
continues; the census still trips on the resulting counter (fundamentals_blind,
fallback_to_static, …).

The whole contract is one predicate, one exception, one helper:

    measured AND load_bearing AND active   ⇒  raise MeasurementHalt   (HALT)
    otherwise                              ⇒  return Degraded(...)     (caller degrades as today)

Relationship to hermetic (core/hermetic.py): hermetic governs *network* ("may I
fetch?"); measured governs *halt-on-missing-baked-input* ("must I stop if a
load-bearing input for an active consumer is absent?"). They compose; neither
subsumes the other. The cloud entrypoint sets BOTH.

Determinism: this module changes execution ONLY when is_measured() is True. With
it OFF (the local/test/paper default) every call returns a Degraded sentinel and
the caller's pre-existing degrade path runs unchanged → byte-identical canon.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Exit code for a measured HALT. Same FAIL family as a census-non-canonical
# result (scripts/run_isolated.py returns 2 on a census block); the run boundary
# maps MeasurementHalt to this so cloud/anchor pipelines fail loud + non-zero.
MEASUREMENT_HALT_EXIT = 2

_TRUE = {"1", "true", "on", "yes", "strict"}
_FALSE = {"0", "false", "off", "no", ""}


def is_measured() -> bool:
    """True when this run is a canonical MEASUREMENT that must fail-closed.

    Sources (any True ⇒ measured):
      * ``ARCHONDEX_MEASURED`` explicitly truthy (the cloud entrypoint,
        run_isolated canonical path, and substrate-arm launchers set =1).
      * ``ARCHONDEX_HERMETIC=strict`` — the strictest network mode also implies
        measurement (a baked-input absence should not be silently tolerated).

    An explicit ``ARCHONDEX_MEASURED`` falsey value (0/off/false) FORCES off even
    under hermetic-strict, so a local strict-hermetic debug run can opt out.
    Default OFF → local dev, paper, and tests keep graceful degradation.
    """
    raw = os.environ.get("ARCHONDEX_MEASURED", "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE and raw != "":
        return False  # explicit opt-out wins
    return os.environ.get("ARCHONDEX_HERMETIC", "").strip().lower() == "strict"


class MeasurementHalt(RuntimeError):
    """A load-bearing input for an ACTIVE consumer was missing in a measured run.

    Raised at the data-load site (fundamentals panel, universe membership, …).
    The run boundary (run_isolated / cloud_entrypoint) maps it to a non-zero
    exit in the census-FAIL family — fail-fast, naming the exact site, instead of
    a multi-hour backtest that the census would mark non-canonical anyway.
    """


@dataclass(frozen=True)
class Degraded:
    """Sentinel returned (outside measured mode) when a load-bearing input is
    missing. The caller runs its existing degrade path AND propagates this so the
    run summary can stamp ``degraded=True``/``skip_reason`` (which T-181's census
    treats as a non-canonical FAIL). It is intentionally NOT falsy-magical — the
    caller decides what its degraded value is (None / empty / static list)."""
    site: str
    reason: str


def halt_or_degrade(site: str, *, load_bearing: bool, active: bool, reason: str) -> Degraded:
    """The one decision every guarded load site makes.

    * measured AND load_bearing AND active → raise MeasurementHalt (HALT, NoReturn).
    * otherwise → return a Degraded sentinel; the caller proceeds with its
      pre-existing degrade behavior (unchanged → OFF is byte-identical).

    ``load_bearing``: does a real headline depend on this input this run?
    ``active``: is the consumer that needs it actually turned on this run?
    Both are computed by the caller from the run's active-set / flags (no global
    state) — a missing input is only fatal if something live actually needs it.
    """
    if is_measured() and load_bearing and active:
        raise MeasurementHalt(f"{site}: {reason} [measured-mode HALT: a load-bearing "
                              f"input for an active consumer is missing]")
    return Degraded(site=site, reason=reason)

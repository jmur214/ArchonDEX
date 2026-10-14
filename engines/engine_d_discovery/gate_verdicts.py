"""RR-6a — one tri-state verdict per gauntlet gate: PASSED | FAILED | NOT_EVALUATED(reason).

THE DEFECT CLASS THIS CLOSES. Gate results were two-valued booleans with DEFAULTS, so a gate
that never ran could not be told apart from a verdict — and consumers resolved the same absence
in OPPOSITE directions. The promotion decision read a skipped Gate 7/8 as PASS
(`result.get("gate_7_passed", True)`): every production candidate got a free Gate 7, because
the substrate-B build died on a swallowed NameError. The T-195 foundry harness read Gate 3 —
which has no pass criterion — as FAIL, and two T-196 records name it as their killer when the
forced Gate 4 was.

THE CONTRACT. `validate_candidate` writes `result["gate_verdicts"]` once, with every gate in
GATE_ORDER present. A gate that did not run is NOT_EVALUATED with a reason ("not reached: …",
"no substrate-B data_map provided", …) — an honest state, not a default. Every reader indexes;
none supplies a default, so a missing gate is a KeyError (a programmer error), never a verdict.
  * promotion: every REQUIRED gate (config, `thresholds.required_gates`) must be PASSED; a
    required NOT_EVALUATED refuses, with the reason recorded.
  * attribution: only a FAILED gate is ever named as the killer.
The legacy `gate_N_passed` / `gate_N_evaluated` booleans are DERIVED from the verdicts and
written for every gate, so an unconverted reader can no longer fall through to a default.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

PASSED = "passed"
FAILED = "failed"
NOT_EVALUATED = "not_evaluated"
VERDICTS = (PASSED, FAILED, NOT_EVALUATED)

GATE_ORDER: Tuple[str, ...] = tuple(f"gate_{i}" for i in range(9))
# Gates that record a metric but have no pass criterion: never PASSED/FAILED, never required,
# never named as a killer. Gate 3 (WFO consistency) — RR-6b decides whether it should bind.
RECORDED_ONLY_GATES: Tuple[str, ...] = ("gate_3",)

Verdicts = Dict[str, Dict[str, str]]


def new_verdicts(reason: str = "not reached") -> Verdicts:
    """Every gate NOT_EVALUATED — the truthful state before any gate has run."""
    return {g: {"verdict": NOT_EVALUATED, "reason": reason} for g in GATE_ORDER}


def render(verdicts: Verdicts, gate: str, passed: bool, reason: str) -> None:
    """Record a PASSED/FAILED verdict for a gate that actually ran."""
    if gate not in verdicts:
        raise KeyError(gate)
    if gate in RECORDED_ONLY_GATES:
        raise ValueError(f"{gate} has no pass criterion; record it with not_evaluated()")
    verdicts[gate] = {"verdict": PASSED if passed else FAILED, "reason": str(reason)}


def not_evaluated(verdicts: Verdicts, gate: str, reason: str) -> None:
    """Record that a gate rendered no verdict, and why."""
    if gate not in verdicts:
        raise KeyError(gate)
    verdicts[gate] = {"verdict": NOT_EVALUATED, "reason": str(reason)}


def not_reached(verdicts: Verdicts, after: str, why: str) -> None:
    """Mark every gate still at its initial 'not reached' state with the reason the run stopped."""
    for g, v in verdicts.items():
        if v["verdict"] == NOT_EVALUATED and v["reason"] == "not reached":
            verdicts[g] = {"verdict": NOT_EVALUATED, "reason": f"not reached: {why} (at {after})"}


def promotion_decision(verdicts: Mapping[str, Mapping[str, str]],
                       required: Iterable[str]) -> Tuple[bool, List[str]]:
    """(passed, refusals). Passed iff every required gate is PASSED. A refusal names each required
    gate that is not PASSED, with its verdict and reason — FAILED and NOT_EVALUATED alike."""
    required = tuple(required)
    if not required:
        raise ValueError("no required gates — a gauntlet that requires nothing passes everything")
    refusals = []
    for g in required:
        v = verdicts[g]                                 # KeyError, never a default
        if v["verdict"] not in VERDICTS:
            raise ValueError(f"{g}: unknown verdict {v['verdict']!r}")
        if v["verdict"] != PASSED:
            refusals.append(f"{g}: {v['verdict']} — {v['reason']}")
    return (not refusals, refusals)


def first_failed_gate(result: Mapping[str, Any]) -> Optional[str]:
    """The first gate, in gauntlet order, whose verdict is FAILED; None if none failed.

    A gate that rendered no verdict is NEVER named as a killer (the T-196 'gate_3' records) —
    including Gate 0 on an unparseable window, whose legacy `killed_by_gate` label
    ('gate_0_unevaluable') is therefore not consulted: the verdicts are the one source."""
    verdicts = result["gate_verdicts"]                  # KeyError, never a default
    for g in GATE_ORDER:
        if verdicts[g]["verdict"] == FAILED:
            return g
    return None


def legacy_flags(verdicts: Mapping[str, Mapping[str, str]]) -> Dict[str, bool]:
    """`gate_N_passed` / `gate_N_evaluated` for EVERY gate, derived from the verdicts.
    Gate 3 gets no `_passed` key (it never had one: it has no pass criterion)."""
    out: Dict[str, bool] = {}
    for g in GATE_ORDER:
        v = verdicts[g]["verdict"]
        out[f"{g}_evaluated"] = v != NOT_EVALUATED
        if g not in RECORDED_ONLY_GATES:
            out[f"{g}_passed"] = v == PASSED
    return out


def verdict_strings(result: Mapping[str, Any]) -> Dict[str, str]:
    """{'g0': 'passed', 'g3': 'not_evaluated', …} — the compact form harness records carry."""
    return {f"g{g[5:]}": v["verdict"] for g, v in result["gate_verdicts"].items()}

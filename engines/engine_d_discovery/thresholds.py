"""The gauntlet's configured thresholds and required gates — read from ONE file, fail-closed.

R's F3 on RR-2: these readers used to live in `orchestration/mode_controller.py`, so five
engine-side scripts imported the orchestrator to learn a Discovery threshold (an inverted
dependency). They live with Engine D now; `mode_controller` imports them from here.

Every reader FAILS CLOSED: a missing or invalid key raises rather than defaulting, because a
silent default is how `significance_threshold=None` went unnoticed for every Discovery cycle
ever run (RR-2).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from engines.engine_d_discovery.gate_verdicts import GATE_ORDER, RECORDED_ONLY_GATES

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "discovery_settings.json"


def _settings(path: Optional[Path] = None) -> Dict[str, Any]:
    return json.loads(Path(path or SETTINGS_PATH).read_text())


def discovery_significance_threshold(path: Optional[Path] = None) -> float:
    """RR-2: the ONE configured Gate-4 threshold (config/discovery_settings.json)."""
    v = _settings(path)["significance_threshold"]
    if not isinstance(v, (int, float)) or not (0.0 < float(v) < 1.0):
        raise ValueError(f"discovery_settings.significance_threshold invalid: {v!r}")
    return float(v)


def discovery_gate2_threshold(path: Optional[Path] = None) -> float:
    """RR-2: the ONE configured Gate-2 survival threshold (was 0.7 in the deleted
    overwrite vs 0.60 in validate_candidate)."""
    v = _settings(path)["gate2_survival_threshold"]
    if not isinstance(v, (int, float)) or not (0.0 < float(v) <= 1.0):
        raise ValueError(f"discovery_settings.gate2_survival_threshold invalid: {v!r}")
    return float(v)


def required_gates(path: Optional[Path] = None) -> Tuple[str, ...]:
    """RR-6a: the gates whose verdict must be PASSED for a candidate to pass the gauntlet.

    A required gate that rendered no verdict (NOT_EVALUATED) refuses promotion. The list is
    validated against the gauntlet, and against `factor_gate_mode` so the two keys can never
    disagree about whether Gate 6 binds: 'kill' requires gate_6 in the list, 'report' requires
    it absent. Gate 3 has no pass criterion (RR-6b decides whether it should), so listing it
    would refuse every candidate — that is rejected too."""
    cfg = _settings(path)
    gates = cfg["required_gates"]
    if not isinstance(gates, list) or not gates or not all(isinstance(g, str) for g in gates):
        raise ValueError(f"discovery_settings.required_gates must be a non-empty list of gate ids: {gates!r}")
    unknown = [g for g in gates if g not in GATE_ORDER]
    if unknown:
        raise ValueError(f"discovery_settings.required_gates names unknown gates {unknown}; known: {GATE_ORDER}")
    recorded = [g for g in gates if g in RECORDED_ONLY_GATES]
    if recorded:
        raise ValueError(f"discovery_settings.required_gates lists {recorded}, which render no pass/fail "
                         f"verdict (recorded only) — requiring them would refuse every candidate")
    mode = cfg["factor_gate_mode"]
    if mode not in ("kill", "report"):
        raise ValueError(f"discovery_settings.factor_gate_mode invalid: {mode!r}")
    if (mode == "kill") != ("gate_6" in gates):
        raise ValueError(f"discovery_settings disagree about Gate 6: factor_gate_mode={mode!r} but gate_6 "
                         f"{'is not' if mode == 'kill' else 'is'} in required_gates")
    return tuple(g for g in GATE_ORDER if g in gates)

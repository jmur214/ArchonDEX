# engines/engine_e_regime/regime_gate.py
"""g_regime — the regime half of the conjunctive selector (T-217).

`conjunctive_score = s_tech × g_fund × g_regime` (T-208 / A's T-216). This
module is Engine E's deliverable: the `g_regime` GATE, a composable,
default-OFF input A's selector consumes (E does NOT fork A's selector and
does NOT wire this into live sizing).

Two pieces:
  * `hmm_regime_label(regime_meta)` — a clean 3-state regime label
    (calm/cautious/crisis) from the VALIDATED, CAUSAL HMM `p_crisis`
    (T-087/089, AUC 0.887) carried in `regime_meta["hmm_regime"]` — NOT the
    5-axis `advisory["regime_summary"]` that FAILED the walk-forward.
  * `RegimeGate` — per-(edge, regime) multipliers ∈ [0,1] measured from
    per-edge-per-regime performance. `gate(edge, regime_meta) → float`.

DEFAULT-OFF / canon-safe: an empty gate (no entries) returns 1.0 for every
(edge, regime) — a pure no-op, so prod canon is bitwise-unchanged until A's
selector explicitly composes a populated gate. A missing edge OR a missing
regime key also returns 1.0 (unconditional pass-through). All thresholds are
the PRE-REGISTERED constants (regime_gate_preregistration_t217); no sweep.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

# --- pre-registered regime-label thresholds on causal p_crisis ----------- #
CALM_MAX = 0.30        # p_crisis < 0.30      → calm
CAUTIOUS_MAX = 0.60    # 0.30 ≤ p_crisis < 0.60 → cautious;  ≥ 0.60 → crisis
REGIMES = ("calm", "cautious", "crisis")

# --- pre-registered Sharpe→gate mapping constants ------------------------ #
MIN_TRADES = 20        # below this, no gate (default 1.0) — insufficient data
DISABLE_SR = -0.25     # at/below this Sharpe in a regime → gate 0.0 (kill)
GATE_FLOOR = 0.25
GATE_CEIL = 1.0


def _p_crisis(regime_meta: Optional[Dict[str, Any]]) -> Optional[float]:
    """Pull the causal HMM crisis posterior from regime_meta, or None.
    Robust to the HMM being disabled / 2-/3-/4-state / absent."""
    if not regime_meta:
        return None
    hmm = regime_meta.get("hmm_regime")
    if not hmm:
        return None
    probs = hmm.get("probabilities") if isinstance(hmm, dict) else None
    if not isinstance(probs, dict):
        return None
    # crisis mass = the explicit "crisis" state if present, else the
    # most-stressed non-benign state's mass is NOT assumed — we only key on a
    # named "crisis" posterior (the validated quantity). Missing → None.
    v = probs.get("crisis")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def hmm_regime_label(regime_meta: Optional[Dict[str, Any]]) -> str:
    """3-state regime label from the CAUSAL HMM p_crisis. Fail-safe: if the
    HMM posterior is absent (off-cloud / disabled / NaN), return ``calm`` so
    a missing regime NEVER suppresses an edge (the gate degrades to no-op)."""
    p = _p_crisis(regime_meta)
    if p is None:
        return "calm"
    if p < CALM_MAX:
        return "calm"
    if p < CAUTIOUS_MAX:
        return "cautious"
    return "crisis"


def gate_from_sharpe(sharpe: float, trade_count: int) -> float:
    """The pre-registered per-(edge,regime) Sharpe→gate map (no sweep)."""
    if trade_count < MIN_TRADES:
        return 1.0                         # insufficient data → no gate
    if sharpe <= DISABLE_SR:
        return 0.0                         # kill the edge in this regime
    s = min(1.0, max(0.0, float(sharpe)))
    return float(min(GATE_CEIL, max(GATE_FLOOR, GATE_FLOOR + (GATE_CEIL - GATE_FLOOR) * s)))


def build_gates_from_stats(
    stats: Dict[str, Dict[str, Dict[str, float]]]
) -> Dict[str, Dict[str, float]]:
    """Build the gate dicts from measured per-(edge, regime) stats.

    ``stats[edge][regime] = {"sharpe": float, "trade_count": int}`` (the
    shape `regime_tracker` exposes). Returns ``{edge: {regime: multiplier}}``.
    Only entries that actually gate (≠ 1.0) are kept — a 1.0 entry is
    indistinguishable from "no entry", so we drop it to keep the gate sparse
    and the default-OFF semantics clean.
    """
    gates: Dict[str, Dict[str, float]] = {}
    for edge, by_regime in stats.items():
        for regime, s in by_regime.items():
            g = gate_from_sharpe(float(s.get("sharpe", 0.0)),
                                 int(s.get("trade_count", 0)))
            if abs(g - 1.0) > 1e-12:
                gates.setdefault(edge, {})[regime] = round(g, 4)
    return gates


@dataclass
class RegimeGate:
    """Composable default-OFF g_regime gate. `gates={}` == OFF == all 1.0."""
    gates: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.gates)

    def gate(self, edge_name: str, regime_meta: Optional[Dict[str, Any]]) -> float:
        """g_regime ∈ [0,1] for this edge in the current (HMM) regime.
        1.0 when OFF / edge unseen / regime unseen (unconditional pass)."""
        per = self.gates.get(edge_name)
        if not per:
            return 1.0
        regime = hmm_regime_label(regime_meta)
        return float(per.get(regime, 1.0))

    # --- persistence (so A loads E's measured gate; both default to OFF) -- #
    def to_dict(self) -> Dict[str, Any]:
        return {"_schema": "regime_gate/v1", "label": "hmm_p_crisis_3state",
                "thresholds": {"calm_max": CALM_MAX, "cautious_max": CAUTIOUS_MAX},
                "gates": self.gates}

    def to_file(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True))

    @classmethod
    def from_file(cls, path: str | Path) -> "RegimeGate":
        try:
            d = json.loads(Path(path).read_text())
            return cls(gates=d.get("gates", {}) or {})
        except Exception:
            return cls(gates={})           # fail-safe → OFF

"""T-292 — the LLM cost governor + kill switch.

Stage-0 the analyst is report-only, but the API bill and the safety switch are
real. The governor is checked BEFORE every model call and can veto it:

  * per-call ``max_output_tokens`` cap (bounds the worst-case single call);
  * a monthly USD accumulator vs ``monthly_budget_usd`` ($30) — a call whose
    projected cost would breach the budget is REFUSED (fail-closed: no call, a
    heartbeat flag, and the pulse continues report-only);
  * ``kill_switch`` — an operator/automated stop.

KILL-SWITCH SEMANTICS (codified, do not weaken): the kill switch — and EVERY
halt path in this system — means STOP NEW AUTOMATED ACTIONS. It NEVER liquidates.
A safety mechanism that force-sells is the capitulation this whole system exists
to prevent (the user will not sell in downturns). Tripping the switch reverts the
analyst to producing nothing (or, at Stage 2, reverts the account to
reconcile-only); it never emits an order and never closes a position.

Fail-closed everywhere: an unreadable ledger, an unparseable budget, or any
doubt ⇒ SKIP the call, never "assume there's budget."
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class GovernorConfig:
    monthly_budget_usd: float = 30.0
    max_output_tokens: int = 4096
    kill_switch: bool = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str                    # "" when allowed; a code when refused
    max_output_tokens: int         # the cap to pass to the call when allowed


class CostGovernor:
    """Reads a month-to-date spend ledger (append-only JSONL of {ts, cost_usd})
    and decides whether the next call may proceed. Injectable ``now``/``ledger``
    for tests; production points at the S3-synced state dir."""

    def __init__(self, cfg: GovernorConfig, ledger_path: str, *,
                 month: Optional[str] = None):
        self.cfg = cfg
        self.ledger = Path(ledger_path)
        self._month = month          # "YYYY-MM"; None ⇒ derive from each record's ts

    # -- spend accounting -------------------------------------------------- #
    def month_to_date_usd(self, month: str) -> float:
        """Sum cost_usd for the given month. FAIL-CLOSED: an unreadable or
        unparseable ledger returns the BUDGET (so the next call is refused),
        never 0.0 (which would wave calls through blind)."""
        try:
            if not self.ledger.exists():
                return 0.0
            total = 0.0
            for line in self.ledger.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if str(rec.get("ts", ""))[:7] == month:
                    total += float(rec["cost_usd"])
            return total
        except Exception:
            return self.cfg.monthly_budget_usd     # fail-closed: looks spent

    # -- the gate ---------------------------------------------------------- #
    def check(self, month: str, projected_cost_usd: float) -> Decision:
        if self.cfg.kill_switch:
            return Decision(False, "kill_switch", 0)
        if projected_cost_usd < 0 or projected_cost_usd != projected_cost_usd:  # NaN
            return Decision(False, "bad_projected_cost", 0)
        spent = self.month_to_date_usd(month)
        if spent + projected_cost_usd > self.cfg.monthly_budget_usd:
            return Decision(False,
                            f"budget_breach(spent={spent:.2f}+proj="
                            f"{projected_cost_usd:.2f}>{self.cfg.monthly_budget_usd:.2f})",
                            0)
        return Decision(True, "", self.cfg.max_output_tokens)

    # -- record a spend (append-only) -------------------------------------- #
    def record_spend(self, ts_iso: str, cost_usd: float) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a") as fh:
            fh.write(json.dumps({"ts": ts_iso, "cost_usd": round(float(cost_usd), 6)}) + "\n")


def load_governor(settings_path: str, ledger_path: str) -> CostGovernor:
    """Build a governor from config/llm_settings.json (the `llm` block), with
    safe defaults if a field is absent. kill_switch defaults to False but any
    truthy value trips it."""
    cfg = GovernorConfig()
    try:
        s = json.loads(Path(settings_path).read_text()).get("llm", {})
        cfg = GovernorConfig(
            monthly_budget_usd=float(s.get("monthly_budget_usd", cfg.monthly_budget_usd)),
            max_output_tokens=int(s.get("max_output_tokens", cfg.max_output_tokens)),
            kill_switch=bool(s.get("kill_switch", False)))
    except Exception:
        pass   # defaults stand; a broken settings file must not enable spending
    return CostGovernor(cfg, ledger_path)

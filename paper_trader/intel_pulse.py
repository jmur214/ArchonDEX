"""T-310 — the intel pulse: the daily LLM report-only steps, wired into the paper
loop's account-1 branch (post-reconcile). Closes the four gaps the T-309 "what
did NOT wake" report named:

  1. the ANALYST actually runs (``run_daily_note``) and its validated note is
     PERSISTED to ``data/intel/analyst_notes/`` — which is what wakes C's shadow
     book (it reads yesterday's note) and feeds A's eval harness;
  2. A's OPS WATCHDOG runs a report-only pass over the pulse bundle;
  3. D's EVENT pulse_step fires (forward-only 8-K interpreter);
  4. all three SHARE one governed ≤$30/mo budget (durable spend ledger).

Every step is REPORT-ONLY and FAIL-OPEN: nothing here can raise into the trading
path or change a run's canonical verdict (an LLM hiccup is not a trading fault).
It is also KEY-OPTIONAL — with no ANTHROPIC_API_KEY the model_call is None and
every step CLEAN-SKIPS (an honest "no adapter" record, never a fabricated note).
The key is read from the environment (the Secrets-Manager-injected var in-cloud /
.env locally) at call time and never enters a prompt, a log, or a return value —
the adapter (``anthropic_adapter``) enforces that.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# where C's shadow book + A's eval harness both read notes from
NOTES_DIR = "data/intel/analyst_notes"
SPEND_LEDGER = "data/intel/llm_spend.jsonl"
RAW_DIR = "data/intel/llm_raw"
MONTHLY_BUDGET_USD = 30.0
DAILY_MAX_OUTPUT_TOKENS = 1500

# projected per-step costs (governor gates on the running monthly total; these
# are conservative upper bounds so the budget is never overshot mid-pulse).
_PROJ_ANALYST = 0.05
_PROJ_WATCHDOG = 0.05
_PROJ_EVENT = 0.10


@dataclass
class IntelPulseResult:
    analyst: Dict[str, Any] = field(default_factory=dict)
    watchdog: Dict[str, Any] = field(default_factory=dict)
    event: Dict[str, Any] = field(default_factory=dict)
    note_written: Optional[str] = None      # path of the persisted analyst note
    model_available: bool = False

    def summary_line(self) -> str:
        a = self.analyst.get("status", "skip")
        w = self.watchdog.get("status", "skip")
        e = self.event.get("status", "skip")
        nw = " note_written" if self.note_written else ""
        key = "" if self.model_available else " (no key → clean skips)"
        return f"analyst={a} watchdog={w} event={e}{nw}{key}"


def _model_call_or_none(tier: str, settings: Optional[dict]) -> Optional[Callable]:
    """Build the raw-REST adapter bound to a tier — or None if no key is present
    (→ every downstream step clean-skips rather than erroring)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from intelligence.analyst.anthropic_adapter import make_model_call
    return make_model_call(tier, settings=settings)


def _model_id(settings: Optional[dict], tier: str) -> str:
    try:
        return settings["tiers"][tier]["model_id"]
    except Exception:
        return "claude-haiku-4-5-20251001"


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    tmp.replace(path)


def _watchdog_bundle(root: Path, as_of: str) -> Dict[str, Any]:
    """Assemble the report-only ops bundle via A's own ``build_bundle`` (correct
    shape + secret-scrub), fed from THIS run's persisted heartbeat status
    (last_run / altdata / news / econ_health blocks). Deliberately thin + honest:
    it carries only what the pulse actually recorded — the watchdog is report-
    only, so a sparse bundle simply yields fewer findings, never a false one.
    Cross-day/sibling depth grows as more state accrues on S3."""
    from intelligence.watchdog import build_watchdog_bundle
    hb_path = root / "data/state/paper_heartbeat.json"
    try:
        heartbeats = json.loads(hb_path.read_text())
    except Exception:
        heartbeats = {}
    return build_watchdog_bundle(as_of=as_of, heartbeats=heartbeats)


def run_intel_pulse(as_of, *, portfolios: Dict[str, Dict[str, float]],
                    allowlist, root: str, now_iso: str,
                    load_panel=None, tier: str = "daily") -> IntelPulseResult:
    """Run the three report-only LLM steps for ``as_of``. Never raises."""
    base = Path(root)
    res = IntelPulseResult()

    try:
        from intelligence.analyst.anthropic_adapter import load_settings
        settings = load_settings()
    except Exception:
        settings = None

    model_call = _model_call_or_none(tier, settings)
    res.model_available = model_call is not None
    model_id = _model_id(settings, tier)
    raw_dir = str(base / RAW_DIR)

    # one shared governor over a durable spend ledger → the ≤$30/mo budget spans
    # analyst + watchdog + event together (not per-step).
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    gov = CostGovernor(
        GovernorConfig(monthly_budget_usd=MONTHLY_BUDGET_USD,
                       max_output_tokens=DAILY_MAX_OUTPUT_TOKENS),
        str(base / SPEND_LEDGER))

    # --- 1. analyst note → persist to data/intel/analyst_notes/ --------------- #
    try:
        from intelligence.analyst.analyst_service import run_daily_note
        if model_call is None:
            res.analyst = {"status": "skipped:no_model_adapter"}
        else:
            r = run_daily_note(
                as_of, portfolios=portfolios, allowlist=allowlist,
                prompt_path="config/prompts/analyst/daily_v1.md",
                model_call=model_call, governor=gov,
                model_id_requested=model_id, prompt_version="daily/v1",
                projected_cost_usd=_PROJ_ANALYST, raw_dir=raw_dir,
                load_panel=load_panel, now_iso=now_iso)
            res.analyst = {"status": r.status,
                           "firewall_rejections": r.firewall_rejections}
            if r.note is not None:
                as_of_s = str(r.note.get("as_of", as_of))
                note_path = base / NOTES_DIR / f"note_{as_of_s}.json"
                _atomic_write_json(note_path, r.note)
                res.note_written = str(note_path)
    except Exception as exc:   # noqa: BLE001 — report-only, never raise
        res.analyst = {"status": f"error:{type(exc).__name__}"}

    # --- 2. ops watchdog (report-only) --------------------------------------- #
    try:
        from intelligence.watchdog import run_watchdog
        if model_call is None:
            res.watchdog = {"status": "skipped:no_model_adapter"}
        else:
            wr = run_watchdog(
                _watchdog_bundle(base, str(as_of)),
                model_call=model_call, governor=gov,
                prompt_path="config/prompts/watchdog/watchdog_v1.md",
                model_id_requested=model_id, prompt_version="watchdog/v1",
                projected_cost_usd=_PROJ_WATCHDOG, raw_dir=raw_dir,
                out_dir=str(base / "data/intel"),
                log_path=str(base / "data/state/paper_alerts.log"),
                now_iso=now_iso)
            rep = getattr(wr, "report", None)
            res.watchdog = {"status": getattr(wr, "status", "unknown"),
                            "n_anomalies": len(rep.get("anomalies", []))
                            if isinstance(rep, dict) else 0}
    except Exception as exc:   # noqa: BLE001
        res.watchdog = {"status": f"error:{type(exc).__name__}"}

    # --- 3. D's event pulse_step (forward-only 8-K interpreter, report-only) -- #
    try:
        from intelligence.event_call.run_forward import pulse_step
        ev = pulse_step(
            as_of, model_call=model_call, governor=gov,
            prompt_path="config/prompts/event_interpreter/v1.txt",
            model_id_requested=model_id, prompt_version="event_interpreter/v1",
            projected_cost_usd=_PROJ_EVENT, raw_dir=raw_dir)
        res.event = ev if isinstance(ev, dict) else {"status": "unknown"}
    except Exception as exc:   # noqa: BLE001
        res.event = {"status": f"error:{type(exc).__name__}"}

    return res

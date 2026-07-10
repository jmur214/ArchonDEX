"""intelligence/watchdog.py — T-303 OPS WATCHDOG (the sibling-number tell, automated).

A daily LLM pass over the machine's OWN operational output, answering ONE question:
"is anything here inconsistent with yesterday — or with its siblings?" It hunts the
single class behind six human-caught incidents in three days: OUTPUT THAT REPORTS
HEALTH WHILE LYING (a status says 'ok' while a count/rate/timestamp next to it, or a
sibling account, disagrees).

Doctrine (applies to the watchdog ITSELF): schema-validated report or NO report; a
malformed model response yields a skip, never a suspect all-clear. Report-only —
NOTHING halts on its word (smoke detector, not breaker). 0 N_trials.

Mirrors the T-292 analyst seams exactly: the deterministic secret-free bundle
(context_builder `_scrub`/`canonical_json`/`bundle_sha256`), the injected `ModelCall`
seam, and the SAME `CostGovernor` budget (an analyst-family cheap-tier call). The
live Anthropic call is injected so this is unit-testable with zero network + zero key.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from intelligence.analyst.context_builder import _scrub, bundle_sha256, canonical_json
from intelligence.analyst.cost_governor import CostGovernor
from intelligence.analyst.note_schema import Provenance, Usage

# model_call(prompt_text, bundle_json, max_output_tokens) -> {"text","model_id_served","usage"}
ModelCall = Callable[[str, str, int], Dict[str, Any]]
WATCHDOG_SCHEMA_VERSION = "watchdog_report/v1"


# ── schema (watchdog_report/v1) — a bad field ⇒ NO report ──────────────────────
class Anomaly(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["low", "medium", "high", "critical"]
    what: str = Field(min_length=1, max_length=500)
    evidence: str = Field(min_length=1, max_length=1000)          # the disagreeing fields/values
    sibling_comparison: str = Field(min_length=1, max_length=1000)  # the yesterday/sibling value it should have matched


class WatchdogReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["watchdog_report/v1"] = "watchdog_report/v1"
    as_of: str = Field(min_length=1)
    anomalies: List[Anomaly] = Field(default_factory=list)
    all_clear: bool
    provenance: Provenance
    usage: Usage

    @model_validator(mode="after")
    def _all_clear_is_consistent(self) -> "WatchdogReport":
        # the report may NOT be an instance of the class it hunts: all_clear ⇔ no anomalies
        if self.all_clear != (len(self.anomalies) == 0):
            raise ValueError("all_clear must equal 'anomalies is empty'")
        return self


def validate_report(payload: dict) -> "tuple[Optional[WatchdogReport], Optional[str]]":
    try:
        return WatchdogReport.model_validate(payload), None
    except Exception as e:   # noqa: BLE001 — any validation error → no report
        return None, str(e).splitlines()[0][:300]


# ── deterministic, secret-free input bundle ────────────────────────────────────
def build_watchdog_bundle(
    as_of: str,
    *,
    pulse_today: Optional[Dict[str, Any]] = None,      # {account: pulse-log dict}
    pulse_yesterday: Optional[Dict[str, Any]] = None,
    heartbeats: Optional[Dict[str, Any]] = None,       # altdata / news / econ-health blocks
    census: Optional[Dict[str, Any]] = None,
    exec_gate_samples: Optional[List[Dict[str, Any]]] = None,
    tracker_headlines: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the watchdog's input bundle. TODAY paired with YESTERDAY and the
    per-account siblings side-by-side so the model can compare. `_scrub`'d (secret-free,
    belt-and-braces) and canonical → a stable SHA-256."""
    bundle = {
        "as_of": as_of,
        "pulse": {"today": pulse_today or {}, "yesterday": pulse_yesterday or {}},
        "heartbeats": heartbeats or {},
        "census": census or {},
        "exec_gate_samples": exec_gate_samples or [],
        "tracker_headlines": tracker_headlines or {},
    }
    return _scrub(bundle)          # final secret scrub — mirrors the analyst bundle


# ── governed run (mirrors analyst_service.run_daily_note) ──────────────────────
@dataclass
class WatchdogResult:
    report: Optional[dict]           # validated watchdog_report/v1 dict, or None
    status: str                      # "ok" | "skipped:<reason>" | "invalid:<reason>"
    raw_path: Optional[str] = None
    out_path: Optional[str] = None


def _prompt(prompt_path: str) -> "tuple[str, str]":
    text = Path(prompt_path).read_text()
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_watchdog(
    bundle: Dict[str, Any],
    *,
    model_call: ModelCall,
    governor: CostGovernor,
    prompt_path: str,
    model_id_requested: str,
    prompt_version: str,
    projected_cost_usd: float,
    raw_dir: str,
    out_dir: str,
    log_path: Optional[str] = None,
    now_iso: str = "1970-01-01T00:00:00",
) -> WatchdogResult:
    as_of = str(bundle.get("as_of", now_iso[:10]))
    month = str(now_iso)[:7]

    # 1. governor / kill switch — fail-closed, no call on refusal
    decision = governor.check(month, projected_cost_usd)
    if not decision.allowed:
        return WatchdogResult(None, f"skipped:{decision.reason}")

    bundle_json = canonical_json(bundle)
    prompt, prompt_sha = _prompt(prompt_path)

    # 2. ONE structured call (no tools, no loop); raw always archived
    try:
        resp = model_call(prompt, bundle_json, decision.max_output_tokens)
    except Exception as e:   # noqa: BLE001
        return WatchdogResult(None, f"skipped:model_call_error:{type(e).__name__}")

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    raw_path = str(Path(raw_dir) / f"watchdog_raw_{as_of}.json")
    Path(raw_path).write_text(json.dumps(
        {"as_of": as_of, "response": resp.get("text", ""),
         "model_id_served": resp.get("model_id_served"),
         "input_bundle_sha256": bundle_sha256(bundle)}, default=str))

    usage = resp.get("usage", {}) or {}
    governor.record_spend(now_iso, float(usage.get("cost_usd", 0.0) or 0.0))

    # 3. parse + independent re-validation → bad ⇒ NO report (doctrine on the watchdog)
    try:
        payload = json.loads(resp.get("text", ""))
    except Exception:
        return WatchdogResult(None, "invalid:not_json", raw_path=raw_path)
    payload.setdefault("as_of", as_of)
    payload["provenance"] = {
        "model_id_requested": model_id_requested,
        "model_id_served": str(resp.get("model_id_served", model_id_requested)),
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha,
        "input_bundle_sha256": bundle_sha256(bundle),
    }
    payload["usage"] = {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "cost_usd": float(usage.get("cost_usd", 0.0) or 0.0),
    }
    report, err = validate_report(payload)
    if report is None:
        return WatchdogResult(None, f"invalid:{err}", raw_path=raw_path)

    # 4. report-only: dashboard JSON + append-only log (FP-rate tracking from day 1)
    report_dict = report.model_dump()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = str(Path(out_dir) / f"watchdog_{as_of}.json")
    Path(out_path).write_text(json.dumps(report_dict, default=str, indent=2))
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as fh:
            for a in report_dict["anomalies"]:
                fh.write(json.dumps({"as_of": as_of, **a, "confirmed": None}) + "\n")
    return WatchdogResult(report_dict, "ok", raw_path=raw_path, out_path=out_path)


def false_positive_rate(log_path: str) -> Optional[float]:
    """FP rate over anomalies a human later labeled `confirmed` (True=real, False=FP).
    None until labels exist. A watchdog that cries wolf must be measurable from day 1."""
    p = Path(log_path)
    if not p.is_file():
        return None
    labeled = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    labeled = [r for r in labeled if r.get("confirmed") is not None]
    if not labeled:
        return None
    return round(sum(1 for r in labeled if r["confirmed"] is False) / len(labeled), 4)

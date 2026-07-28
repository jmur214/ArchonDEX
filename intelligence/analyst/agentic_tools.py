"""T-321 — read-only tools for the AGENTIC analyst (P2.5).

The constrained analyst reads a fixed bundle. The agentic one INVESTIGATES — it
pulls history, checks how similar setups resolved, reads its own past calls. This
module is the tool surface for that, and it is deliberately narrow:

  * READ-ONLY over OUR OWN STORES — never the open web, never the filesystem at
    large. Each tool is backed by an INJECTED reader callable, so the model can
    only reach what the caller wired in (the paper loop wires the news panel,
    price history, rate-path store, events ledger, and its own notes + resolved
    predictions — nothing else).
  * The attack surface is UNCHANGED from the constrained analyst: the same corpus
    (our stores). Tools ADD retrieval, not exposure. Every result is `_scrub`'d
    (the same secret-scrub the bundle uses) and SIZE-BOUNDED before it re-enters
    the model — a store that somehow held a key can't launder it through a tool
    result, and a huge result can't blow the context / budget.
  * Every call is fail-CLOSED: an unknown tool, a bad argument, or a reader that
    raises returns an ``is_error`` tool result (logged), never a crash and never
    a fabricated value. A tool result is DATA, not instructions — the downstream
    schema/firewall gates treat the final note exactly as they treat the
    constrained one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from intelligence.analyst.context_builder import _scrub

# Hard cap on a single tool result's serialized size (chars) — a retrieval tool
# must not be able to flood the context window or the token budget.
MAX_RESULT_CHARS = 6000

# A Reader takes a kwargs dict (the model's tool input, already shape-checked) and
# returns any JSON-able value. It MUST be read-only; this module never passes a
# writer in. Missing reader → the tool is simply absent from the offered set.
Reader = Callable[[Dict[str, Any]], Any]


# ── the tool catalogue (name → JSON-Schema input + the reader key) ─────────────
# input_schema uses additionalProperties:false so a malformed/injected extra arg
# is rejected at the transport before the reader ever sees it.
_TOOL_SPECS: Dict[str, Dict[str, Any]] = {
    "query_news": {
        "description": "Search OUR point-in-time news panel for headlines about a "
                       "ticker in a date range. Returns only articles created BEFORE "
                       "as_of (no look-ahead). Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "date_from": {"type": "string", "description": "YYYY-MM-DD inclusive"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD inclusive"},
            },
            "required": ["ticker"], "additionalProperties": False},
    },
    "query_prices": {
        "description": "Fetch OUR daily price history (adjusted closes) for a ticker "
                       "over a date range. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "date_from": {"type": "string"}, "date_to": {"type": "string"}},
            "required": ["ticker"], "additionalProperties": False},
    },
    "query_rate_path": {
        "description": "Read OUR archived rate-path store (Fed funds target / EFFR). "
                       "Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {"date_from": {"type": "string"}, "date_to": {"type": "string"}},
            "required": [], "additionalProperties": False},
    },
    "query_events": {
        "description": "Read OUR forward event-interpreter ledger (8-K / special-sits "
                       "event calls). Optionally filter by symbol. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}, "limit": {"type": "integer"}},
            "required": [], "additionalProperties": False},
    },
    "query_own_notes": {
        "description": "Read the analyst's OWN past notes (this model's prior daily "
                       "notes). Use to check what you said before. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [], "additionalProperties": False},
    },
    "query_resolved_predictions": {
        "description": "Read the analyst's OWN resolved-prediction record (which past "
                       "predictions came true, with Brier). Learn your own calibration. "
                       "Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [], "additionalProperties": False},
    },
}


@dataclass
class ToolCallRecord:
    """One tool call, for the note's provenance (the audit of what it looked at)."""
    tool: str
    input: Dict[str, Any]
    is_error: bool
    n_results: Optional[int] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"tool": self.tool, "input": self.input, "is_error": self.is_error,
                "n_results": self.n_results, "reason": self.reason}


@dataclass
class AgenticTools:
    """The read-only tool surface, bound to a set of injected readers. Only tools
    whose reader was supplied are offered to the model."""
    readers: Dict[str, Reader]
    trace: List[ToolCallRecord] = field(default_factory=list)

    def specs(self) -> List[Dict[str, Any]]:
        """The Messages-API ``tools`` array — only the tools we have a reader for."""
        return [{"name": name, "description": _TOOL_SPECS[name]["description"],
                 "input_schema": _TOOL_SPECS[name]["input_schema"]}
                for name in _TOOL_SPECS if name in self.readers]

    def execute(self, name: str, tool_input: Dict[str, Any]) -> "tuple[str, bool]":
        """Run one tool. Returns (result_text, is_error). NEVER raises. The result
        is scrubbed + size-bounded before it goes back to the model."""
        if name not in _TOOL_SPECS or name not in self.readers:
            self.trace.append(ToolCallRecord(name, tool_input, True, reason="unknown_tool"))
            return f"error: unknown tool {name!r}", True
        try:
            raw = self.readers[name](dict(tool_input) if isinstance(tool_input, dict) else {})
            scrubbed = _scrub(raw)
            n = len(scrubbed) if isinstance(scrubbed, (list, dict)) else None
            text = json.dumps(scrubbed, default=str)
            if len(text) > MAX_RESULT_CHARS:
                text = text[:MAX_RESULT_CHARS] + f"\n…[truncated at {MAX_RESULT_CHARS} chars]"
            self.trace.append(ToolCallRecord(name, tool_input, False, n_results=n))
            return text, False
        except Exception as exc:   # noqa: BLE001 — fail-closed, the model sees an error result
            self.trace.append(ToolCallRecord(name, tool_input, True,
                                             reason=f"reader_error:{type(exc).__name__}"))
            return f"error: {type(exc).__name__}", True

    def trace_dicts(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.trace]

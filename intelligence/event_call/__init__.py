"""T-304 — the event-interpreter (info-layer program §P2.4, Lane: D).

Forward-only structured interpretation of ONE discrete document (an 8-K item or a
special-situations delta) into a TYPED, machine-scoreable `event_call/v1`. Mirrors
E's analyst service idiom (`intelligence/analyst/`): a single structured model call
(no tools, no agent loop), independent local re-validation, the shared cost governor,
and predictions that must pass A's `resolver/v1` gate so every call is Brier-scoreable.

Ownership: D owns `event_schema.py` / `event_service.py` / `eightk_feed.py`. Reused
verbatim from the analyst package: `Provenance`/`Usage`/`Prediction` (note_schema),
`is_resolvable_spec` + the `run()` scorer (eval_harness), `CostGovernor` (cost_governor).

`[NN-AI-GATE]`: exploration on a SEPARATE track, FORWARD-ONLY (no historical LLM calls —
memorization look-ahead), machine-scoreable. It becomes a live signal only after the
pre-registered forward bar in `docs/Audit/event_interpreter_design_t304_2026_07_10.md`
clears. Live model calls await the shared Anthropic adapter (the injected `ModelCall`).
"""
from intelligence.event_call.event_schema import (EVENT_TYPES, SCHEMA_VERSION,
                                                  EventCall, validate_event_call)

__all__ = ["EVENT_TYPES", "SCHEMA_VERSION", "EventCall", "validate_event_call"]

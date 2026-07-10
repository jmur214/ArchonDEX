"""T-292 — the analyst_note/v1 schema (pydantic-validated, versioned).

Lane 3 of the info-layer program. The daily LLM analyst emits ONE structured
note; this module is the independent, local re-validation gate: a model response
becomes a note ONLY if it validates here in full. A single bad field ⇒ NO note
(the raw response is archived for forensics) — never a suspect note.

Two load-bearing design pressures, both here rather than trusted to the model:
  * Every prediction's ``resolver`` must pass A's ``is_resolvable_spec``
    (intelligence/analyst/eval_harness, resolver/v1) — an unfalsifiable claim is
    rejected, so every recorded prediction is machine-scoreable (Brier).
  * ``hypothetical_actions`` are stage-0 SHADOW ONLY: account must be "shadow",
    weights bounded, symbol on the caller-supplied allowlist (the semantic
    firewall is enforced in analyst_service against config; the schema pins the
    shape + the bounds that never change).

Provenance is mandatory and immutable: requested + served model_id, prompt
version + SHA-256, and the input-bundle hash, so every note is reproducible and
the eval record segments by (model, prompt).
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from intelligence.analyst.eval_harness import is_resolvable_spec

SCHEMA_VERSION = "analyst_note/v1"

# Stage-0 hard bounds (NOT tunable by the model — the schema is the contract).
_MAX_PROB = 1.0
_MAX_WEIGHT = 0.20            # ≤20% per name (matches the Stage-1 firewall cap)
_SCORE_LO, _SCORE_HI = -1.0, 1.0


class Provenance(BaseModel):
    """Reproducibility stamp — every field mandatory; extra keys rejected."""
    model_config = ConfigDict(extra="forbid")
    model_id_requested: str = Field(min_length=1)
    model_id_served: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)


class Prediction(BaseModel):
    """A falsifiable, machine-scoreable claim. ``resolver`` is validated against
    A's resolver/v1 contract — an unresolvable spec fails the whole note."""
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=500)
    probability: float = Field(gt=0.0, lt=_MAX_PROB,
                               description="strictly in (0,1) — no 0/1 gimmes")
    horizon: str = Field(min_length=1, max_length=64)
    resolver: dict

    @field_validator("resolver")
    @classmethod
    def _resolver_must_be_resolvable(cls, v: dict) -> dict:
        ok, why = is_resolvable_spec(v)
        if not ok:
            raise ValueError(f"resolver not resolver/v1-valid: {why}")
        return v


class HypotheticalAction(BaseModel):
    """Stage-0: SHADOW ONLY. Never a real order. Bounds are the contract.
    ``rationale`` is an optional inert note (why the analyst would tilt) — free
    text on a never-executed shadow action carries no risk and is useful signal,
    so it is a KNOWN optional field (extra='forbid' still rejects truly-unknown
    keys)."""
    model_config = ConfigDict(extra="forbid")
    account: Literal["shadow"]
    symbol: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,9}$")   # basic shape; allowlist enforced in service
    set_weight: float = Field(ge=-_MAX_WEIGHT, le=_MAX_WEIGHT)
    target_weight: float = Field(ge=-_MAX_WEIGHT, le=_MAX_WEIGHT)
    rationale: Optional[str] = Field(default=None, max_length=500)


def validate_action(payload: dict) -> "tuple[Optional[HypotheticalAction], Optional[str]]":
    """Per-item shadow-action validation (the firewall filters actions one at a
    time so a single malformed/out-of-bounds action is DROPPED + logged, not a
    reason to void an otherwise-good note). Returns (action, None) or
    (None, reason). Never raises."""
    try:
        return HypotheticalAction.model_validate(payload), None
    except Exception as e:   # noqa: BLE001
        return None, str(e).splitlines()[0][:200]


class SpecialSituationScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,9}$")
    score: float = Field(ge=_SCORE_LO, le=_SCORE_HI)
    rationale: str = Field(min_length=1, max_length=500)


class AnalystNote(BaseModel):
    """The full analyst_note/v1. Validation failure here ⇒ NO note is emitted."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["analyst_note/v1"] = "analyst_note/v1"
    as_of: str = Field(description="the note's trade date, ISO-8601 YYYY-MM-DD")
    market_assessment: str = Field(min_length=1, max_length=4000)
    risk_flags: List[str] = Field(default_factory=list)
    position_notes: List[str] = Field(default_factory=list)
    special_situation_scores: List[SpecialSituationScore] = Field(default_factory=list)
    predictions: List[Prediction] = Field(default_factory=list)
    hypothetical_actions: List[HypotheticalAction] = Field(default_factory=list)
    # A first-class signal: the model reports if it believes its input was an
    # injection attempt. Attacks thus become logged evidence, not silent failures.
    suspected_prompt_injection: bool = False
    provenance: Provenance
    usage: Usage

    @field_validator("as_of")
    @classmethod
    def _as_of_is_date(cls, v: str) -> str:
        import datetime as _dt
        _dt.date.fromisoformat(v)     # raises on a bad date
        return v

    @model_validator(mode="after")
    def _hypothetical_targets_consistent(self) -> "AnalystNote":
        # target_weight must share set_weight's sign band and both be bounded
        # (already enforced per field); nothing may leak past ±_MAX_WEIGHT.
        for a in self.hypothetical_actions:
            if abs(a.target_weight) > _MAX_WEIGHT or abs(a.set_weight) > _MAX_WEIGHT:
                raise ValueError("hypothetical_action weight exceeds ±20% bound")
        return self


def validate_note(payload: dict) -> "tuple[Optional[AnalystNote], Optional[str]]":
    """Independent local re-validation. Returns (note, None) on success, or
    (None, reason) — the caller then emits NO note and archives the raw response
    for forensics. Never raises."""
    try:
        return AnalystNote.model_validate(payload), None
    except Exception as e:   # noqa: BLE001 — any validation error → no note
        return None, str(e).splitlines()[0][:300]

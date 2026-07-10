"""T-304 — the event_call/v1 schema (pydantic-validated, versioned).

One discrete document (an 8-K item, or a special-situations delta) → ONE typed,
machine-scoreable event call. Same discipline as `analyst_note/v1`: a model response
becomes an event call ONLY if it validates here in full; a single bad field ⇒ NO call
(raw archived for forensics), never a suspect record.

Reused verbatim from the analyst schema (DRY — same contract, one source of truth):
`Provenance`, `Usage`, `Prediction` (whose `resolver` must pass A's `is_resolvable_spec`,
resolver/v1). This module adds only the typed event body: a CLOSED `event_type` taxonomy,
`materiality` ∈ [0,1], a `direction`, a short `rationale`, and ≥1 falsifiable `Prediction`.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Reuse the analyst sub-models verbatim (Prediction carries the resolver/v1 gate).
from intelligence.analyst.note_schema import Prediction, Provenance, Usage

SCHEMA_VERSION = "event_call/v1"

# ---- the CLOSED event taxonomy (the model MUST pick exactly one) --------------------
# Designed from the 8-K item semantics + the special-situations classes. `direction`
# carries the sign (e.g. guidance raise vs cut, dividend initiate vs suspend), so the
# taxonomy stays compact. `routine_non_material` is the honest-null; `other_material`
# is the escape hatch — BOTH still require ≥1 resolvable prediction (no dodging).
_8K_EVENT_TYPES = (
    "going_concern", "bankruptcy", "acquisition_target", "acquisition_acquirer",
    "divestiture_spinoff", "guidance_change", "earnings_result", "material_agreement",
    "debt_event", "impairment_restructuring", "management_change",
    "restatement_nonreliance", "delisting_deficiency", "capital_return",
    "legal_regulatory",
)
_SPECIAL_SIT_EVENT_TYPES = ("odd_lot_tender", "cef_action", "rights_going_private")
_META_EVENT_TYPES = ("routine_non_material", "other_material")
EVENT_TYPES = _8K_EVENT_TYPES + _SPECIAL_SIT_EVENT_TYPES + _META_EVENT_TYPES

_MATERIALITY_ROUTINE_MAX = 0.30      # a 'routine_non_material' call cannot claim high materiality
_SYM = r"^[A-Z][A-Z0-9.\-]{0,9}$"


def sha256_text(s: str) -> str:
    """SHA-256 of the single interpreted document (PIT provenance)."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


class EventCall(BaseModel):
    """A typed interpretation of ONE document. Validation failure ⇒ NO call is emitted."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["event_call/v1"] = "event_call/v1"

    # --- what was read (PIT provenance) ---
    as_of: str = Field(description="decision date, ISO-8601 YYYY-MM-DD (the call is made at/after this)")
    source: Literal["8k", "special_situation"]
    document_ref: str = Field(min_length=1, max_length=128,
                              description="'{accession}#{item}' for 8-K, or the special-sit event_id")
    symbol: str = Field(pattern=_SYM)
    file_date: str = Field(description="the document's own PIT date, ISO-8601 YYYY-MM-DD (must be ≤ as_of)")
    input_document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$",
                                       description="hash of the ONE document interpreted")

    # --- the typed interpretation ---
    event_type: Literal[EVENT_TYPES] = Field(  # type: ignore[valid-type]
        description="exactly one of the CLOSED taxonomy")
    materiality: float = Field(ge=0.0, le=1.0)
    direction: Literal["bullish", "bearish", "neutral", "uncertain"]
    rationale: str = Field(min_length=1, max_length=800)

    # --- the falsifiable claim(s): ≥1, each resolver/v1-valid (Brier-scoreable) ---
    predictions: List[Prediction] = Field(min_length=1)

    # first-class injection signal (mirrors the analyst): attacks become logged evidence
    suspected_prompt_injection: bool = False

    provenance: Provenance
    usage: Usage

    @field_validator("as_of", "file_date")
    @classmethod
    def _is_date(cls, v: str) -> str:
        _dt.date.fromisoformat(v)     # raises on a bad date
        return v

    @model_validator(mode="after")
    def _consistency(self) -> "EventCall":
        # PIT: the document must not be dated after the decision (no reading the future).
        if _dt.date.fromisoformat(self.file_date) > _dt.date.fromisoformat(self.as_of):
            raise ValueError("file_date is after as_of (PIT violation)")
        # a 'routine_non_material' call cannot smuggle high materiality.
        if self.event_type == "routine_non_material" and self.materiality > _MATERIALITY_ROUTINE_MAX:
            raise ValueError(f"routine_non_material with materiality {self.materiality} > {_MATERIALITY_ROUTINE_MAX}")
        # source ↔ taxonomy: special-sit event types only from the special-sit feed, and vice-versa.
        if self.event_type in _SPECIAL_SIT_EVENT_TYPES and self.source != "special_situation":
            raise ValueError(f"{self.event_type} requires source=special_situation")
        return self


def validate_event_call(payload: dict) -> "tuple[Optional[EventCall], Optional[str]]":
    """Independent local re-validation. Returns (call, None) or (None, reason); never raises.
    On failure the caller emits NO event call and archives the raw response for forensics."""
    try:
        return EventCall.model_validate(payload), None
    except Exception as e:   # noqa: BLE001 — any validation error → no call
        return None, str(e).splitlines()[0][:300]

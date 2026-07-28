"""T-324 — the `thesis_call/v1` schema. The thematic/narrative faculty, made falsifiable.

Sibling of `event_call/v1`: the event-interpreter reads ONE discrete document; the THESIS DESK reads
THEMES ACROSS TIME. Design spec = the user's own record (BTC@$500, NVDA pre-inflection, RKLB@$23 on the
story despite weak fundamentals, defense-during-war, picks-and-shovels-for-AI) — reading narratives and
mapping SECOND-ORDER beneficiaries, which was impossible pre-LLM.

The load-bearing design decision: **`falsifiers` is REQUIRED and non-empty.** A thesis without a falsifier
is a story, not a position. Every thesis must be able to DIE visibly, on a date, by a rule — that is what
separates this from narrative rationalization. Where the falsifier is machine-checkable it carries a
resolver/v1 spec (A's harness scores it); where it is genuinely qualitative it must still carry a hard
`check_by` date so it cannot drift indefinitely.

Horizons are LONG (months-to-years) — the schema says so honestly rather than forcing a 21-day window that
would misprice the whole faculty. Forward-only by necessity: a backtested thesis is memorization.
"""
from __future__ import annotations

import datetime as _dt
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from intelligence.analyst.eval_harness import is_resolvable_spec
from intelligence.analyst.note_schema import Provenance, Usage

SCHEMA_VERSION = "thesis_call/v1"

# The CLOSED theme taxonomy (the model picks exactly one).
THEME_CLASSES = (
    "tech_inflection",      # NVDA pre-inflection: a capability crosses a threshold
    "geopolitical",         # defense-during-war
    "supply_demand",        # a physical//capacity imbalance
    "adoption_curve",       # BTC@$500: an S-curve early
    "picks_and_shovels",    # the SECOND-ORDER play — suppliers to the obvious winner
    "regulatory",           # a rule change creates/destroys a market
    "other",
)
_SYM = r"^[A-Z][A-Z0-9.\-]{0,9}$"
_MAX_HORIZON_DAYS = 5 * 365          # theses are long, but not open-ended


class InstrumentLeg(BaseModel):
    """One instrument in the thesis, WITH its mapping reasoning. For second-order plays the
    `mapping_reason` is the actual intellectual content ('AI → compute → the named supplier')."""
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(pattern=_SYM)
    role: Literal["primary", "second_order", "sector_etf", "hedge"]
    mapping_reason: str = Field(min_length=1, max_length=600,
                                description="WHY this instrument benefits — required for second_order")
    weight_hint: float = Field(ge=0.0, le=1.0, default=0.0)

    @model_validator(mode="after")
    def _second_order_needs_a_real_chain(self) -> "InstrumentLeg":
        if self.role == "second_order" and len(self.mapping_reason.split()) < 5:
            raise ValueError("second_order leg needs a substantive mapping_reason (the causal chain)")
        return self


class Falsifier(BaseModel):
    """How this thesis DIES. Required. Machine-checkable where possible; always time-bounded."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["resolver", "qualitative"]
    statement: str = Field(min_length=1, max_length=500)
    check_by: str = Field(description="hard date the falsifier is evaluated, ISO-8601 YYYY-MM-DD")
    resolver: Optional[dict] = None      # required when kind == "resolver"

    @field_validator("check_by")
    @classmethod
    def _date(cls, v: str) -> str:
        _dt.date.fromisoformat(v); return v

    @model_validator(mode="after")
    def _resolver_kind_must_resolve(self) -> "Falsifier":
        if self.kind == "resolver":
            if not isinstance(self.resolver, dict):
                raise ValueError("kind='resolver' requires a resolver/v1 spec")
            ok, why = is_resolvable_spec(self.resolver)
            if not ok:
                raise ValueError(f"falsifier resolver not resolver/v1-valid: {why}")
        return self


class ThesisCall(BaseModel):
    """A thematic thesis. Validation failure ⇒ NO thesis is filed (raw archived)."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["thesis_call/v1"] = "thesis_call/v1"

    thesis_id: str = Field(min_length=1, max_length=96)
    as_of: str = Field(description="filing date, ISO-8601 YYYY-MM-DD")
    origin: Literal["machine", "user_seeded"]
    narrative: str = Field(min_length=20, max_length=4000,
                           description="the story, in words — what is happening and why it matters")
    theme_class: Literal[THEME_CLASSES] = Field(description="exactly one of the CLOSED taxonomy")  # type: ignore[valid-type]
    instruments: List[InstrumentLeg] = Field(min_length=1)
    conviction: float = Field(ge=0.0, le=1.0)
    horizon_days: int = Field(gt=0, le=_MAX_HORIZON_DAYS,
                              description="months-to-years; theses are long by nature")
    entry_basis: str = Field(min_length=1, max_length=800,
                             description="why NOW — what makes this the entry, not just the idea")
    # THE load-bearing requirement: a thesis without a falsifier is a story, not a position.
    falsifiers: List[Falsifier] = Field(min_length=1)

    suspected_prompt_injection: bool = False
    provenance: Provenance
    usage: Usage

    @field_validator("as_of")
    @classmethod
    def _as_of_date(cls, v: str) -> str:
        _dt.date.fromisoformat(v); return v

    @model_validator(mode="after")
    def _coherent(self) -> "ThesisCall":
        as_of = _dt.date.fromisoformat(self.as_of)
        horizon_end = as_of + _dt.timedelta(days=self.horizon_days)
        for f in self.falsifiers:
            cb = _dt.date.fromisoformat(f.check_by)
            if cb <= as_of:
                raise ValueError(f"falsifier check_by {f.check_by} must be AFTER as_of {self.as_of}")
            # a falsifier that can only fire after the thesis has already resolved is not a falsifier
            if cb > horizon_end + _dt.timedelta(days=30):
                raise ValueError("falsifier check_by is beyond the thesis horizon (+30d grace) — it could never kill it")
        if self.theme_class == "picks_and_shovels" and not any(i.role == "second_order" for i in self.instruments):
            raise ValueError("picks_and_shovels thesis must name at least one second_order instrument")
        return self


def validate_thesis_call(payload: dict) -> "tuple[Optional[ThesisCall], Optional[str]]":
    """Independent local re-validation; never raises. (None, reason) ⇒ NO thesis filed, raw archived."""
    try:
        return ThesisCall.model_validate(payload), None
    except Exception as e:   # noqa: BLE001
        return None, str(e).splitlines()[0][:300]

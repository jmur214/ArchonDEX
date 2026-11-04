# engines/engine_a_alpha/edge_registry.py
"""Engine A's view of `data/governor/edges.yml` — specs in, explicit saves out, IMPORTS PURE.

Until 2026-10-22 this file was the third writer of the registry and the worst one: `_load` ended
in `except Exception: self._specs = {}`, `_save` was a non-atomic `write_text`, and `ensure()` —
called at IMPORT by every auto-registering edge module — saved unconditionally. On an unreadable
registry the first import rewrote the file holding ONE edge (R, proven on planted files;
`docs/Sources/edge_registry_single_writer_brief_2026-10-14.md`).

Now (the single-writer unit, user-approved 2026-10-22):
* the read is the ONE fail-closed reader (`core.edge_registry_io.read_registry`): an unreadable
  registry RAISES `RegistryUnreadableError` at construction, never becomes "no edges";
* every write is EXPLICIT and goes through the ONE atomic writer: `register`, `set_status`,
  `set_failure_metadata`, `save` (alias `_save`, kept for the tier classifier and journal_apply);
* `ensure()` NEVER writes. It records what the module registered, in memory, process-wide
  (`EdgeRegistry.import_registrations()`), with whether the registry already holds it and which
  code-owned fields drifted. Unpersisted registrations are INVISIBLE to consumers — the file is
  the sole authority — until `scripts/sync_edge_registry.py` persists them, reporting each class
  of change. The params merge it applies is KEY-WISE (`merge_code_owned`): code-owned keys are
  the module's `DEFAULT_PARAMS` keys and CODE wins on them; every other key is preserved verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from core.edge_registry_io import (
    KNOWN_ROW_KEYS,
    REFUSAL,
    RegistryUnreadableError,
    RegistryWriteError,
    canonical_row,
    coerce_scalars,
    read_registry,
    write_registry_atomic,
)


# Closed vocabulary for `EdgeSpec.failure_reason`. Keep narrow on purpose;
# adding members is a deliberate decision (downstream tooling switches on
# this set). New reasons should be added with a memory-link rationale.
VALID_FAILURE_REASONS: frozenset = frozenset({
    "regime_conditional",   # signal real but only fires in some regimes
    "universe_too_small",   # cross-sectional work below stat threshold
    "data_quality",         # source-side issue (stale, sparse, biased)
    "overfit",              # in-sample win, OOS collapse
    "cost_dominated",       # alpha exists pre-cost, gone post-cost
    "other",                # explicit unknown — better than null
})


@dataclass
class EdgeSpec:
    edge_id: str
    category: str
    module: str                 # e.g. "rsi_mean_reversion"
    version: str = "1.0.0"
    params: Optional[Dict[str, Any]] = None
    status: str = "active"      # "active" | "candidate" | "retired"
    # Regime-conditional weight gate: maps Engine E regime_summary labels
    # ("benign", "stressed", "crisis") to weight multipliers [0, 1].
    # Empty dict / None means the edge is unconditionally weighted (no gate).
    # Applied by SignalProcessor on top of alpha_settings edge_weights.
    regime_gate: Optional[Dict[str, float]] = None

    # ------------------------- Phase 1 tier system ------------------------- #
    # Three-layer architecture (see docs/Core/phase1_metalearner_design.md):
    #   tier="alpha"    → standalone signal that trades directly (factor t > 2)
    #   tier="feature"  → input to the meta-learner, not a direct trade signal
    #   tier="context"  → regime modifier, weights other edges
    # Machine-classified by `engines/engine_a_alpha/tier_classifier.py` from
    # factor-decomposition diagnostics. Default "feature" so newly-registered
    # edges feed the meta-learner until enough data accumulates to promote.
    tier: str = "feature"  # "alpha" | "feature" | "context"
    # ISO-8601 timestamp of the last TierClassifier run that touched this
    # spec. None means tier was never machine-classified (legacy edge or
    # newly-registered candidate awaiting first run).
    tier_last_updated: Optional[str] = None
    # How this edge participates in signal aggregation:
    #   "standalone" → tier=alpha edges contribute directly to the score
    #   "input"      → tier=feature edges feed the meta-learner
    #   "gate"       → tier=context edges modify other edges' weights
    # Default "input" matches default tier="feature".
    combination_role: str = "input"  # "standalone" | "input" | "gate"
    # ----------------------- Edge graveyard tags ----------------------- #
    # Optional structured tagging for failed edges (status="failed"). Both
    # fields are nullable and ignored on round-trip when None, so legacy
    # registries without them parse identically. See
    # docs/Measurements/2026-05/ws_j_cross_cutting_trio.md for the closed vocabulary.
    #   failure_reason ∈ {"regime_conditional", "universe_too_small",
    #                     "data_quality", "overfit", "cost_dominated", "other"}
    failure_reason: Optional[str] = None
    # edge_id of a replacement edge, or None if no replacement exists.
    # Tooling later traces `superseded_by` chains to surface "what should I
    # use instead?" without requiring readers to grep memory files.
    superseded_by: Optional[str] = None
    # Catch-all for fields the registry doesn't model first-class (e.g.,
    # `reclassified_to`, `reclassified_on`, `reclassification_note` added
    # 2026-05-02 for the macro→regime-input reclassification audit). Loaded
    # from yml and round-tripped on save; not interpreted by the registry.
    extra: Optional[Dict[str, Any]] = None


def spec_to_row(spec: EdgeSpec) -> Dict[str, Any]:
    """The registry row for a spec — Engine A's shape, which `canonical_row` leaves unchanged."""
    row: Dict[str, Any] = {
        "edge_id": spec.edge_id,
        "category": spec.category,
        "module": spec.module,
        "version": spec.version,
        "params": spec.params or {},
        "status": spec.status,
    }
    if spec.regime_gate:
        row["regime_gate"] = spec.regime_gate
    if spec.tier:
        row["tier"] = spec.tier
    if spec.tier_last_updated:
        row["tier_last_updated"] = spec.tier_last_updated
    if spec.combination_role and spec.combination_role != "input":
        row["combination_role"] = spec.combination_role
    if spec.failure_reason is not None:
        row["failure_reason"] = spec.failure_reason
    if spec.superseded_by is not None:
        row["superseded_by"] = spec.superseded_by
    if spec.extra:
        for k, v in spec.extra.items():
            row[k] = v
    return row


def row_to_spec(row: Mapping[str, Any], *, path: Optional[Path] = None) -> EdgeSpec:
    """A spec from a registry row. A row without a `module` cannot be loaded by Engine A (nothing
    could instantiate it), so it REFUSES — `RegistryUnreadableError`, never a silently dropped row."""
    if not row.get("module"):
        raise RegistryUnreadableError(
            f"{path or 'registry'}: row {row.get('edge_id')!r} has no module — Engine A cannot load it; {REFUSAL}")
    extra = {k: v for k, v in row.items() if k not in KNOWN_ROW_KEYS}
    return EdgeSpec(
        edge_id=row["edge_id"],
        category=row.get("category", "other"),
        module=row["module"],
        version=row.get("version", "1.0.0"),
        params=row.get("params") or {},
        status=row.get("status", "active"),
        regime_gate=row.get("regime_gate") or None,
        tier=row.get("tier", "feature"),
        tier_last_updated=row.get("tier_last_updated"),
        combination_role=row.get("combination_role", "input"),
        failure_reason=row.get("failure_reason"),
        superseded_by=row.get("superseded_by"),
        extra=extra or None,
    )


# --------------------------------------------------------------------------- #
# The code-owned merge (applied ONLY by the sync — never at import)
# --------------------------------------------------------------------------- #
#: Whole fields the module's code owns. Status, tier, tier_last_updated, combination_role,
#: regime_gate, the graveyard tags and every extra key are registry-owned and never touched.
CODE_OWNED_FIELDS: Tuple[str, ...] = ("category", "module", "version")

ABSENT = "<absent>"   # a registry value that did not exist, in a report


@dataclass
class MergeReport:
    """What a sync did (or would do) to ONE edge's row — four distinct classes (the brief's sync
    specification): never registered, drift applied, type changes, registry-only keys preserved."""
    edge_id: str
    never_registered: bool = False
    #: "category" | "module" | "version" | "params.<key>" -> (registry value or ABSENT, code value)
    drift_applied: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)
    #: "params.<key>" -> (registry type name, code type name); the code value is applied
    type_changes: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    #: "params.<key>" the code does not own, preserved verbatim (Discovery's verdict fields, notes)
    registry_only_keys: List[str] = field(default_factory=list)

    @property
    def changes_file(self) -> bool:
        return self.never_registered or bool(self.drift_applied) or bool(self.type_changes)


def merge_code_owned(row: Optional[Mapping[str, Any]], spec: EdgeSpec) -> Tuple[Dict[str, Any], MergeReport]:
    """The KEY-WISE merge of a module's registration into its registry row (R §4.1, ruled).

    * no row → the spec's full row, class "never registered" (status and tier as the module
      declares them: that is what a NEW registration gets);
    * category / module / version → the code value when the code sets one and it differs
      ("drift applied"); an empty code value keeps the registry's (`spec.x or s.x`, as before);
    * params, key by key: a code-owned key (one in the module's params) absent in the registry is
      added, a differing value takes the code value ("drift applied"), a differing TYPE is its own
      class ("type change", the code value applied); every registry key the code does not own is
      preserved verbatim and listed ("registry-only keys preserved"). The old wholesale
      `s.params = spec.params or s.params` dropped those keys on every import.
    The returned row is a NEW dict; `row` is not mutated."""
    report = MergeReport(edge_id=spec.edge_id)
    if row is None:
        report.never_registered = True
        return spec_to_row(spec), report
    out: Dict[str, Any] = dict(row)
    for f in CODE_OWNED_FIELDS:
        code_v = getattr(spec, f)
        if not code_v:
            continue
        if f not in row:
            report.drift_applied[f] = (ABSENT, code_v)
            out[f] = code_v
        elif row[f] != code_v:
            report.drift_applied[f] = (row[f], code_v)
            out[f] = code_v
    reg_params: Dict[str, Any] = dict(row.get("params") or {})
    code_params: Dict[str, Any] = {k: coerce_scalars(v) for k, v in (spec.params or {}).items()}
    merged = dict(reg_params)                       # registry keys first, verbatim, order kept
    for k, code_v in code_params.items():
        if k not in reg_params:
            merged[k] = code_v
            report.drift_applied[f"params.{k}"] = (ABSENT, code_v)
            continue
        reg_v = reg_params[k]
        if type(reg_v) is not type(code_v):
            report.type_changes[f"params.{k}"] = (type(reg_v).__name__, type(code_v).__name__)
            merged[k] = code_v
        elif reg_v != code_v:
            report.drift_applied[f"params.{k}"] = (reg_v, code_v)
            merged[k] = code_v
    report.registry_only_keys = [f"params.{k}" for k in reg_params if k not in code_params]
    out["params"] = merged
    return out, report


@dataclass
class ImportRegistration:
    """What one module registered at import, and how it stands against the registry that module
    read at the time. Recorded in memory only; the sync persists it."""
    spec: EdgeSpec
    persisted: bool                 # the registry held this edge_id when the module imported
    report: MergeReport             # the drift the sync would apply (empty when nothing differs)
    registry_path: str


class EdgeRegistry:
    """
    File-backed view of the edge registry (`data/governor/edges.yml`).

    Reads through the ONE fail-closed reader; writes through the ONE atomic writer, and ONLY from
    the explicit methods (`register`, `set_status`, `set_failure_metadata`, `save`). Constructing
    an instance never writes and never creates directories. `ensure()` never writes.
    """

    #: Process-wide record of every import-time registration (`ensure()`), keyed by edge_id.
    #: The sync reads it; consumers never do — an unpersisted registration is invisible.
    _import_registrations: Dict[str, ImportRegistration] = {}

    def __init__(self, store_path: "str | Path" = "data/governor/edges.yml") -> None:
        self.path = Path(store_path)
        self._specs: Dict[str, EdgeSpec] = {}
        self._load()

    # ---------------- file i/o ---------------- #
    def _load(self) -> None:
        """FAIL CLOSED: an absent file is the only empty registry; anything unreadable raises."""
        data = read_registry(self.path)
        specs: Dict[str, EdgeSpec] = {}
        for row in data["edges"]:
            spec = row_to_spec(row, path=self.path)
            specs[spec.edge_id] = spec
        self._specs = specs

    def save(self) -> None:
        """The EXPLICIT save — atomic, through the one writer. Raises `RegistryWriteError`."""
        write_registry_atomic(self.path, {"edges": [spec_to_row(s) for s in self._specs.values()]})

    # The private name is what the tier classifier, journal_apply and older tests call.
    _save = save

    # --------------- public api ---------------- #
    def register(self, spec: EdgeSpec) -> None:
        """Explicit registration: upsert the spec and SAVE. Not for import time (use `ensure`)."""
        self._specs[spec.edge_id] = spec
        self.save()

    def set_status(self, edge_id: str, status: str) -> None:
        if edge_id in self._specs:
            self._specs[edge_id].status = status
            self.save()

    def set_failure_metadata(
        self,
        edge_id: str,
        failure_reason: Optional[str] = None,
        superseded_by: Optional[str] = None,
    ) -> None:
        """Tag a failed edge with structured graveyard metadata.

        Validates ``failure_reason`` against ``VALID_FAILURE_REASONS``.
        ``superseded_by`` is a free-form edge_id reference; if provided
        and non-empty, it must match a known edge to catch typos. Pass
        ``None`` for either field to leave it unchanged on the existing
        spec, or pass an explicit empty-string sentinel via ``""`` to
        clear it (rare — typically only when re-tagging).

        Does not mutate ``status``: callers should use the existing
        ``set_status(edge_id, "failed")`` first if needed.
        """
        if edge_id not in self._specs:
            raise KeyError(f"unknown edge_id: {edge_id!r}")
        spec = self._specs[edge_id]
        if failure_reason is not None:
            if failure_reason == "":
                spec.failure_reason = None
            else:
                if failure_reason not in VALID_FAILURE_REASONS:
                    raise ValueError(
                        f"failure_reason {failure_reason!r} not in "
                        f"{sorted(VALID_FAILURE_REASONS)}"
                    )
                spec.failure_reason = failure_reason
        if superseded_by is not None:
            if superseded_by == "":
                spec.superseded_by = None
            else:
                if superseded_by not in self._specs:
                    raise ValueError(
                        f"superseded_by {superseded_by!r} is not a "
                        f"registered edge_id"
                    )
                if superseded_by == edge_id:
                    raise ValueError(
                        f"edge cannot supersede itself: {edge_id!r}"
                    )
                spec.superseded_by = superseded_by
        self.save()

    def list(self, status: Optional[str] = None,
             statuses: Optional[List[str]] = None) -> List[EdgeSpec]:
        """List edges filtered by status. Pass `status="active"` for single
        match or `statuses=["active","paused"]` for multi-match (used for
        soft-pause behavior where paused edges keep trading at reduced weight).
        """
        vals = list(self._specs.values())
        if statuses:
            allowed = set(statuses)
            return [s for s in vals if s.status in allowed]
        if status:
            return [s for s in vals if s.status == status]
        return vals

    def list_tradeable(self) -> List[EdgeSpec]:
        """Return edges that should be loaded into the alpha pipeline: active
        edges trade at their config weight; paused edges trade at a reduced
        weight (soft-pause) so the revival gate can observe post-pause
        performance. Retired/failed/archived/candidate edges do NOT trade.
        """
        return self.list(statuses=["active", "paused"])

    def list_modules(self, status: str = "active") -> List[str]:
        """
        Returns module names for edges with the specified status.
        """
        return [s.module for s in self._specs.values() if s.status == status]

    def list_active_modules(self) -> List[str]:
        """
        Returns module names for edges whose status == 'active'.
        Example output: ["rsi_mean_reversion", "bb_breakout"]
        """
        return self.list_modules(status="active")

    def get(self, edge_id: str) -> Optional[EdgeSpec]:
        return self._specs.get(edge_id)

    def get_all_specs(self) -> List[EdgeSpec]:
        """Returns all registered edge specs regardless of status."""
        return list(self._specs.values())

    # ------------------- import-time registration (PURE) ------------------- #
    def ensure(self, spec: EdgeSpec) -> None:
        """Record an import-time registration. NEVER writes, never mutates the loaded specs.

        Records, process-wide, what the module registered and how it stands against the registry
        this instance read: `persisted` (the id exists) and the code-owned drift the sync would
        apply. Status, tier, tier_last_updated and combination_role are registry-owned and are not
        part of the drift (the 2026-04-25 status-stomp and the tier-stomp guard, kept by
        construction: the sync's merge never reads them from the spec for an existing row).

        Before 2026-10-22 this registered-and-SAVED at import — ~30 non-atomic rewrites per
        process, and on an unreadable registry a one-edge file (R's F1).
        """
        existing = self._specs.get(spec.edge_id)
        row = canonical_row(spec_to_row(existing)) if existing is not None else None
        _, report = merge_code_owned(row, spec)
        EdgeRegistry._import_registrations[spec.edge_id] = ImportRegistration(
            spec=spec, persisted=existing is not None, report=report, registry_path=str(self.path))

    @classmethod
    def import_registrations(cls) -> Dict[str, ImportRegistration]:
        """Every registration `ensure()` recorded in this process, by edge_id (a copy)."""
        return dict(cls._import_registrations)

    @classmethod
    def clear_import_registrations(cls) -> None:
        """Forget the recorded registrations (tests that re-import modules under a planted registry)."""
        cls._import_registrations.clear()


__all__ = [
    "ABSENT", "CODE_OWNED_FIELDS", "EdgeRegistry", "EdgeSpec", "ImportRegistration", "MergeReport",
    "RegistryUnreadableError", "RegistryWriteError", "VALID_FAILURE_REASONS", "merge_code_owned",
    "row_to_spec", "spec_to_row",
]

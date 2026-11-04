"""core/edge_registry_io.py — the ONE reader and the ONE atomic writer for `data/governor/edges.yml`.

`edges.yml` is the SOLE authority on which edges exist and in what state (`[NN-NO-MANUAL-EDGES]`).
Until 2026-10-22 three engines wrote it with three serialisers, two of them non-atomic inside a
swallowing `except`, and Engine A's wrote it at IMPORT in a shape that could reduce it to one edge
(`docs/Sources/edge_registry_single_writer_brief_2026-10-14.md`). This module is neutral ground —
Engines A, D and F import it; none imports another — and it holds exactly four things:

* the FAIL-CLOSED read (`read_registry`): an ABSENT file is the only empty registry; a file that
  exists but is unparseable, empty, not an edge registry, or holds a row without an `edge_id`
  RAISES `RegistryUnreadableError` and is never treated as "no edges";
* ONE row canonicaliser (`canonical_row`): Engine A's key order, `category` / `version` /
  `params` / `status` / `tier` materialised exactly as `EdgeRegistry` has always written them,
  extras appended in their original order — the real registry already round-trips through it
  byte-identically, so adopting it is a null diff (R §4.2);
* ONE serialiser (`serialise`): `yaml.safe_dump(sort_keys=False)` with numpy / pandas scalars
  coerced to Python types; anything else unrepresentable RAISES. No value validation — `error`
  and `archived` are live statuses;
* the ATOMIC write (`write_registry_atomic`): serialise first, sibling temp file, fsync, the
  file's mode kept, `os.replace`. A failure at any step RAISES `RegistryWriteError` and leaves the
  registry's bytes untouched (the temp file stays as evidence).

It is called from EXPLICIT steps only — the governor's own save path, `scripts/sync_edge_registry.py`,
and the explicit writers (`EdgeRegistry.register/set_status/set_failure_metadata/save`, Discovery's
`save_candidates`, Engine F's lifecycle save). Never from an import.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Dict, Mapping, Union

import yaml

PathLike = Union[str, "os.PathLike[str]"]

DEFAULT_REGISTRY_PATH = Path("data/governor/edges.yml")

REFUSAL = "refusing — the file is untouched"


class RegistryUnreadableError(RuntimeError):
    """edges.yml exists but cannot be read as an edge registry. Every consumer REFUSES — nothing
    rewrites, or carries on with "no edges" from, a registry it could not read."""


class RegistryWriteError(RuntimeError):
    """A registry save failed. The registry's bytes are untouched (serialise-first, temp file,
    atomic replace); the cause is chained. Raised, never logged-and-swallowed."""


# Engine A's row shape (EdgeRegistry._save, unchanged since the tier fields): these six always, in
# this order; the optional fields after them when set; every other key verbatim, in its original order.
_HEAD_KEYS = ("edge_id", "category", "module", "version", "params", "status")
KNOWN_ROW_KEYS = frozenset({
    "edge_id", "category", "module", "version", "params", "status", "regime_gate",
    "tier", "tier_last_updated", "combination_role", "failure_reason", "superseded_by",
})


# --------------------------------------------------------------------------- #
# read
# --------------------------------------------------------------------------- #
def read_registry(path: PathLike) -> Dict[str, Any]:
    """The registry as a dict holding an `edges` list of row dicts.

    An ABSENT file is an empty registry (the only legitimate empty). A file that EXISTS but is
    unparseable, empty, a scalar, a dict without an `edges` list, or holds a row that is not a
    dict with a non-empty string `edge_id`, RAISES `RegistryUnreadableError`. A bare list at the
    root (the legacy format) is still read."""
    p = Path(path)
    if not p.exists():
        return {"edges": []}
    try:
        text = p.read_text()
    except OSError as exc:
        raise RegistryUnreadableError(f"{p} cannot be read ({exc}); {REFUSAL}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RegistryUnreadableError(f"{p} is not parseable YAML ({exc}); {REFUSAL}") from exc
    if isinstance(data, list):                     # legacy format: a bare edge list at the root
        data = {"edges": data}
    if not isinstance(data, dict) or not isinstance(data.get("edges"), list):
        shape = type(data).__name__ + ("" if not isinstance(data, dict) else f", keys {sorted(data)}")
        raise RegistryUnreadableError(f"{p} exists but holds no edge registry (root {shape}); {REFUSAL}")
    for i, row in enumerate(data["edges"]):
        if not isinstance(row, dict) or not isinstance(row.get("edge_id"), str) or not row["edge_id"]:
            raise RegistryUnreadableError(
                f"{p} row {i} is not an edge row (a dict with a non-empty string edge_id): "
                f"{str(row)[:120]!r}; {REFUSAL}")
    return data


# --------------------------------------------------------------------------- #
# canonical form
# --------------------------------------------------------------------------- #
def canonical_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """One row in Engine A's canonical form (what `EdgeRegistry._load` → `_save` has always produced).

    `category` (default "other"), `version` ("1.0.0"), `params` ({}), `status` ("active") and
    `tier` ("feature") are materialised; `module` is written when the row has one (an Engine-A
    reader refuses a row without it); `regime_gate` / `tier_last_updated` when truthy;
    `combination_role` when not the default "input"; `failure_reason` / `superseded_by` when not
    None; every other key verbatim, in its original order."""
    if not isinstance(row, Mapping) or not isinstance(row.get("edge_id"), str) or not row["edge_id"]:
        raise RegistryWriteError(f"not an edge row (a dict with a non-empty string edge_id): {str(row)[:120]!r}")
    out: Dict[str, Any] = {"edge_id": row["edge_id"], "category": row.get("category", "other")}
    if "module" in row:
        out["module"] = row["module"]
    out["version"] = row.get("version", "1.0.0")
    out["params"] = row.get("params") or {}
    out["status"] = row.get("status", "active")
    regime_gate = row.get("regime_gate") or None
    if regime_gate:
        out["regime_gate"] = regime_gate
    tier = row.get("tier", "feature")
    if tier:
        out["tier"] = tier
    tier_last_updated = row.get("tier_last_updated")
    if tier_last_updated:
        out["tier_last_updated"] = tier_last_updated
    combination_role = row.get("combination_role", "input")
    if combination_role and combination_role != "input":
        out["combination_role"] = combination_role
    if row.get("failure_reason") is not None:
        out["failure_reason"] = row["failure_reason"]
    if row.get("superseded_by") is not None:
        out["superseded_by"] = row["superseded_by"]
    for k, v in row.items():
        if k not in KNOWN_ROW_KEYS:
            out[k] = v
    return out


def _coerce(obj: Any) -> Any:
    """numpy / pandas scalars → Python scalars, arrays → lists, Timestamps → ISO strings; everything
    else passes through for `safe_dump` to accept or REFUSE (never a `!!python` tag the reader would
    then refuse)."""
    if isinstance(obj, dict):
        return {_coerce(k): _coerce(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_coerce(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return [_coerce(v) for v in obj.tolist()]
    except ImportError:  # pragma: no cover — numpy is a hard dependency of the project
        pass
    try:
        import pandas as pd
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
    except ImportError:  # pragma: no cover
        pass
    return obj


#: The scalar coercion the serialiser applies, for callers that compare code values against the
#: registry's (the sync's key-wise merge): a numpy float in a module's DEFAULT_PARAMS is the same
#: value as the registry's Python float, not a type change.
coerce_scalars = _coerce


def serialise(registry: Mapping[str, Any]) -> str:
    """The ONE serialisation: `edges` first (every row canonical), any other top-level key after it in
    its original order (Discovery kept them; Engine A dropped them — none exists in practice, so
    keeping them is the no-loss choice). Raises `RegistryWriteError` on anything unrepresentable."""
    if not isinstance(registry, Mapping) or not isinstance(registry.get("edges"), (list, tuple)):
        raise RegistryWriteError(f"not a registry (a dict with an `edges` list): {type(registry).__name__}")
    doc: Dict[str, Any] = {"edges": [canonical_row(r) for r in registry["edges"]]}
    for k, v in registry.items():
        if k != "edges":
            doc[k] = v
    try:
        return yaml.safe_dump(_coerce(doc), sort_keys=False)
    except yaml.YAMLError as exc:
        raise RegistryWriteError(f"the registry could not be serialised ({type(exc).__name__}: {exc})") from exc


# --------------------------------------------------------------------------- #
# write
# --------------------------------------------------------------------------- #
def write_registry_atomic(path: PathLike, registry: Mapping[str, Any]) -> str:
    """Serialise FIRST, write a sibling temp file, fsync, keep the registry's mode, `os.replace`.
    Any failure raises `RegistryWriteError` with the registry's bytes untouched; a failed attempt
    leaves the temp file in place as evidence. Returns the text written."""
    p = Path(path)
    text = serialise(registry)                      # raises RegistryWriteError; nothing touched yet
    tmp = p.with_name(f".{p.name}.tmp-{os.getpid()}")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if p.exists():
            # keep the registry's permissions across the replace (a 600 file became 644 — the temp
            # file's umask default — after a single save; R's note on the Engine-D unit)
            os.chmod(tmp, stat.S_IMODE(p.stat().st_mode))
        os.replace(tmp, p)
    except Exception as exc:
        raise RegistryWriteError(
            f"{p}: the atomic write failed ({type(exc).__name__}: {exc}); the registry is untouched "
            f"(temp file {tmp} left as evidence)") from exc
    return text


def write_registry_if_changed(path: PathLike, registry: Mapping[str, Any]) -> bool:
    """Write only when the serialised bytes differ from the file's. A no-op leaves the bytes AND the
    mtime untouched (the sync's idempotence). Returns True when it wrote."""
    p = Path(path)
    text = serialise(registry)
    if p.exists():
        try:
            if p.read_text() == text:
                return False
        except OSError as exc:
            raise RegistryUnreadableError(f"{p} cannot be read ({exc}); {REFUSAL}") from exc
    write_registry_atomic(p, registry)
    return True


def rows_by_id(registry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """{edge_id: row} over a registry dict (insertion order kept)."""
    return {r["edge_id"]: r for r in registry["edges"]}


__all__ = [
    "DEFAULT_REGISTRY_PATH", "KNOWN_ROW_KEYS", "REFUSAL", "RegistryUnreadableError", "RegistryWriteError",
    "canonical_row", "coerce_scalars", "read_registry", "rows_by_id", "serialise",
    "write_registry_atomic", "write_registry_if_changed",
]

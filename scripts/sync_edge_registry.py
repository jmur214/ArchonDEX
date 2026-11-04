"""scripts/sync_edge_registry.py — the ONE explicit step that persists what the edge modules register.

    python scripts/sync_edge_registry.py                     # sync data/governor/edges.yml
    python scripts/sync_edge_registry.py --check             # write nothing; exit 1 if a sync would change the file
    python scripts/sync_edge_registry.py --registry PATH     # another registry (an isolated run's)
    python scripts/sync_edge_registry.py --json              # the report as JSON

Since the edges.yml single-writer unit (2026-10-22) importing an edge module NEVER writes the
registry: `EdgeRegistry.ensure()` records the module's registration in memory. This script imports
every auto-registering module under `engines/engine_a_alpha/edges/` (the set is enumerated from the
source by AST: a module-level `.ensure(` call), merges each registration into the registry
KEY-WISE (`merge_code_owned`: code-owned fields and params keys take the code value; every other key
is preserved verbatim; status, tier and the registry-owned fields are never touched), and writes
through the ONE atomic writer only when the bytes would change.

The report has four DISTINCT classes: never registered (additions), drift applied, type changes,
registry-only keys preserved. `--check` writes nothing and exits non-zero when the sync WOULD CHANGE
the file (additions, drift, type changes); registry-only keys are reported, not failed — they are
what the sync preserves, not what it changes. A sync with nothing to change leaves the bytes AND
the mtime untouched; a second run reports nothing. The network is dead-ended by construction while
the modules import (a socket cannot be created).

A fresh checkout has no registry; this is its step one. An UNREADABLE registry refuses before any
module is imported (exit 2) — the file is never rewritten from a failed read.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import socket
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.edge_registry_io import (  # noqa: E402
    DEFAULT_REGISTRY_PATH,
    RegistryUnreadableError,
    read_registry,
    rows_by_id,
    serialise,
    write_registry_if_changed,
)
from engines.engine_a_alpha.edge_registry import (  # noqa: E402
    EdgeRegistry,
    ImportRegistration,
    merge_code_owned,
)

EDGES_PACKAGE = "engines.engine_a_alpha.edges"
EDGES_DIR = ROOT / "engines" / "engine_a_alpha" / "edges"


# --------------------------------------------------------------------------- #
# which modules register at import — from the source, not a hand-kept list
# --------------------------------------------------------------------------- #
def _module_level_calls_ensure(tree: ast.Module) -> bool:
    """True when a `.ensure(...)` call sits in the module's top-level code (inside try/for/if/with
    is still top level); calls inside function or class bodies do not count."""
    stack: List[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "ensure"):
            return True
        stack.extend(ast.iter_child_nodes(node))
    return False


def auto_registering_modules(edges_dir: Path = EDGES_DIR) -> List[str]:
    """Bare module names under the edges package whose module-level code calls `.ensure(` — the
    set this sync imports and the pure-import lock enumerates. Sorted; helpers (`_…`) excluded."""
    out = []
    for p in sorted(edges_dir.glob("*.py")):
        if p.name.startswith("_"):
            continue
        if _module_level_calls_ensure(ast.parse(p.read_text())):
            out.append(p.stem)
    return out


# --------------------------------------------------------------------------- #
# importing the modules with the network dead-ended
# --------------------------------------------------------------------------- #
@contextmanager
def network_dead_ended() -> Iterator[None]:
    """By construction: while the edge modules import, no socket can be created."""
    def _refused(*a: Any, **k: Any) -> Any:
        raise RuntimeError("sync_edge_registry: the network is dead-ended while edge modules import")
    saved = (socket.socket, socket.create_connection, socket.getaddrinfo)
    socket.socket, socket.create_connection, socket.getaddrinfo = _refused, _refused, _refused  # type: ignore[misc]
    try:
        yield
    finally:
        socket.socket, socket.create_connection, socket.getaddrinfo = saved  # type: ignore[misc]


def collect_registrations(modules: Iterable[str]) -> Dict[str, ImportRegistration]:
    """Import `modules` (bare names under the edges package) with the network dead-ended and return
    the registrations they recorded, keyed by edge_id. Only registrations whose `module` is one of
    these modules count — an archived module imported elsewhere in the process is never synced."""
    names = list(modules)
    accepted = {f"{EDGES_PACKAGE}.{n}" for n in names} | set(names)
    # What a module registers is EXECUTED here, never remembered: a module imported earlier in
    # this process (a test session, a harness) registered against whatever registry its cwd held
    # at the time — or nothing, if that read refused — so it is re-run (reload), and its earlier
    # record dropped first, so the result reflects this execution only.
    for eid, r in list(EdgeRegistry.import_registrations().items()):
        if str(r.spec.module) in accepted:
            EdgeRegistry._import_registrations.pop(eid, None)
    with network_dead_ended():
        for name in names:
            full = f"{EDGES_PACKAGE}.{name}"
            if full in sys.modules:
                importlib.reload(sys.modules[full])
            else:
                importlib.import_module(full)
    return {eid: r for eid, r in EdgeRegistry.import_registrations().items()
            if str(r.spec.module) in accepted}


# --------------------------------------------------------------------------- #
# the sync
# --------------------------------------------------------------------------- #
@dataclass
class SyncReport:
    registry: str
    n_rows_before: int
    n_rows_after: int
    modules: List[str]
    registrations_per_module: Dict[str, int]
    additions: List[str] = field(default_factory=list)                        # never registered
    drift_applied: Dict[str, Dict[str, List[Any]]] = field(default_factory=dict)   # edge -> field -> [registry, code]
    type_changes: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)    # edge -> field -> [reg type, code type]
    registry_only_keys: Dict[str, List[str]] = field(default_factory=dict)         # edge -> keys preserved
    check: bool = False
    wrote: bool = False
    sha256_before: Optional[str] = None
    sha256_after: Optional[str] = None

    @property
    def changes_file(self) -> bool:
        return bool(self.additions or self.drift_applied or self.type_changes)

    def lines(self) -> List[str]:
        n_drift = sum(len(v) for v in self.drift_applied.values())
        n_types = sum(len(v) for v in self.type_changes.values())
        n_keep = sum(len(v) for v in self.registry_only_keys.values())
        zero = sorted(m for m, n in self.registrations_per_module.items() if n == 0)
        out = [
            f"[SYNC] registry: {self.registry} ({self.n_rows_before} rows) — "
            f"{len(self.modules)} auto-registering module(s) imported, "
            f"{sum(self.registrations_per_module.values())} registration(s)"
            + (f"; registered nothing (data-driven or refused at import): {zero}" if zero else ""),
            f"[SYNC] never registered (additions): {len(self.additions)}"
            + (f" — {self.additions}" if self.additions else ""),
            f"[SYNC] drift applied: {n_drift} field(s) on {len(self.drift_applied)} edge(s)"
            + "".join(f"\n         {e}.{f}: {old!r} -> {new!r}"
                      for e, fs in self.drift_applied.items() for f, (old, new) in fs.items()),
            f"[SYNC] type changes: {n_types}"
            + "".join(f"\n         {e}.{f}: {a} -> {b}"
                      for e, fs in self.type_changes.items() for f, (a, b) in fs.items()),
            f"[SYNC] registry-only params keys preserved: {n_keep} on {len(self.registry_only_keys)} edge(s)"
            + "".join(f"\n         {e}: {ks}" for e, ks in self.registry_only_keys.items()),
        ]
        if self.check:
            out.append("[SYNC] --check: nothing written; " + (
                "a sync WOULD CHANGE the file (exit 1)" if self.changes_file else "the registry is in sync (exit 0)"))
        elif self.wrote:
            out.append(f"[SYNC] written: {self.n_rows_after} rows; sha256 {self.sha256_before} -> {self.sha256_after}")
        else:
            out.append("[SYNC] no change — bytes identical, file untouched")
        return out


def _sha(path: Path) -> Optional[str]:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def sync(registry_path: "str | Path" = DEFAULT_REGISTRY_PATH, *, modules: Optional[Iterable[str]] = None,
         check: bool = False) -> SyncReport:
    """Merge every auto-registering module's registration into `registry_path` and write it through
    the one atomic writer when the bytes would change. `check=True` writes nothing.

    Refuses (RegistryUnreadableError) on an unreadable target registry BEFORE importing anything,
    and likewise on an unreadable DEFAULT registry when the target is another file — the modules
    read the default path at import, and a module whose read refused records no registration,
    which the sync must not mistake for "registers nothing"."""
    path = Path(registry_path)
    registry = read_registry(path)
    if path.resolve() != Path(DEFAULT_REGISTRY_PATH).resolve():
        read_registry(DEFAULT_REGISTRY_PATH)
    names = list(modules) if modules is not None else auto_registering_modules()
    regs = collect_registrations(names)

    per_module = {n: 0 for n in names}
    for r in regs.values():
        bare = str(r.spec.module).rsplit(".", 1)[-1]
        if bare in per_module:
            per_module[bare] += 1

    by_id = rows_by_id(registry)
    rows: List[Dict[str, Any]] = list(registry["edges"])
    index = {eid: i for i, eid in enumerate(by_id)}
    report = SyncReport(registry=str(path), n_rows_before=len(rows), n_rows_after=len(rows),
                        modules=names, registrations_per_module=per_module, check=check,
                        sha256_before=_sha(path))
    for eid in sorted(regs):
        merged, mr = merge_code_owned(by_id.get(eid), regs[eid].spec)
        if mr.never_registered:
            rows.append(merged)
            report.additions.append(eid)
        else:
            rows[index[eid]] = merged
        if mr.drift_applied:
            report.drift_applied[eid] = {f: [old, new] for f, (old, new) in mr.drift_applied.items()}
        if mr.type_changes:
            report.type_changes[eid] = {f: [a, b] for f, (a, b) in mr.type_changes.items()}
        if mr.registry_only_keys:
            report.registry_only_keys[eid] = list(mr.registry_only_keys)
    report.n_rows_after = len(rows)
    new_registry = {**registry, "edges": rows}
    serialise(new_registry)                                  # unrepresentable → raises before any write
    if not check:
        report.wrote = write_registry_if_changed(path, new_registry)
        report.sha256_after = _sha(path)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH), help="the registry to sync")
    p.add_argument("--check", action="store_true", help="write nothing; exit 1 if a sync would change the file")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    a = p.parse_args(argv)
    try:
        report = sync(a.registry, check=a.check)
    except RegistryUnreadableError as exc:
        print(f"[SYNC][REFUSED] {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({**asdict(report), "changes_file": report.changes_file}, indent=2, default=str))
    else:
        print("\n".join(report.lines()))
    if a.check and report.changes_file:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

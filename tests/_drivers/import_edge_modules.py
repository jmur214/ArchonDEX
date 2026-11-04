"""Driver for the pure-import lock (tests/test_edge_registry_single_writer.py): a FRESH interpreter,
run with its cwd on a planted `data/governor/edges.yml`, imports the auto-registering edge modules
named on argv and prints what each registered — as JSON on the last line.

Run in a subprocess so the modules import for the first time in that process (an already-imported
module runs no import-time code). The repo root is put on sys.path from this file's own location;
the cwd stays wherever the test planted the registry, which is the path the modules read.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from engines.engine_a_alpha.edge_registry import EdgeRegistry  # noqa: E402

PACKAGE = "engines.engine_a_alpha.edges"


def main(modules: list[str]) -> int:
    per_module: dict[str, list[str]] = {}
    failures: dict[str, str] = {}
    for name in modules:
        before = set(EdgeRegistry.import_registrations())
        try:
            importlib.import_module(f"{PACKAGE}.{name}")
        except Exception as exc:  # the lock asserts the import SUCCEEDS; a failure is reported, not hidden
            failures[name] = f"{type(exc).__name__}: {exc}"
            continue
        after = EdgeRegistry.import_registrations()
        per_module[name] = sorted(set(after) - before)
    regs = EdgeRegistry.import_registrations()
    print(json.dumps({
        "per_module": per_module,
        "failures": failures,
        "registered": sorted(regs),
        "unpersisted": sorted(eid for eid, r in regs.items() if not r.persisted),
        "drifted": sorted(eid for eid, r in regs.items() if r.report.changes_file and r.persisted),
    }))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Driver for the fleet-purity lock (tests/test_edge_registry_single_writer.py): a FRESH interpreter
imports every module under `paper_trader/` and `scripts.run_paper_cloud_day` (the cloud paper
fleet's entrypoint), plus any extra modules named on argv (the positive control), and prints — as
JSON on the last line — which edge-registry modules ended up in `sys.modules`.

Not a grep: the real import graph is executed. The cwd is wherever the test planted a registry,
so a stray import-time registry access would also show as changed bytes there.
"""
from __future__ import annotations

import importlib
import json
import pkgutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

WATCHED_PREFIXES = ("engines.engine_a_alpha.edges", "engines.engine_a_alpha.edge_registry")


def main(extra: list[str]) -> int:
    imported: list[str] = []
    failures: dict[str, str] = {}
    import paper_trader  # noqa: F401  (the package __init__ imports the fleet's core)
    imported.append("paper_trader")
    for m in pkgutil.iter_modules(paper_trader.__path__):
        name = f"paper_trader.{m.name}"
        try:
            importlib.import_module(name)
            imported.append(name)
        except Exception as exc:
            failures[name] = f"{type(exc).__name__}: {exc}"
    for name in ["scripts.run_paper_cloud_day", *extra]:
        try:
            importlib.import_module(name)
            imported.append(name)
        except Exception as exc:
            failures[name] = f"{type(exc).__name__}: {exc}"
    watched = sorted(m for m in sys.modules if m.startswith(WATCHED_PREFIXES))
    live_trader = (REPO / "live_trader").exists()
    print(json.dumps({"imported": imported, "failures": failures, "edge_modules_loaded": watched,
                      "live_trader_dir_exists": live_trader}))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

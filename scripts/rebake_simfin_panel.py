"""The SimFin panel RE-BAKE: the one declared entrypoint that rebuilds
data/processed/fundamentals_simfin.parquet and (with --download) refreshes data/raw/simfin.

The class of scripts/rebake_fundamentals.py: explicit, NON-canonical, refused under the canonical
switch, ARCHONDEX_MEASURED and ARCHONDEX_HERMETIC (a refresh IS the network), and it WARNs that
the substrate manifest's verify reads red until a re-pin. A READ of the panel
(`simfin_adapter.load_panel`) never rebuilds and never downloads — the 2026-10-22 incident
(the library's refresh download replaced the six pinned raw files through a worktree symlink,
then the first read in any tree rewrote the pinned panel) is written up in
engines/data_manager/fundamentals/simfin_adapter.py.

Usage:
  python -m scripts.rebake_simfin_panel               # rebuild the panel from data/raw/simfin
  python -m scripts.rebake_simfin_panel --download    # refresh the raw datasets first (needs SIMFIN_API_KEY)
"""
from __future__ import annotations

import argparse
import sys

from core.env import load_local_env
from engines.data_manager.fundamentals.simfin_adapter import (
    FundamentalsRebuildRefused,
    rebuild_panel,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Declared rebuild of the SimFin fundamentals panel.")
    ap.add_argument("--download", action="store_true",
                    help="refresh the raw datasets from SimFin first (needs SIMFIN_API_KEY)")
    args = ap.parse_args(argv)
    try:
        path = rebuild_panel(download=args.download)
    except FundamentalsRebuildRefused as exc:
        print(f"[REBAKE][REFUSED] {exc}", file=sys.stderr)
        return 2
    print(f"[REBAKE] wrote {path}")
    return 0


if __name__ == "__main__":
    load_local_env()   # the repo's own .env, explicitly, at the process entry (ruling C-1)
    sys.exit(main())

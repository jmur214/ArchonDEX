"""Run one EvolutionController cycle (Engine F).

Moved verbatim from `engines/engine_f_governance/evolution_controller.py`'s `__main__` block
(2026-10-15): a library module is not a process entry, and only process entries load the
local .env. (Distinct from scripts/run_evolution_cycle.py, which defines its own loop.)

    python -m scripts.run_evolution_controller_cycle
"""
from __future__ import annotations


def main() -> int:
    from engines.engine_f_governance.evolution_controller import EvolutionController
    EvolutionController().run_cycle()
    return 0


if __name__ == "__main__":
    from core.env import load_local_env
    load_local_env()
    raise SystemExit(main())

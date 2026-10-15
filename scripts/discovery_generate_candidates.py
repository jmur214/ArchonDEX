"""Generate Discovery candidates only (no validation) and save them.

Moved verbatim from `engines/engine_d_discovery/discovery.py`'s `__main__` block (2026-10-15):
a library module is not a process entry, and only process entries load the local .env.
There is no data_map here, so candidates are saved without validation — as before.

    python -m scripts.discovery_generate_candidates
"""
from __future__ import annotations


def main() -> int:
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    disc = DiscoveryEngine()
    cands = disc.generate_candidates(n_mutations=3)
    print(f"Generated {len(cands)} candidates.")
    disc.save_candidates(cands)
    return 0


if __name__ == "__main__":
    from core.env import load_local_env
    load_local_env()
    raise SystemExit(main())

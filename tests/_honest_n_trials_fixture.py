"""T-391 test fixture: the minimal standalone-trials record a temp pin directory needs.

The honest-N gate now REQUIRES `honest_n_trials.json` beside the pin (it fails closed without it), so
every fixture that writes a temp pin and then gates through it writes this record too. It holds one
`n_trials: 0` row — S = 0 — so the RR-3 / §9.3 / re-pin #1 locks keep their expected N unchanged.
Written by the recorder's own serializer, so it is a record the gate accepts, digest and all.
"""
from __future__ import annotations

from pathlib import Path

from scripts.honest_n_trials import write_record

FIXTURE_HEADER = {"task": "fixture", "activation_date": "2026-11-13", "grandfathered_through": "2026-11-12",
                  "rule": "fixture", "note": "test fixture — S = 0"}


def fixture_row(trial_id: str = "FIX-0", n_trials: int = 0, counted_in: str = "standalone",
                ledger_id: str | None = None) -> dict:
    return {"trial_id": trial_id, "task_id": trial_id, "date": "2026-11-13", "n_trials": n_trials,
            "counted_in": counted_in, "ledger_id": ledger_id, "family": "fixture", "substrate": "fixture",
            "prereg": "—", "verdict": "—", "source": "fixture", "note": ""}


def write_fixture_trials_record(directory: Path, rows: list | None = None) -> Path:
    path = Path(directory) / "honest_n_trials.json"
    write_record(path, FIXTURE_HEADER, rows if rows is not None else [fixture_row()], [])
    return path

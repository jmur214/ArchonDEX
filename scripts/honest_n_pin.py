"""Pin or verify the honest-N gate's two inputs — the ρ̄ artifact and the run registry (RR-3 §9.3).

    python -m scripts.honest_n_pin --verify
    python -m scripts.honest_n_pin --pin n_effective_<date>.json --note "why"              # first pin only
    python -m scripts.honest_n_pin --pin n_effective_<date>.json --note "why" --replace    # change an existing pin

The WRITER lives here, not in `core/measurement/mbl_gate.py`: the referee module only reads and
verifies (R's note on the 9.3 review). Writing a pin never changes the gate by itself — it takes
effect only when `config/honest_n_pin.json` is COMMITTED, and that commit is the review.

An existing pin is never overwritten silently. Replacing one changes what Gate 0/8 compute N from,
so it requires `--replace` — an explicit, visible act — and refuses without it.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import core.measurement.mbl_gate as mbl


class PinExistsError(FileExistsError):
    """A pin already exists and `replace` was not requested."""


def write_pin(artifact_name: str, *, artifact_dir: Optional[Path] = None, db_path: Optional[Path] = None,
              pin_path: Optional[Path] = None, note: str = "", replace: bool = False) -> Dict:
    """Pin the gate to `artifact_dir/artifact_name` AND the current run registry, recording each file's
    sha256. Refuses to pin anything the gate could not read, and refuses to overwrite an existing pin
    unless `replace=True`. Defaults are resolved from `mbl_gate` at call time."""
    artifact_dir = Path(artifact_dir) if artifact_dir is not None else mbl.DEFAULT_ARTIFACT_DIR
    db_path = Path(db_path) if db_path is not None else mbl.DEFAULT_DB_PATH
    pin_path = Path(pin_path) if pin_path is not None else mbl.DEFAULT_PIN_PATH
    if pin_path.exists() and not replace:
        current = pin_path.read_text()
        raise PinExistsError(
            f"refusing to overwrite the existing pin {pin_path} — replacing it changes what the honest-N "
            f"gate computes N from. Pass replace=True / --replace to do it deliberately.\n"
            f"current pin: {current.strip()[:300]}")
    art = artifact_dir / artifact_name
    mbl.load_n_effective_artifact(path=art)                    # refuse what the gate couldn't read
    rows = mbl.compute_n_effective(db_path)                    # (also refuses an empty registry)
    pin = {"schema": "honest_n_pin/v1",
           "artifact": {"file": artifact_name, "sha256": mbl.sha256_file(art)},
           "registry": {"file": db_path.name, "sha256": mbl.sha256_file(db_path), "rows_at_pin": rows},
           "pinned_on": _dt.date.today().isoformat(), "note": note}
    pin_path.write_text(json.dumps(pin, indent=2) + "\n")
    return pin


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pin", metavar="ARTIFACT_FILENAME", help="pin the gate to this artifact + the current registry")
    g.add_argument("--verify", action="store_true", help="verify the committed pin against both files")
    ap.add_argument("--replace", action="store_true", help="allow overwriting an existing pin (deliberate)")
    ap.add_argument("--note", default="", help="why these inputs (recorded in the pin)")
    a = ap.parse_args(argv)
    if a.pin:
        try:
            pin = write_pin(a.pin, note=a.note, replace=a.replace)
        except PinExistsError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 4
        print(f"pinned artifact {pin['artifact']['file']} + registry {pin['registry']['file']} "
              f"({pin['registry']['rows_at_pin']} rows) -> {mbl.DEFAULT_PIN_PATH} (commit it to take effect)")
        return 0
    try:
        art = mbl.pinned_n_effective_artifact()
        reg = mbl.verify_pinned_registry()
    except mbl.HonestNUnavailableError as exc:
        print(f"PIN INVALID: {exc}")
        return 3
    print(f"PIN OK: {art.name} and {reg.name} both match their pinned sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

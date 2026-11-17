"""Pin or verify the pairs edge's input — the cointegration screen's survivor manifest (T-389, cutover P6).

    python -m scripts.pairs_manifest_pin --verify
    python -m scripts.pairs_manifest_pin --pin data/research/cointegrated_pairs_<date>.json --note "why"             # first pin only
    python -m scripts.pairs_manifest_pin --pin data/research/cointegrated_pairs_<date>.json --note "why" --replace   # change an existing pin

WHY THIS EXISTS. `engines/engine_a_alpha/edges/pairs_trading_v1.py` registers its pair edges at
import FROM this file (`MANIFEST_PATH`). When the file is absent the module registers nothing and
logs a warning — and the image's registry check (`scripts/sync_edge_registry.py --check`) then has
nothing to compare the anchor's pairs rows against: it exits 0 on a correct row, a drifted `beta`, a
drifted `z_entry` and an absent row alike (T-389 evidence, 2026-11-12). The file is gitignored and
was in neither the substrate manifest nor the image. This pin is the honest-N discipline
(`scripts/honest_n_pin.py`) applied to it: the file is pinned BY NAME + sha256 in the committed
pointer `config/pairs_manifest_pin.json`, carried by name in the substrate manifest's
SUBSTRATE_FILES, COPYd by name into the backtest image, and `--verify` runs at image build BEFORE
the registry check — exit 3 fails the build, so the image cannot carry a pairs input its pin
disagrees with, and the registry check then verifies the anchor's pairs rows against real input.

A pin takes effect only when `config/pairs_manifest_pin.json` is COMMITTED; that commit is the review.
An existing pin is never overwritten silently: `--pin` refuses (exit 4) unless `--replace` is given.
No network, no `.env`, no engine import: the verify reads two files and hashes one.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIN_PATH = ROOT / "config" / "pairs_manifest_pin.json"
SCHEMA = "pairs_manifest_pin/v1"


class PairsPinInvalid(RuntimeError):
    """The pin, or the file it names, cannot be verified. Never degraded to a pass."""


class PinExistsError(FileExistsError):
    """A pin already exists and `replace` was not requested."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def survivor_edge_ids(payload: Dict[str, Any], *, source: str) -> List[str]:
    """The edge ids the pairs module registers from `payload`, as the screen recorded them.

    The screen writes BOTH a per-candidate `survives` flag (what the edge module reads) and a
    `survivor_pair_ids` list; they must agree — a payload where they disagree is refused, never
    reconciled. Refuses an empty survivor set: a pin on a file that registers nothing would let the
    image's registry check pass vacuously on any pairs row, which is the defect this pin closes."""
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise PairsPinInvalid(f"{source}: no `candidates` list — not a cointegration screen manifest")
    survivors = [c for c in candidates if isinstance(c, dict) and c.get("survives")]
    bad = [c for c in survivors if not (c.get("ticker_x") and c.get("ticker_y") and "beta" in c)]
    if bad:
        raise PairsPinInvalid(f"{source}: surviving candidate(s) lack ticker_x/ticker_y/beta: {str(bad)[:200]}")
    # the id the edge module builds (`pairs_trading_v1._build_pair_spec`; equality locked in the tests)
    from_flags = sorted(f"pairs_trading_{c['ticker_x']}_{c['ticker_y']}_v1" for c in survivors)
    recorded = payload.get("survivor_pair_ids")
    if not isinstance(recorded, list) or sorted(recorded) != from_flags:
        raise PairsPinInvalid(
            f"{source}: `survivor_pair_ids` {recorded!r} disagrees with the candidates' `survives` "
            f"flags {from_flags} — the file is inconsistent; re-run the screen")
    if not from_flags:
        raise PairsPinInvalid(
            f"{source}: zero surviving pairs — the pairs module would register nothing from it, and "
            f"the image's registry check would pass vacuously on any pairs row in the anchor")
    return from_flags


def _read_payload(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PairsPinInvalid(f"{path} cannot be read as JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PairsPinInvalid(f"{path}: root is {type(payload).__name__}, not an object")
    return payload


def load_pin(pin_path: Optional[Path] = None) -> Dict[str, Any]:
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    if not pin_path.is_file():
        raise PairsPinInvalid(f"no pin at {pin_path} — the pairs input is unpinned")
    try:
        pin = json.loads(pin_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PairsPinInvalid(f"the pin {pin_path} cannot be read: {exc}") from exc
    if not isinstance(pin, dict) or pin.get("schema") != SCHEMA:
        raise PairsPinInvalid(f"the pin {pin_path} is not a {SCHEMA} pin: {str(pin)[:200]}")
    for key, kind in (("file", str), ("sha256", str), ("survivor_edge_ids", list)):
        if not isinstance(pin.get(key), kind) or not pin[key]:
            raise PairsPinInvalid(f"the pin {pin_path} lacks a non-empty `{key}`")
    if Path(pin["file"]).is_absolute() or ".." in Path(pin["file"]).parts:
        raise PairsPinInvalid(f"the pin's file {pin['file']!r} must be repo-relative")
    return pin


def verify(*, root: Optional[Path] = None, pin_path: Optional[Path] = None) -> Dict[str, Any]:
    """Verify the committed pin against `root/<pin.file>`: present, sha256-equal, and its survivor
    edge ids equal the pin's. Returns the pin; raises PairsPinInvalid naming what disagrees.
    Defaults (ROOT, DEFAULT_PIN_PATH) are resolved at call time."""
    root = Path(root) if root is not None else ROOT
    pin = load_pin(pin_path)
    path = root / pin["file"]
    if not path.is_file():
        raise PairsPinInvalid(
            f"the pinned pairs input {pin['file']} is ABSENT under {root} — the pairs edge would "
            f"register nothing and the registry check could not verify its rows")
    got = sha256_file(path)
    if got != pin["sha256"]:
        raise PairsPinInvalid(f"{pin['file']} sha256 {got} != pinned {pin['sha256']}")
    ids = survivor_edge_ids(_read_payload(path), source=pin["file"])
    if ids != sorted(pin["survivor_edge_ids"]):
        raise PairsPinInvalid(f"{pin['file']} survivors {ids} != pinned {pin['survivor_edge_ids']}")
    return pin


def write_pin(rel_file: str, *, root: Optional[Path] = None, pin_path: Optional[Path] = None, note: str = "",
              replace: bool = False) -> Dict[str, Any]:
    """Pin `root/<rel_file>`: its sha256 and the survivor edge ids it registers. Refuses what the
    verify would refuse, and refuses to overwrite an existing pin unless `replace=True`."""
    root = Path(root) if root is not None else ROOT
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    if pin_path.exists() and not replace:
        raise PinExistsError(
            f"refusing to overwrite the existing pin {pin_path} — replacing it changes the input the "
            f"pairs edge registers from. Pass replace=True / --replace to do it deliberately.\n"
            f"current pin: {pin_path.read_text().strip()[:300]}")
    rel = Path(rel_file)
    if rel.is_absolute() or ".." in rel.parts:
        raise PairsPinInvalid(f"pin a repo-relative path, not {rel_file!r}")
    path = root / rel
    if not path.is_file():
        raise PairsPinInvalid(f"{rel_file} is absent under {root}")
    ids = survivor_edge_ids(_read_payload(path), source=rel_file)
    pin = {"schema": SCHEMA, "file": rel.as_posix(), "sha256": sha256_file(path),
           "survivor_edge_ids": ids, "pinned_on": _dt.date.today().isoformat(), "note": note}
    pin_path.write_text(json.dumps(pin, indent=2) + "\n")
    return pin


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pin", metavar="REPO_RELATIVE_FILE", help="pin this screen manifest (sha256 + survivors)")
    g.add_argument("--verify", action="store_true", help="verify the committed pin against the file it names")
    ap.add_argument("--replace", action="store_true", help="allow overwriting an existing pin (deliberate)")
    ap.add_argument("--note", default="", help="why this input (recorded in the pin)")
    a = ap.parse_args(argv)
    if a.pin:
        try:
            pin = write_pin(a.pin, note=a.note, replace=a.replace)
        except PinExistsError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 4
        except PairsPinInvalid as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 3
        print(f"pinned {pin['file']} (sha256 {pin['sha256'][:12]}…; survivors {pin['survivor_edge_ids']}) "
              f"-> {DEFAULT_PIN_PATH} (commit it to take effect)")
        return 0
    try:
        pin = verify()
    except PairsPinInvalid as exc:
        print(f"PIN INVALID: {exc}")
        return 3
    print(f"PIN OK: {pin['file']} matches its pinned sha256 (survivors {pin['survivor_edge_ids']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""core/measurement/mbl_gate.py
==============================
T-083: MBL Gate-0 — Minimum Backtest Length check.
RR-3 (2026-09-30, PROPOSAL): fail-closed honest-N, exact E[max], correlation-aware N_eff.

Per CLAUDE.md non-negotiable `[NN-MBL]` and Bailey-Borwein-López de Prado-Zhu (Notices
AMS 2014), the Minimum Backtest Length is

    MinBTL = E[max_N]^2 / SR_target^2

where E[max_N] is the expected maximum of N independent standard normals. The familiar
`2 * ln(N) / SR^2` is the UPPER BOUND that paper quotes for intuition (E[max_N] <=
sqrt(2 ln N)); used as the gate itself it overstates required years by ~39% at N=260
(`scripts/probe_mbl_n_effective.py`). The exact form is the default; the bound stays
behind `upper_bound=True` for comparison only.

THE THREE DEFECTS RR-3 REPAIRS (each verified on main before changing it):
  1. FAIL-OPEN N. `compute_n_effective` returned 1 when the registry was absent, and 1
     gives MinBTL = 0, so Gate 0 PASSED. The registry is `.dockerignore`d and never
     pulled from S3, so this was not a latent risk: every cloud Discovery cell ran Gate 0
     at N=1. An EMPTY registry did the same via `max(1, 0)`. Both now raise
     `HonestNUnavailableError`. **A trial count that cannot be established is never a
     licence to proceed at N=1.**
  2. THE UPPER BOUND USED AS THE GATE. Now exact E[max]^2 (Euler-γ approximation, the
     same constant `MetricsEngine.deflated_sharpe_ratio` uses — one definition).
  3. EVERY RUN COUNTED AS AN INDEPENDENT TRIAL. `compute_n_effective_correlated` adjusts
     the count for the measured correlation between trials, read from the empirical
     artifact `data/observability/n_effective_<date>.json` (`scripts/rr3_empirical_rho.py`).
     It fails closed if the artifact is missing — the adjustment is never assumed.

A correlation estimate is NEVER allowed to collapse the multiple-testing correction to
none: N_eff is floored at `N_EFF_FLOOR` (2). With N_eff = 1 the gate is vacuous (MinBTL
= 0) — the same door defect 1 left open, reached by a different route.

T-391 (PROPOSAL, docs/Sources/proposal_honest_n_trials_recorder_t391_2026-11-13.md): THE
REGISTRY CANNOT SEE A STANDALONE-HARNESS TRIAL. It ingests only controller run directories, so
every trial a research script runs (the frontier program requires them) was missing from N.
The committed record `config/honest_n_trials.json` (written by ONE recorder,
`scripts/honest_n_trials.py`) carries them; the gate ADDS them at raw (rule R2: no correlation
credit is borrowed from a population that excludes them — ruling 9.2), cross-checks the
record's registry-ledger rows against the registry (no double count, no omission), and FAILS
CLOSED on an absent, empty, edited or inconsistent record.

Public API
----------
- `compute_n_effective(db_path)`                  raw registry count; FAILS CLOSED
- `compute_n_effective_correlated(db_path, ...)`  correlation-aware N_eff + standalone trials; FAILS CLOSED
- `honest_n_breakdown(...)`                       the same, itemised (registry part, S, R2 gated, R3 reported)
- `load_trials_record(path)`                      the standalone-trials record, validated; FAILS CLOSED
- `expected_max_normal(n)`                        E[max of n iid N(0,1)] (Euler-γ)
- `n_eff_equicorrelated(n, rho_bar)`              the equicorrelated-trials identity
- `compute_mbl_min(n_effective, sr_target)`       exact MinBTL (or the bound, on request)
- `check_mbl_gate(t_years, n_effective=None, ...)` the full Gate-0 check
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from scipy import stats as _stats

from core.metrics_engine import _EULER_GAMMA

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data/observability/run_registry.sqlite"
DEFAULT_ARTIFACT_DIR = DEFAULT_DB_PATH.parent
# RR-3 §9.3 (2026-10-13): BOTH honest-N inputs — the ρ̄ artifact and the run registry — are
# PINNED by one committed pointer carrying each file's sha256.
DEFAULT_PIN_PATH = Path(__file__).resolve().parents[2] / "config/honest_n_pin.json"

# A correlation estimate may shrink N, never erase the correction (see module docstring).
N_EFF_FLOOR = 2.0

METHODS = ("conservative", "onc", "equicorr")

# T-391: the standalone-trials record lives BESIDE the pin (config/), is committed, and is read
# by name — the same no-path rule the pin applies to its two data inputs.
TRIALS_FILE_NAME = "honest_n_trials.json"
TRIALS_SCHEMA = "honest_n_trials/v1"
COUNTED_IN = ("registry_ledger", "standalone")
_TRIAL_STR_FIELDS = ("trial_id", "task_id", "date", "counted_in", "family", "substrate",
                     "prereg", "verdict", "source")
_UNRESOLVED_STR_FIELDS = ("item_id", "task_id", "stated", "why", "source")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class HonestNUnavailableError(FileNotFoundError):
    """The honest trial count cannot be established (registry or ρ̄ artifact absent,
    empty, or unreadable). A HARNESS failure, never a candidate failure: callers must
    let it propagate rather than convert it into a per-candidate verdict, or a missing
    registry reads as "nothing passed" — a plausible, wrong number (`[NN-FAIL-CLOSED]`)."""


# ----------------------------------------------------------------------------- math
def expected_max_normal(n: float) -> float:
    """E[max of n iid standard normals], Bailey-López de Prado (2014) approximation:

        E[max_n] ≈ (1 - γ)·Φ⁻¹(1 - 1/n) + γ·Φ⁻¹(1 - 1/(n·e))

    The identical expression `MetricsEngine.deflated_sharpe_ratio` inlines, with the same
    γ, so Gate 0 and Gate 8 cannot drift apart. Within ~1.3% of exact numerical
    integration at n=260 (the probe reports both). n <= 1 → 0.0 (no selection)."""
    if n <= 1:
        return 0.0
    a = float(_stats.norm.ppf(1.0 - 1.0 / n))
    b = float(_stats.norm.ppf(1.0 - 1.0 / (n * math.e)))
    return (1.0 - _EULER_GAMMA) * a + _EULER_GAMMA * b


def n_eff_equicorrelated(n: float, rho_bar: float) -> float:
    """The equicorrelated-trials identity. If N trials have pairwise correlation ρ̄,

        X_i = sqrt(ρ̄)·Z₀ + sqrt(1-ρ̄)·Z_i   ⇒   E[max_i X_i] = sqrt(1-ρ̄)·E[max_N]

    so the selection benchmark shrinks by sqrt(1-ρ̄). Returns the N_eff of INDEPENDENT
    trials with that same expected maximum (solved by bisection), floored at N_EFF_FLOOR.
    ρ̄ <= 0 returns n unchanged: negative average correlation does not license more
    trials than were run."""
    if n <= N_EFF_FLOOR:
        return float(max(n, 1.0))
    if not (rho_bar == rho_bar) or rho_bar <= 0.0:
        return float(n)
    if rho_bar >= 1.0:
        return N_EFF_FLOOR
    target = math.sqrt(1.0 - rho_bar) * expected_max_normal(n)
    lo, hi = N_EFF_FLOOR, float(n)
    if expected_max_normal(lo) >= target:
        return N_EFF_FLOOR
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if expected_max_normal(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def compute_mbl_min(n_effective: float, sr_target: float = 1.0, *, upper_bound: bool = False) -> float:
    """Minimum Backtest Length in years.

    Exact (default):  E[max_N]^2 / SR_target^2
    Upper bound:      2·ln(N) / SR_target^2   (`upper_bound=True`; comparison only)

    At N=1 there is no selection, so MinBTL = 0 in both forms. That is correct maths and
    the reason N must never DEFAULT to 1 — see `compute_n_effective`.

    Raises ValueError if n_effective < 1 or sr_target <= 0."""
    if n_effective < 1:
        raise ValueError(f"n_effective must be >= 1, got {n_effective}")
    if sr_target <= 0:
        raise ValueError(f"sr_target must be > 0, got {sr_target}")
    if n_effective == 1:
        return 0.0
    if upper_bound:
        return 2.0 * math.log(n_effective) / (sr_target ** 2)
    return expected_max_normal(n_effective) ** 2 / (sr_target ** 2)


# ----------------------------------------------------------------------------- N sources
def compute_n_effective(
    db_path: Optional[Path] = None,
    since_iso: Optional[str] = None,
) -> int:
    """Raw honest-N: the run registry's row count. FAILS CLOSED.

    Raises `HonestNUnavailableError` when the registry is absent OR holds zero rows.
    Both used to return 1, and N=1 makes Gate 0 vacuous; since the registry is excluded
    from the Docker image, "absent" was the normal state of every cloud container.

    This is a RAW count — every row one trial, including determinism reps and near-
    identical A/B arms. Prefer `compute_n_effective_correlated` for gating."""
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    if not db_path.exists():
        raise HonestNUnavailableError(
            f"run registry absent at {db_path} — honest N cannot be established. "
            f"Pass an explicit trial count or supply the registry; never proceed at N=1.")
    import sqlite3
    # Read-only (RR-3 §9.3): the registry's bytes are pinned, so the gate must never be
    # able to change them — not even a journal side effect of a read-write connection.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        try:
            if since_iso:
                cur = conn.execute("SELECT COUNT(*) FROM runs WHERE snapshot_at >= ?", (since_iso,))
            else:
                cur = conn.execute("SELECT COUNT(*) FROM runs")
        except sqlite3.DatabaseError as exc:          # e.g. a 0-byte file or no `runs` table
            raise HonestNUnavailableError(f"run registry at {db_path} unreadable: {exc}") from exc
        n = int(cur.fetchone()[0])
    finally:
        conn.close()
    if n < 1:
        raise HonestNUnavailableError(
            f"run registry at {db_path} holds 0 rows — an empty registry is not evidence of "
            f"zero prior trials.")
    return n


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pin(pin_path: Optional[Path] = None) -> Dict:
    """Read and validate the committed honest-N pin. FAILS CLOSED on absence or malformation."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    try:
        pin = json.loads(pin_path.read_text())
        # T-391: "trials" is OPTIONAL until re-pin #2 writes it (honest_n_pin/v2); once present it is
        # validated exactly like the two data inputs and the gate verifies the record against it.
        for key in ("artifact", "registry") + (("trials",) if "trials" in pin else ()):
            entry = pin[key]
            if not (isinstance(entry, dict) and isinstance(entry["file"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", str(entry["sha256"]).lower())):
                raise ValueError(f"{key!r} needs a file name and a 64-hex sha256")
            if "/" in entry["file"] or "\\" in entry["file"]:
                raise HonestNUnavailableError(
                    f"honest-N pin {pin_path} names a path for {key!r}, not a file name: {entry['file']!r}")
    except HonestNUnavailableError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HonestNUnavailableError(
            f"honest-N pin {pin_path} absent or malformed ({exc}) — the gate will not guess which "
            f"inputs to trust") from exc
    return pin


def _verify_pinned(path: Path, entry: Dict, what: str, pin_path: Path) -> Path:
    if path.name != entry["file"]:
        raise HonestNUnavailableError(
            f"the gate was given {what} {path.name!r} but the pin names {entry['file']!r} ({pin_path})")
    if not path.exists():
        raise HonestNUnavailableError(f"pinned {what} {path} is absent (pin: {pin_path}). Ship it, or re-pin by commit.")
    got, want = sha256_file(path), str(entry["sha256"]).lower()
    if got != want:
        raise HonestNUnavailableError(
            f"pinned {what} {path} does not match its pin: sha256 {got[:12]}… ≠ pinned {want[:12]}…. "
            f"It changed after it was pinned; re-pin by commit, after review.")
    return path


def pinned_n_effective_artifact(
    pin_path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
) -> Path:
    """The ρ̄ artifact the gate is PINNED to, hash-verified. FAILS CLOSED.

    RR-3 §9.3. This replaced `latest_n_effective_artifact()`, which took the NEWEST
    `n_effective_*.json` by filename — so any re-run of `scripts/rr3_empirical_rho.py`, by anyone,
    silently replaced the live gate's input with no review. The 2026-10-13 Option B pass avoided
    that only by choosing a different output name; a filename convention is not a control."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    artifact_dir = Path(artifact_dir) if artifact_dir is not None else DEFAULT_ARTIFACT_DIR
    entry = load_pin(pin_path)["artifact"]
    return _verify_pinned(artifact_dir / entry["file"], entry, "n_effective artifact", pin_path)


def verify_pinned_registry(db_path: Optional[Path] = None, pin_path: Optional[Path] = None) -> Path:
    """The run registry the gate is PINNED to, hash-verified. FAILS CLOSED.

    R's addition to §9.3: pinning the registry as well closes T-356b's rebuild-after-loss case.
    `rebuild()` upserts from whatever sits in local `data/trade_logs/` on the day, and the 125 run
    rows' directories exist nowhere, so a registry rebuilt after loss would hand the gate a SMALLER
    N without complaint. With the registry pinned, any rebuild, backfill or recreation changes its
    bytes and the gate refuses until someone re-pins by a reviewed commit."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    return _verify_pinned(db_path, load_pin(pin_path)["registry"], "run registry", pin_path)


def load_n_effective_artifact(
    path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
) -> Dict:
    """Load and validate a ρ̄ artifact. With no explicit `path` — every production call — it is
    the PINNED artifact, hash-verified. An explicit `path` is a deliberate choice by the caller
    (tools, tests), the way an explicit `n_trials_for_dsr` is."""
    p = Path(path) if path else pinned_n_effective_artifact(pin_path, artifact_dir)
    try:
        art = json.loads(p.read_text())
    except (OSError, ValueError) as exc:
        raise HonestNUnavailableError(f"n_effective artifact {p} unreadable: {exc}") from exc
    gi = art.get("gate_inputs")
    if not isinstance(gi, dict):
        raise HonestNUnavailableError(f"n_effective artifact {p} lacks a `gate_inputs` block")
    for key in ("rho_bar", "onc_compression"):
        v = gi.get(key)
        if not isinstance(v, (int, float)) or v != v:
            raise HonestNUnavailableError(f"n_effective artifact {p} gate_inputs lacks a numeric {key!r}")
    return art


# ----------------------------------------------------------------------------- standalone trials (T-391)
def default_trials_path(pin_path: Optional[Path] = None) -> Path:
    """The standalone-trials record sits BESIDE the pin (config/), so a caller that passes its own
    pin (Discovery passes `<root>/config/honest_n_pin.json`) reads its own tree's record."""
    return (Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH).parent / TRIALS_FILE_NAME


def trials_digest(rows: List[Dict[str, Any]], unresolved: List[Dict[str, Any]],
                  activation_date: Any = None) -> str:
    """sha256 of the canonical JSON of both blocks AND the activation date (review F4: the date
    decides which ledger rows the forward lint binds, so moving it to 2099 must not verify). The
    recorder writes it; the gate re-derives it, so a hand edit that bypasses the recorder (or a
    truncated file) is refused, not read."""
    payload = json.dumps({"activation_date": activation_date, "rows": rows, "unresolved": unresolved},
                         sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _refuse(path: Path, why: str) -> HonestNUnavailableError:
    return HonestNUnavailableError(
        f"standalone-trials record {path}: {why} — honest N cannot be established without it; the "
        f"gate never proceeds on the registry alone (T-391).")


def _validate_trial_row(row: Any, i: int, path: Path) -> None:
    if not isinstance(row, dict):
        raise _refuse(path, f"row {i} is not an object")
    tid = row.get("trial_id")
    for key in _TRIAL_STR_FIELDS:
        v = row.get(key)
        if not isinstance(v, str) or not v.strip():
            raise _refuse(path, f"row {i} ({tid!r}) lacks a non-empty {key!r}")
    n = row.get("n_trials")
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise _refuse(path, f"row {i} ({tid!r}) n_trials must be an int >= 0, got {n!r}")
    if row["counted_in"] not in COUNTED_IN:
        raise _refuse(path, f"row {i} ({tid!r}) counted_in {row['counted_in']!r} not in {COUNTED_IN}")
    if not _ISO_DATE.fullmatch(row["date"]):
        raise _refuse(path, f"row {i} ({tid!r}) date {row['date']!r} is not YYYY-MM-DD")
    lid = row.get("ledger_id")
    if lid is not None and (not isinstance(lid, str) or not lid.strip()):
        raise _refuse(path, f"row {i} ({tid!r}) ledger_id must be a non-empty string or null")
    if row["counted_in"] == "registry_ledger" and lid is None:
        raise _refuse(path, f"row {i} ({tid!r}) is counted in the registry but names no ledger_id")
    if not isinstance(row.get("pending_ruling", False), bool):
        raise _refuse(path, f"row {i} ({tid!r}) pending_ruling must be true or false")
    twin = row.get("also_in_registry_as")
    if twin is not None and (not isinstance(twin, str) or not twin.strip()):
        raise _refuse(path, f"row {i} ({tid!r}) also_in_registry_as must name a registry trial_id or be null")


def load_trials_record(path: Optional[Path] = None) -> Dict[str, Any]:
    """The committed standalone-trials record, validated. FAILS CLOSED on absence, unreadability,
    a wrong schema, an EMPTY row list (an empty record is not evidence of zero trials — the
    registry's own rule), a digest mismatch, a malformed row, or a duplicate trial_id."""
    p = Path(path) if path is not None else default_trials_path()
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError) as exc:
        raise _refuse(p, f"absent or unreadable ({exc})") from exc
    if not isinstance(rec, dict) or rec.get("schema") != TRIALS_SCHEMA:
        raise _refuse(p, f"schema is not {TRIALS_SCHEMA!r}")
    rows, unresolved = rec.get("rows"), rec.get("unresolved")
    if not isinstance(rows, list) or not rows:
        raise _refuse(p, "holds no rows — an empty record is not evidence of zero standalone trials")
    if not isinstance(unresolved, list):
        raise _refuse(p, "`unresolved` must be a list (empty when nothing is pending a ruling)")
    if rec.get("rows_sha256") != trials_digest(rows, unresolved, rec.get("activation_date")):
        raise _refuse(p, "rows_sha256 does not match its rows — edited outside the recorder "
                         "(`python -m scripts.honest_n_trials record`)")
    if not (isinstance(rec.get("activation_date"), str) and _ISO_DATE.fullmatch(rec["activation_date"])):
        raise _refuse(p, "activation_date must be YYYY-MM-DD")
    seen: set = set()
    for i, row in enumerate(rows):
        _validate_trial_row(row, i, p)
        if row["trial_id"] in seen:
            raise _refuse(p, f"duplicate trial_id {row['trial_id']!r} — one trial, one row")
        seen.add(row["trial_id"])
    # Review F5c — the double-count lock's second half: a task the registry already counts may not
    # ALSO appear as a standalone row (T-137 re-added at raw would be counted twice), unless the row
    # names the registry trial it is a DIFFERENT trial from (T-260: 2026-07-02 vs 2026-07-27).
    # Review round 2 F5: the named twin must be an EXISTING registry row of the SAME task with a
    # DIFFERENT date — naming any registry id (T-137 naming itself, or T-135) is not a distinction.
    reg_rows = [r for r in rows if r["counted_in"] == "registry_ledger"]
    by_task = {r["task_id"]: r["trial_id"] for r in reg_rows}
    by_lid = {r["ledger_id"]: r["trial_id"] for r in reg_rows}
    reg_by_id = {r["trial_id"]: r for r in reg_rows}
    for row in rows:
        twin_id = row.get("also_in_registry_as")
        if row["counted_in"] != "standalone":
            if twin_id is not None:
                raise _refuse(p, f"registry row {row['trial_id']!r} may not carry also_in_registry_as")
            continue
        clash = by_task.get(row["task_id"]) or by_lid.get(row.get("ledger_id"))
        if twin_id is not None:
            twin = reg_by_id.get(twin_id)
            if (twin is None or twin["task_id"] != row["task_id"] or twin["date"] == row["date"]
                    or twin["trial_id"] == row["trial_id"]):
                raise _refuse(p, f"standalone row {row['trial_id']!r} names also_in_registry_as {twin_id!r}, "
                                 f"which is not a different-dated registry row of task {row['task_id']!r}")
        elif clash:
            raise _refuse(p, f"standalone row {row['trial_id']!r} names a task the registry already counts "
                             f"({clash!r}) — it would be double-counted")
    for i, item in enumerate(unresolved):
        if not isinstance(item, dict) or any(
                not isinstance(item.get(k), str) or not item[k].strip() for k in _UNRESOLVED_STR_FIELDS):
            raise _refuse(p, f"unresolved item {i} lacks one of {_UNRESOLVED_STR_FIELDS}")
    return rec


def verify_trials_citations(record: Dict[str, Any], root: Path) -> None:
    """Review F5a: every citation must EXIST — `source` (path[:line[-line]], the line within the
    file) and `prereg` / `verdict` (unless '—'). FAILS CLOSED. Callers run it wherever the cited
    tree exists; the backtest image carries no docs/ (.dockerignore), so there the gate reports
    `citations_checked: False` instead of refusing every cloud run for a file it never ships."""
    root = Path(root)

    def _exists(rel: str, what: str, tid: str) -> Path:
        q = root / rel
        if rel.startswith("/") or ".." in Path(rel).parts or not q.is_file():
            raise HonestNUnavailableError(
                f"standalone-trials record: {tid!r} cites {what} {rel!r}, which does not exist under {root}")
        return q

    for item in list(record["rows"]) + list(record["unresolved"]):
        tid = item.get("trial_id") or item.get("item_id")
        m = re.fullmatch(r"(?P<path>[^:]+)(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?", item["source"])
        if not m:
            raise HonestNUnavailableError(
                f"standalone-trials record: {tid!r} source {item['source']!r} is not path[:line]")
        q = _exists(m["path"], "source", tid)
        if m["a"]:
            n_lines = len(q.read_text(errors="replace").splitlines())
            if not (1 <= int(m["a"]) <= int(m["b"] or m["a"]) <= n_lines):
                raise HonestNUnavailableError(
                    f"standalone-trials record: {tid!r} cites {item['source']!r}, past the end of the "
                    f"file ({n_lines} lines)")
        for key in ("prereg", "verdict"):
            if key in item and item[key] != "—":
                _exists(item[key], key, tid)


def registry_ledger_counts(db_path: Optional[Path] = None) -> Dict[str, int]:
    """{ledger id: rows} for the registry's `ledger:<id>` rows (T-336's backfill). Read-only.
    A registry with no `source` column has none."""
    import sqlite3
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    if not db_path.exists():
        raise HonestNUnavailableError(f"run registry absent at {db_path} — cannot reconcile the trials record")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(runs)")}
            if "source" not in cols:
                return {}
            got = conn.execute("SELECT source, COUNT(*) FROM runs WHERE source LIKE 'ledger:%' "
                               "GROUP BY source").fetchall()
        except sqlite3.DatabaseError as exc:
            raise HonestNUnavailableError(f"run registry at {db_path} unreadable: {exc}") from exc
    finally:
        conn.close()
    return {str(src)[len("ledger:"):]: int(n) for src, n in got}


def reconcile_trials_with_registry(record: Dict[str, Any], db_path: Optional[Path] = None) -> None:
    """THE DOUBLE-COUNT LOCK. The record's `registry_ledger` rows must equal the registry's
    `ledger:<id>` rows, id by id and count by count, in BOTH directions: a standalone row that is
    really a registry row would be counted twice; a registry row the record lacks means the record
    was built against a different registry. Either way the gate refuses."""
    want = registry_ledger_counts(db_path)
    have: Dict[str, int] = {}
    for row in record["rows"]:
        if row["counted_in"] == "registry_ledger":
            have[row["ledger_id"]] = have.get(row["ledger_id"], 0) + int(row["n_trials"])
    if have != want:
        diffs = [f"{k}: record {have.get(k, 0)} vs registry {want.get(k, 0)}"
                 for k in sorted(set(have) | set(want)) if have.get(k, 0) != want.get(k, 0)]
        raise HonestNUnavailableError(
            "standalone-trials record and run registry disagree on the registry's ledger rows ("
            + "; ".join(diffs) + ") — a trial would be double-counted or omitted. Rebuild the record "
            "against the pinned registry; never edit either by hand.")


def standalone_trials_total(record: Dict[str, Any]) -> int:
    """S: the trials the registry cannot see (rows counted_in == 'standalone')."""
    return int(sum(int(r["n_trials"]) for r in record["rows"] if r["counted_in"] == "standalone"))


def verify_pinned_trials(trials_path: Optional[Path] = None, pin_path: Optional[Path] = None) -> bool:
    """When the pin names the record (re-pin #2 onward), verify its sha256 and return True.
    Before then the record is integrity-checked by git (committed) and its own digest: False."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    entry = load_pin(pin_path).get("trials")
    if entry is None:
        return False
    tp = Path(trials_path) if trials_path is not None else default_trials_path(pin_path)
    _verify_pinned(tp, entry, "standalone-trials record", pin_path)
    return True


def _registry_n_eff(n_raw: float, gi: Dict[str, Any], method: str) -> float:
    eq = n_eff_equicorrelated(n_raw, float(gi["rho_bar"]))
    onc = max(N_EFF_FLOOR, min(float(n_raw), n_raw * float(gi["onc_compression"])))
    if method == "equicorr":
        return eq
    if method == "onc":
        return onc
    return max(eq, onc)


def honest_n_breakdown(
    db_path: Optional[Path] = None,
    method: str = "conservative",
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
    trials_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """The production honest N, itemised. FAILS CLOSED on every input (registry, artifact and
    — once pinned — the trials record are pin-verified; the record is digest-checked and
    reconciled with the registry).

    Three DISJOINT populations (the pinned artifact says of the registry: it "registers none of
    these runs — the two sets are disjoint"; S excludes both by construction):
      registry   231 rows — 125 pre-2026-05-09 run rows + 106 ledger rows
      executed   the artifact's `funnel.after_dedupe` distinct controller/cloud trials (252)
      standalone S — research-script trials, from the committed record

    `n_eff` (GATED, rule R2′) = N_eff(registry) + N_eff(executed) + S at raw. Each of the first two
    is compressed with the gate's conservative ρ̄/ONC bounds WITHIN its own population only; the
    terms are ADDED, which claims NO correlation credit BETWEEN populations — the sum of group
    N_effs is what independent groups give, and any cross-population correlation only lowers the
    true N_eff, so the sum errs strict. S gets no credit at all (no return streams: ruling 9.2).
    (ρ̄ was measured ON the executed population, so its credit there is not borrowed; the
    registry's is the merged Option-A treatment — R3 strips it.)

    `n_eff_omitting_executed` (REPORTED, the first build's R2) = N_eff(registry) + S. It counts
    NONE of the executed controller/cloud runs and is kept only so the correction is visible.

    `n_eff_ruling_9_2_all` (REPORTED, rule R3) also strips the borrowed credit from the registry's
    own curve-less rows: N_eff(executed) + N_raw + S. It is the honest number under ruling 9.2 and
    is NOT gated here — adopting it is the user's decision; every caller that quotes `n_eff` has
    it beside it."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    db = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    verify_pinned_registry(db, pin_path)
    n_raw = compute_n_effective(db)
    art = load_n_effective_artifact(None, artifact_dir, pin_path)
    gi = art["gate_inputs"]
    n_eff_registry = _registry_n_eff(n_raw, gi, method)
    tp = Path(trials_path) if trials_path is not None else default_trials_path(pin_path)
    trials_pinned = verify_pinned_trials(tp, pin_path)
    record = load_trials_record(tp)
    reconcile_trials_with_registry(record, db)
    cited_root = tp.resolve().parent.parent
    citations_checked = (cited_root / "docs").is_dir()
    if citations_checked:
        verify_trials_citations(record, cited_root)
    s = standalone_trials_total(record)
    pending = int(sum(int(r["n_trials"]) for r in record["rows"]
                      if r["counted_in"] == "standalone" and r.get("pending_ruling")))
    funnel = art.get("funnel")
    executed = funnel.get("after_dedupe") if isinstance(funnel, dict) else None
    if isinstance(executed, bool) or not isinstance(executed, int) or executed < 0:
        raise HonestNUnavailableError(
            "the pinned n_effective artifact carries no integer `funnel.after_dedupe` — the executed "
            "controller/cloud population cannot be counted, and the registry holds none of those runs")
    n_eff_executed = _registry_n_eff(executed, gi, method) if executed > 0 else 0.0
    r3 = n_eff_executed + n_raw + s
    pin_trials = load_pin(pin_path).get("trials") or {}
    return {
        "n_eff": n_eff_registry + n_eff_executed + s,
        "rule": "R2': registry N_eff + executed-population N_eff (each compressed within itself, no "
                "cross-population credit) + standalone trials at raw",
        "n_eff_executed": n_eff_executed,
        "n_eff_omitting_executed": n_eff_registry + s,
        "citations_verified_at_pin": bool(pin_trials.get("citations_verified", False)),
        "method": method,
        "n_raw_registry": n_raw,
        "n_eff_registry": n_eff_registry,
        "n_standalone": s,
        "n_standalone_pending_ruling": pending,
        "n_eff_excluding_pending": n_eff_registry + n_eff_executed + s - pending,
        "citations_checked": citations_checked,
        "n_raw_total": n_raw + s,
        "n_eff_ruling_9_2_all": r3,
        "executed_population": executed,
        "trials_record": tp.name,
        "trials_pinned": trials_pinned,
        "n_unresolved_items": len(record["unresolved"]),
    }


def compute_n_effective_correlated(
    db_path: Optional[Path] = None,
    method: str = "conservative",
    artifact_path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
    trials_path: Optional[Path] = None,
) -> float:
    """Correlation-aware N_eff of the registry PLUS the standalone-harness trials it cannot see
    (T-391). FAILS CLOSED (registry, pin, pinned artifact, or trials record missing, mismatched or
    inconsistent → raise).

    method="conservative" (default): the LARGER of the two below. On the 2026-09-30
                       measurement the estimators disagree (equicorrelated ~33, ONC ~21
                       at the registry's 231) and nothing in the data says which is right,
                       so the referee takes the one that makes the gate stricter.
    method="onc":      N_raw × (ONC clusters / runs), the compression López de Prado's
                       Optimal Number of Clusters measured on the executed runs. Its
                       silhouette criterion favours coarse splits when clusters overlap, so
                       it is the LESS conservative estimator on our data.
    method="equicorr": the equicorrelated identity at the measured ρ̄.
    The method applies to the REGISTRY part; standalone trials are added at raw under every
    method (`honest_n_breakdown` itemises both).

    The artifact's `gate_inputs` are the CONSERVATIVE CI bounds, not the point estimates
    (`[NN-SHARPE-CI]`'s logic applied to the trial count): ρ̄'s ci_LOW and the ONC
    compression's ci_HIGH, both of which make N_eff LARGER and the gate STRICTER. N_eff
    moves from 231 to ~61 to ~10 as ρ̄ goes 0 → 0.3 → 0.68, so gating on a noisy point
    would let estimation error loosen the bar.

    N_raw is the registry count (per the RR-3 brief). The proposal documents that the
    registry is a stale manual snapshot DISJOINT from the surviving run evidence — the
    choice of N_raw's population is flagged there for the user, not settled here.

    An explicit `artifact_path` (tools, tests) is a deliberate caller choice that bypasses the
    pins; such a call counts the standalone record only when `trials_path` is passed too. No
    production caller passes `artifact_path`."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    if artifact_path is None:
        # Production path: every input verified against the committed pin, the registry checked
        # before it is read, the trials record digest-checked and reconciled (honest_n_breakdown).
        return float(honest_n_breakdown(db_path, method, artifact_dir, pin_path, trials_path)["n_eff"])
    n_raw = compute_n_effective(db_path)
    gi = load_n_effective_artifact(artifact_path, artifact_dir, pin_path)["gate_inputs"]
    n = _registry_n_eff(n_raw, gi, method)
    if trials_path is not None:
        record = load_trials_record(trials_path)
        reconcile_trials_with_registry(record, db_path)
        n += standalone_trials_total(record)
    return n


def resolve_cycle_n_trials(
    batch_len: int,
    db_path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
    trials_path: Optional[Path] = None,
) -> Dict:
    """The trial count a Discovery cycle gates Gate 0 and Gate 8 on. FAILS CLOSED.

    Replaces production's `max(1, len(batch))`. The batch is one cycle's candidates;
    [NN-MBL]'s honest N counts every configuration ever run on the substrate, so the
    batch size under-counted by every prior cycle — and when the batch held one
    candidate, it disabled Gate 8 outright. `batch_len` is carried for the log only,
    so the pre-RR-3 figure stays visible beside the one now used. T-391: the standalone
    trials are included; the itemised breakdown rides along for the cycle's log."""
    b = honest_n_breakdown(db_path, "conservative", artifact_dir, pin_path, trials_path)
    return {"n_trials": float(b["n_eff"]), "source": "registry_correlated", "batch_len": int(batch_len),
            "breakdown": b}


# ----------------------------------------------------------------------------- gate
def check_mbl_gate(
    t_years: float,
    n_effective: Optional[float] = None,
    sr_target: float = 1.0,
    db_path: Optional[Path] = None,
    *,
    upper_bound: bool = False,
) -> Dict:
    """Run the MBL Gate-0 check and return a verdict dict.

    n_effective None → `compute_n_effective_correlated(db_path)`, which FAILS CLOSED.
    Keys: passed, t_years, mbl_min, n_effective, n_effective_source, sr_target,
    margin_years, formula, reason."""
    source = "explicit"
    if n_effective is None:
        n_effective = compute_n_effective_correlated(db_path)
        source = "registry_correlated"
    mbl_min = compute_mbl_min(n_effective, sr_target, upper_bound=upper_bound)
    margin = t_years - mbl_min
    passed = margin >= 0.0
    formula = "2ln(N)/SR^2 (upper bound)" if upper_bound else "E[max_N]^2/SR^2 (exact)"
    if passed:
        reason = (
            f"PASS: T_years={t_years:.2f} >= MBL_min={mbl_min:.2f} "
            f"(N_effective={n_effective:.2f} [{source}], SR_target={sr_target}, "
            f"margin={margin:+.2f}yr, {formula})")
    else:
        reason = (
            f"FAIL: T_years={t_years:.2f} < MBL_min={mbl_min:.2f} "
            f"(N_effective={n_effective:.2f} [{source}], SR_target={sr_target}, "
            f"short by {-margin:.2f}yr, {formula}). "
            f"Backtest is statistically under-powered to clear DSR — "
            f"per CLAUDE.md `[NN-MBL]`, no deployment decision is valid until the "
            f"window extends or N_effective decreases.")
    return {
        "passed": passed,
        "t_years": float(t_years),
        "mbl_min": float(mbl_min),
        "n_effective": round(float(n_effective), 4),
        "n_effective_source": source,
        "sr_target": float(sr_target),
        "margin_years": float(margin),
        "formula": formula,
        "reason": reason,
    }


def years_from_window(start_date: str, end_date: str) -> float:
    """Convert ISO date strings (YYYY-MM-DD) to a year-fraction window length."""
    from datetime import datetime
    s = datetime.fromisoformat(start_date)
    e = datetime.fromisoformat(end_date)
    return (e - s).days / 365.25

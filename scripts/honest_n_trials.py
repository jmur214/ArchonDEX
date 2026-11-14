"""The standalone-trials record behind the honest-N gate (T-391): the ONE recorder, the lint, a read-only show.

    python -m scripts.honest_n_trials record --trial-id T-392 --task-id T-392 --date 2026-11-14 --n-trials 1 \
        --family "..." --substrate "..." --prereg docs/Sources/prereg_x.md --verdict docs/Audit/x_verdict.md \
        --source docs/Audit/x_verdict.md:12 [--ledger-id T-392] [--note "..."]
    python -m scripts.honest_n_trials check     # the lint: exit 0 pass / 1 findings / 3 an input is unreadable
    python -m scripts.honest_n_trials show      # the gate's itemised N, read-only (registry opened mode=ro)

WHY: `data/observability/run_registry.sqlite` ingests only controller run directories, so a trial a
research script runs never reached `compute_n_effective_correlated` (health MEDIUM, main 573fc62). The
record `config/honest_n_trials.json` carries those trials; the gate adds them at raw and fails closed
on an absent, edited or inconsistent record (`core/measurement/mbl_gate.py`).

THE WRITER LIVES HERE, not in the referee module (the honest_n_pin precedent): the director runs `record`
at each verdict merge and commits the record in the same commit — that commit is the review. `record`
appends `counted_in = standalone` rows ONLY; the `registry_ledger` rows are the frozen backfill, mirrored
1:1 against the registry by the gate. Once re-pin #2 names the record in `config/honest_n_pin.json`, every
`record` must be followed by `python -m scripts.honest_n_pin --pin <artifact> --replace` in the same commit.

THE LINT (`check`), fail closed:
  * every TASK_LEDGER.md row declaring N > 0 has record rows with that ledger_id summing >= the declared N;
  * forward-only from the record's activation_date (a date RANGE reads by its LATEST date; a row with no
    parseable date is treated as forward): a row that states a trial count in ANY status (`dispatched`
    and `in-flight` included), OR whose status is closed (done/refuted/superseded), must have >= 1 record
    row (an n_trials 0 row counts); a closed row must also STATE N (`N_trials 0` counts). A row is exempt
    only while it states no count and is not closed;
  * no record row names a ledger_id the ledger lacks;
  * every citation in the record exists (path, and line within the file);
  * the registry cross-check where the registry exists on this host (SKIPPED, said so, where it does not —
    the gate itself refuses on a mismatch wherever it runs).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import core.measurement.mbl_gate as mbl

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "State" / "TASK_LEDGER.md"
ROW_KEYS = ("trial_id", "task_id", "date", "n_trials", "counted_in", "ledger_id", "family", "substrate",
            "prereg", "verdict", "source", "pending_ruling", "also_in_registry_as", "note")
HEADER_KEYS = ("schema", "task", "activation_date", "grandfathered_through", "rule", "note")
FORWARD_STATUSES = ("done", "refuted", "superseded")

# The N-declaration forms the ledger actually uses (T-336's two, plus the B-series `N_trials +k`,
# `n_trials_consumed k` and `N_trials consumed: k`). Case-sensitive on purpose: prose like "n+1" is not one.
_N_DECL = re.compile(r"(?:\bN_trials|\bN)\s*\+=?\s*(\d+)|\bn_trials_consumed\s*:?\s*(\d+)"
                     r"|\bN_trials consumed:?\s*\**\s*\+?(\d+)|\bN_trials\s*[:=]\s*\**\s*\+?([1-9]\d*)")
# A ledger date cell: a full date, optionally a range whose end may be abbreviated (2026-11-12→14,
# 2026-07-30→08-06, 2026-11-01→2026-11-20). The forward rule reads the LATEST date.
_RANGE_END = re.compile(r"(?:→|->|–|—|\bto\b)\s*(?:(\d{4})-)?(?:(\d{2})-)?(\d{2})\b")
_N_ZERO = re.compile(r"\b0 N_trials\b|\b[Zz]ero N_trials\b|\bno N_trials\b|\bN_trials:?\s*\**0\b"
                     r"|\bN ?\+= ?0\b|\b0 N\b|N_trials consumed:?\s*\**0\b")
_TASK_CELL = re.compile(r"^\|\s*((?:T|B|RR)-[^|]+?)\s*\|")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SOURCE = re.compile(r"^(?P<path>[^:]+):(?P<a>\d+)(?:-(?P<b>\d+))?$")


class RecordError(ValueError):
    """A recorder refusal: the row would make the record wrong or uncitable."""


# ----------------------------------------------------------------------------- serialisation (one writer)
def write_record(path: Path, header: Dict[str, Any], rows: List[Dict[str, Any]],
                 unresolved: List[Dict[str, Any]]) -> str:
    """Serialise with ONE row per line (a row's diff is one line) and the digest the gate re-derives.
    Refuses to write anything `mbl_gate.load_trials_record` would refuse to read. Returns the digest."""
    rows = [{k: (bool(r.get(k, False)) if k == "pending_ruling" else r.get(k)) for k in ROW_KEYS} for r in rows]
    digest = mbl.trials_digest(rows, unresolved, header.get("activation_date"))
    head = {k: header[k] for k in HEADER_KEYS if k in header}
    head["schema"] = mbl.TRIALS_SCHEMA
    lines = ["{"]
    lines += [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}," for k, v in head.items()]
    lines.append(f'  "rows_sha256": "{digest}",')
    lines.append('  "rows": [')
    lines += [f"    {json.dumps(r, ensure_ascii=False)}{',' if i < len(rows) - 1 else ''}"
              for i, r in enumerate(rows)]
    lines.append("  ],")
    lines.append('  "unresolved": [')
    lines += [f"    {json.dumps(u, ensure_ascii=False)}{',' if i < len(unresolved) - 1 else ''}"
              for i, u in enumerate(unresolved)]
    lines.append("  ]")
    lines.append("}")
    text = "\n".join(lines) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    try:
        mbl.load_trials_record(tmp)                       # refuse to write what the gate could not read
    except mbl.HonestNUnavailableError:
        tmp.unlink()
        raise
    tmp.replace(path)
    return digest


# ----------------------------------------------------------------------------- the recorder
def _check_repo_path(rel: str, root: Path, what: str) -> Path:
    if rel.startswith("/") or ".." in Path(rel).parts:
        raise RecordError(f"{what} {rel!r} must be a repo-relative path without '..'")
    p = root / rel
    if not p.is_file():
        raise RecordError(f"{what} {rel!r} does not exist under {root}")
    return p


def _check_source(source: str, root: Path) -> None:
    m = _SOURCE.match(source)
    if not m:
        raise RecordError(f"source {source!r} must be 'path:line' or 'path:line-line'")
    p = _check_repo_path(m["path"], root, "source")
    n_lines = len(p.read_text(errors="replace").splitlines())
    last = int(m["b"] or m["a"])
    if not (1 <= int(m["a"]) <= last <= n_lines):
        raise RecordError(f"source {source!r}: line(s) outside {m['path']} (1..{n_lines})")


def record_trial(*, trial_id: str, task_id: str, date: str, n_trials: int, family: str, substrate: str,
                 prereg: str, verdict: str, source: str, ledger_id: Optional[str] = None,
                 note: str = "", pending_ruling: bool = False, also_in_registry_as: Optional[str] = None,
                 record_path: Optional[Path] = None,
                 root: Path = ROOT) -> Dict[str, Any]:
    """Append ONE standalone trial row. Refuses a duplicate trial_id, a non-ISO date, a negative count,
    and any citation (prereg, verdict, source line) that does not exist in the repo."""
    record_path = Path(record_path) if record_path is not None else mbl.default_trials_path()
    rec = mbl.load_trials_record(record_path)
    if any(r["trial_id"] == trial_id for r in rec["rows"]):
        raise RecordError(f"trial_id {trial_id!r} is already recorded — one trial, one row")
    if not _DATE.fullmatch(date):
        raise RecordError(f"date {date!r} is not YYYY-MM-DD")
    if isinstance(n_trials, bool) or not isinstance(n_trials, int) or n_trials < 0:
        raise RecordError(f"n_trials must be an int >= 0, got {n_trials!r}")
    for rel, what in ((prereg, "prereg"), (verdict, "verdict")):
        _check_repo_path(rel, root, what)
    _check_source(source, root)
    row = {"trial_id": trial_id, "task_id": task_id, "date": date, "n_trials": n_trials,
           "counted_in": "standalone", "ledger_id": ledger_id or None, "family": family,
           "substrate": substrate, "prereg": prereg, "verdict": verdict, "source": source,
           "pending_ruling": bool(pending_ruling), "also_in_registry_as": also_in_registry_as or None,
           "note": note}
    write_record(record_path, rec, rec["rows"] + [row], rec["unresolved"])
    return row


# ----------------------------------------------------------------------------- the lint
@dataclass(frozen=True)
class LedgerRow:
    line: int
    ledger_id: str
    date: Optional[str]
    status: str
    doc: str
    declared: int
    states_n: bool


def latest_date(cell: str) -> Optional[str]:
    """The LATEST date a ledger date cell names (None when it names none). A range closes on its
    end date, so a row opened before activation and closed after it is a forward row."""
    first = _DATE.search(cell)
    if not first:
        return None
    dates = _DATE.findall(cell)
    y, mth, _ = first.group(0).split("-")
    for ey, em, ed in _RANGE_END.findall(cell[first.end():]):
        dates.append(f"{ey or y}-{em or mth}-{ed}")
    return max(dates)


def parse_ledger(path: Path = LEDGER) -> List[LedgerRow]:
    out: List[LedgerRow] = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        m = _TASK_CELL.match(line)
        if not m or m.group(1).strip() == "T-ID":
            continue
        cells = [c.strip() for c in line.split("|")]
        status = cells[4].lower() if len(cells) > 4 else ""
        doc = cells[-2] if len(cells) >= 3 else ""
        hits = _N_DECL.findall(line)
        declared = sum(int(next(g for g in h if g)) for h in hits)
        out.append(LedgerRow(i, m.group(1).strip(), latest_date(cells[2] if len(cells) > 2 else ""), status,
                             doc, declared, bool(hits) or bool(_N_ZERO.search(line))))
    return out


def lint(record: Dict[str, Any], ledger: Sequence[LedgerRow]) -> List[str]:
    """The findings; [] is a pass."""
    findings: List[str] = []
    by_ledger: Dict[str, int] = {}
    rows_for: Dict[str, int] = {}
    for r in record["rows"]:
        lid = r.get("ledger_id")
        if lid:
            by_ledger[lid] = by_ledger.get(lid, 0) + int(r["n_trials"])
            rows_for[lid] = rows_for.get(lid, 0) + 1
    declared: Dict[str, int] = {}
    first_line: Dict[str, int] = {}
    for row in ledger:
        declared[row.ledger_id] = declared.get(row.ledger_id, 0) + row.declared
        first_line.setdefault(row.ledger_id, row.line)
    for lid, k in sorted(declared.items()):
        if k > 0 and by_ledger.get(lid, 0) < k:
            findings.append(f"TASK_LEDGER.md:{first_line[lid]} {lid} declares N_trials {k} but the record "
                            f"holds {by_ledger.get(lid, 0)} — record it (`honest_n_trials record`)")
    activation = record["activation_date"]
    for row in ledger:
        if row.date is not None and row.date < activation:          # an unparseable date is FORWARD
            continue
        closed = row.status in FORWARD_STATUSES
        if not (closed or row.states_n):        # exempt ONLY while it states no count and is not closed
            continue
        if closed and not row.states_n:
            findings.append(f"TASK_LEDGER.md:{row.line} {row.ledger_id} ({row.status}, {row.date}) closes "
                            f"without stating N_trials (write `N_trials 0` if none was consumed)")
        if rows_for.get(row.ledger_id, 0) == 0:
            findings.append(f"TASK_LEDGER.md:{row.line} {row.ledger_id} ({row.status}, {row.date}) has no "
                            f"trials-record row (an n_trials 0 row counts) — run `honest_n_trials record`")
    known = {row.ledger_id for row in ledger}
    for r in record["rows"]:
        if r.get("ledger_id") and r["ledger_id"] not in known:
            findings.append(f"record row {r['trial_id']!r} names ledger_id {r['ledger_id']!r}, which no "
                            f"TASK_LEDGER.md row carries")
    return findings


def check(record_path: Optional[Path] = None, ledger_path: Path = LEDGER,
          db_path: Optional[Path] = None) -> int:
    try:
        rec = mbl.load_trials_record(record_path)
        mbl.verify_trials_citations(rec, ROOT)
        ledger = parse_ledger(ledger_path)
    except (mbl.HonestNUnavailableError, OSError) as exc:
        print(f"TRIALS CHECK DEFECT: {exc}")
        return 3
    db = Path(db_path) if db_path is not None else mbl.DEFAULT_DB_PATH
    findings = lint(rec, ledger)
    if db.exists():
        try:
            mbl.reconcile_trials_with_registry(rec, db)
            print(f"registry cross-check: OK ({db.name}, {sum(mbl.registry_ledger_counts(db).values())} ledger rows)")
        except mbl.HonestNUnavailableError as exc:
            findings.append(str(exc))
    else:
        print(f"registry cross-check: SKIPPED — {db} absent on this host (the gate refuses a mismatch where it runs)")
    for f in findings:
        print(f"FINDING: {f}")
    s = mbl.standalone_trials_total(rec)
    print(f"{'TRIALS CHECK FAILED' if findings else 'TRIALS CHECK OK'}: {len(rec['rows'])} rows, standalone S = {s}, "
          f"{len(rec['unresolved'])} unresolved (not counted), activation {rec['activation_date']}, "
          f"{len(findings)} finding(s)")
    return 1 if findings else 0


# ----------------------------------------------------------------------------- CLI
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="append ONE standalone trial row (the director, at a verdict merge)")
    for flag in ("--trial-id", "--task-id", "--date", "--family", "--substrate", "--prereg", "--verdict", "--source"):
        r.add_argument(flag, required=True)
    r.add_argument("--n-trials", type=int, required=True)
    r.add_argument("--ledger-id", default=None)
    r.add_argument("--note", default="")
    r.add_argument("--also-in-registry-as", default=None, metavar="REGISTRY_TRIAL_ID",
                   help="this is a DIFFERENT trial of a task the registry already counts: name that registry row")
    r.add_argument("--pending-ruling", action="store_true",
                   help="counted now, flagged for the user's ruling (the fail-closed default for a run trial)")
    sub.add_parser("check", help="the lint (exit 0 / 1 findings / 3 unreadable input)")
    sub.add_parser("show", help="the gate's itemised honest N, read-only")
    a = ap.parse_args(argv)
    if a.cmd == "record":
        try:
            row = record_trial(trial_id=a.trial_id, task_id=a.task_id, date=a.date, n_trials=a.n_trials,
                               family=a.family, substrate=a.substrate, prereg=a.prereg, verdict=a.verdict,
                               source=a.source, ledger_id=a.ledger_id, note=a.note,
                               pending_ruling=a.pending_ruling, also_in_registry_as=a.also_in_registry_as)
        except (RecordError, mbl.HonestNUnavailableError) as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 4
        print(f"recorded {row['trial_id']} (+{row['n_trials']}) -> {mbl.default_trials_path()} — commit it with the verdict")
        if "trials" in mbl.load_pin():
            print("the pin names the record: re-pin in the same commit — "
                  "python -m scripts.honest_n_pin --pin <pinned artifact> --replace --note \"<task> trials recorded\"")
        return 0
    if a.cmd == "check":
        return check()
    try:
        b = mbl.honest_n_breakdown()
    except mbl.HonestNUnavailableError as exc:
        print(f"HONEST N UNAVAILABLE: {exc}")
        return 3
    print(json.dumps(b, indent=2, default=str))
    print(f"as of {_dt.date.today().isoformat()}: gated N_eff {b['n_eff']:.2f} (R2'); "
          f"{b['n_eff_excluding_pending']:.2f} without the rows pending a ruling; "
          f"ruling-9.2-for-all {b['n_eff_ruling_9_2_all']:.2f} (R3, reported)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""reviewer_liveness_sweep.py — the independent reviewer's instrument (Agent R, director-approved 2026-09-18).

Born from two misses in the 2026-09-17 fresh-eyes audit, both with the same cause — the
record was READ instead of TESTED:
  miss 1: an autonomy-ledger row labeled `scheduled_pass` at 13:37 local, on a schedule that
          fires at 07:00, reported without the two facts ever being put side by side;
  miss 2: `cash_adj` exactly zero on every family-tracker point, quoted as a small number
          instead of asked "has this field EVER been non-default?".

This tool makes both questions mechanical, over EVERY rendered field and EVERY schedule
label, so a reviewer cannot skip them.

THE THREE RAILS (director ruling, 2026-09-18):
  1. READ-ONLY, ENFORCED STRUCTURALLY. There is no write path in this module: no file is
     opened for writing, nothing is created, moved, or deleted, no network call, no
     subprocess. Its only outputs are the fixed-format table on stdout and the exit code.
     `tests/test_reviewer_liveness_sweep.py` proves this by AST scan and by a byte-for-byte
     tree hash before/after a run, and proves the guard itself by mutation.
  2. REUSE the registries. The clock census (`run_census`) and the T-342 channel-liveness
     registry (`channel_liveness`, `CHANNELS`) are called, not re-implemented. The field
     scan is deliberately OVER-INCLUSIVE; a NEVER-non-default field that the registry does
     not declare is reported as `undeclared` — a finding to file against the registry
     owner, never a private duplicate.
  3. ADVISORY BY CONSTRUCTION. Findings never change the exit code. Exit 0 = the table was
     rendered from readable inputs; exit 2 = an input root was unreadable and NO table was
     rendered (a table from missing inputs would be a plausible number wearing a real
     one's face — [NN-FAIL-CLOSED]). It gates nothing and alarms nothing.

The artifacts it reads are whatever directories it is pointed at. Pulling them from S3 is
the operator's job, outside this tool (e.g. `aws s3 sync` into a scratch dir); the tool never
touches S3. Usage:

    reviewer_liveness_sweep.py --root acct1=/scratch/paper_state \\
                               --root acct2=/scratch/paper_state_offense_sso \\
                               --root acct3=/scratch/paper_state_ai_trader \\
                               --ledger data/state/autonomy_ledger.jsonl \\
                               --plist ops/com.archondex.janitor.plist \\
                               --plist ops/com.archondex.director-pass.plist \\
                               [--as-of YYYY-MM-DD] [--tz America/Chicago] [--all]
"""
from __future__ import annotations

import argparse
import json
import plistlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from paper_trader.clock_census import (  # noqa: E402  (rail 2: reuse, never duplicate)
    CHANNELS, LIVE, NEVER_ALIVE, UNVERIFIABLE, census_line, channel_liveness,
    liveness_line, run_census)

# Field-scan statuses (the sweep's own vocabulary; the registry's are imported above).
NEVER_NONDEFAULT = "NEVER_NONDEFAULT"     # present on points but never left its default
ABSENT = "ABSENT"                         # never written on any point at all
# Schedule-check verdicts.
LABEL_OK, LABEL_MISMATCH, LABEL_UNSCHEDULED = "OK", "LABEL_MISMATCH", "NO_SCHEDULE_FOR_SESSION"

# What "default" means for a rendered value. A number that has only ever been 0 is the
# exact shape of miss 2: zero-because-unmeasured wearing zero-because-small's clothes.
def _is_default(v: Any) -> bool:
    if v is None or v is False:
        return True
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v == 0
    if isinstance(v, (str, list, dict, tuple)):
        return len(v) == 0
    return False


# --------------------------------------------------------------------------------------
# Section A — the over-inclusive FIELD scan (miss 2 made mechanical)
# --------------------------------------------------------------------------------------
@dataclass
class FieldRow:
    root: str
    file: str
    field: str
    n_points: int
    n_nondefault: int
    first: Optional[str]
    last: Optional[str]
    status: str
    declared: bool


def _flatten(pt: Dict[str, Any], prefix: str = "", depth: int = 0) -> Iterable[Tuple[str, Any]]:
    """One level of nesting is enough for the trackers (`exec.slippage_bps`, `closes.SPY`)."""
    for k, v in pt.items():
        name = f"{prefix}{k}"
        if isinstance(v, dict) and depth == 0:
            yield from _flatten(v, prefix=f"{name}.", depth=1)
        else:
            yield name, v


def _series_of(doc: Any) -> List[Dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    pts = doc.get("points") or doc.get("days") or []
    return [p for p in pts if isinstance(p, dict)]


def _declared_fields() -> set:
    """(relative-file, field) pairs the T-342 registry already declares — via the closure's
    captured arguments, so the sweep tracks the registry without a second list."""
    out = set()
    for ch in CHANNELS:
        cv = getattr(ch.check, "__closure__", None) or ()
        strs = [c.cell_contents for c in cv if isinstance(getattr(c, "cell_contents", None), str)]
        rels = [s for s in strs if "/" in s]
        for rel in rels:
            out.add((Path(rel).name, ch.name))
            for s in strs:
                if s != rel and "/" not in s:
                    out.add((Path(rel).name, s))
    return out


def scan_fields(label: str, root: Path) -> List[FieldRow]:
    declared = _declared_fields()
    rows: List[FieldRow] = []
    state = root / "data" / "state"
    if not state.exists():
        return rows
    for f in sorted(state.glob("*.json")):
        try:
            doc = json.loads(f.read_text())
        except Exception:
            continue                                   # unparseable files are the census's job
        pts = _series_of(doc)
        if not pts:
            continue
        seen: Dict[str, Dict[str, Any]] = {}
        for pt in pts:
            date = pt.get("date") or pt.get("as_of")
            flat = dict(_flatten(pt))
            for k in flat:
                seen.setdefault(k, {"n": 0, "nd": 0, "first": None, "last": None})
            for k, st in seen.items():
                if k in flat:
                    st["n"] += 1
                    if not _is_default(flat[k]):
                        st["nd"] += 1
                        st["first"] = st["first"] or date
                        st["last"] = date
        for k, st in sorted(seen.items()):
            if st["nd"] == 0:
                status = NEVER_NONDEFAULT if st["n"] == len(pts) else ABSENT if st["n"] == 0 else NEVER_NONDEFAULT
            else:
                status = LIVE
            rows.append(FieldRow(label, f.name, k, len(pts), st["nd"], st["first"], st["last"],
                                 status, (f.name, k.split(".")[0]) in declared or (f.name, k) in declared))
        # a field the registry declares for this file but no point has ever carried
        for (fname, field) in declared:
            if fname == f.name and field not in seen and not any(s.startswith(field + ".") for s in seen):
                rows.append(FieldRow(label, f.name, field, len(pts), 0, None, None, ABSENT, True))
    return rows


# --------------------------------------------------------------------------------------
# Section B — schedule-label cross-check (miss 1 made mechanical)
# --------------------------------------------------------------------------------------
@dataclass
class LabelRow:
    ts_local: str
    session: str
    trigger: str
    schedule: str
    delta_min: Optional[int]
    verdict: str
    annotated: bool


# Which ledger `session` values claim which launchd label, and which trigger strings are
# schedule-class. Only the wrappers may claim these (B's rule, 4c94219).
SCHEDULE_CLASS = {"nightly_schedule": "com.archondex.janitor",
                  "scheduled_pass": "com.archondex.director-pass"}
TOLERANCE_MIN = 20


def _plist_schedules(paths: List[Path]) -> Dict[str, List[Tuple[int, int]]]:
    out: Dict[str, List[Tuple[int, int]]] = {}
    for p in paths:
        with p.open("rb") as fh:                                   # read-only
            d = plistlib.load(fh)
        label = d.get("Label") or p.stem
        sci = d.get("StartCalendarInterval") or []
        if isinstance(sci, dict):
            sci = [sci]
        out[label] = [(int(x.get("Hour", 0)), int(x.get("Minute", 0))) for x in sci]
    return out


def check_labels(ledger: Path, schedules: Dict[str, List[Tuple[int, int]]], tz: str) -> List[LabelRow]:
    rows: List[LabelRow] = []
    zone = ZoneInfo(tz)
    recs = []
    for line in ledger.read_text().splitlines():
        if line.strip():
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    # Annotation rows (B's convention, never rewrites): session="annotation",
    # kind="trigger_correction", corrects_ts = one ISO string or a list, possibly truncated
    # to the minute — so match by PREFIX, never by equality.
    corrected: List[str] = []
    for r in recs:
        if r.get("kind") == "trigger_correction" or r.get("session") == "trigger_correction":
            c = r.get("corrects_ts") or r.get("corrects") or []
            corrected += [str(x) for x in (c if isinstance(c, list) else [c])]

    def _annotated(ts: Any) -> bool:
        return any(str(ts).startswith(c) for c in corrected)
    for r in recs:
        trig = r.get("trigger")
        if trig not in SCHEDULE_CLASS:
            continue
        label = SCHEDULE_CLASS[trig]
        ts = datetime.fromisoformat(str(r.get("ts")).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        local = ts.astimezone(zone)
        slots = schedules.get(label)
        if not slots:
            rows.append(LabelRow(local.strftime("%Y-%m-%d %H:%M"), r.get("session", "?"), trig, label,
                                 None, LABEL_UNSCHEDULED, _annotated(r.get("ts"))))
            continue
        deltas = []
        for (h, m) in slots:
            sched = local.replace(hour=h, minute=m, second=0, microsecond=0)
            deltas.append(abs(int((local - sched).total_seconds() // 60)))
        d = min(deltas)
        rows.append(LabelRow(local.strftime("%Y-%m-%d %H:%M"), r.get("session", "?"), trig, label, d,
                             LABEL_OK if d <= TOLERANCE_MIN else LABEL_MISMATCH,
                             _annotated(r.get("ts"))))
    return rows


# --------------------------------------------------------------------------------------
# Rendering — one fixed format, stdout only
# --------------------------------------------------------------------------------------
def _md(rows: List[List[str]], header: List[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(roots: Dict[str, Path], ledger: Optional[Path], plists: List[Path],
           as_of: str, tz: str, show_all: bool) -> str:
    parts = [f"# Reviewer liveness sweep — as of {as_of} (advisory; gates nothing)", ""]

    # Section 1: the registries, reused verbatim, per root.
    parts.append("## 1. Registries (reused: clock census + T-342 channel liveness), per root")
    for label, root in roots.items():
        try:
            live = channel_liveness(str(root))
            cen = run_census(str(root), as_of)
            parts.append(f"- **{label}** (`{root}`): {liveness_line(live)}")
            parts.append(f"  - {census_line(cen)}")
            for r in live["detail"]:
                if r["status"] in (NEVER_ALIVE, UNVERIFIABLE) and "source missing" not in r["detail"]:
                    parts.append(f"    - {r['status']} `{r['consumer']}:{r['channel']}` — {r['detail']}")
        except Exception as exc:                       # a raising registry is a finding, not a crash
            parts.append(f"- **{label}**: registry call raised {type(exc).__name__}: {exc}")
    parts.append("")

    # Section 2: the over-inclusive field scan.
    parts.append("## 2. Field scan — every point field on every tracker/book: has it EVER been non-default?")
    frows: List[FieldRow] = []
    for label, root in roots.items():
        frows += scan_fields(label, root)
    shown = [r for r in frows if show_all or r.status != LIVE]
    if not frows:
        parts.append("_no tracker/book series found under the given roots_")
    elif not shown:
        parts.append(f"_all {len(frows)} fields have been non-default at least once (pass `--all` to list)_")
    else:
        parts.append(_md([[r.root, r.file, r.field, r.n_points, r.n_nondefault, r.first or "—",
                           r.last or "—", r.status, "yes" if r.declared else "**undeclared**"] for r in shown],
                         ["root", "file", "field", "n", "non-default", "first", "last", "status", "in registry"]))
        undeclared = [r for r in shown if r.status != LIVE and not r.declared]
        parts.append("")
        parts.append(f"_{len(frows)} fields scanned; {len([r for r in frows if r.status != LIVE])} never non-default; "
                     f"{len(undeclared)} of those UNDECLARED in the T-342 registry → file against the registry owner, "
                     f"do not add a private list here._")
    parts.append("")

    # Section 3: schedule labels.
    parts.append("## 3. Schedule-class ledger labels vs the installed launchd schedule")
    if ledger is None:
        parts.append("_no ledger given_")
    else:
        sched = _plist_schedules(plists)
        lrows = check_labels(ledger, sched, tz)
        bad = [r for r in lrows if r.verdict != LABEL_OK]
        parts.append(f"_schedules read: {', '.join(f'{k}={v}' for k, v in sched.items()) or 'none'} ({tz}); "
                     f"tolerance ±{TOLERANCE_MIN} min; {len(lrows)} schedule-class rows, {len(bad)} not matching_")
        if bad or show_all:
            parts.append(_md([[r.ts_local, r.session, r.trigger, r.schedule,
                               "—" if r.delta_min is None else r.delta_min, r.verdict,
                               "yes" if r.annotated else "no"] for r in (lrows if show_all else bad)],
                             ["ts (local)", "session", "trigger label", "schedule", "Δ min", "verdict", "annotated"]))
    parts.append("")
    parts.append("_Advisory. Findings above change nothing by themselves; they are read into the DEFECT round "
                 "or the checkpoint addendum by a person._")
    return "\n".join(parts)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", action="append", default=[], metavar="LABEL=DIR",
                    help="a directory shaped like a container root (has data/state/); repeatable")
    ap.add_argument("--ledger", type=Path, default=None, help="autonomy_ledger.jsonl to label-check")
    ap.add_argument("--plist", action="append", default=[], type=Path, help="installed launchd plist(s)")
    ap.add_argument("--as-of", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--tz", default="America/Chicago")
    ap.add_argument("--all", action="store_true", help="show LIVE/OK rows too")
    a = ap.parse_args(argv)

    roots: Dict[str, Path] = {}
    for spec in a.root:
        label, _, d = spec.partition("=")
        if not d:
            label, d = Path(spec).name, spec
        p = Path(d)
        if not p.is_dir():
            print(f"[reviewer_liveness_sweep] FAIL-CLOSED: root {label}={p} is not a readable directory; "
                  f"no table rendered.", file=sys.stderr)
            return 2
        roots[label] = p
    if a.ledger is not None and not a.ledger.is_file():
        print(f"[reviewer_liveness_sweep] FAIL-CLOSED: ledger {a.ledger} unreadable; no table rendered.",
              file=sys.stderr)
        return 2
    for p in a.plist:
        if not p.is_file():
            print(f"[reviewer_liveness_sweep] FAIL-CLOSED: plist {p} unreadable; no table rendered.",
                  file=sys.stderr)
            return 2
    if not roots and a.ledger is None:
        ap.error("give at least one --root or a --ledger")
    print(render(roots, a.ledger, a.plist, a.as_of, a.tz, a.all))
    return 0


if __name__ == "__main__":
    sys.exit(main())

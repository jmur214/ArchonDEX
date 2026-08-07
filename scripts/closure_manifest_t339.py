"""T-339 — the CLOSURE MANIFEST: make closure-grade artifacts un-deletable.

THE DEFECT (found by C/T-337): all five Arm-1 run directories under the T-215 /
T-180-v2 closures are DELETED. A load-bearing closure's receipt is unobtainable, and
every closure is one `rm -rf data/trade_logs/<uuid>` away from the same fate. The
ledger says "refuted/done" but the evidence is gone.

WHAT THIS DOES
  1. MANIFEST  — enumerate every ledger row whose verdict cites a MEASUREMENT, resolve
     its receipt set, and record on-disk presence (COMPLETE / PARTIAL / MISSING).
  2. ARCHIVE   — push surviving receipt sets to S3 under an immutable, task-keyed
     `closures/<TASK-ID>/` prefix ([NN-ARCHIVE] extended to measurement artifacts).
  3. VERIFY    — restore one set from S3 and prove it reads back.

THE RECEIPT SET (minimal, per the dispatch): the audit doc (the written verdict), the
task-keyed research artifacts, and any performance_summary.json / trades canon or md5 /
config hashes reachable from them. The census already md5s the last three, so where a
summary exists its census block IS the tamper-evident receipt.

Usage:
  python -m scripts.closure_manifest_t339                 # manifest only
  python -m scripts.closure_manifest_t339 --archive       # + push survivors to S3
  python -m scripts.closure_manifest_t339 --verify T-311  # restore one set from S3
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# receipts live in the MAIN checkout's data store (worktrees share it)
STORE = Path("/Users/jacksonmurphy/Dev/trading_machine-2")
LEDGER = ROOT / "docs" / "State" / "TASK_LEDGER.md"
OUT_JSON = ROOT / "data" / "research" / "closure_manifest_t339.json"
OUT_MD = ROOT / "docs" / "Audit" / "closure_manifest_t339.md"
BUCKET = "archondex-results-407539788432"
PREFIX = "closures"

# A verdict is MEASUREMENT-GRADE if it quotes a statistic or consumes trials.
_MEASURED = re.compile(
    r"Sharpe|Sortino|ci_low|95%\s*CI|\bCI\b|DSR|MaxDD|CAGR|N_trials\s*\+=|bps/yr|α|alpha",
    re.I)
_ROW = re.compile(r"^\|\s*(T-[0-9A-Za-z\-\.]+)\s*\|")


def _task_num(task: str) -> str:
    m = re.search(r"(\d{2,4}[a-z]*)$", task)
    return m.group(1) if m else task


def parse_ledger():
    rows = []
    for line in LEDGER.read_text().splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        task = m.group(1)
        status = cells[4] if len(cells) > 4 else ""
        audit_doc = cells[-2] if len(cells) > 2 else ""
        measured = bool(_MEASURED.search(line))
        rows.append({"task": task, "status": status, "audit_doc": audit_doc,
                     "measured": measured})
    return rows


def resolve_receipts(task: str, audit_doc: str) -> dict:
    """Locate the receipt set for one closure. Presence is checked, never assumed."""
    num = _task_num(task)
    found = {"audit_doc": [], "research": [], "perf_summary": [], "trades": []}
    # the written verdict
    doc = re.sub(r"[`\s]", "", audit_doc or "")
    if doc.endswith(".md"):
        for base in (ROOT / "docs" / "Audit", ROOT / "docs" / "Measurements",
                     ROOT / "docs" / "Sources"):
            for p in base.rglob(doc):
                found["audit_doc"].append(str(p.relative_to(ROOT)))
    if not found["audit_doc"]:
        for base in (ROOT / "docs" / "Audit", ROOT / "docs" / "Sources"):
            found["audit_doc"] += [str(p.relative_to(ROOT))
                                   for p in base.rglob(f"*t{num}*.md")]
    # task-keyed data artifacts
    for pat in (f"t{num}", f"t{num}_*", f"*t{num}*.json", f"*t{num}*.parquet",
                f"*t{num}*.csv"):
        for p in (STORE / "data" / "research").glob(pat):
            rel = str(p.relative_to(STORE))
            if rel not in found["research"]:
                found["research"].append(rel)
    # measurement receipts reachable inside those artifacts
    for rel in list(found["research"]):
        p = STORE / rel
        if p.is_dir():
            for s in p.rglob("performance_summary.json"):
                found["perf_summary"].append(str(s.relative_to(STORE)))
            for s in list(p.rglob("trades*.csv")) + list(p.rglob("*canon*")):
                found["trades"].append(str(s.relative_to(STORE)))
    n_doc = len(found["audit_doc"])
    n_data = len(found["research"]) + len(found["perf_summary"]) + len(found["trades"])
    state = ("COMPLETE" if n_doc and n_data else
             "DOC-ONLY" if n_doc else
             "DATA-ONLY" if n_data else "MISSING")
    return {"receipts": found, "state": state, "n_doc": n_doc, "n_data": n_data}


def build_manifest() -> dict:
    rows = parse_ledger()
    measured = [r for r in rows if r["measured"]]
    out = []
    for r in measured:
        res = resolve_receipts(r["task"], r["audit_doc"])
        out.append({**r, **res})
    tally = {}
    for e in out:
        tally[e["state"]] = tally.get(e["state"], 0) + 1
    return {"ledger_rows": len(rows), "measured_rows": len(measured),
            "tally": tally, "closures": out}


def _aws(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["aws", *args, "--profile", "archondex"],
                          capture_output=True, text=True)


def archive(man: dict) -> dict:
    """Push each surviving receipt set to closures/<TASK>/ — immutable, task-keyed."""
    pushed, skipped = 0, 0
    for e in man["closures"]:
        if e["state"] == "MISSING":
            skipped += 1
            continue
        for kind, rels in e["receipts"].items():
            for rel in rels:
                src = (ROOT / rel) if kind == "audit_doc" else (STORE / rel)
                if not src.exists():
                    continue
                dst = f"s3://{BUCKET}/{PREFIX}/{e['task']}/{kind}/{Path(rel).name}"
                if src.is_dir():
                    _aws("s3", "sync", str(src), dst.rstrip("/"), "--no-progress")
                else:
                    _aws("s3", "cp", str(src), dst, "--no-progress")
                pushed += 1
    return {"objects_pushed": pushed, "closures_skipped_missing": skipped}


def verify(task: str) -> dict:
    """INTEGRATION BAR: restore one receipt set from S3 and prove it reads back."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = _aws("s3", "sync", f"s3://{BUCKET}/{PREFIX}/{task}/", td, "--no-progress")
        files = [p for p in Path(td).rglob("*") if p.is_file()]
        readable = []
        for p in files:
            try:
                if p.suffix == ".json":
                    json.loads(p.read_text()); readable.append(f"{p.name} (json OK)")
                elif p.suffix in (".md", ".csv"):
                    n = len(p.read_text(errors="replace").splitlines())
                    readable.append(f"{p.name} ({n} lines)")
                else:
                    readable.append(f"{p.name} ({p.stat().st_size} B)")
            except Exception as exc:
                readable.append(f"{p.name} UNREADABLE {type(exc).__name__}")
        return {"task": task, "restored_files": len(files), "readable": readable,
                "rc": r.returncode}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", action="store_true")
    ap.add_argument("--verify", metavar="TASK")
    a = ap.parse_args()
    if a.verify:
        print(json.dumps(verify(a.verify), indent=2)); return 0
    man = build_manifest()
    print(f"[T339] ledger rows {man['ledger_rows']} | MEASURED closures {man['measured_rows']}")
    print(f"       receipt state tally: {man['tally']}")
    miss = [e["task"] for e in man["closures"] if e["state"] == "MISSING"]
    doconly = [e["task"] for e in man["closures"] if e["state"] == "DOC-ONLY"]
    print(f"\n  ALREADY UNVERIFIABLE (no receipts at all): {len(miss)}")
    print(f"    {miss}")
    print(f"\n  DOC-ONLY (verdict written, DATA gone — cannot re-derive): {len(doconly)}")
    print(f"    {doconly[:20]}{' ...' if len(doconly) > 20 else ''}")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(man, indent=2))
    print(f"\n  wrote {OUT_JSON.relative_to(ROOT)}")
    if a.archive:
        print(f"  archiving survivors -> s3://{BUCKET}/{PREFIX}/ ...")
        print(f"  {archive(man)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

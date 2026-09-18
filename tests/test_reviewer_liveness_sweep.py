"""The reviewer liveness sweep — the three rails, PROVEN not promised (Agent R, 2026-09-18).

Rail 1 (read-only, structural): (a) an AST scan of the module finds no write-shaped call —
open() in a write mode, Path.write_*/touch/mkdir/unlink/rename/replace, os.remove/makedirs/
rename, shutil.*, json.dump, subprocess, urllib/requests/boto3; (b) a run over a fixture tree
leaves every byte identical; (c) the AST guard itself is proven by MUTATION — a copy of the
module with one write call added must FAIL the guard, or the guard is theatre.
Rail 2 (reuse): the module imports the registry's `channel_liveness`/`run_census`/`CHANNELS`
and defines no parallel channel list.
Rail 3 (advisory): findings never change the exit code; only unreadable inputs do.

Plus the two retroactive catches the instrument was born from: a `scheduled_pass` row at
13:37 local against a 07:00 schedule → LABEL_MISMATCH; a tracker whose `cash_adj` never left
zero → NEVER_NONDEFAULT.
"""
from __future__ import annotations

import ast
import hashlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "reviewer_liveness_sweep.py"
sys.path.insert(0, str(REPO))
from scripts import reviewer_liveness_sweep as sweep  # noqa: E402

# Attribute calls that write, spawn, or delete. Network reach is caught by the IMPORT scan
# (requests/urllib/boto3/socket), not by attribute names — `.get()` is also dict.get and
# `.replace()` is also str.replace, so those names would only produce false positives.
WRITE_ATTRS = {"write_text", "write_bytes", "touch", "mkdir", "unlink", "rename",
               "rmdir", "remove", "makedirs", "removedirs", "put_object", "upload_file",
               "upload_fileobj", "delete_object", "to_csv", "to_json", "to_parquet", "dump",
               "run", "Popen", "call", "check_output", "check_call", "system", "urlopen"}
WRITE_MODULES = {"shutil", "subprocess", "boto3", "requests", "urllib", "socket", "os"}


def _write_shaped_calls(src: str) -> list[str]:
    """Every call that could write, spawn, or reach the network. Over-inclusive on purpose."""
    tree = ast.parse(src)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for n in names:
                if n.split(".")[0] in WRITE_MODULES:
                    hits.append(f"import {n} @L{node.lineno}")
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name) and f.id == "open":
            mode = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if mode is None or any(c in str(mode) for c in "wax+"):
                hits.append(f"open(mode={mode!r}) @L{node.lineno}")
        if isinstance(f, ast.Attribute) and f.attr in WRITE_ATTRS:
            hits.append(f".{f.attr}() @L{node.lineno}")
    return hits


# ---------------------------------------------------------------- rail 1: read-only
def test_rail1_no_write_shaped_call_in_module():
    hits = _write_shaped_calls(MODULE.read_text())
    assert hits == [], f"write/spawn/network-shaped calls in the sweep: {hits}"


def test_rail1_guard_proven_by_mutation(tmp_path):
    """A guard that cannot fail is not a guard. Add ONE write to a copy; it must be caught."""
    mutated = MODULE.read_text() + "\n\ndef _leak():\n    Path('x').write_text('y')\n"
    assert any("write_text" in h for h in _write_shaped_calls(mutated))
    mutated2 = MODULE.read_text() + "\n\ndef _leak2():\n    open('x', 'w')\n"
    assert any("open(mode='w')" in h for h in _write_shaped_calls(mutated2))
    mutated3 = MODULE.read_text() + "\nimport subprocess\n"
    assert any("import subprocess" in h for h in _write_shaped_calls(mutated3))


def _tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- fixtures
def _fixture(tmp_path: Path):
    root = tmp_path / "acct1"; state = root / "data" / "state"; state.mkdir(parents=True)
    pts = [{"date": f"2026-09-{d:02d}", "sleeve_equity": 100000.0 - d, "cash_adj": 0.0,
            "closes": {"SPY": 700 + d}, "exec": {"slippage_bps": 0.0 if d < 5 else 1.2, "te": None}}
           for d in range(1, 8)]
    (state / "sleeve_tracking.json").write_text(json.dumps({"_schema": "x", "points": pts}))
    ledger = tmp_path / "autonomy_ledger.jsonl"
    rows = [
        {"ts": "2026-09-17T08:02:33+00:00", "session": "janitor_nightly", "trigger": "nightly_schedule"},
        {"ts": "2026-09-17T18:37:08+00:00", "session": "director_pass", "trigger": "scheduled_pass"},   # miss 1
        {"ts": "2026-09-18T12:00:12+00:00", "session": "director_pass", "trigger": "scheduled_pass"},   # 07:00 CDT
        {"ts": "2026-09-17T19:00:00+00:00", "session": "director_pass", "trigger": "manual"},
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    plists = []
    for label, hour in (("com.archondex.janitor", 3), ("com.archondex.director-pass", 7)):
        p = tmp_path / f"{label}.plist"
        with p.open("wb") as fh:
            plistlib.dump({"Label": label, "StartCalendarInterval": {"Hour": hour, "Minute": 0}}, fh)
        plists.append(p)
    return root, ledger, plists


def test_rail1_run_leaves_every_byte_identical(tmp_path):
    root, ledger, plists = _fixture(tmp_path)
    before = _tree_hash(tmp_path)
    rc = sweep.main(["--root", f"acct1={root}", "--ledger", str(ledger),
                     *sum((["--plist", str(p)] for p in plists), []), "--as-of", "2026-09-18"])
    assert rc == 0
    assert _tree_hash(tmp_path) == before


# ---------------------------------------------------------------- rail 2: reuse
def test_rail2_reuses_the_registries_and_declares_no_private_channel_list():
    src = MODULE.read_text()
    assert "from paper_trader.clock_census import" in src
    for name in ("channel_liveness", "run_census", "CHANNELS"):
        assert name in src
    tree = ast.parse(src)
    private = [n.targets[0].id for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and isinstance(n.targets[0], ast.Name) and n.targets[0].id.upper() == n.targets[0].id
               and isinstance(n.value, ast.List) and n.targets[0].id.endswith("CHANNELS")]
    assert private == [], f"a private channel list would duplicate the registry: {private}"


# ---------------------------------------------------------------- rail 3: advisory
def test_rail3_findings_do_not_change_exit_code_only_unreadable_inputs_do(tmp_path, capsys):
    root, ledger, plists = _fixture(tmp_path)
    args = ["--root", f"acct1={root}", "--ledger", str(ledger),
            *sum((["--plist", str(p)] for p in plists), []), "--as-of", "2026-09-18"]
    assert sweep.main(args) == 0                       # findings present (see tests below) → still 0
    out = capsys.readouterr().out
    assert "LABEL_MISMATCH" in out and "NEVER_NONDEFAULT" in out
    assert sweep.main(["--root", f"acct1={tmp_path / 'nope'}"]) == 2
    err = capsys.readouterr()
    assert "FAIL-CLOSED" in err.err and "no table rendered" in err.err and err.out.strip() == ""


# ---------------------------------------------------------------- the two retroactive catches
def test_catches_miss1_scheduled_label_off_schedule(tmp_path):
    _, ledger, plists = _fixture(tmp_path)
    rows = sweep.check_labels(ledger, sweep._plist_schedules(plists), "America/Chicago")
    by = {(r.ts_local, r.trigger): r for r in rows}
    bad = by[("2026-09-17 13:37", "scheduled_pass")]
    assert bad.verdict == sweep.LABEL_MISMATCH and bad.delta_min > 300
    assert by[("2026-09-18 07:00", "scheduled_pass")].verdict == sweep.LABEL_OK
    assert by[("2026-09-17 03:02", "nightly_schedule")].verdict == sweep.LABEL_OK
    assert all(r.trigger != "manual" for r in rows)     # manual rows are not schedule-class


def test_catches_miss2_field_never_nondefault(tmp_path):
    root, _, _ = _fixture(tmp_path)
    rows = {(r.file, r.field): r for r in sweep.scan_fields("acct1", root)}
    ca = rows[("sleeve_tracking.json", "cash_adj")]
    assert ca.status == sweep.NEVER_NONDEFAULT and ca.n_nondefault == 0 and ca.n_points == 7
    assert ca.declared is True                          # T-352 registered it; the sweep sees that
    te = rows[("sleeve_tracking.json", "exec.te")]
    assert te.status == sweep.NEVER_NONDEFAULT and te.declared is False   # → file against the registry
    sl = rows[("sleeve_tracking.json", "exec.slippage_bps")]
    assert sl.status == sweep.LIVE and sl.first == "2026-09-05" and sl.last == "2026-09-07"


def test_cli_smoke_via_subprocess(tmp_path):
    root, ledger, plists = _fixture(tmp_path)
    r = subprocess.run([sys.executable, str(MODULE), "--root", f"acct1={root}", "--ledger", str(ledger),
                        "--plist", str(plists[0]), "--plist", str(plists[1]), "--as-of", "2026-09-18"],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("# Reviewer liveness sweep")

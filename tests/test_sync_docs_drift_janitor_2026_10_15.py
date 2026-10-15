"""The sync_docs index-drift check (the director's ruling, 2026-10-15): the ~540 lines of pre-existing
index.md drift get one unit of their own, and the nightly janitor gains a read-only `index_drift`
check so drift stops accumulating unseen. Locks, on planted directories and through the real entry
points (`render_index`, `drifted`, the `--check` CLI, `check_index_drift`):
  * rendering is PURE — it never writes;
  * drift is seen (a missing generated section; a changed docstring) and cleared by a sync;
  * `--check` exits 1 with DRIFT lines, 0 when clean — and never writes;
  * the janitor check: clean → PASS; drift → FAIL, mechanical, naming the files; a crashed checker
    → FAIL, NOT mechanical (a crash is not drift); and it is in the nightly run.
"""
from __future__ import annotations

import inspect
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import janitor_nightly as jn
from scripts import sync_docs as sd

REPO = Path(__file__).resolve().parent.parent
MARKER = "<!-- AUTO-GENERATED: DO NOT EDIT BELOW -->"


def _plant(root: Path, rel: str = "scripts", doc: str = "Adds two numbers.") -> Path:
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.md").write_text("# Hand-written top half\n\nKept verbatim.\n\n" + MARKER + "\nstale\n")
    (d / "mod.py").write_text(f'def add(a, b):\n    """{doc}"""\n    return a + b\n')
    return d


def test_render_is_PURE_and_keeps_the_hand_written_top_half(tmp_path):
    d = _plant(tmp_path)
    before = (d / "index.md").read_text()
    index_file, content = sd.render_index(d)
    assert (d / "index.md").read_text() == before, "render_index must never write"
    assert content.startswith("# Hand-written top half\n\nKept verbatim.\n\n")
    assert "### `mod.py`" in content and "Adds two numbers." in content


def test_drift_is_SEEN_cleared_by_a_sync_and_seen_again_on_a_docstring_change(tmp_path):
    d = _plant(tmp_path)
    assert sd.drifted([d]) == [str(d / "index.md")]
    sd.sync_directory(d)
    assert sd.drifted([d]) == []
    (d / "mod.py").write_text('def add(a, b):\n    """Adds two numbers, now documented."""\n    return a + b\n')
    assert sd.drifted([d]) == [str(d / "index.md")]


def test_a_directory_without_an_index_is_not_drift(tmp_path):
    d = tmp_path / "noindex"
    d.mkdir()
    (d / "m.py").write_text("x = 1\n")
    assert sd.render_index(d) is None and sd.drifted([d]) == []


def _cli(monkeypatch, cwd: Path, *args) -> int:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sync_docs.py", *args])
    with pytest.raises(SystemExit) as e:
        runpy.run_path(str(REPO / "scripts" / "sync_docs.py"), run_name="__main__")
    return e.value.code


def test_the_CHECK_cli_exits_1_with_DRIFT_lines_and_never_writes(tmp_path, monkeypatch, capsys):
    d = _plant(tmp_path)                                # tmp/scripts is one of DIRS_TO_SYNC
    before = (d / "index.md").read_text()
    assert _cli(monkeypatch, tmp_path, "--check") == 1
    out = capsys.readouterr().out
    assert "DRIFT scripts/index.md" in out and "index drift: 1 file(s)" in out
    assert (d / "index.md").read_text() == before


def test_the_CHECK_cli_exits_0_when_clean(tmp_path, monkeypatch, capsys):
    d = _plant(tmp_path)
    sd.sync_directory(d)
    assert _cli(monkeypatch, tmp_path, "--check") == 0
    assert "index drift: none" in capsys.readouterr().out


def _fake_run(rc: int, out: str = "", err: str = ""):
    return lambda cmd, **kw: subprocess.CompletedProcess(cmd, rc, out, err)


def test_the_JANITOR_check_PASS_FAIL_and_a_crash_that_is_not_drift(monkeypatch):
    monkeypatch.setattr(jn, "_run", _fake_run(0, "index drift: none\n"))
    c = jn.check_index_drift()
    assert c.name == "index_drift" and c.status == "PASS"
    monkeypatch.setattr(jn, "_run", _fake_run(1, "DRIFT scripts/index.md\nDRIFT orchestration/index.md\n"
                                                 "index drift: 2 file(s)\n"))
    c = jn.check_index_drift()
    assert c.status == "FAIL" and c.mechanical is True
    assert "scripts/index.md" in c.detail and "orchestration/index.md" in c.detail
    monkeypatch.setattr(jn, "_run", _fake_run(1, "", "Traceback ...\nSyntaxError: bad\n"))
    c = jn.check_index_drift()
    assert c.status == "FAIL" and c.mechanical is False and "SyntaxError" in c.detail


def test_the_JANITOR_runs_the_check_with_the_REAL_cli(monkeypatch):
    seen = []

    def _rec(cmd, **kw):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "index drift: none\n", "")
    monkeypatch.setattr(jn, "_run", _rec)
    jn.check_index_drift()
    assert seen and seen[0][1:] == ["scripts/sync_docs.py", "--check"]
    assert "check_index_drift()" in inspect.getsource(jn.run_checks)

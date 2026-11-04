"""tests/conftest.py's data/ write guard — reversion-proven where it runs.

THE DEFECT (2026-10-22): run in a clean worktree the suite created real directories and files
under data/, and through a worktree's data/processed and data/raw symlinks it wrote INTO the
pinned canonical cache (a fundamentals parquet; the six raw SimFin files; the pinned panel).
The guard fails the session (exit status 1, never a warning) for any path created under
<repo>/data and names the test by nodeid.

Each case runs a real pytest subprocess on a throwaway layout — a copy of the LIVE conftest
beside a planted writer — so the proof is of the conftest as shipped, not of a re-statement
of it. The reversion arm runs the same planted writer with NO conftest and must be green:
the failure is the guard's doing and nothing else's.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LIVE_CONFTEST = REPO / "tests" / "conftest.py"

PLANTED = '''
from pathlib import Path
DATA = Path(__file__).resolve().parents[1] / "data"

def test_plant_writes_under_data():
    p = DATA / "planted" / "x.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")

def test_clean():
    assert True
'''

IMPORT_TIME_WRITER = '''
from pathlib import Path
DATA = Path(__file__).resolve().parents[1] / "data"
(DATA / "governor").mkdir(parents=True, exist_ok=True)
(DATA / "governor" / "edges.yml").write_text("edges: []\\n")

def test_clean():
    assert True
'''

IMPORT_TIME_WRITER_ELSEWHERE = IMPORT_TIME_WRITER.replace('"governor"', '"intel"').replace(
    '"edges.yml"', '"panel.parquet"')


@pytest.fixture
def layout(tmp_path):
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                           "-p", "no:randomly", *args],
                          cwd=root, env=env, capture_output=True, text=True, timeout=180)


def test_without_the_guard_the_planted_writer_is_green(layout):
    """Reversion arm: no conftest -> the writer passes. Whatever fails it below is the guard."""
    (layout / "tests" / "test_plant.py").write_text(PLANTED)
    r = _run(layout)
    assert r.returncode == 0 and "2 passed" in r.stdout, (r.stdout + r.stderr)[-2000:]
    assert (layout / "data" / "planted" / "x.txt").exists()


def test_with_the_live_conftest_the_writer_fails_the_session_and_is_named(layout):
    shutil.copy(LIVE_CONFTEST, layout / "tests" / "conftest.py")
    (layout / "tests" / "test_plant.py").write_text(PLANTED)
    r = _run(layout)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-2000:]
    assert "2 passed" in r.stdout, "the guard fails the SESSION; the tests themselves still ran"
    assert "data/ write guard: FAILED" in out
    assert "tests/test_plant.py::test_plant_writes_under_data" in out
    assert "data/planted/x.txt" in out
    assert "test_clean" not in out.split("data/ write guard: FAILED")[1], "the clean test is not blamed"


def test_with_the_live_conftest_a_clean_suite_is_green(layout):
    """Negative control: the guard raises nothing on a suite that writes nothing."""
    shutil.copy(LIVE_CONFTEST, layout / "tests" / "conftest.py")
    (layout / "tests" / "test_plant.py").write_text(PLANTED)
    r = _run(layout, "-k", "test_clean")
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    assert "data/ write guard" not in r.stdout + r.stderr


def test_import_time_writes_are_attributed_to_collection_and_fail(layout):
    shutil.copy(LIVE_CONFTEST, layout / "tests" / "conftest.py")
    (layout / "tests" / "test_importer.py").write_text(IMPORT_TIME_WRITER_ELSEWHERE)
    r = _run(layout)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-2000:]
    assert "<collection/import time>" in out and "data/intel/panel.parquet" in out


def test_an_import_time_edges_yml_write_fails_the_session_at_collection(layout):
    """No allowance for data/governor/edges.yml at IMPORT any more. Until the edges.yml
    single-writer unit (2026-10-22) every edge module's import-time `EdgeRegistry().ensure()`
    wrote that file, and the guard tolerated it at collection time only; `ensure()` now records in
    memory and never writes (proven at the merge, 2026-11-04: collecting the whole suite on a tree
    with no data/ created nothing), so an import-time write of the file fails like any other."""
    shutil.copy(LIVE_CONFTEST, layout / "tests" / "conftest.py")
    (layout / "tests" / "test_importer.py").write_text(IMPORT_TIME_WRITER)
    r = _run(layout)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-2000:]
    assert "<collection/import time>" in out and "data/governor/edges.yml" in out
    assert "tolerated" not in out


def test_a_test_that_writes_edges_yml_fails_the_session(layout):
    shutil.copy(LIVE_CONFTEST, layout / "tests" / "conftest.py")
    (layout / "tests" / "test_plant.py").write_text(
        PLANTED.replace('"planted" / "x.txt"', '"governor" / "edges.yml"'))
    r = _run(layout)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-2000:]
    assert "tests/test_plant.py::test_plant_writes_under_data" in out
    assert "data/governor/edges.yml" in out

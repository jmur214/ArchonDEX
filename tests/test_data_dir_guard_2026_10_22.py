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


# ── 2026-11-04: MODIFIED, REMOVED and create-then-unlink (review of the 2026-10-22 unit) ──────
# The first guard caught only CREATED paths. Review proved by planted probes that an in-place
# replacement (os.replace; DataFrame.to_parquet over an existing path — the incident's own
# shape), a deletion and a create-then-unlink inside one test all passed unreported. Each case
# below SEEDS the layout with baseline files before pytest starts, so they are in the guard's
# baseline walk, and plants one writer per shape. Attribution is asserted per nodeid from the
# summary table: the rename and the deletion are caught by the per-test directory poll; the
# in-place rewrites move no directory mtime and are attributed at session end by the file's
# ctime against the test's recorded window; the create-then-unlink leaves a directory whose
# mtime moved with an unchanged listing (TRANSIENT).
# Review findings applied at the merge onto main (2026-11-04): a same-size rewrite that RESTORES
# its mtime (os.utime after the write) differs from the baseline only in ctime, so the guard
# compares the full (size, mtime_ns, ctime_ns) triple — the reversion arm proves the planted
# writer leaves size and mtime equal and moves ctime alone, so only the triple can catch it; and
# a SESSION-fixture teardown write is attributed to the LAST test, never unattributed, because
# pytest tears session fixtures down inside the last item's runtest protocol.

SEEDED = {
    "data/processed/existing_1d.csv": "a,b\n1,2\n",
    "data/processed/other_1d.csv": "a,b\n3,4\n",
    "data/processed/doomed_1d.csv": "a,b\n5,6\n",
    "data/processed/restored_1d.csv": "a,b\n3,3\n",
    "data/governor/edges.yml": "edges: [seeded]\n",
}

WRITERS = '''
import os
from pathlib import Path
import pandas as pd
DATA = Path(__file__).resolve().parents[1] / "data"

def test_plant_replaces_by_rename():
    tmp = DATA / "processed" / "existing_1d.csv.tmp"
    tmp.write_text("a,b\\n9,9\\n")
    os.replace(tmp, DATA / "processed" / "existing_1d.csv")

def test_plant_rewrites_in_place_same_size():
    (DATA / "processed" / "other_1d.csv").write_text("a,b\\n7,7\\n")

def test_plant_to_parquet_over_the_pinned_panel():
    pd.DataFrame({"a": [2]}).to_parquet(DATA / "processed" / "parquet" / "pinned.parquet")

def test_plant_deletes():
    (DATA / "processed" / "doomed_1d.csv").unlink()

def test_plant_creates_then_unlinks():
    p = DATA / "processed" / "scratch.tmp"
    p.write_text("x")
    p.unlink()

def test_plant_rewrites_same_size_and_restores_mtime():
    p = DATA / "processed" / "restored_1d.csv"
    st = p.stat()
    p.write_text("a,b\\n8,8\\n")
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))

def test_clean():
    assert True
'''

SESSION_TEARDOWN_WRITER = '''
from pathlib import Path
import pytest
DATA = Path(__file__).resolve().parents[1] / "data"

@pytest.fixture(scope="session", autouse=True)
def _session_scoped():
    yield
    (DATA / "processed" / "existing_1d.csv").write_text("a,b\\n0,0\\n")

def test_first():
    assert True

def test_last():
    assert True
'''

EDGES_YML_REWRITER = '''
from pathlib import Path
DATA = Path(__file__).resolve().parents[1] / "data"

def test_plant_rewrites_edges_yml():
    (DATA / "governor" / "edges.yml").write_text("edges: []\\n")

def test_clean():
    assert True
'''


@pytest.fixture
def seeded(layout):
    """The throwaway layout with BASELINE files under data/ (present before pytest starts)."""
    import pandas as pd
    for rel, text in SEEDED.items():
        p = layout / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    pq = layout / "data" / "processed" / "parquet" / "pinned.parquet"
    pq.parent.mkdir(parents=True)
    pd.DataFrame({"a": [1]}).to_parquet(pq)
    return layout


def _table(out: str) -> dict:
    """The FAILED section of the terminal summary as {nodeid: [entry lines]}."""
    body = out.split("data/ write guard: FAILED", 1)[1]
    table, node = {}, None
    for line in body.splitlines()[1:]:
        if line.startswith("      "):
            table.setdefault(node, []).append(line.strip())
        elif line.startswith("  ") and not line.startswith("   "):
            node = line.strip()
            table.setdefault(node, [])
        elif line.startswith(("=", "-")):
            break
    return table


def test_without_the_guard_every_planted_writer_is_green(seeded):
    """Reversion arm: no conftest -> all seven pass and the files show the writes landed. The
    mtime-restoring writer's INPUT CONDITION is proven here: size and mtime_ns equal the seeded
    file's, ctime_ns moved — the shape only the full triple can catch."""
    restored = seeded / "data/processed/restored_1d.csv"
    before = restored.stat()
    (seeded / "tests" / "test_plant.py").write_text(WRITERS)
    r = _run(seeded)
    assert r.returncode == 0 and "7 passed" in r.stdout, (r.stdout + r.stderr)[-2000:]
    assert (seeded / "data/processed/existing_1d.csv").read_text() == "a,b\n9,9\n"
    assert (seeded / "data/processed/other_1d.csv").read_text() == "a,b\n7,7\n"
    assert not (seeded / "data/processed/doomed_1d.csv").exists()
    after = restored.stat()
    assert restored.read_text() == "a,b\n8,8\n"
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns), \
        "the planted writer must leave size and mtime exactly as seeded"
    assert after.st_ctime_ns != before.st_ctime_ns, "only ctime moved"


def test_with_the_live_conftest_every_planted_shape_fails_the_session_and_is_named(seeded):
    shutil.copy(LIVE_CONFTEST, seeded / "tests" / "conftest.py")
    (seeded / "tests" / "test_plant.py").write_text(WRITERS)
    r = _run(seeded)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-3000:]
    assert "7 passed" in r.stdout, "the guard fails the SESSION; the tests themselves still ran"
    assert "data/ write guard: FAILED" in out, out[-3000:]
    t = _table(out)
    P = "tests/test_plant.py::"
    assert any(e.startswith("MODIFIED") and "data/processed/existing_1d.csv" in e
               for e in t.get(P + "test_plant_replaces_by_rename", [])), t
    assert any(e.startswith("MODIFIED") and "data/processed/restored_1d.csv" in e
               for e in t.get(P + "test_plant_rewrites_same_size_and_restores_mtime", [])), t
    assert any(e.startswith("MODIFIED") and "data/processed/other_1d.csv" in e
               for e in t.get(P + "test_plant_rewrites_in_place_same_size", [])), t
    assert any(e.startswith("MODIFIED") and "data/processed/parquet/pinned.parquet" in e
               for e in t.get(P + "test_plant_to_parquet_over_the_pinned_panel", [])), t
    assert any(e.startswith("REMOVED") and "data/processed/doomed_1d.csv" in e
               for e in t.get(P + "test_plant_deletes", [])), t
    assert any(e.startswith("TRANSIENT") and "data/processed/" in e
               for e in t.get(P + "test_plant_creates_then_unlinks", [])), t
    assert P + "test_clean" not in t, "the clean test is not blamed"
    assert not any("unattributed" in n for n in t), f"every write is attributed to its test: {t}"


def test_a_session_fixture_teardown_write_is_attributed_to_the_last_test(seeded):
    """pytest tears session fixtures down inside the LAST item's runtest protocol
    (`pytest_runtest_teardown(item, nextitem=None)` -> `teardown_exact(None)`), so the window the
    guard records for the last test holds the teardown write: it is MODIFIED by `test_last`,
    never unattributed, and `test_first` is not blamed."""
    shutil.copy(LIVE_CONFTEST, seeded / "tests" / "conftest.py")
    (seeded / "tests" / "test_plant.py").write_text(SESSION_TEARDOWN_WRITER)
    r = _run(seeded)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-3000:]
    assert "2 passed" in r.stdout
    t = _table(out)
    P = "tests/test_plant.py::"
    assert any(e.startswith("MODIFIED") and "data/processed/existing_1d.csv" in e
               for e in t.get(P + "test_last", [])), t
    assert P + "test_first" not in t, t
    assert not any("unattributed" in n for n in t), t


def test_a_pre_existing_edges_yml_rewritten_in_place_at_collection_fails_and_is_named(seeded):
    """The main tree's OLD shape: edges.yml EXISTS and an import-time writer rewrites it in
    place. No allowance covers it any more (the single-writer unit retired the import-time
    EdgeRegistry writer; imports never write): the rewrite moves no directory mtime, so it is
    found by the session-end stat diff, attributed by the file's ctime to the collection window,
    and FAILS the session like any other write."""
    shutil.copy(LIVE_CONFTEST, seeded / "tests" / "conftest.py")
    (seeded / "tests" / "test_importer.py").write_text(IMPORT_TIME_WRITER)
    r = _run(seeded)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-3000:]
    assert "data/ write guard: FAILED" in out, out[-3000:]
    assert "tolerated" not in out
    t = _table(out)
    assert any(e.startswith("MODIFIED") and "data/governor/edges.yml" in e
               for e in t.get("<collection/import time>", [])), t
    assert "tests/test_importer.py::test_clean" not in t, "the clean test is not blamed"


def test_a_test_that_rewrites_edges_yml_in_place_fails_the_session(seeded):
    shutil.copy(LIVE_CONFTEST, seeded / "tests" / "conftest.py")
    (seeded / "tests" / "test_plant.py").write_text(EDGES_YML_REWRITER)
    r = _run(seeded)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-3000:]
    t = _table(out)
    assert any(e.startswith("MODIFIED") and "data/governor/edges.yml" in e
               for e in t.get("tests/test_plant.py::test_plant_rewrites_edges_yml", [])), t
    assert "tests/test_plant.py::test_clean" not in t


def test_with_the_live_conftest_a_seeded_layout_left_alone_is_green(seeded):
    """Negative control for the extension: baseline files that nobody touches raise nothing."""
    shutil.copy(LIVE_CONFTEST, seeded / "tests" / "conftest.py")
    (seeded / "tests" / "test_plant.py").write_text(WRITERS)
    r = _run(seeded, "-k", "test_clean")
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    assert "data/ write guard" not in r.stdout + r.stderr

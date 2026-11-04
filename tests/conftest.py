"""Suite-wide hermeticity: no test may run with the real .env's secrets in its environment.

THE DEFECT THIS CLOSES (#156 hang, root-caused 2026-10-15). `engines/data_manager/
data_manager.py` calls `load_dotenv(<repo>/.env, override=True)` at IMPORT. Collection
imports every test module before the first test runs, so in the main tree — the only
tree holding a .env — every key was in `os.environ` for the whole session.
`paper_trader/intel_pulse.py` goes LIVE when `ANTHROPIC_API_KEY` is present, so the
pulse test made a real provider call on the user's key and hung on the network. Other
trees have no .env, which is why the hang never reproduced there.

The fixture removes, before EVERY test, each variable NAMED in the repo's .env. Only
names are read (`dotenv_values(...).keys()`); values are never kept or printed. Where
there is no .env (worktrees, CI, the janitor's runner) it does nothing.

This is the guard around the TEST. The import-time `load_dotenv` itself, and a refusal
at the provider call site under pytest, are propose-first changes to engine and live
code, briefed separately.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_DOTENV = Path(__file__).resolve().parent.parent / ".env"


def _env_key_names(path: Path = _DOTENV) -> frozenset:
    """The variable NAMES a .env file defines — never its values."""
    if not path.exists():
        return frozenset()
    from dotenv import dotenv_values
    return frozenset(dotenv_values(path).keys())


_SECRET_NAMES = _env_key_names()


@pytest.fixture(autouse=True)
def _no_real_secrets(monkeypatch):
    """Strip every .env-defined variable from the environment for the test's duration."""
    for name in _SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


# ---------------------------------------------------------------------------
# data/ write guard (2026-10-22). THE DEFECT: run in a clean worktree, the suite CREATED
# data/{processed,macro,research,raw,governor,intel,earnings,state}, and where data/processed
# and data/raw were symlinks into the pinned canonical cache the suite wrote INTO it: one test's
# fundamentals fetch landed parquet/AAPL_fundamentals.parquet; a panel fixture's rebuild let the
# simfin library REFRESH the six pinned raw files and then rewrote the pinned panel. A test that
# writes into the data layer is a hygiene defect: tests touching DataManager / foundry / governor
# paths STUB the data layer (tmp_path caches, stubbed providers). This guard is [NN-FAIL-CLOSED]
# applied to the suite: any path created under <repo>/data during the session FAILS the session
# (exit status 1, never a warning) and is attributed to the test whose runtest protocol created
# it (timing attribution: whatever ran while the path appeared) or to collection/import time.
#
# Mechanism, chosen for cost in the main tree (data/ holds ~32k files in ~2.7k dirs):
#   sessionstart       one full walk -> the baseline set of paths + every dir's mtime_ns;
#   each test          stat every known dir (~15 ms for 2.7k dirs); a dir whose mtime moved
#                      is re-listed and its entries not in the baseline are the test's writes
#                      (a NEW dir is walked whole); the stat set grows with new dirs;
#   collection_finish  the same poll, attributed to "<collection/import time>";
#   sessionfinish      one full walk vs the baseline (catches native writers that touched a
#                      dir the poll missed, and session-fixture teardown) -> exit status 1.
# Top-level data/ symlinks ARE followed: in agent worktrees data/processed and data/raw point
# into main's canonical cache, and a write through the link is exactly the defect.
#
# Reversion-proven by tests/test_data_dir_guard_2026_10_22.py (a planted writer fails under
# the live conftest, by nodeid and path, and passes without it).
# ---------------------------------------------------------------------------
import os as _os

_REPO = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO / "data"
_COLLECTION_NODEID = "<collection/import time>"
_UNATTRIBUTED_NODEID = "<unattributed: session-fixture teardown or after the last test>"
# NO collection-time allowance. Until the edges.yml single-writer unit (2026-10-22) every edge
# module's import-time `EdgeRegistry().ensure()` wrote data/governor/edges.yml, so merely
# COLLECTING the suite created data/, data/governor/ and the file, and those three paths were
# tolerated at collection time only. `ensure()` now records in memory and never writes — proven
# at the merge (2026-11-04): collecting the whole suite (4553 tests) on a tree with NO data/
# created nothing. A path created at collection is attributed to _COLLECTION_NODEID and fails
# the session like any other.


class _DataDirGuardState:
    def __init__(self) -> None:
        self.armed = False
        self.baseline: set[str] = set()
        self.dir_mtimes: dict[str, int] = {}
        self.attributed: dict[str, list[str]] = {}   # nodeid -> created paths (ordered)
        self.seen: set[str] = set()                   # every created path already attributed
        self.final_new: list[str] = []
        self.failed = False


_GUARD = _DataDirGuardState()


def _rel(p: str) -> str:
    return _os.path.relpath(p, _REPO)


def _walk_data() -> tuple[set[str], dict[str, int]]:
    """Every path under data/ (dirs end with '/') and every dir's mtime_ns. Follows the
    top-level symlinks an agent worktree holds; a realpath set stops cycles."""
    paths: set[str] = set()
    mtimes: dict[str, int] = {}
    if not _DATA_DIR.exists():
        return paths, mtimes
    seen_real: set[str] = set()
    for dp, dns, fns in _os.walk(_DATA_DIR, followlinks=True):
        real = _os.path.realpath(dp)
        if real in seen_real:
            dns[:] = []
            continue
        seen_real.add(real)
        rel_d = _rel(dp) + "/"
        paths.add(rel_d)
        try:
            mtimes[rel_d] = _os.stat(dp).st_mtime_ns
        except OSError:
            mtimes[rel_d] = -1
        for f in fns:
            paths.add(_os.path.join(_rel(dp), f))
    return paths, mtimes


def _poll_data_dir() -> list[str]:
    """Cheap per-test check: stat every known dir; re-list the ones whose mtime moved; return
    the paths that exist now but did not at baseline and were not attributed before."""
    g = _GUARD
    new: list[str] = []
    probe = dict(g.dir_mtimes)
    if "data/" not in probe:
        probe["data/"] = -1          # data/ absent at baseline: watch for its appearance
    for rel_d, old in probe.items():
        abs_d = _REPO / rel_d
        try:
            now = _os.stat(abs_d).st_mtime_ns
        except OSError:
            g.dir_mtimes.pop(rel_d, None)
            continue
        if now == old:
            continue
        g.dir_mtimes[rel_d] = now
        if rel_d not in g.baseline and rel_d not in g.seen:
            g.seen.add(rel_d)          # the probed dir itself appeared (data/ in a tree without one)
            new.append(rel_d)
        try:
            entries = list(_os.scandir(abs_d))
        except OSError:
            continue
        for e in entries:
            is_dir = e.is_dir()
            rel_e = _rel(e.path) + ("/" if is_dir else "")
            if rel_e in g.baseline or rel_e in g.seen:
                continue
            if is_dir:
                for dp, dns, fns in _os.walk(e.path, followlinks=True):
                    rd = _rel(dp) + "/"
                    g.dir_mtimes.setdefault(rd, _os.stat(dp).st_mtime_ns)
                    for q in [rd] + [_os.path.join(_rel(dp), f) for f in fns]:
                        if q not in g.baseline and q not in g.seen:
                            g.seen.add(q)
                            new.append(q)
            else:
                g.seen.add(rel_e)
                new.append(rel_e)
    return sorted(new)


def _record(nodeid: str, created: list[str]) -> None:
    if created:
        _GUARD.attributed.setdefault(nodeid, []).extend(created)


def pytest_sessionstart(session):
    _GUARD.baseline, _GUARD.dir_mtimes = _walk_data()
    _GUARD.armed = True


def pytest_collection_finish(session):
    if _GUARD.armed:
        _record(_COLLECTION_NODEID, _poll_data_dir())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    yield
    if not _GUARD.armed:
        return
    created = _poll_data_dir()
    if created:
        _record(item.nodeid, created)
        tr = item.config.pluginmanager.get_plugin("terminalreporter")
        if tr is not None:
            tr.write_line(f"\n[data-guard] {item.nodeid} created under data/: {created}", red=True)


def _offending() -> dict[str, list[str]]:
    """The attributed table: every nodeid (collection time included) with the paths it created."""
    return {nodeid: paths for nodeid, paths in _GUARD.attributed.items() if paths}


def pytest_sessionfinish(session, exitstatus):
    if not _GUARD.armed:
        return
    final, _ = _walk_data()
    _GUARD.final_new = sorted(final - _GUARD.baseline)
    leftover = [p for p in _GUARD.final_new if p not in _GUARD.seen]
    _record(_UNATTRIBUTED_NODEID, leftover)
    if _offending():
        _GUARD.failed = True
        if session.exitstatus == 0:
            session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _GUARD.armed:
        return
    offending = _offending()
    if not offending:
        return
    tr = terminalreporter
    tr.section("data/ write guard: FAILED — the suite created paths under data/", sep="=", red=True)
    tr.write_line("A test that writes into the data layer must stub it (tmp_path cache dirs, a "
                  "stubbed provider, a monkeypatched DataManager cache root). Session exit status "
                  "forced to 1 ([NN-FAIL-CLOSED]).")
    for nodeid, paths in offending.items():
        tr.write_line(f"  {nodeid}")
        for p in paths:
            tr.write_line(f"      {p}")

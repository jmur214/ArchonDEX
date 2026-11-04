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
# data/ write guard (2026-10-22; MODIFIED and REMOVED paths added 2026-11-04). THE DEFECT: run
# in a clean worktree, the suite CREATED data/{processed,macro,research,raw,governor,intel,
# earnings,state}, and where data/processed and data/raw were symlinks into the pinned canonical
# cache the suite wrote INTO it: one test's fundamentals fetch landed parquet/AAPL_fundamentals.
# parquet; a panel fixture's rebuild let the simfin library REFRESH the six pinned raw files and
# then rewrote the pinned panel. The first guard caught only CREATED paths; the incident itself
# was a REPLACEMENT (the library's download over the pinned raw files, to_parquet over the
# pinned panel), and review proved by planted probes that an in-place replacement, a deletion
# and a create-then-unlink inside one test all passed unreported. A test that writes into the
# data layer is a hygiene defect: tests touching DataManager / foundry / governor paths STUB the
# data layer (tmp_path caches, stubbed providers). This guard is [NN-FAIL-CLOSED] applied to the
# suite: any path CREATED, MODIFIED or REMOVED under <repo>/data during the session FAILS the
# session (exit status 1, never a warning) and is attributed to a test by nodeid.
#
# Mechanism, chosen for cost in the main tree (data/ holds ~32k files in ~2.7k dirs; one stat
# per path is ~0.2 s, so a per-test stat of every FILE — ~0.14 s x ~4.4k tests, ~10 min — is not
# acceptable; a per-test stat of every DIR is ~15 ms and stays):
#   sessionstart       one full walk, ONE stat per path -> every file's (size, mtime_ns), every
#                      dir's mtime_ns and its listing;
#   each test          stat every known dir; a dir whose mtime moved is re-listed against its
#                      known listing: a new entry is CREATED (a new dir is walked whole), a
#                      missing baseline entry is REMOVED (with everything beneath it), a baseline
#                      file whose (size, mtime_ns) changed is MODIFIED (the rename-over shape:
#                      os.replace, a temp file renamed onto the target), and a dir whose mtime
#                      moved while its listing and every baseline entry's stat are unchanged is
#                      TRANSIENT — something was created and removed inside it during the test;
#   collection_finish  the same poll, attributed to "<collection/import time>";
#   sessionfinish      one full walk vs the baseline. An IN-PLACE rewrite of a baseline file
#                      (open(path, "w"), DataFrame.to_parquet over an existing path: the
#                      incident's shape) moves no dir mtime, so the per-test poll cannot see it;
#                      it is found here by the stat diff and ATTRIBUTED BY TIMESTAMP: the file's
#                      ctime_ns (set by the kernel on every change; user code cannot set it,
#                      unlike mtime) is matched against each test's recorded protocol window
#                      [start_ns, end_ns] (time.time_ns(), the same CLOCK_REALTIME the
#                      filesystem stamps with; nanosecond on APFS/ext4). A path whose ctime
#                      falls in no window (session-fixture teardown after the last test) is
#                      reported unattributed. The LAST writer is the one named.
# Top-level data/ symlinks ARE followed: in agent worktrees data/processed and data/raw point
# into main's canonical cache, and a write through the link is exactly the defect. A per-file
# symlink is stat'ed through to its target, so an in-place write through it is MODIFIED, and
# replacing the link itself with a real file is MODIFIED too (the new inode's stat differs).
#
# Reversion-proven by tests/test_data_dir_guard_2026_10_22.py (planted writers of every shape
# fail under the live conftest, named by nodeid and path, and pass without it).
# ---------------------------------------------------------------------------
import bisect as _bisect
import os as _os
import time as _time

_REPO = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO / "data"
_COLLECTION_NODEID = "<collection/import time>"
_UNATTRIBUTED_NODEID = ("<unattributed: changed outside every test's window — session-fixture "
                        "teardown after the last test, or a copy that preserved its timestamps>")
# NO collection-time allowance. Until the edges.yml single-writer unit (2026-10-22) every edge
# module's import-time `EdgeRegistry().ensure()` wrote data/governor/edges.yml, so merely
# COLLECTING the suite created data/, data/governor/ and the file (or REWROTE it in place in the
# main tree), and those three paths were tolerated at collection time only. `ensure()` now records
# in memory and never writes — proven at the merge (2026-11-04): collecting the whole suite (4553
# tests) on a tree with NO data/ created nothing. A path created, modified or removed at
# collection is attributed to _COLLECTION_NODEID and fails the session like any other.
_CREATED, _MODIFIED, _REMOVED, _TRANSIENT = "CREATED", "MODIFIED", "REMOVED", "TRANSIENT"
_MISSING = (-1, -1, -1)      # a path the walk could not stat (a dangling symlink)


class _DataDirGuardState:
    def __init__(self) -> None:
        self.armed = False
        self.baseline: dict[str, tuple | None] = {}       # path -> (size, mtime_ns, ctime_ns); None = dir
        self.listing: dict[str, set[str]] = {}            # known dir -> its entries as last seen
        self.dir_mtimes: dict[str, int] = {}
        self.attributed: dict[str, list[tuple[str, str, str]]] = {}   # nodeid -> [(kind, path, note)]
        self.seen: set[str] = set()                       # every path already reported
        self.windows: list[tuple[int, int, str]] = []     # (start_ns, end_ns, nodeid), in run order
        self.started_ns = 0
        self.baseline_walk_seconds = 0.0
        self.failed = False


_GUARD = _DataDirGuardState()


def _rel(p: str) -> str:
    return _os.path.relpath(p, _REPO)


def _sig(abs_path: str) -> tuple:
    """ONE stat: (size, mtime_ns, ctime_ns) through a symlink to its target."""
    try:
        st = _os.stat(abs_path)
    except OSError:
        return _MISSING
    return (st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _walk_subtree(abs_root: str, seen_real: set[str]):
    """Yield (rel_dir_with_slash, dir_mtime_ns, {entry: sig-or-None}) for every dir under
    abs_root, the root included. Follows symlinks; a realpath set stops cycles."""
    for dp, dns, fns in _os.walk(abs_root, followlinks=True):
        real = _os.path.realpath(dp)
        if real in seen_real:
            dns[:] = []
            continue
        seen_real.add(real)
        rel = _rel(dp)
        try:
            mtime = _os.stat(dp).st_mtime_ns
        except OSError:
            mtime = -1
        entries: dict[str, tuple | None] = {}
        for d in dns:
            entries[_os.path.join(rel, d) + "/"] = None
        for f in fns:
            entries[_os.path.join(rel, f)] = _sig(_os.path.join(dp, f))
        yield rel + "/", mtime, entries


def _walk_data() -> tuple[dict[str, tuple | None], dict[str, int], dict[str, set[str]]]:
    """Every path under data/ with one stat each: files -> (size, mtime_ns, ctime_ns), dirs ->
    None; every dir's mtime_ns; every dir's listing."""
    paths: dict[str, tuple | None] = {}
    mtimes: dict[str, int] = {}
    listing: dict[str, set[str]] = {}
    if not _DATA_DIR.exists():
        return paths, mtimes, listing
    for rel_d, mtime, entries in _walk_subtree(str(_DATA_DIR), set()):
        paths[rel_d] = None
        mtimes[rel_d] = mtime
        listing[rel_d] = set(entries)
        paths.update(entries)
    return paths, mtimes, listing


def _removed_under(rel: str) -> list[tuple[str, str, str]]:
    """A baseline path vanished: report it once; a dir takes everything beneath it with it."""
    g = _GUARD
    if rel in g.seen:
        return []
    g.seen.add(rel)
    beneath = 0
    if rel.endswith("/"):
        for p in g.baseline:
            if p != rel and p.startswith(rel) and p not in g.seen:
                g.seen.add(p)
                beneath += 1
    return [(_REMOVED, rel, f"(and {beneath} baseline paths beneath it)" if beneath else "")]


def _created_subtree(abs_dir: str) -> list[tuple[str, str, str]]:
    """A new dir appeared: walk it whole, register its dirs for later polls, report every path."""
    g = _GUARD
    found = []
    for rel_d, mtime, entries in _walk_subtree(abs_dir, set()):
        g.dir_mtimes.setdefault(rel_d, mtime)
        g.listing[rel_d] = set(entries)
        for q in [rel_d] + list(entries):
            if q not in g.baseline and q not in g.seen:
                g.seen.add(q)
                found.append((_CREATED, q, ""))
    return found


def _poll_data_dir(current: str) -> list[tuple[str, str, str, str]]:
    """Cheap per-test check: stat every known dir; re-list the ones whose mtime moved. Returns
    (kind, path, note, nodeid): a new or vanished entry belongs to `current` (only a write inside
    this test moved the dir's mtime); a baseline FILE whose stat changed is attributed by its
    ctime window instead — a re-listed dir also exposes an EARLIER test's in-place rewrite of a
    file in it, which must not be blamed on the test that happened to move the dir."""
    g = _GUARD
    found: list[tuple[str, str, str, str]] = []
    probe = dict(g.dir_mtimes)
    if "data/" not in probe:
        probe["data/"] = -1          # data/ absent at baseline: watch for its appearance
    for rel_d, old in probe.items():
        abs_d = _REPO / rel_d
        try:
            now = _os.stat(abs_d).st_mtime_ns
        except OSError:
            g.dir_mtimes.pop(rel_d, None)
            g.listing.pop(rel_d, None)
            if rel_d in g.baseline:
                found += [(*f, current) for f in _removed_under(rel_d)]
            continue
        if now == old:
            continue
        g.dir_mtimes[rel_d] = now
        if rel_d not in g.baseline and rel_d not in g.seen:
            g.seen.add(rel_d)          # the probed dir itself appeared (data/ in a tree without one)
            found.append((_CREATED, rel_d, "", current))
        try:
            entries = list(_os.scandir(abs_d))
        except OSError:
            continue
        known = g.listing.get(rel_d, set())
        present: set[str] = set()
        changed_here = False
        for e in entries:
            is_dir = e.is_dir()
            rel_e = _rel(e.path) + ("/" if is_dir else "")
            present.add(rel_e)
            if rel_e in known:
                base = g.baseline.get(rel_e)
                if base is not None and rel_e not in g.seen:
                    sig = _sig(e.path)
                    if sig[:2] != base[:2]:
                        g.seen.add(rel_e)
                        owner = _attribute(sig[2])
                        found.append((_MODIFIED, rel_e, "(attributed by the file's ctime)", owner))
                        changed_here = changed_here or owner == current
                continue
            changed_here = True
            if is_dir:
                found += [(*f, current) for f in _created_subtree(e.path)]
            elif rel_e not in g.seen:
                g.seen.add(rel_e)
                found.append((_CREATED, rel_e, "", current))
        for rel_e in known - present:
            changed_here = True
            if rel_e in g.baseline:
                found += [(*f, current) for f in _removed_under(rel_e)]
            g.dir_mtimes.pop(rel_e, None)
            g.listing.pop(rel_e, None)
        g.listing[rel_d] = present
        if not changed_here and rel_d in g.baseline:
            found.append((_TRANSIENT, rel_d,
                          "(its mtime moved while its listing and every baseline entry's stat are "
                          "unchanged: an entry was created and removed inside the test)", current))
    return found


def _record(nodeid: str, found: list[tuple[str, str, str]]) -> None:
    if found:
        _GUARD.attributed.setdefault(nodeid, []).extend(found)


def _record_found(found: list[tuple[str, str, str, str]]) -> None:
    for kind, path, note, nodeid in found:
        _record(nodeid, [(kind, path, note)])


def _attribute(ctime_ns: int | None) -> str:
    """The nodeid whose protocol window holds this ctime; the unattributed bucket otherwise."""
    g = _GUARD
    if ctime_ns is None or ctime_ns < 0 or not g.windows:
        return _UNATTRIBUTED_NODEID
    starts = [w[0] for w in g.windows]
    i = _bisect.bisect_right(starts, ctime_ns) - 1
    if i >= 0 and g.windows[i][0] <= ctime_ns <= g.windows[i][1]:
        return g.windows[i][2]
    return _UNATTRIBUTED_NODEID


def pytest_sessionstart(session):
    g = _GUARD
    g.started_ns = _time.time_ns()
    t0 = _time.perf_counter()
    g.baseline, g.dir_mtimes, g.listing = _walk_data()
    g.baseline_walk_seconds = _time.perf_counter() - t0
    g.armed = True


def pytest_collection_finish(session):
    g = _GUARD
    if g.armed:
        g.windows.append((g.started_ns, _time.time_ns(), _COLLECTION_NODEID))
        _record_found(_poll_data_dir(_COLLECTION_NODEID))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    t0 = _time.time_ns()
    yield
    if not _GUARD.armed:
        return
    _GUARD.windows.append((t0, _time.time_ns(), item.nodeid))
    found = _poll_data_dir(item.nodeid)
    if found:
        _record_found(found)
        tr = item.config.pluginmanager.get_plugin("terminalreporter")
        if tr is not None:
            tr.write_line(f"\n[data-guard] {item.nodeid}: "
                          + ", ".join(f"{kind} {path}" + ("" if who == item.nodeid else f" (by {who})")
                                      for kind, path, _, who in found), red=True)


def pytest_sessionfinish(session, exitstatus):
    g = _GUARD
    if not g.armed:
        return
    final, _, _ = _walk_data()
    for p, sig in final.items():
        if p in g.seen:
            continue
        base = g.baseline.get(p, _MISSING) if p in g.baseline else None
        if p not in g.baseline:
            kind, note = _CREATED, ""
        elif base is not None and sig is not None and sig[:2] != base[:2]:
            kind, note = _MODIFIED, "(in place; attributed by the file's ctime to this window)"
        else:
            continue
        g.seen.add(p)
        _record(_attribute(sig[2] if sig else None), [(kind, p, note)])
    for p in sorted(g.baseline):
        if p not in g.seen and p not in final:
            _record(_UNATTRIBUTED_NODEID, _removed_under(p))
    if g.attributed:                 # every entry is a finding: _record never adds an empty list
        g.failed = True
        if session.exitstatus == 0:
            session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    g = _GUARD
    if not g.armed or not g.attributed:
        return
    tr = terminalreporter
    tr.section("data/ write guard: FAILED — the suite created, modified or removed paths under data/",
               sep="=", red=True)
    tr.write_line("A test that writes into the data layer must stub it (tmp_path cache dirs, a "
                  "stubbed provider, a monkeypatched DataManager cache root). Session exit status "
                  "forced to 1 ([NN-FAIL-CLOSED]).")
    for nodeid, found in g.attributed.items():
        tr.write_line(f"  {nodeid}")
        for kind, path, note in found:
            tr.write_line(f"      {kind:<9} {path}" + (f"   {note}" if note else ""))

"""Collection stays inside tests/ — a stray test_*.py under data/ must not abort the suite.

2026-10-14: a bare `pytest` walked data/; in every agent worktree data/{logs,trade_logs,
processed,research,observability} are SYMLINKS into main's data/, and a stash-accident
dir there held a test_*.py — the director's full main-suite run aborted at collection.
The janitor's FAST_SUITE named no path, so the 03:00 run was exposed the same way.

Two guards, each sufficient alone: pytest.ini `testpaths = tests`, and "tests" named
explicitly in FAST_SUITE. These tests run real pytest subprocesses against a throwaway
layout — nothing is ever planted in the real data/ (it is main's, via symlink).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import janitor_nightly as jn

REPO = Path(__file__).resolve().parent.parent
LIVE_INI = REPO / "pytest.ini"


@pytest.fixture
def layout(tmp_path):
    """tests/test_ok.py, plus data/ as a SYMLINK (as in agent worktrees) holding a
    test file that cannot even be imported."""
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "test_ok.py").write_text("def test_ok():\n    pass\n")
    elsewhere = tmp_path / "mains_data"
    elsewhere.mkdir()
    (elsewhere / "test_bad.py").write_text(
        "import a_module_that_does_not_exist_anywhere\n\ndef test_bad():\n    pass\n")
    (root / "data").symlink_to(elsewhere, target_is_directory=True)
    return root


def _ini(root: Path, keep_testpaths: bool) -> None:
    lines = LIVE_INI.read_text().splitlines()
    if not keep_testpaths:
        lines = [l for l in lines if not l.strip().startswith("testpaths")]
    (root / "pytest.ini").write_text("\n".join(lines) + "\n")


def _collect(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *args],
        cwd=root, capture_output=True, text=True, timeout=120)


def test_the_planted_file_IS_a_real_hazard_without_the_guards(layout):
    """Validates the fixture: with no testpaths and no path argument, collection walks
    the symlinked data/ and fails — so the passes below mean something."""
    _ini(layout, keep_testpaths=False)
    r = _collect(layout)
    assert r.returncode != 0 and "test_bad" in (r.stdout + r.stderr)


def test_a_bare_pytest_under_the_LIVE_config_never_collects_data(layout):
    _ini(layout, keep_testpaths=True)
    r = _collect(layout)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-1500:]
    assert "test_ok" in out and "test_bad" not in out


def test_the_janitors_FAST_SUITE_is_safe_even_if_testpaths_is_removed(layout):
    """The two guards are independent: FAST_SUITE's explicit path alone suffices."""
    _ini(layout, keep_testpaths=False)
    janitor_args = [a for a in jn.FAST_SUITE if a != "-q"]   # -q is already passed
    r = _collect(layout, *janitor_args)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-1500:]
    assert "test_ok" in out and "test_bad" not in out


def test_the_live_config_names_tests_as_its_only_testpath():
    ini = LIVE_INI.read_text().splitlines()
    assert [l.split("=", 1)[1].strip() for l in ini if l.strip().startswith("testpaths")] == ["tests"]

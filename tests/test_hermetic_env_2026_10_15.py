"""tests/conftest.py keeps the real .env out of every test — the #156 hang's guard.

Each case runs a real pytest subprocess on a throwaway layout: a FAKE .env, a copy of
the live conftest, and a test module that puts the keys into os.environ AT IMPORT —
exactly what data_manager.py's import-time load_dotenv(override=True) does during
collection. No real secret is read, and no provider call is ever constructed in the
run that lacks the guard.
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
FAKE = "fake-not-a-real-key"

LEAKING_TEST = f'''
import os
# The leak, simulated: data_manager.py:34 does load_dotenv(override=True) at IMPORT.
os.environ["ANTHROPIC_API_KEY"] = "{FAKE}"
os.environ["FAKE_ONLY_IN_THE_ENV_FILE"] = "x"

def test_the_keys_are_gone_inside_a_test():
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert "FAKE_ONLY_IN_THE_ENV_FILE" not in os.environ

def test_the_pulse_gate_stays_offline():
    from paper_trader.intel_pulse import _model_call_or_none, _scan_model_call_or_none
    assert _model_call_or_none("daily", None) is None
    assert _scan_model_call_or_none(None) is None
'''


@pytest.fixture
def layout(tmp_path):
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / ".env").write_text(f"ANTHROPIC_API_KEY={FAKE}\nFAKE_ONLY_IN_THE_ENV_FILE=x\n")
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    (root / "tests" / "test_leak.py").write_text(LEAKING_TEST)
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "FAKE_ONLY_IN_THE_ENV_FILE")}
    env["PYTHONPATH"] = str(REPO)
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                           "-p", "no:randomly", *args],
                          cwd=root, env=env, capture_output=True, text=True, timeout=180)


def test_without_the_guard_the_leak_reaches_the_test(layout):
    """Validates the fixture: no conftest -> the import-time leak is visible inside a test.
    Only the env check runs here; the pulse gate is never touched without the guard."""
    r = _run(layout, "-k", "keys_are_gone")
    assert r.returncode != 0 and "ANTHROPIC_API_KEY" in (r.stdout + r.stderr)


def test_with_the_live_conftest_the_keys_are_gone_and_the_pulse_stays_offline(layout):
    shutil.copy(LIVE_CONFTEST, layout / "tests" / "conftest.py")
    r = _run(layout)
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    assert "2 passed" in r.stdout


def test_the_guard_reads_key_NAMES_only(tmp_path):
    from tests.conftest import _env_key_names
    env = tmp_path / ".env"
    env.write_text("A_NAME=a-value\nB_NAME=b-value\n")
    names = _env_key_names(env)
    assert names == frozenset({"A_NAME", "B_NAME"})
    assert not any("value" in n for n in names), "values must never be carried"
    assert _env_key_names(tmp_path / "absent.env") == frozenset()

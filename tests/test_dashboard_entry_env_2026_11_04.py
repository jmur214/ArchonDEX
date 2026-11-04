"""The dashboard loads the repo's .env at its process ENTRIES, never on import (2026-11-04).

THE BREACH: cockpit/dashboard_v2/app.py loaded the REPO-ROOT .env at IMPORT — a bare
`load_dotenv()` until 2026-10-22 (which also searched UPWARD and pulled the MAIN tree's .env into
an agent worktree's test session), then `core.env.load_local_env()` at module level, which stops
the upward search but still loads a .env at the repo root whenever the module is imported. The
2026-10-15 rule is that no import loads the environment: `load_local_env` is called at process
entries. Neither existing lock saw it: tests/test_env_entries_2026_10_15.py's roots do not include
cockpit/, and tests/test_env_loading_2026_10_15.py's AST scan matched load_dotenv/dotenv_values
only (both widened in that unit).

INSTRUMENT. Planting a .env at the real repo root is out of the question (in the main tree it IS
the real file), so each case runs a child process on a throwaway root holding a planted .env of
fake values under real names and a COPY of core/ — `core.env` resolves its DOTENV_PATH from its
own file, so to that child the planted file is the repo-root .env (asserted). sys.path puts the
throwaway root first and the real repo second, so cockpit/ is the real package. The planted names
are the two .env names the suite's hermeticity fixture strips here (SIMFIN_API_KEY,
ANTHROPIC_API_KEY) and the two Alpaca names the dashboard's callbacks read at module level.

  negative   importing cockpit.dashboard_v2 (the package), .app, and the tab chain
             tests/test_feature_foundry.py takes puts NOTHING into os.environ;
  positive   each real entry — `python cockpit_dashboard_v2.py` and `python -m
             cockpit.dashboard_v2.app` — loads the planted file, and through the second the keys
             REACH the callbacks' module-level reads (the package's lazy __init__ is what makes
             that ordering possible; the eager form imported the callbacks first).

No socket on the planted keys: dashboard_callbacks starts the Alpaca stream at import when both
keys are set, so every child replaces threading.Thread.start with a recorder; the recorder
firing is itself evidence that the keys reached that module body.

Reversion-proven (revert, run, must fail, restore): app.py's module-level load -> the negative
case fails (and test_env_loading's widened AST lock names app.py); the eager __init__ -> the
`-m` positive case fails (the callbacks saw empty keys).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "cockpit_dashboard_v2.py"
PLANTED = {
    "SIMFIN_API_KEY": "fake-simfin-key-planted-by-the-lock",
    "ANTHROPIC_API_KEY": "fake-anthropic-key-planted-by-the-lock",
    "APCA_API_KEY_ID": "fake-alpaca-key-id-planted-by-the-lock",
    "APCA_API_SECRET_KEY": "fake-alpaca-secret-planted-by-the-lock",
}
IMPORT_CHAIN = ["cockpit.dashboard_v2", "cockpit.dashboard_v2.tabs.feature_foundry_tab",
                "cockpit.dashboard_v2.app"]

_PRELUDE = """
import json, os, sys, threading
NAMES = json.loads(sys.argv[1])
for n in NAMES:
    os.environ.pop(n, None)
started = []
threading.Thread.start = lambda self: started.append(self.name)   # never a socket on planted keys
def report(**extra):
    import core.env
    print(json.dumps({"core_env": core.env.__file__, "dotenv": str(core.env.DOTENV_PATH),
                      "entered": {n: os.environ[n] for n in NAMES if n in os.environ},
                      "stream_thread_started": bool(started), **extra}))
"""

_IMPORT_CHILD = _PRELUDE + """
import importlib
before = dict(os.environ)
for m in sys.argv[2:]:
    importlib.import_module(m)
changed = sorted(k for k in set(before) | set(os.environ) if before.get(k) != os.environ.get(k))
report(changed=changed, imported=sys.argv[2:])
"""

_LAUNCHER_CHILD = _PRELUDE + """
import runpy, types
seen = {}
stub = types.ModuleType("cockpit.dashboard_v2.app")
stub.run_dashboard = lambda live=False, port=8050: seen.update(
    {"at_run": {n: os.environ[n] for n in NAMES if n in os.environ}, "live": live, "port": port})
sys.modules["cockpit.dashboard_v2.app"] = stub          # the real launcher, a stubbed server
sys.argv = ["cockpit_dashboard_v2.py", "--port", "8123"]
runpy.run_path(LAUNCHER, run_name="__main__")
report(**seen)
""".replace("LAUNCHER", repr(str(LAUNCHER)))

_MODULE_ENTRY_CHILD = _PRELUDE + """
import runpy
import dash
ran = {}
dash.Dash.run = lambda self, *a, **k: ran.update(k)   # the real app, no server
sys.argv = ["app.py", "--port", "8124"]
runpy.run_module("cockpit.dashboard_v2.app", run_name="__main__", alter_sys=True)
from cockpit.dashboard_v2.callbacks import mode_callbacks, dashboard_callbacks
report(mode_key=mode_callbacks.ALPACA_API_KEY, dash_key=dashboard_callbacks.ALPACA_API_KEY,
       dash_secret=dashboard_callbacks.ALPACA_API_SECRET, ran=ran)
"""


@pytest.fixture
def planted_root(tmp_path):
    """A throwaway repo root: a copy of core/ (so core.env's DOTENV_PATH is HERE) and the .env."""
    root = tmp_path / "root"
    shutil.copytree(REPO / "core", root / "core",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (root / ".env").write_text("".join(f"{k}={v}\n" for k, v in PLANTED.items()))
    return root


def _child(root: Path, script: str, *args: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in PLANTED}
    env["PYTHONPATH"] = f"{root}{os.pathsep}{REPO}"
    r = subprocess.run([sys.executable, "-c", script, json.dumps(list(PLANTED)), *args],
                       cwd=root, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    # the instrument: to this child the planted file IS the repo-root .env
    assert out["core_env"].startswith(str(root)), out["core_env"]
    assert out["dotenv"] == str(root / ".env"), out["dotenv"]
    return out


def test_importing_the_package_the_tab_chain_and_the_app_loads_nothing(planted_root):
    out = _child(planted_root, _IMPORT_CHILD, *IMPORT_CHAIN)
    assert out["imported"] == IMPORT_CHAIN
    assert out["entered"] == {}, f"a repo-root .env entered os.environ on import: {out['entered']}"
    assert out["changed"] == [], f"import changed the environment: {out['changed']}"
    assert out["stream_thread_started"] is False, "the import started the Alpaca stream"


def test_the_launcher_entry_loads_the_planted_env_before_it_runs_the_app(planted_root):
    out = _child(planted_root, _LAUNCHER_CHILD)
    assert out["port"] == 8123 and out["live"] is False, out
    assert out["at_run"] == PLANTED, f"the launcher did not load the repo-root .env: {out}"


def test_the_module_entry_loads_the_planted_env_before_the_callbacks_read_it(planted_root):
    """`python -m cockpit.dashboard_v2.app`: the keys reach the MODULE-LEVEL reads in
    mode_callbacks and dashboard_callbacks, which only the early guard + lazy __init__ allow."""
    out = _child(planted_root, _MODULE_ENTRY_CHILD)
    assert out["ran"].get("port") == 8124, f"the entry did not reach app.run: {out}"
    assert out["entered"] == PLANTED, out
    assert out["mode_key"] == PLANTED["APCA_API_KEY_ID"], \
        f"mode_callbacks read the keys BEFORE the entry loaded them: {out}"
    assert out["dash_key"] == PLANTED["APCA_API_KEY_ID"], out
    assert out["dash_secret"] == PLANTED["APCA_API_SECRET_KEY"], out
    assert out["stream_thread_started"] is True, \
        "dashboard_callbacks' module body did not see both keys (its stream start never fired)"


def test_importing_the_launcher_file_itself_loads_nothing(planted_root):
    """The launcher is a script; imported as a module its guard does not run."""
    script = _PRELUDE + """
import importlib.util
spec = importlib.util.spec_from_file_location("launcher_as_module", LAUNCHER)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
report()
""".replace("LAUNCHER", repr(str(LAUNCHER)))
    out = _child(planted_root, script)
    assert out["entered"] == {}, out

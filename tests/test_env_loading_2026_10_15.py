"""Importing a module must never change the environment (Change A; Agent R's locks 1, 2, 4).

Before 2026-10-15 four modules loaded .env on IMPORT — data_manager with override=True — and a
pytest session in the main tree went live on the user's provider key (#156). Now only process
entries load it, through `core.env.load_local_env()`.

These locks do not depend on a real .env existing (worktrees and CI have none): lock 1 records
any dotenv call made during import, lock 2 reads the source tree's AST, lock 4 uses temp files.
No real secret is read anywhere here.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core import env as core_env

REPO = Path(__file__).resolve().parent.parent
LOADER_MODULES = [
    "engines.data_manager.data_manager",
    "engines.data_manager.earnings_data",
    "engines.data_manager.macro_data",
    "intelligence.news_collector",
    "orchestration.mode_controller",      # the import pytest collection actually makes
]
LIBRARY_ROOTS = ["engines", "intelligence", "paper_trader", "core"]

_CHILD = """
import json, os, sys
import dotenv, dotenv.main
calls = []
def _rec(name):
    def f(*a, **k):
        calls.append(name)
        return {} if name == "dotenv_values" else True
    return f
dotenv.load_dotenv = dotenv.main.load_dotenv = _rec("load_dotenv")
dotenv.dotenv_values = dotenv.main.dotenv_values = _rec("dotenv_values")
# Make every .env "exist", so a load guarded by `if path.exists():` still reaches the recorder
# in a tree that has no .env (worktrees, CI) — found by reversion: without this, a guarded
# import-time load passes this lock wherever the file is absent.
import os.path, pathlib
_pe, _ope, _opi = pathlib.Path.exists, os.path.exists, os.path.isfile
pathlib.Path.exists = lambda self, *a, **k: True if self.name == ".env" else _pe(self, *a, **k)
os.path.exists = lambda p: True if str(p).endswith(".env") else _ope(p)
os.path.isfile = lambda p: True if str(p).endswith(".env") else _opi(p)
before = dict(os.environ)
import importlib
for m in sys.argv[1:]:
    importlib.import_module(m)
changed = sorted(k for k in set(before) | set(os.environ) if before.get(k) != os.environ.get(k))
print(json.dumps({"calls": calls, "changed_names": changed}))
"""


# ── lock 1: importing the loaders changes nothing ─────────────────────────────

def test_importing_the_loader_modules_makes_no_dotenv_call_and_changes_no_variable():
    r = subprocess.run([sys.executable, "-c", _CHILD, *LOADER_MODULES], cwd=REPO,
                       capture_output=True, text=True, timeout=300,
                       env={**os.environ, "PYTHONPATH": str(REPO)})
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["calls"] == [], f"a module loaded .env on import: {out['calls']}"
    assert out["changed_names"] == [], f"import changed the environment: {out['changed_names']}"


# ── lock 2: no module-level dotenv call in library code (AST) ─────────────────

def _module_level_dotenv_calls(path: Path) -> list:
    """Calls to load_dotenv/dotenv_values that execute at IMPORT: top-level statements and
    top-level if/try blocks — never inside a def or class body."""
    tree = ast.parse(path.read_text(), filename=str(path))
    hits = []

    class _ImportTime(ast.NodeVisitor):
        # Bodies that do NOT run at import: functions, lambdas, classes' methods are
        # functions; a class body DOES run at import, so only its defs are skipped.
        def visit_FunctionDef(self, node): pass
        def visit_AsyncFunctionDef(self, node): pass
        def visit_Lambda(self, node): pass

        def visit_If(self, node):
            if _is_main_guard(node):      # runs only when executed as a script
                for st in node.orelse:
                    self.visit(st)
                return
            self.generic_visit(node)

        def visit_Call(self, node):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in ("load_dotenv", "dotenv_values"):
                hits.append(node.lineno)
            self.generic_visit(node)

    _ImportTime().visit(tree)
    return sorted(hits)


def _is_main_guard(node: ast.If) -> bool:
    t = node.test
    return (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "__name__"
            and any(isinstance(c, ast.Constant) and c.value == "__main__" for c in t.comparators))


def test_no_library_module_loads_dotenv_at_import():
    offenders = []
    for root in LIBRARY_ROOTS:
        for f in sorted((REPO / root).rglob("*.py")):
            for line in _module_level_dotenv_calls(f):
                offenders.append(f"{f.relative_to(REPO)}:{line}")
    assert not offenders, ("module-level .env loads (an import must not change the environment; "
                           f"call core.env.load_local_env() from the process entry): {offenders}")


def test_the_ast_scan_sees_a_module_level_load(tmp_path):
    """The scanner itself: a top-level load is caught; one inside a function or __main__ is not."""
    f = tmp_path / "m.py"
    f.write_text("from dotenv import load_dotenv\nload_dotenv()\n"            # 2: import-time
                 "def g():\n    load_dotenv()\n"                               # 4: in a def
                 "if __name__ == '__main__':\n    load_dotenv()\n"             # 6: __main__
                 "if True:\n    def h():\n        pass\n    load_dotenv()\n"  # 10: after a nested def
                 "class C:\n    X = load_dotenv()\n")                          # 12: class body runs
    assert _module_level_dotenv_calls(f) == [2, 10, 12]


# ── lock 4: the helper never overrides, and is idempotent ─────────────────────

@pytest.fixture
def fresh_helper(monkeypatch):
    monkeypatch.setattr(core_env, "_loaded_from", None)
    return core_env


def test_a_preset_variable_survives_and_the_file_fills_only_the_gaps(tmp_path, monkeypatch, fresh_helper):
    f = tmp_path / ".env"
    f.write_text("B_ENVTEST_PRESET=from-file\nB_ENVTEST_ONLY_IN_FILE=file-value\n")
    monkeypatch.setenv("B_ENVTEST_PRESET", "from-process")
    monkeypatch.delenv("B_ENVTEST_ONLY_IN_FILE", raising=False)
    assert fresh_helper.load_local_env(f) is True
    assert os.environ["B_ENVTEST_PRESET"] == "from-process", "override must be False"
    assert os.environ["B_ENVTEST_ONLY_IN_FILE"] == "file-value"
    monkeypatch.delenv("B_ENVTEST_ONLY_IN_FILE")


def test_the_helper_is_idempotent_and_an_absent_file_is_a_no_op(tmp_path, monkeypatch, fresh_helper):
    f = tmp_path / ".env"
    f.write_text("B_ENVTEST_IDEM=1\n")
    monkeypatch.delenv("B_ENVTEST_IDEM", raising=False)
    assert fresh_helper.load_local_env(f) is True
    assert fresh_helper.load_local_env(f) is False
    assert fresh_helper.load_local_env(tmp_path / "absent.env") is False
    monkeypatch.delenv("B_ENVTEST_IDEM")

"""Change B — the provider call site refuses a LIVE call under pytest (Agent R's lock 5; ruling C-3).

The conftest fixture guards the TEST; it cannot reach a subprocess child. The refusal at the call
site guards the MONEY, and PYTEST_CURRENT_TEST — set by pytest during every test — is inherited by
children spawned with the parent's environment.

SAFETY: every case patches `requests.post` with a recorder BEFORE a closure is built, so even with
the guard reverted nothing here can reach the network. No real key is used anywhere.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from intelligence.analyst import anthropic_adapter as aa

REPO = Path(__file__).resolve().parent.parent
SETTINGS = aa.load_settings(str(REPO / "config" / "llm_settings.json"))
FAKE_KEY = "fake-not-a-real-key"


class _Resp:
    status_code = 200
    text = ""

    def json(self):
        return {"content": [{"type": "text", "text": "ok"}], "model": "fake",
                "usage": {"input_tokens": 1, "output_tokens": 1}, "stop_reason": "end_turn"}


class _FakeSession:
    def __init__(self):
        self.posts = 0

    def post(self, *a, **k):
        self.posts += 1
        return _Resp()


@pytest.fixture
def recorder(monkeypatch):
    """requests.post replaced BEFORE any closure is built — the network is unreachable here."""
    sent = []
    monkeypatch.setattr(aa.requests, "post", lambda *a, **k: sent.append(1) or _Resp())
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    return sent


def _calls(session=None):
    return [
        ("make_model_call", lambda: aa.make_model_call("daily", settings=SETTINGS, session=session)(
            "p", "{}", 16)),
        ("make_agentic_call", lambda: aa.make_agentic_call("daily", settings=SETTINGS, session=session)(
            "p", "{}", 16, [], lambda n, i: ("", False), 1)),
    ]


def test_no_session_under_pytest_is_REFUSED_in_both_closures(recorder):
    assert os.environ.get("PYTEST_CURRENT_TEST"), "pytest sets this during every test"
    for name, call in _calls():
        with pytest.raises(RuntimeError, match="refused under pytest"):
            call()
    assert recorder == [], "nothing may be sent once refused"


def test_an_injected_fake_session_proceeds(recorder):
    for name, _ in _calls():
        fake = _FakeSession()
        build = aa.make_model_call if name == "make_model_call" else aa.make_agentic_call
        fn = build("daily", settings=SETTINGS, session=fake)
        if name == "make_model_call":
            fn("p", "{}", 16)
        else:
            fn("p", "{}", 16, [], lambda n, i: ("", False), 1)
        assert fake.posts >= 1, name
    assert recorder == [], "a fake session must never fall through to requests.post"


def test_outside_pytest_the_guard_is_inert(recorder, monkeypatch):
    """The production case, proven: no PYTEST_CURRENT_TEST -> the request is sent (to the recorder)."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    for _, call in _calls():
        call()
    assert len(recorder) == 2


_CHILD = f"""
import sys
sys.path.insert(0, {str(REPO)!r})
from intelligence.analyst import anthropic_adapter as aa
sent = []
aa.requests.post = lambda *a, **k: sent.append(1)   # the network is unreachable in the child too
fn = aa.make_model_call("daily", settings=aa.load_settings({str(REPO / 'config' / 'llm_settings.json')!r}))
try:
    fn("p", "{{}}", 16)
    print("SENT" if sent else "NO_SEND")
except RuntimeError as e:
    print("REFUSED" if "refused under pytest" in str(e) else "OTHER: " + str(e))
"""


def test_a_child_spawned_with_the_parents_environment_is_refused_too():
    """C-3: the guard reaches a subprocess through the INHERITED environment."""
    env = {**os.environ, "ANTHROPIC_API_KEY": FAKE_KEY}
    r = subprocess.run([sys.executable, "-c", _CHILD], capture_output=True, text=True,
                       timeout=120, env=env)
    assert r.stdout.strip().splitlines()[-1] == "REFUSED", r.stdout + r.stderr[-1500:]


# ── C-3's blind spots, locked as rules over the source ─────────────────────────

def _env_kwargs_not_from_os_environ(path: Path) -> list:
    """subprocess calls whose `env=` is NOT derived from os.environ — such a child loses the
    inherited guard (and the test-side fixture), the blind spot R named."""
    tree = ast.parse(path.read_text(), filename=str(path))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "env" and not (isinstance(kw.value, ast.Constant) and kw.value.value is None):
                    if "os.environ" not in ast.unparse(kw.value) and _names_env_var_from_environ(tree, kw.value) is False:
                        bad.append(node.lineno)
    return bad


def _names_env_var_from_environ(tree: ast.Module, value: ast.expr) -> bool:
    """`env=env` where `env = {**os.environ, ...}` (or similar) was assigned in the same file."""
    if not isinstance(value, ast.Name):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == value.id for t in node.targets):
            if "os.environ" in ast.unparse(node.value):
                return True
    return False


def test_every_subprocess_env_in_tests_inherits_os_environ():
    offenders = []
    for f in sorted((REPO / "tests").glob("*.py")):
        if "subprocess" not in f.read_text():
            continue
        offenders += [f"{f.name}:{ln}" for ln in _env_kwargs_not_from_os_environ(f)]
    assert not offenders, ("a hand-built env= drops PYTEST_CURRENT_TEST, so the child is no longer "
                           f"refused at the provider — derive it from os.environ: {offenders}")


def test_no_module_builds_a_provider_call_at_import():
    """Collection time is outside the guard (PYTEST_CURRENT_TEST is unset while importing), so no
    module may build or invoke a provider call at module level."""
    roots = ["engines", "intelligence", "paper_trader", "core", "scripts", "orchestration"]
    offenders = []
    for root in roots:
        for f in sorted((REPO / root).rglob("*.py")):
            tree = ast.parse(f.read_text(), filename=str(f))
            for st in tree.body:
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if isinstance(st, ast.If) and getattr(st.test, "left", None) is not None \
                        and getattr(st.test.left, "id", "") == "__name__":
                    continue
                for node in ast.walk(st):
                    if isinstance(node, ast.Call):
                        fn = node.func
                        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                        if name in ("make_model_call", "make_agentic_call"):
                            offenders.append(f"{f.relative_to(REPO)}:{node.lineno}")
    assert not offenders, f"module-level provider construction: {offenders}"


def test_the_env_scanner_flags_a_hand_built_env(tmp_path):
    f = tmp_path / "t.py"
    f.write_text("import os, subprocess\n"
                 "subprocess.run(['x'], env={'PATH': '/bin'})\n"              # 2: hand-built
                 "subprocess.run(['x'], env={**os.environ, 'A': '1'})\n"       # ok
                 "e = dict(os.environ)\nsubprocess.run(['x'], env=e)\n"        # ok via a name
                 "subprocess.run(['x'], env=None)\n")                          # ok
    assert _env_kwargs_not_from_os_environ(f) == [2]

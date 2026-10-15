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

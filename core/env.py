"""The ONE place a local process loads the repo's .env — called by process entries, never on import.

Before 2026-10-15 four modules loaded .env as an IMPORT side effect, one of them with
override=True (`engines/data_manager/data_manager.py`). Importing an engine therefore rewrote
the real environment — and a pytest session in the main tree went LIVE on the user's provider
key (the #156 hang). Importing a module must never change the environment.

Rules (Agent R's design read, ruling C-1):
  * call `load_local_env()` from a TRUE process entry (a script's `__main__`, a harness `main`),
    never from a library module and never at module level;
  * `override=False`: a variable the process already has always wins over the file;
  * idempotent: a second call is a no-op;
  * no .env (a container, CI, an agent worktree) -> nothing happens. Containers get their keys
    from the job environment / Secrets Manager.

A forgotten call is NOT harmless: without keys, `DataManager` goes offline and fetches uncached
tickers from yfinance — a different adjustment basis. That is why the census records the feed
and canonical runs refuse the fallback (ruling C-2), and why an AST lock requires every entry
that reaches the data manager to call this helper or declare itself offline by design.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = REPO_ROOT / ".env"

#: The exact marker an entry may carry INSTEAD of calling the helper, when running without
#: local keys is intended. The AST lock looks for this string.
OFFLINE_BY_DESIGN = "load_local_env: offline by design"

_loaded_from: Optional[Path] = None


def load_local_env(path: Optional[Path] = None) -> bool:
    """Load `<repo>/.env` into os.environ WITHOUT overriding anything already set.

    Returns True if a file was loaded on this call, False if it was absent or already loaded.
    """
    global _loaded_from
    target = Path(path) if path is not None else DOTENV_PATH
    if _loaded_from == target:
        return False
    if not target.exists():
        return False
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=target, override=False)
    _loaded_from = target
    return True

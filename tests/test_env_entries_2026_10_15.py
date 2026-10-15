"""Every process entry that reaches the data layer loads .env EXPLICITLY (Agent R's lock 3, ruling C-1).

With the import-time loads gone, an entry that forgets `core.env.load_local_env()` does not fail:
`DataManager` sees no keys, goes offline, and fetches uncached tickers from yfinance — a silent
SOURCE SWITCH onto a different adjustment basis (R's §2). So every file with a `__main__` block
whose imports (lazy ones included) reach a former loader must CALL the helper inside that block,
or carry the explicit offline-by-design marker there. The check is on the AST CALL — never on
text: while building this, a comment that merely mentioned `load_local_env()` satisfied a text
check and left `fetch_missing_delisted.py` with no call at all.
"""
from __future__ import annotations

import ast
from pathlib import Path

from core.env import OFFLINE_BY_DESIGN

REPO = Path(__file__).resolve().parent.parent
FORMER_LOADERS = {
    "engines.data_manager.data_manager", "engines.data_manager.earnings_data",
    "engines.data_manager.macro_data", "intelligence.news_collector",
}
SKIP_DIRS = {"Archive", ".venv", "data", "tests", "node_modules", ".git", ".claude", "docs"}


def _py_files() -> list:
    return [p for p in REPO.rglob("*.py") if not (set(p.relative_to(REPO).parts) & SKIP_DIRS)]


def _module_name(p: Path) -> str:
    parts = list(p.relative_to(REPO).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _main_guards(tree: ast.Module) -> list:
    """EVERY module-level `if __name__ == "__main__":` — a file may have several (the B-1 scripts
    run an env-pin check in an early guard and `main()` in the last one)."""
    out = []
    for node in tree.body:
        t = getattr(node, "test", None)
        if (isinstance(node, ast.If) and isinstance(t, ast.Compare)
                and getattr(t.left, "id", "") == "__name__"):
            out.append(node)
    return out


def _main_guard(tree: ast.Module):
    guards = _main_guards(tree)
    return guards[0] if guards else None


def _dynamic_targets(call: ast.Call, known: set) -> list:
    """Modules a dynamic import can reach (Agent R's review of bde1ff3): import_module/__import__
    of a string literal, or of an f-string / concatenation with a literal PREFIX — the edge
    loader's pattern (f"engines.engine_a_alpha.edges.{x}") — which reaches every module under it."""
    fn = call.func
    name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
    if name not in ("import_module", "__import__") or not call.args:
        return []
    a0 = call.args[0]
    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
        return [a0.value]
    prefix = None
    if isinstance(a0, ast.JoinedStr) and a0.values and isinstance(a0.values[0], ast.Constant):
        prefix = a0.values[0].value
    elif (isinstance(a0, ast.BinOp) and isinstance(a0.op, ast.Add)
          and isinstance(a0.left, ast.Constant) and isinstance(a0.left.value, str)):
        prefix = a0.left.value
    if not prefix:
        return []
    return [m for m in known if m.startswith(prefix)]


def _graph():
    files = _py_files()
    mod_of = {p: _module_name(p) for p in files}
    known = set(mod_of.values())
    graph, trees = {}, {}
    for p, mod in mod_of.items():
        try:
            tree = ast.parse(p.read_text(), filename=str(p))
        except SyntaxError:
            continue
        trees[p] = tree
        pkg = mod.split(".") if p.name == "__init__.py" else mod.split(".")[:-1]
        deps = set()
        for n in ast.walk(tree):                      # lazy (function-level) imports count
            names = []
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                base = n.module or ""
                if n.level:
                    base = ".".join(pkg[:len(pkg) - n.level + 1] + ([base] if base else []))
                names = [base] + [f"{base}.{a.name}" for a in n.names]
            elif isinstance(n, ast.Call):
                names = _dynamic_targets(n, known)
            for m in names:
                while m and m not in known:
                    m = m.rpartition(".")[0]
                if m:
                    deps.add(m)
        graph[mod] = deps
    return mod_of, graph, trees


def _reaches(start: str, graph: dict) -> bool:
    seen, stack = set(), [start]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        if m in FORMER_LOADERS and m != start:
            return True
        stack.extend(graph.get(m, ()))
    return False


def _calls_helper(guard: ast.If) -> bool:
    for node in ast.walk(guard):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name == "load_local_env":
                return True
    return False


def _declares_offline(src: str, guard: ast.If) -> bool:
    block = src.splitlines()[guard.lineno - 1: guard.end_lineno]
    return any(OFFLINE_BY_DESIGN in line for line in block)


def test_every_entry_that_reaches_the_data_layer_calls_the_helper():
    mod_of, graph, trees = _graph()
    missing, checked = [], 0
    for p, tree in trees.items():
        guards = _main_guards(tree)
        if not guards or not (_reaches(mod_of[p], graph) or mod_of[p] in FORMER_LOADERS):
            continue
        checked += 1
        src = p.read_text()
        if not any(_calls_helper(g) or _declares_offline(src, g) for g in guards):
            missing.append(str(p.relative_to(REPO)))
    assert checked >= 50, f"only {checked} entries found — the reachability scan is broken"
    assert not missing, (
        "these entries reach the data layer but neither CALL core.env.load_local_env() in their "
        f"__main__ nor declare '{OFFLINE_BY_DESIGN}' there — without keys they silently switch "
        f"to yfinance: {missing}")


def test_library_engine_modules_have_no_main_block():
    """A library module is not a process entry (ruling C-1): their CLIs moved to scripts/.
    alpha_engine's block downloaded AAPL from yfinance (found by R's importlib-aware trace)."""
    for rel in ("engines/engine_d_discovery/discovery.py",
                "engines/engine_f_governance/evolution_controller.py",
                "engines/engine_a_alpha/alpha_engine.py"):
        assert _main_guard(ast.parse((REPO / rel).read_text())) is None, rel


def test_a_comment_mentioning_the_helper_does_not_count(tmp_path):
    """The defect this lock was built from: text that names the helper is not a call."""
    src = ('# loaded via core.env.load_local_env() elsewhere\n'
           'if __name__ == "__main__":\n    main()\n')
    tree = ast.parse(src)
    assert not _calls_helper(_main_guard(tree))
    called = ast.parse('if __name__ == "__main__":\n'
                       '    from core.env import load_local_env\n    load_local_env()\n')
    assert _calls_helper(_main_guard(called))


def test_dynamic_imports_are_followed(tmp_path):
    """The edge loader's pattern: a literal, an f-string prefix, a concatenation prefix."""
    known = {"engines.engine_a_alpha.edges.a", "engines.engine_a_alpha.edges.b", "core.x"}
    calls = [ast.parse(src).body[0].value for src in (
        'importlib.import_module("core.x")',
        'import_module(f"engines.engine_a_alpha.edges.{name}")',
        '__import__("engines.engine_a_alpha.edges." + name)',
        'import_module(some_variable)')]
    got = [sorted(_dynamic_targets(c, known)) for c in calls]
    assert got == [["core.x"],
                   ["engines.engine_a_alpha.edges.a", "engines.engine_a_alpha.edges.b"],
                   ["engines.engine_a_alpha.edges.a", "engines.engine_a_alpha.edges.b"],
                   []]

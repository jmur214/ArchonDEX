"""T-2026-06-10-138 Part C — forbidden-pattern lint for signal/feature/risk code.

Grep-level CI gate against the agent-generated-code failure modes named in
the blind-spots research (docs/Sources/Research_2026_06_10_blindspots/
RESULTS_single_pass_no_research_mode.md §AREA 1): future leaks, wall-clock
nondeterminism, and silent NaN-papering in return pipelines. Runs as part
of the normal pytest suite (same idiom as tests/test_contracts.py) so the
contract-tests CI workflow picks it up with zero extra wiring.

Philosophy: cheap, high-precision patterns with an EXPLICIT allowlist.
A lint that cries wolf gets deleted; every pattern here was calibrated
against the current tree (zero false positives at introduction) and every
allowlist entry carries its justification inline.

Scope: signal/feature/risk/portfolio code paths only — NOT tests/ (test
fixtures legitimately build future-dependent expectations), NOT scripts/
(analysis/validation scripts measure lookahead deliberately, e.g. AUC
validators), NOT research/.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Signal/feature/risk paths the gate protects. New engine dirs are picked
# up automatically (glob), so an agent adding a new edge file is covered
# without touching this list.
SCOPED_DIRS = [
    "engines/engine_a_alpha",
    "engines/engine_b_risk",
    "engines/engine_c_portfolio",
    "engines/engine_e_regime",
    "core/feature_foundry",
]

# (pattern-name, compiled regex, why-it's-forbidden)
PATTERNS = [
    (
        "shift-negative (future leak)",
        re.compile(r"\.shift\(\s*-"),
        "shift(-N) pulls FUTURE rows into the current bar — the canonical "
        "lookahead bug. Label construction for supervised training is the "
        "one legitimate use (allowlist).",
    ),
    (
        "forward positional index",
        # Bare identifier + integer inside iloc, NOT a negative backward
        # window like iloc[-(lookback + 1)] and NOT a slice that merely
        # ENDS at idx+1 (inclusive-of-current-bar window). Calibrated
        # against the tree: backward idioms do not match.
        re.compile(r"\.iloc\[\s*[a-zA-Z_][a-zA-Z_0-9]*\s*\+\s*\d+\s*\]"),
        "iloc[i + N] reads a row AFTER the current position in signal "
        "context — a positional future leak.",
    ),
    (
        "wall-clock now in signal code",
        re.compile(r"datetime\.now\(\)|datetime\.utcnow\(\)|Timestamp\.now\(\)|Timestamp\.utcnow\(\)"),
        "Signals must be functions of bar data, not wall-clock time — "
        "wall-clock reads are nondeterministic across runs and break "
        "canon reproducibility. (Tree was clean at T-138; keep it that way.)",
    ),
    (
        "bare fillna on a return series",
        re.compile(r"pct_change\(\)[^\n]*\.fillna\(|\breturns\.fillna\(|\brets\.fillna\("),
        "Filling NaN returns silently fabricates data points (a delisted "
        "ticker's missing days become 0% returns). Handle missingness "
        "explicitly (dropna + alignment). (Tree was clean at T-138.)",
    ),
]

# (path-suffix, pattern-name, line-substring) -> why it's allowed.
ALLOWLIST = {
    (
        "engines/engine_a_alpha/ml_predictor.py",
        "shift-negative (future leak)",
        "target = (df['Close'].pct_change().shift(-1) > 0).astype(int)",
    ): (
        "Supervised-learning LABEL construction: the next-day return IS "
        "the training target, not a feature. The model never sees the "
        "label at inference. (T-138 review.)"
    ),
}


def _scoped_files():
    for d in SCOPED_DIRS:
        base = REPO / d
        if not base.is_dir():
            continue
        yield from sorted(base.rglob("*.py"))


def _is_allowlisted(rel: str, pattern_name: str, line: str) -> bool:
    for (suffix, pname, snippet), _why in ALLOWLIST.items():
        if rel.endswith(suffix) and pname == pattern_name and snippet in line:
            return True
    return False


def test_no_forbidden_patterns_in_signal_code():
    """Every hit must be either fixed or explicitly allowlisted WITH a
    justification. If your new code trips this: the pattern text explains
    what is wrong; do not extend the allowlist to silence a real leak."""
    violations = []
    for f in _scoped_files():
        rel = f.relative_to(REPO).as_posix()
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pname, rx, why in PATTERNS:
                if rx.search(line) and not _is_allowlisted(rel, pname, line):
                    violations.append(f"{rel}:{lineno} [{pname}] {stripped[:100]}")
    assert not violations, (
        "Forbidden patterns found in signal/feature/risk code "
        "(fix, or allowlist WITH justification in "
        "tests/test_forbidden_patterns.py):\n  " + "\n  ".join(violations)
    )


def test_allowlist_entries_still_exist():
    """A stale allowlist entry means the code it excused changed or moved —
    prune it so the allowlist stays an exact, reviewed set."""
    stale = []
    for (suffix, pname, snippet), _why in ALLOWLIST.items():
        p = REPO / suffix
        if not p.exists() or snippet not in p.read_text():
            stale.append(f"{suffix} [{pname}] {snippet[:60]}")
    assert not stale, "Stale allowlist entries (prune them):\n  " + "\n  ".join(stale)


# --------------------------------------------------------------------------- #
# T-181 — pure-AST guard: no bare `.std() == 0` (or `.var() == 0`) anywhere in
# the measurement path. CLAUDE.md non-negotiable #8: pandas std on numerically
# identical floats returns ~2e-19, not exactly 0, so a bare `== 0` guard fails
# to fire and a downstream division explodes to ~1e15. The required form is the
# tolerance guard (`std < 1e-12 or not np.isfinite(std)`). This is a STRUCTURE
# check (regex can't tell `x.std() == 0` from a comment), so it parses the AST.
# --------------------------------------------------------------------------- #
STD_GUARD_DIRS = ["backtester", "orchestration", "core", "engines"]


def _std_guard_files():
    for d in STD_GUARD_DIRS:
        base = REPO / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if "Archive" in p.parts or "archive" in p.parts:
                continue
            yield p


def _is_std_or_var_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("std", "var")
    )


def _is_zero(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
        and not isinstance(node.value, bool) and float(node.value) == 0.0


def test_no_bare_std_equals_zero_guard():
    """No `X.std() == 0` / `0 == X.std()` (or `.var()`) in the measurement
    path. Use the tolerance guard instead (CLAUDE.md #8). If this trips, your
    new guard is a latent ~1e15 explosion on near-constant input — replace it
    with `not np.isfinite(s) or s < 1e-12`."""
    violations = []
    for f in _std_guard_files():
        try:
            tree = ast.parse(f.read_text())
        except (UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            # only flag exact-equality comparisons against literal zero
            if not all(isinstance(op, ast.Eq) for op in node.ops):
                continue
            operands = [node.left, *node.comparators]
            has_std = any(_is_std_or_var_call(o) for o in operands)
            has_zero = any(_is_zero(o) for o in operands)
            if has_std and has_zero:
                rel = f.relative_to(REPO).as_posix()
                violations.append(f"{rel}:{node.lineno}")
    assert not violations, (
        "Bare `.std()/.var() == 0` guard(s) found in the measurement path "
        "(CLAUDE.md #8 — use `not np.isfinite(s) or s < 1e-12`):\n  "
        + "\n  ".join(violations)
    )

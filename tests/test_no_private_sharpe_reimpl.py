"""T-203 move 3 — CI guard against NEW private Sharpe reimplementations in scripts/.

The sibling of the contract-test family (test_contracts / test_forbidden_patterns):
a new ``scripts/*.py`` that computes a Sharpe inline as ``mean()/std()*sqrt(252)``
instead of routing through ``core.metrics_engine.MetricsEngine.sharpe_ratio`` is
measurement drift — the same metric reimplemented N ways diverges silently
(annualization, ddof, rf, zero-guard all differ). This gate flags any new one.

## The audit (T-203, done FIRST — the dispatch's "audit each before consolidating")
Scanning scripts/ found the "14 private Sharpe reimpls" are NOT 14 naive
duplicates — they are mostly **custom variants** (which a blanket consolidation
would have SILENTLY CORRUPTED) or **frozen point-in-time one-offs** (archive-
track territory; rewriting them risks breaking a frozen result for no gain):

  - CUSTOM VARIANT (preserve, do NOT fold to the default):
      run_benchmark.py:172  — LOG returns + a 2% rf (not simple returns)
      measure_pit_strategy_t154.py:364 — `madj_sharpe`, a MEDIAN-adjusted Sharpe
      edge_compression_t117.py — an APPRAISAL ratio (alpha / residual-std), not a Sharpe
  - FROZEN one-off (archive-pending; not consolidated to avoid churn/breakage):
      factor_decomp_substrate_honest.py:271, measure_pit_strategy_t154.py:248,
      analyze_overnight_intraday_t135.py:249 (`sharpe_naive`), edge_compression_t117.py:329
  - CONSUMERS (no compute — read a pre-computed sharpe): per_edge_per_year_attribution,
      analyze_per_edge_isolation, analyze_engine_e_hmm_ab, substrate_arms_analytics,
      audit_per_edge_substrate — out of scope (they already consume the canonical value).

The durable win is therefore PREVENTING NEW drift (this guard), not churning the
frozen/custom set. Each existing compute is allowlisted below WITH its
classification; a NEW unallowlisted compute fails until it uses core or is
explicitly justified here.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"

# A Sharpe COMPUTED inline from a return series: mean()/std() annualized by
# sqrt(252|250). Calibrated to the tree (zero false positives at introduction).
SHARPE_COMPUTE = re.compile(
    r"\.mean\(\)[^\n]*\.std\(\)[^\n]*sqrt\(\s*25[02]\s*\)"
)

# (file-suffix, line-substring) -> classification + justification. Each entry is
# a reviewed permission slip; keep it MINIMAL and accurate.
ALLOWLIST = {
    ("scripts/run_benchmark.py", "log_ret.mean() - 0.02 / 252"):
        "CUSTOM VARIANT: log-return Sharpe with a 2% rf — not the simple-return "
        "MetricsEngine default. Preserve; folding it to the default would change "
        "the benchmark numbers. Candidate for a documented core option later.",
    ("scripts/measure_pit_strategy_t154.py", "r.mean() / r.std() * np.sqrt(252)"):
        "FROZEN T-154 one-off (PIT-strategy measurement). Archive-track; not "
        "consolidated to avoid breaking a frozen result.",
    ("scripts/measure_pit_strategy_t154.py", "x.mean() / x.std() * np.sqrt(252)"):
        "CUSTOM VARIANT: `madj_sharpe` (median-adjusted). Distinct metric; a "
        "blanket consolidation would silently drop the median adjustment.",
    ("scripts/analyze_overnight_intraday_t135.py", "sharpe_naive"):
        "FROZEN T-135 one-off; the field is explicitly labelled `sharpe_naive`. "
        "Archive-track.",
    ("scripts/factor_decomp_substrate_honest.py", '"raw_sharpe"'):
        "FROZEN substrate-honest factor diagnostic; mirrors "
        "factor_decomposition.raw_sharpe. Archive-track.",
    ("scripts/edge_compression_t117.py", '"raw_sharpe"'):
        "FROZEN T-117 one-off (edge-compression analysis). Archive-track.",
}


def _is_allowlisted(rel: str, line: str) -> bool:
    return any(rel.endswith(suf) and snippet in line for (suf, snippet) in ALLOWLIST)


def _script_files():
    if not SCRIPTS.is_dir():
        return
    for p in sorted(SCRIPTS.rglob("*.py")):
        if "Archive" in p.parts or "archive" in p.parts:
            continue
        yield p


def test_no_new_private_sharpe_reimplementation_in_scripts():
    """A new inline Sharpe in scripts/ must route through
    core.metrics_engine.MetricsEngine.sharpe_ratio — or, if it is a genuine
    custom variant, be allowlisted HERE with its justification (and ideally
    added as a documented option on MetricsEngine)."""
    violations = []
    for f in _script_files():
        rel = f.relative_to(REPO).as_posix()
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if SHARPE_COMPUTE.search(line) and not _is_allowlisted(rel, line):
                violations.append(f"{rel}:{lineno}  {line.strip()[:90]}")
    assert not violations, (
        "New private Sharpe reimplementation(s) in scripts/ — use "
        "core.metrics_engine.MetricsEngine.sharpe_ratio, or (if a genuine custom "
        "variant) allowlist in tests/test_no_private_sharpe_reimpl.py WITH a "
        "justification:\n  " + "\n  ".join(violations)
    )


def test_allowlist_entries_still_exist():
    """A stale allowlist entry means the code it excused moved/changed — prune
    it so the allowlist stays an exact, reviewed set."""
    stale = []
    for (suf, snippet), _why in ALLOWLIST.items():
        p = REPO / suf
        if not p.exists() or snippet not in p.read_text():
            stale.append(f"{suf}  [{snippet[:40]}]")
    assert not stale, "Stale allowlist entries (prune them):\n  " + "\n  ".join(stale)

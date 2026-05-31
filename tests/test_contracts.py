"""T-2026-05-31-090 contract-test suite — permanent regression guards
against the silent-mismatch bug family.

The 2026-05-31 silent-bug audit (`docs/Audit/silent_bug_audit_2026_05_31.md`)
identified 9 confirmed defects, ALL from ONE family:

    A producer writes a key/field/column under one name; a consumer reads
    it under a different name; a `.get()` default silently masks the gap.

The project has hit this family ≥7 times (cockpit peak_equity slot,
hunt() ticker=, env-config, T-055g v1 patch keys, the director's
'Sharpe' vs 'Sharpe Ratio' bug, run_registry 'Sortino Ratio', the
13-harness 'Total Trades').

These tests make the family **fail at PR/CI time instead of after
corrupting a measurement**. They assert INVARIANTS (config-key ⊆
dataclass-field, consumer-read ⊆ producer-emit), not hardcoded values
— so they remain green as configs/schemas evolve, but fire the
moment a new mismatch appears.

## Layers

  Layer 1 — Config-key ⊆ dataclass-field contract:
    for each (config_json, dataclass, known_alias_allowlist), assert
    every JSON key is either a dataclass field or in the alias list.

  Layer 2 — Performance-summary producer/consumer key contract:
    consumer-read keys (from `summary.get(...)` across scripts/)
    must each be in the producer's emit-set (cockpit/metrics.py
    `_compute_summary()` keys) or in a known-alias allowlist.

  Layer 3 — Cross-engine signal-dict contract (DEFERRED):
    runtime-shaped dict from Engine A to Engine B/C. Static analysis
    infeasible without a smoke test. Documented in audit doc as
    deferred to a follow-up dispatch.

## Currently-failing contracts (proof the suite catches real bugs)

At the moment of writing, Layer 1 and Layer 2 each catch the bugs A
is fixing in T-088. Expected: the test file is FAILING ON MAIN until
T-088 lands. This is documented and intentional — when T-088 merges,
the suite goes green.
"""
from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pytest

REPO = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------------
# Layer 1 — config-key ⊆ dataclass-field contract
# ----------------------------------------------------------------------

def _import_dataclass(import_path: str, class_name: str):
    """Lazy import of a dataclass from a module path. Lets us assemble
    the test matrix without triggering top-of-test heavy imports."""
    mod = __import__(import_path, fromlist=[class_name])
    return getattr(mod, class_name)


# Each entry: (label, json_path_rel, import_module, class_name, known_aliases).
# `known_aliases` allowlists JSON keys that are legitimately not
# dataclass fields (e.g., legacy aliases preserved for tooling
# compatibility; nested sub-config dicts consumed by a different
# loader; documentation-only keys). KEEP THIS LIST MINIMAL — each
# entry is a permission slip and should carry a short justification
# in a code comment near where it's added.

LAYER1_CONTRACTS: List[Tuple[str, str, str, str, Set[str]]] = [
    # AlphaConfig — config/alpha_settings.{env}.json. Three nested
    # sub-config dicts (`hygiene`, `ensemble`, `regime`) are legit
    # dataclass fields of dict type, so they're in the field set.
    # Extras: `edge_params` (per-edge override map consumed by
    # individual edges, not AlphaConfig); `fill_share_cap` (consumed
    # downstream by risk-sizing, not by alpha aggregation directly);
    # `metalearner` (nested settings consumed by MetaLearnerSettings).
    (
        "AlphaConfig vs alpha_settings.prod.json",
        "config/alpha_settings.prod.json",
        "engines.engine_a_alpha.alpha_engine",
        "AlphaConfig",
        {"edge_params", "fill_share_cap", "metalearner"},
    ),
    (
        "AlphaConfig vs alpha_settings.dev.json",
        "config/alpha_settings.dev.json",
        "engines.engine_a_alpha.alpha_engine",
        "AlphaConfig",
        {"edge_params", "fill_share_cap", "metalearner"},
    ),
    # RiskConfig — config/risk_settings.{env}.json. T-088 is fixing
    # this contract right now: prod.json names sizing knobs
    # `risk_per_trade` / `max_position_value` while RiskConfig fields
    # are `risk_per_trade_pct` / `max_pos_value_pct`. Until T-088
    # merges, this test is EXPECTED TO FAIL listing those keys + the
    # ATR/commission/slippage/debug/position_sizing extras that aren't
    # in RiskConfig. After T-088 the contract goes green.
    (
        "RiskConfig vs risk_settings.prod.json",
        "config/risk_settings.prod.json",
        "engines.engine_b_risk.risk_engine",
        "RiskConfig",
        set(),  # NO aliases — every key must be a real field after T-088
    ),
    (
        "RiskConfig vs risk_settings.dev.json",
        "config/risk_settings.dev.json",
        "engines.engine_b_risk.risk_engine",
        "RiskConfig",
        set(),
    ),
    # GovernorConfig — config/governor_settings.json. One legit alias:
    # `max_turnover_per_month` is documented in the JSON but consumed
    # by a downstream throttle (not GovernorConfig directly).
    (
        "GovernorConfig vs governor_settings.json",
        "config/governor_settings.json",
        "engines.engine_f_governance.governor",
        "GovernorConfig",
        {"max_turnover_per_month"},
    ),
    # PortfolioPolicyConfig — config/portfolio_settings.json. Three
    # nested sub-config dicts (`lt_hold_preference`, `portfolio_optimizer`,
    # `wash_sale_avoidance`) are consumed by other engines.
    (
        "PortfolioPolicyConfig vs portfolio_settings.json",
        "config/portfolio_settings.json",
        "engines.engine_c_portfolio.policy",
        "PortfolioPolicyConfig",
        {"lt_hold_preference", "portfolio_optimizer", "wash_sale_avoidance"},
    ),
]


@pytest.mark.parametrize(
    "label,json_path_rel,import_module,class_name,known_aliases",
    LAYER1_CONTRACTS,
    ids=[c[0] for c in LAYER1_CONTRACTS],
)
def test_layer1_config_key_in_dataclass_field(
    label, json_path_rel, import_module, class_name, known_aliases,
):
    """Every JSON config key must map to a dataclass field, OR appear
    in the explicit `known_aliases` allowlist documented above.

    Failure message names the offending key, dataclass, and JSON file
    so the reader can act on the diagnostic immediately."""
    json_path = REPO / json_path_rel
    if not json_path.exists():
        pytest.skip(f"config file missing: {json_path_rel}")
    dc = _import_dataclass(import_module, class_name)
    field_names = {f.name for f in fields(dc)}
    cfg = json.loads(json_path.read_text())

    missing = []
    for k in cfg.keys():
        if k in field_names:
            continue
        if k in known_aliases:
            continue
        missing.append(k)

    assert not missing, (
        f"\n[Layer 1 contract violation] {label}\n"
        f"  JSON file: {json_path_rel}\n"
        f"  Dataclass: {import_module}.{class_name}\n"
        f"  Keys present in JSON but NOT in dataclass fields "
        f"(and not in known_aliases):\n"
        + "\n".join(f"    - {k!r}" for k in missing)
        + f"\n\n  These keys are SILENTLY DROPPED by the dataclass filter on load.\n"
        f"  Fix one of:\n"
        f"    1. Rename the JSON key to match the dataclass field.\n"
        f"    2. Add a field to the dataclass with a matching name.\n"
        f"    3. If the key is consumed by a different loader,"
        f" add it to known_aliases with a brief justification comment."
    )


# ----------------------------------------------------------------------
# Layer 2 — performance-summary producer/consumer key contract
# ----------------------------------------------------------------------

# Producer location: cockpit/metrics.py `PerformanceMetrics._compute_summary()`
# returns this fixed-key dict. `summary_metrics()` adds one extra key
# ("Trades"). `mode_controller.run_backtest()` returns `metrics.summary()`
# (so consumers see the smaller set, NOT the "Trades" addition).

# This list MUST be kept in sync with cockpit/metrics.py:_compute_summary.
# Test below ALSO statically scrapes that function to verify these match.
PRODUCER_SUMMARY_KEYS: Set[str] = {
    "Starting Equity",
    "Ending Equity",
    "Net Profit",
    "Total Return (%)",
    "CAGR (%)",
    "Max Drawdown (%)",
    "Sharpe Ratio",
    "Volatility (%)",
    "Win Rate (%)",
}

# `summary_metrics()` adds this; `summary()` does NOT.
PRODUCER_SUMMARY_METRICS_EXTRA_KEYS: Set[str] = {"Trades"}

# Keys legitimately added by callers AFTER summary() returns. Mode
# controller appends `timestamp`; harnesses may add `run_id` etc.
# Allowlisting these prevents the test from flagging downstream
# augmentations.
KNOWN_DOWNSTREAM_AUGMENT_KEYS: Set[str] = {
    "timestamp",   # mode_controller.run_backtest:1097
    "run_id",      # tested separately (added by harnesses)
}


def _scrape_compute_summary_keys() -> Set[str]:
    """Static scrape of `cockpit/metrics.py:_compute_summary()`'s key
    literals. Catches the case where someone updates the producer
    without updating this test's PRODUCER_SUMMARY_KEYS constant —
    keeps both in sync."""
    src = (REPO / "cockpit" / "metrics.py").read_text()
    # Find the _compute_summary function body via simple bracket match.
    m = re.search(
        r"def _compute_summary\b.*?return\s*\{(.*?)\}", src, re.DOTALL,
    )
    if m is None:
        return set()
    body = m.group(1)
    # Pull every string literal that looks like a dict key.
    keys = set(re.findall(r'"([^"]+)"\s*:', body))
    return keys


def test_layer2a_producer_key_constant_matches_source():
    """The PRODUCER_SUMMARY_KEYS constant must match what
    cockpit/metrics.py:_compute_summary actually returns. If the
    producer is updated without updating this constant, this test
    fires and points to the drift."""
    scraped = _scrape_compute_summary_keys()
    assert scraped, (
        "Could not scrape cockpit/metrics.py:_compute_summary keys — "
        "this regression test's source-parsing logic broke. The producer "
        "may still be correct; investigate."
    )
    only_in_constant = PRODUCER_SUMMARY_KEYS - scraped
    only_in_source = scraped - PRODUCER_SUMMARY_KEYS
    msg_parts = []
    if only_in_constant:
        msg_parts.append(
            "  Keys in PRODUCER_SUMMARY_KEYS but NOT in _compute_summary():"
            + "\n".join(f"\n    - {k!r}" for k in sorted(only_in_constant))
        )
    if only_in_source:
        msg_parts.append(
            "\n  Keys in _compute_summary() but NOT in PRODUCER_SUMMARY_KEYS:"
            + "\n".join(f"\n    - {k!r}" for k in sorted(only_in_source))
        )
    assert not msg_parts, (
        "\n[Layer 2a contract drift] PRODUCER_SUMMARY_KEYS constant in\n"
        "tests/test_contracts.py is out of sync with\n"
        "cockpit/metrics.py:_compute_summary.\n"
        + "\n".join(msg_parts)
        + "\n\n  Fix: update PRODUCER_SUMMARY_KEYS to match the producer's\n"
        "  emit-set. Then re-run; downstream consumer tests below may\n"
        "  newly fire if a renamed key broke a consumer contract."
    )


# Consumer paths to scan for `summary.get(...)` / `_safe_float(...)`
# / similar calls. SCAN COVERAGE is intentionally bounded to scripts/
# and core/observability (where the 13-harness + run_registry bug
# lives). Other call sites may exist in tests/ but those are intended
# for mock/stub use; including them would over-constrain.
CONSUMER_SCAN_ROOTS = ["scripts", "core/observability"]

# Regex that captures a key string from any of:
#   summary.get("Key Name", ...)
#   summary.get('Key Name')
#   _safe_float(summary, "Key Name")
#   perf.get("Key Name")
#   perf_summary.get("Key Name")
#   stats.get("Key Name")
CONSUMER_KEY_PATTERNS = [
    re.compile(r"""\bsummary\.get\(\s*["']([^"']+)["']"""),
    re.compile(r"""\bperf\.get\(\s*["']([^"']+)["']"""),
    re.compile(r"""\bperf_summary\.get\(\s*["']([^"']+)["']"""),
    re.compile(r"""\bstats\.get\(\s*["']([^"']+)["']"""),
    re.compile(r"""\b_safe_float\(\s*[a-zA-Z_]+\s*,\s*["']([^"']+)["']"""),
]


def _scan_consumer_summary_reads() -> Dict[str, List[Tuple[str, int]]]:
    """Walk CONSUMER_SCAN_ROOTS and collect every (key, [(file, line)])
    occurrence of the consumer-read patterns. Returns a dict mapping
    key → list of (relative_path, line_number)."""
    by_key: Dict[str, List[Tuple[str, int]]] = {}
    for root_rel in CONSUMER_SCAN_ROOTS:
        root = REPO / root_rel
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            try:
                lines = py_file.read_text().splitlines()
            except Exception:
                continue
            for lineno, line in enumerate(lines, start=1):
                for pat in CONSUMER_KEY_PATTERNS:
                    for m in pat.finditer(line):
                        key = m.group(1)
                        by_key.setdefault(key, []).append(
                            (str(py_file.relative_to(REPO)), lineno)
                        )
    return by_key


# Consumer-read keys that are LEGITIMATELY not in the producer's
# summary set. Document each with a short reason. Examples:
#   - 'run_id' — added by run_isolated.py to the summary AFTER
#     summary() returns; not from _compute_summary.
#   - 'Net Profit' — IS in producer; safe.
#   - keys that come from a DIFFERENT producer (e.g., MetricsEngine
#     instead of cockpit/metrics) — out of scope for this contract.
#
# Keep this allowlist MINIMAL.
KNOWN_CONSUMER_ALIAS_KEYS: Set[str] = {
    # Added by run_isolated.py / mode_controller AFTER summary().
    "run_id",
    # Mode-controller's optional fallback reads (line 1104-1106).
    # These intentionally use `.get(a) or .get(b)` to swallow nulls
    # when reading legacy snapshots. The presence test below catches
    # the spirit of the bug; allowlisting the lowercase aliases
    # acknowledges they're defensive fallbacks, not strict contracts.
    "sharpe",
    "sharpe_ratio",
    "cagr",
    "CAGR",
    "max_drawdown",
    "MDD",
    # `Trades` only appears in summary_metrics(), and some scripts
    # legitimately call summary_metrics() then read 'Trades'. We
    # cover this in PRODUCER_SUMMARY_METRICS_EXTRA_KEYS below by
    # ALSO checking against the augmented set.
}


# Keys the consumer reads but the producer does NOT emit. These are
# the LIVE silent-mismatch bugs the audit identified. The test below
# is EXPECTED to fire on each until A's T-088 lands fixes for them.
# After T-088 (which adds 'Total Trades' to _compute_summary, fixes
# 'Sortino Ratio' alignment, etc.), the test goes green.
EXPECTED_PRE_T088_VIOLATIONS: Set[str] = {
    "Total Trades",      # bug [1]: 13 harnesses; producer has 'Trades' in summary_metrics() only
    "Sortino Ratio",     # bug [2]: run_registry; producer has no Sortino at all in cockpit summary
}


def test_layer2b_consumer_keys_subset_of_producer_keys():
    """Every consumer-read summary key (in scripts/ + core/observability)
    must appear in either:
      - PRODUCER_SUMMARY_KEYS (returned by `summary()` / `summary_dict`)
      - PRODUCER_SUMMARY_METRICS_EXTRA_KEYS (returned only by `summary_metrics()`)
      - KNOWN_DOWNSTREAM_AUGMENT_KEYS (added by callers after producer)
      - KNOWN_CONSUMER_ALIAS_KEYS (documented legacy aliases)

    Failure prints the OFFENDING KEY + every consumer (file:line) that
    reads it, so the reader can patch them all in one pass."""
    by_key = _scan_consumer_summary_reads()
    legal_keys = (
        PRODUCER_SUMMARY_KEYS
        | PRODUCER_SUMMARY_METRICS_EXTRA_KEYS
        | KNOWN_DOWNSTREAM_AUGMENT_KEYS
        | KNOWN_CONSUMER_ALIAS_KEYS
    )

    violations: List[Tuple[str, List[Tuple[str, int]]]] = []
    for key, sites in sorted(by_key.items()):
        if key in legal_keys:
            continue
        violations.append((key, sites))

    if not violations:
        # No silent-mismatch reads. T-088 fully landed.
        return

    # Render a single actionable failure message listing each offending
    # key + ALL consumers that read it. Don't truncate — the reader
    # wants to know every site to fix.
    lines = [
        "\n[Layer 2b contract violation] Consumer-read summary keys not "
        "produced by cockpit/metrics.py.",
        "",
        "These are the silent-mismatch bugs: consumers `.get(key)` will "
        "return None (or _safe_float's default), corrupting the field "
        "they were meant to populate.",
        "",
        "Fix options:",
        "  1. Add the key to cockpit/metrics.py:_compute_summary "
        "(or summary_metrics for trade-count-style fields).",
        "  2. Rename the consumer's key to match an existing producer key.",
        "  3. If the key is intentional (e.g., reading a different "
        "producer), add it to KNOWN_CONSUMER_ALIAS_KEYS with a "
        "justification comment.",
        "",
        "Offending keys and their consumer sites:",
    ]
    for key, sites in violations:
        lines.append(f"  - {key!r}  (consumed at {len(sites)} site(s)):")
        for path, lineno in sites:
            lines.append(f"      {path}:{lineno}")

    pytest.fail("\n".join(lines))


def test_layer2c_expected_pre_t088_violations_documented():
    """Sanity test: after T-088 lands, this test reminds the reader to
    REMOVE the EXPECTED_PRE_T088_VIOLATIONS list and unconditionally
    fail on any new mismatch. Currently the EXPECTED set documents
    which keys WILL fire on main pre-T-088.

    This test ALWAYS passes — it just exists to anchor a TODO that
    the test-suite reviewer can see and act on when T-088 merges."""
    # Just assert the constant exists and is non-empty, so the
    # documentation in this file is discoverable.
    assert isinstance(EXPECTED_PRE_T088_VIOLATIONS, set)
    assert len(EXPECTED_PRE_T088_VIOLATIONS) >= 2
    # After T-088 lands and test_layer2b goes green, this set should
    # shrink to empty — at which point this test stays passing trivially.


# ----------------------------------------------------------------------
# Layer 3 — cross-engine signal-dict contract (DEFERRED)
# ----------------------------------------------------------------------

def test_layer3_cross_engine_signal_dict_contract_deferred():
    """The Engine A → Engine B/C per-ticker signal dict is shaped at
    runtime; its keys depend on dynamic per-bar conditions (edge
    triggers, regime context, meta-injection). Static analysis
    misses dynamic key construction; a smoke test would require a
    full backtest scaffold beyond this PR's scope (test code only,
    no engine logic per dispatch hard constraint).

    DEFERRED to a follow-up dispatch that:
      (a) defines a TypedDict / Pydantic model for the signal contract
          (proposal-first since it touches Engine A producer),
      (b) wires a runtime assertion into the producer (Engine A
          end-of-bar emit), so the contract is enforced at every
          bar regardless of test coverage,
      (c) OR runs a 1-day micro-backtest in this test file with
          mocked data + per-bar key inspection.

    The (b) approach is recommended in the audit doc. This test is
    a permanent landmark in the test file so the deferral isn't
    forgotten — when (a)/(b)/(c) lands, replace this test body with
    the actual contract check."""
    # ALWAYS PASS — this test is a landmark, not a guard.
    # See docs/Audit/contract_test_suite_t090_2026_05_31.md for the
    # full deferral rationale + follow-up dispatch sketch.
    assert True

"""Contract-test suite — permanent regression guards against the
silent-mismatch bug family.

A producer writes a key/field/column under one name; a consumer reads
it under a different name; a `.get()` default silently masks the gap.
The project has hit this family >= 9 times (cockpit peak_equity slot,
hunt() ticker=, env-config, T-055g v1 patch keys, 'Sharpe' vs
'Sharpe Ratio', run_registry 'Sortino Ratio', 13-harness 'Total Trades',
T-088 risk_per_trade rename, T-090 sweep found 7 more in vol-target
harnesses).

These tests assert INVARIANTS (config-key in dataclass-field,
consumer-read in producer-emit), not hardcoded values — so they
remain green as configs/schemas evolve, but fire the moment a new
mismatch appears.

## Layers

  Layer 1 — Config-key contract: every JSON top-level key must map
    to a dataclass field OR be in an explicit allowlist (legit alias
    or KNOWN_DEAD — dead config key, candidate for cleanup but not a
    silent-mismatch hazard right now).

  Layer 2 — Performance-summary producer/consumer key contract:
    consumer-read keys (from `summary.get(...)` patterns) must each
    be in the producer's emit-set (cockpit/metrics.py
    `_compute_summary()`) or in a known-alias allowlist.

  Layer 3 — Cross-engine signal-dict contract (DEFERRED).
    Engine A -> B/C signal dict is shaped at runtime. Right path is
    a producer-side TypedDict + runtime assert; landmark test below
    is the anchor.

## History

  T-090 (2026-05-31) — built suite; on-main 4 failures all real
    bugs (RiskConfig x 2, Layer 2a producer-stale, Layer 2b 9 keys).
  T-091 (2026-05-31) — green-up: T-088 merged + PSR added to producer
    + 6 RiskConfig keys triaged (3 legit, 3 KNOWN_DEAD) + 7 NEW bugs
    resolved (1 archived script, 2 live consumers patched).
"""
from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Dict, List, Set, Tuple

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

# Config keys that are GENUINELY DEAD in the live consuming path —
# they sit in JSON but no code reads them. Distinct from legit aliases
# (which DO have a consumer, just not the dataclass under test). This
# set explicitly tags them as "cleanup candidate, not a silent-mismatch
# hazard" so the suite stays green WHILE preserving the cleanup signal.
#
# Each entry: justify the dead-status with a one-line comment + cite
# the audit/dispatch that triaged it. Removal of these keys from the
# JSON is a propose-first Engine B config cleanup (not a test concern).
KNOWN_DEAD_CONFIG_KEYS: Set[str] = {
    # Triaged by T-091 dispatch (2026-05-31). 0 live refs in the risk
    # consuming path. Same class as T-088's risk_per_trade_pct dead-knob.
    "atr_lookback",         # Engine B risk path — dead knob, cleanup candidate
    "position_sizing",      # Engine B risk path — dead knob, cleanup candidate
    "commission_per_trade", # Engine B risk path — dead knob, cleanup candidate
}


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
    # RiskConfig — config/risk_settings.{env}.json. T-088 fixed the
    # sizing knob rename (risk_per_trade_pct + max_pos_value_pct now
    # match the dataclass). The remaining 6 keys triaged 2026-05-31:
    #   - `slippage_bps`            -> consumed via exec_params, not RiskConfig
    #   - `debug`                   -> universal flag, consumed by many components
    #   - `max_position_value`      -> intentionally-dropped absolute-$ variant
    #                                  (we use max_pos_value_pct=0.30 instead).
    #                                  See T-088 (Path-B decision pending).
    # These 3 are LEGIT aliases (allowlisted below). The other 3
    # (`atr_lookback`, `position_sizing`, `commission_per_trade`)
    # are GENUINELY DEAD config keys with zero consumers in the live
    # risk path — same class as T-088's risk_per_trade_pct Path-B
    # dead-knob finding. They go in KNOWN_DEAD_CONFIG_KEYS (below)
    # so the suite stays green WHILE preserving the signal that they
    # are real cruft, not legit aliases. Cleanup to Engine B config
    # is propose-first.
    (
        "RiskConfig vs risk_settings.prod.json",
        "config/risk_settings.prod.json",
        "engines.engine_b_risk.risk_engine",
        "RiskConfig",
        {"slippage_bps", "debug", "max_position_value"},
    ),
    (
        "RiskConfig vs risk_settings.dev.json",
        "config/risk_settings.dev.json",
        "engines.engine_b_risk.risk_engine",
        "RiskConfig",
        {"slippage_bps", "debug", "max_position_value"},
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
        if k in KNOWN_DEAD_CONFIG_KEYS:
            continue
        missing.append(k)

    assert not missing, (
        f"\n[Layer 1 contract violation] {label}\n"
        f"  JSON file: {json_path_rel}\n"
        f"  Dataclass: {import_module}.{class_name}\n"
        f"  Keys present in JSON but NOT in dataclass fields "
        f"(and not in known_aliases or KNOWN_DEAD_CONFIG_KEYS):\n"
        + "\n".join(f"    - {k!r}" for k in missing)
        + f"\n\n  These keys are SILENTLY DROPPED by the dataclass filter on load.\n"
        f"  Fix one of:\n"
        f"    1. Rename the JSON key to match the dataclass field.\n"
        f"    2. Add a field to the dataclass with a matching name.\n"
        f"    3. If the key is consumed by a DIFFERENT loader,"
        f" add to known_aliases with a justification comment.\n"
        f"    4. If the key is GENUINELY DEAD (0 consumers), add to"
        f" KNOWN_DEAD_CONFIG_KEYS as a cleanup candidate."
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
    # T-088 (2026-05-31) added trade count to the summary path. Before
    # T-088 it lived only in summary_metrics() under the legacy key
    # 'Trades', so 13 harnesses reading 'Total Trades' got None silently.
    "Total Trades",
    # T-091 (2026-05-31) added PSR (Probabilistic Sharpe Ratio) to the
    # summary path. Before T-091 PSR was computed via _engine_metrics()
    # but not surfaced in the summary dict written to
    # performance_summary.json; run_registry's _safe_float(perf, 'PSR')
    # at run_registry.py:117 silently read NULL. Per CLAUDE.md #6 PSR
    # is a headline statistic — it belongs in the summary.
    "PSR",
    # T-091 (2026-05-31) added Sortino to the summary path (same family
    # as PSR; _engine_metrics() emits it but _compute_summary did not).
    # 13 A/B harnesses read summary.get('Sortino Ratio') and got NULL;
    # this dispatch renamed those reads to 'Sortino' and emits 'Sortino'
    # here. run_registry at line 122-124 has a T-088 backward-compat
    # fallback that reads 'Sortino Ratio' from historical JSONs.
    "Sortino",
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
    # T-088 backward-compat fallback at core/observability/run_registry.py:124.
    # The canonical producer-emitted key is 'Sortino' (T-091 added that
    # emission to _compute_summary). The fallback reads 'Sortino Ratio'
    # from any historical perf_summary.json that may carry the legacy
    # name (run_benchmark.py:332 emits 'Sortino Ratio' into its own
    # summary output). If any NEW code reads 'Sortino Ratio', revert
    # this allowlist entry and treat as a real bug.
    "Sortino Ratio",
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


def test_layer2c_known_dead_config_keys_documented():
    """Landmark: KNOWN_DEAD_CONFIG_KEYS exists + every entry has a
    comment justifying its dead status. This test is a periodic-review
    nudge: when this set has been stable for a quarter, someone should
    propose an Engine B config cleanup PR to remove the dead keys from
    the JSON.

    Always passes — exists so the cleanup signal isn't lost when the
    suite is green."""
    assert isinstance(KNOWN_DEAD_CONFIG_KEYS, set)
    # If the set ever empties, this test can be deleted along with
    # the constant — at that point all configs are clean.


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

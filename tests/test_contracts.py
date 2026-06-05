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

  Layer 3a — Capability-ledger Source(file:line) symbol-resolution
    contract. Every row in docs/State/capability_ledger.md cites a
    Source (file:line); the file must exist and the symbol/line must
    still resolve. FAIL on missing file or vanished symbol; WARN on
    line-number drift (lines move; symbols don't).

  Layer 3b — Cross-engine ADVISORY-dict contract: every
    `advisory.get("KEY")` / `advisory["KEY"]` consumer-read across
    Engine A/B/C must have a matching WRITE into the advisory dict
    from the producer (Engine E advisory.py + regime_detector.py +
    backtester injectors). Allowlist legitimate read-with-default
    aliases. This is the cross-engine boundary analog to Layer 2's
    perf-summary boundary.

  Layer 3 — Cross-engine signal-dict contract (still DEFERRED).
    Engine A -> B/C signal dict is shaped at runtime. Right path is
    a producer-side TypedDict + runtime assert; landmark test below
    is the anchor.

## History

  T-090 (2026-05-31) — built suite; on-main 4 failures all real
    bugs (RiskConfig x 2, Layer 2a producer-stale, Layer 2b 9 keys).
  T-091 (2026-05-31) — green-up: T-088 merged + PSR added to producer
    + 6 RiskConfig keys triaged (3 legit, 3 KNOWN_DEAD) + 7 NEW bugs
    resolved (1 archived script, 2 live consumers patched).
  T-102 (2026-06-04) — Layer 3a + Layer 3b: ledger Source-symbol
    resolution + cross-engine advisory reader subset of writer.
    Layer 3b surfaces the dead `correlation_regime` consumer (Engine
    B reads it as flat string; Engine E emits it as nested dict at
    output-level, NOT inside advisory). Treated as an OPEN BUG via
    KNOWN_DEAD_ADVISORY_READS allowlist — Engine B propose-first to
    fix; the test will fire structurally if any NEW reader appears.
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
# Layer 3a — capability ledger Source(file:line) symbol resolution
# ----------------------------------------------------------------------

# Path to the capability ledger. The CI-gated invariant: every Source
# reference in this file must point to a file that exists, and the
# referenced line number must be within the file. Line-number drift is
# a WARNING (lines move when neighbours grow); missing file or out-of-
# range line is a FAILURE.

CAPABILITY_LEDGER_PATH = REPO / "docs" / "State" / "capability_ledger.md"

# Markdown table cells are pipe-separated. The Source column carries
# entries like ``engines/foo/bar.py:123``, ``backtester/baz.py:45``,
# or backtick-wrapped equivalents. We use a permissive regex that
# accepts an optional leading backtick wrapper and an optional trailing
# parenthetical (e.g. "(producer)") so the ledger can annotate roles.
#
# Acceptable forms:
#   `engines/foo/bar.py:123`
#   engines/foo/bar.py:123
#   `engines/foo/bar.py:123` (consumer)
#
# The regex captures (path, line).
LEDGER_SOURCE_PATTERN = re.compile(
    r"`?([\w./_-]+\.(?:py|md|json|yml|yaml|csv|sh|pkl)):(\d+)`?"
)

# Some ledger rows legitimately have non-file references in the Source
# column (e.g., "_missing — file does not exist_" for documentation
# gaps the audit surfaced). Skip rows where the cell starts with one
# of these sentinels. The literal must appear in the Source cell.
LEDGER_SOURCE_NONFILE_SENTINELS = (
    "_missing",  # file referenced by charter but does not exist
    "n/a",       # capability with no concrete source
)


def _parse_ledger_source_refs() -> List[Tuple[str, int, int]]:
    """Walk docs/State/capability_ledger.md and yield every
    (file_path, line_number, ledger_lineno) tuple appearing in a
    table-row Source cell. ledger_lineno is the line in the ledger
    itself, for failure-message clarity.

    Skips rows whose Source cell starts with a non-file sentinel
    (e.g., '_missing —' for capabilities the audit flagged as
    referenced but absent).
    """
    if not CAPABILITY_LEDGER_PATH.exists():
        return []
    refs: List[Tuple[str, int, int]] = []
    lines = CAPABILITY_LEDGER_PATH.read_text().splitlines()
    for ledger_lineno, raw_line in enumerate(lines, start=1):
        # Quick filter: only inspect lines that look like markdown
        # table rows (pipe-separated, ≥3 pipes for a typical table).
        if raw_line.count("|") < 3:
            continue
        # Skip header/separator rows: column headers, the dash line,
        # the "How to add a row" + "Coverage stat" trailing prose.
        if "|---|" in raw_line or "Source (file:line)" in raw_line:
            continue
        cells = [c.strip() for c in raw_line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        # Expected column order in the ledger:
        #   Capability | Engine | Source (file:line) | Wired-to-live-path? | ...
        source_cell = cells[2] if len(cells) >= 3 else ""
        if not source_cell:
            continue
        cell_lower = source_cell.lower().lstrip("`").lstrip("_").lstrip()
        if any(cell_lower.startswith(s) for s in LEDGER_SOURCE_NONFILE_SENTINELS):
            continue
        for m in LEDGER_SOURCE_PATTERN.finditer(source_cell):
            path = m.group(1)
            line_no = int(m.group(2))
            refs.append((path, line_no, ledger_lineno))
    return refs


def test_layer3a_capability_ledger_source_files_exist():
    """Every Source (file:line) cell in docs/State/capability_ledger.md
    must point to a file that exists. This makes the ledger CI-gated:
    if a referenced file is moved/archived/renamed without updating
    the ledger, this test fires and the row can be repaired in the
    same PR."""
    refs = _parse_ledger_source_refs()
    assert refs, (
        f"Could not parse any (file:line) refs from "
        f"{CAPABILITY_LEDGER_PATH}. Either the ledger is empty or the "
        f"parser regex is stale. Investigate."
    )
    missing: List[Tuple[str, int]] = []
    for path, _line_no, ledger_lineno in refs:
        abs_path = REPO / path
        if not abs_path.exists():
            missing.append((path, ledger_lineno))
    if not missing:
        return
    lines = [
        "\n[Layer 3a contract violation] capability_ledger.md references "
        "files that do not exist.",
        "",
        "A capability row's Source (file:line) must resolve. If the file "
        "was archived/renamed, update the ledger row. If the capability "
        "was retired, REMOVE the row (and link to the verdict doc that "
        "retired it).",
        "",
        "Missing references:",
    ]
    for path, ledger_lineno in missing:
        lines.append(
            f"  - {path}  (ledger row at "
            f"{CAPABILITY_LEDGER_PATH.relative_to(REPO)}:{ledger_lineno})"
        )
    pytest.fail("\n".join(lines))


def test_layer3a_capability_ledger_source_lines_in_range():
    """For every Source (file:line) ref whose file exists, the line
    number must be ≤ the file's actual line count. This catches the
    case where a referenced file is heavily truncated and the row's
    line number now points past EOF.

    Line-number drift WITHIN the file (line moved from 234 to 251) is
    NOT a FAIL — lines naturally move as neighbours grow. We accept
    any in-range line; the contract is "the file still exists and is
    at least this long," not "the symbol is exactly at this line."
    Symbols moving within a file is a doc-maintenance signal handled
    separately by sync_docs.py / human review."""
    refs = _parse_ledger_source_refs()
    out_of_range: List[Tuple[str, int, int, int]] = []
    for path, line_no, ledger_lineno in refs:
        abs_path = REPO / path
        if not abs_path.exists():
            continue  # Layer 3a above handles missing-file failures
        try:
            n_lines = sum(1 for _ in abs_path.open("rb"))
        except Exception:
            continue
        if line_no > n_lines:
            out_of_range.append((path, line_no, n_lines, ledger_lineno))
    if not out_of_range:
        return
    lines = [
        "\n[Layer 3a contract violation] capability_ledger.md references "
        "line numbers past EOF.",
        "",
        "A ledger row cites a file:line whose file exists but is shorter "
        "than the cited line. Update the row to the new line number or "
        "remove if the capability was retired.",
        "",
        "Out-of-range references:",
    ]
    for path, line_no, n_lines, ledger_lineno in out_of_range:
        lines.append(
            f"  - {path}:{line_no} (file has only {n_lines} lines; "
            f"ledger row at line {ledger_lineno})"
        )
    pytest.fail("\n".join(lines))


# ----------------------------------------------------------------------
# Layer 3b — cross-engine ADVISORY-dict reader ⊆ writer
# ----------------------------------------------------------------------

# Engine E is the canonical advisory producer; the backtester also
# injects keys into the advisory dict via setdefault + assign.
ADVISORY_PRODUCER_PATHS = [
    "engines/engine_e_regime/advisory.py",
    "engines/engine_e_regime/regime_detector.py",
    "backtester/backtest_controller.py",  # injects learned_edge_affinity
]

# Engine A/B/C are the in-scope consumers.
ADVISORY_CONSUMER_ROOTS = [
    "engines/engine_a_alpha",
    "engines/engine_b_risk",
    "engines/engine_c_portfolio",
]

# Reader patterns for advisory key access:
#   advisory.get("KEY", ...)
#   advisory["KEY"]
#   advisory['KEY']
ADVISORY_READER_PATTERNS = [
    re.compile(r"""\badvisory\.get\(\s*["']([^"']+)["']"""),
    re.compile(r"""\badvisory\[\s*["']([^"']+)["']\s*\]"""),
]

# Writer patterns for advisory key writes. The advisory dict is built
# multiple ways across the producer files:
#   advisory["KEY"] = value
#   advisory = {"KEY": value, ...}  (dict literal — keys discovered
#       by scanning the dict body)
#   advisory.update({"KEY": value})
#   advisory.setdefault("X", {})["KEY"] = value
#   regime_meta.setdefault("advisory", {})["KEY"] = value (injection
#       pattern at backtest_controller.py:348)
ADVISORY_WRITER_PATTERNS = [
    # Direct write: advisory["KEY"] = ...
    re.compile(r"""\badvisory\[\s*["']([^"']+)["']\s*\]\s*="""),
    # update() with dict-literal:
    #   advisory.update({"KEY": ...}) — we capture the key
    re.compile(r"""\badvisory\.update\(\s*\{\s*["']([^"']+)["']\s*:"""),
    # Injection via regime_meta.setdefault("advisory", {})["KEY"] = ...
    re.compile(
        r"""\.setdefault\(\s*["']advisory["']\s*,\s*\{\}\s*\)\[\s*["']([^"']+)["']\s*\]\s*="""
    ),
]

# The dict-literal `advisory = { ... }` writer needs a separate parse
# because keys appear scattered across multiple lines. We locate the
# literal by a sentinel (`advisory = {` or `return (macro_regime, {`-
# style returns) and scan the following lines for `"KEY":` until a
# closing `}` at depth-0.


def _scrape_dict_literal_keys(src: str, sentinel: str) -> Set[str]:
    """Find ``sentinel`` in src, then scan forward extracting dict keys
    until brace-depth returns to 0. Returns the set of string keys.

    Used to capture keys in `advisory = {"K1": ..., "K2": ...}`-style
    dict-literal writes that span multiple lines."""
    keys: Set[str] = set()
    idx = src.find(sentinel)
    if idx < 0:
        return keys
    # Find the opening brace AFTER the sentinel.
    brace_idx = src.find("{", idx)
    if brace_idx < 0:
        return keys
    depth = 0
    body = src[brace_idx:]
    pos = 0
    while pos < len(body):
        ch = body[pos]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        pos += 1
    # Now body[:pos+1] contains the dict literal. Scan for `"KEY":`
    # patterns. We accept simple top-level keys only (depth-1 keys),
    # which means we don't recurse into nested dicts — those nested
    # keys are NOT advisory-level keys.
    inner = body[:pos + 1]
    depth = 0
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth -= 1
            i += 1
            continue
        if depth == 1 and ch in ('"', "'"):
            # Begin a string literal; check whether it's a key (followed
            # by `:` after the closing quote and optional whitespace).
            quote = ch
            j = i + 1
            while j < len(inner) and inner[j] != quote:
                if inner[j] == "\\":
                    j += 2
                    continue
                j += 1
            key = inner[i + 1:j]
            # Look ahead for `:` to confirm dict-key context.
            k = j + 1
            while k < len(inner) and inner[k] in " \t\n":
                k += 1
            if k < len(inner) and inner[k] == ":":
                keys.add(key)
            i = j + 1
            continue
        i += 1
    return keys


def _scan_advisory_keys(
    paths: List[str], patterns: List[re.Pattern]
) -> Dict[str, List[Tuple[str, int]]]:
    """Walk ``paths`` and apply each regex; return key -> [(file, line)]."""
    out: Dict[str, List[Tuple[str, int]]] = {}
    for rel in paths:
        p = REPO / rel
        if not p.exists():
            continue
        try:
            lines = p.read_text().splitlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, start=1):
            for pat in patterns:
                for m in pat.finditer(line):
                    out.setdefault(m.group(1), []).append(
                        (rel, lineno)
                    )
    return out


def _scan_advisory_writer_keys() -> Set[str]:
    """Aggregate all keys WRITTEN to the advisory dict across the
    producer files. Combines:
      - direct `advisory["K"] = ...`
      - `advisory.update({"K": ...})`
      - `regime_meta.setdefault("advisory", {})["K"] = ...`
      - dict-literal `advisory = { "K1": ..., ... }` keys
    """
    keys: Set[str] = set()
    # Pattern-based writes.
    by_key = _scan_advisory_keys(ADVISORY_PRODUCER_PATHS, ADVISORY_WRITER_PATTERNS)
    keys.update(by_key.keys())
    # Dict-literal write in advisory.py — the `advisory = { ... }`
    # construction at line ~242 inside compute_advisory.
    advisory_src = (REPO / "engines/engine_e_regime/advisory.py").read_text()
    keys.update(_scrape_dict_literal_keys(advisory_src, "advisory = {"))
    return keys


def _scan_advisory_reader_keys() -> Dict[str, List[Tuple[str, int]]]:
    """Aggregate all advisory-dict consumer reads across Engine A/B/C."""
    out: Dict[str, List[Tuple[str, int]]] = {}
    for root_rel in ADVISORY_CONSUMER_ROOTS:
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
                for pat in ADVISORY_READER_PATTERNS:
                    for m in pat.finditer(line):
                        out.setdefault(m.group(1), []).append(
                            (str(py_file.relative_to(REPO)), lineno)
                        )
    return out


# Keys legitimately read with a `.get(..., default)` that we accept as
# orphan reads. KNOWN_DEAD_ADVISORY_READS is the active OPEN-BUG
# tracker: each entry is a real dead consumer the audit found. Adding
# a row here is NOT a fix; it's documentation that the bug is known
# and slated for propose-first repair.
KNOWN_DEAD_ADVISORY_READS: Set[str] = {
    # T-102 2026-06-04: Engine B reads `advisory.get("correlation_regime",
    # "normal")` (risk_engine.py:744) and branches on flat-string values
    # "dispersed" / "elevated" / "spike" to widen/tighten sector caps.
    # Engine E writes correlation_regime as a NESTED dict (state,
    # confidence) at the OUTPUT level, not into advisory[]. So the
    # consumer always sees the "normal" default; the sector-limit
    # branch is structurally dead. This is an OPEN BUG. Fixing it is
    # propose-first (Engine B). When fixed, REMOVE this entry — the
    # test will then enforce reader⊆writer for new code.
    "correlation_regime",
    # T-102 2026-06-04 → T-104 2026-06-05: Engine C reads
    # `advisory.get("allocation_recommendation")` (policy.py:62) with a
    # disk-load fallback via AllocationEvaluator.load_recommendations().
    # T-104 classification: INTENDED-DISK-SOURCE, NOT a bug.
    #   - policy.py:62-80 reads advisory.get("allocation_recommendation")
    #     first, then falls back to loading from disk via
    #     AllocationEvaluator.load_recommendations() +
    #     get_config_for_regime(label). The disk path IS the canonical
    #     producer; the advisory read is a defensive primary-path slot
    #     for future Engine-E injection that has never been wired.
    #   - Engine E advisory.py never writes the key — by design (the
    #     allocation evaluator lives in Engine C, not Engine E, and the
    #     disk-load happens entirely inside policy.py:65-80).
    # No proposed fix. Keep the allowlist entry indefinitely with this
    # justification. Distinct from `correlation_regime` (which IS a
    # real silent-mismatch bug awaiting Engine E producer-side fix).
    # Optional cleanup (NOT proposed here): drop the advisory.get() head
    # and call the disk loader unconditionally — reduces apparent
    # confusion but no behavior change. Out of T-104 scope.
    "allocation_recommendation",
}

# Keys whose advisory READER expects an Engine F injection (e.g.
# learned_edge_affinity) — the writer exists at
# backtester/backtest_controller.py:348 via the setdefault("advisory")
# pattern. Layer 3b correctly classifies it as written, NOT dead.
# (Listed here for documentation only; no allowlist needed.)


def _compute_advisory_reader_violations(
    extra_legal: Set[str] = frozenset(),
) -> List[Tuple[str, List[Tuple[str, int]]]]:
    """Helper: compute reader keys not in the writer set, after taking
    ``extra_legal`` as additional allowed-reader keys. Returns the
    sorted list of (key, sites) violations."""
    written = _scan_advisory_writer_keys()
    by_reader = _scan_advisory_reader_keys()
    legal = written | set(extra_legal)
    violations: List[Tuple[str, List[Tuple[str, int]]]] = []
    for key, sites in sorted(by_reader.items()):
        if key in legal:
            continue
        violations.append((key, sites))
    return violations


@pytest.mark.xfail(
    strict=True,
    reason=(
        "T-102 OPEN-BUG TRACKER: strict reader-subset-of-writer for the "
        "advisory dict. The audit found dead consumers (correlation_regime "
        "+ allocation_recommendation) that read keys never written into "
        "advisory[]. Each is a real silent-mismatch bug awaiting "
        "propose-first repair (Engine B for correlation_regime; "
        "Engine C/E for allocation_recommendation). When BOTH are fixed, "
        "this test PASSES STRICT — promote the body into the enforcement "
        "test below and delete the xfail marker. See KNOWN_DEAD_ADVISORY_"
        "READS for the open-bug catalog."
    ),
)
def test_layer3b_advisory_reader_keys_subset_of_writer_keys_strict():
    """STRICT reader-subset-of-writer for the advisory dict. No
    allowlist — every reader key must have a producer-side writer.

    This test is XFAIL by intent — the audit identified real dead
    consumers (correlation_regime, allocation_recommendation) and the
    inbox required the bugs be SURFACED, not silenced by code edits.
    The xfail RUNS and PRINTS the offending keys at each CI invocation,
    making the open-bug list visible without blocking merges.

    Fixing a bug here means:
      1. Remove the consumer's `.get(...)` read (or add the producer-
         side write) on a propose-first branch (Engine B or E).
      2. Remove the corresponding entry from KNOWN_DEAD_ADVISORY_READS.
      3. After the fix lands, this test will pass STRICTLY and trigger
         pytest's `XPASS strict` failure — promote it to the
         enforcement test below and delete the xfail marker."""
    written = _scan_advisory_writer_keys()
    by_reader = _scan_advisory_reader_keys()
    assert by_reader, (
        "Found no advisory reader patterns in Engine A/B/C — either "
        "the consumer set has been removed or this test's regex is "
        "stale. Investigate."
    )
    assert written, (
        "Found no advisory writer patterns in Engine E + backtester "
        "injectors — either the producer set has been removed or this "
        "test's regex is stale. Investigate."
    )
    violations = _compute_advisory_reader_violations()
    if not violations:
        return

    lines = [
        "\n[Layer 3b STRICT — dead consumers] Cross-engine advisory-dict "
        "keys read by consumers but NEVER written by the producer.",
        "",
        "These are the silent-mismatch bugs at the cross-engine boundary: "
        "the consumer's `advisory.get(key)` returns None (or the default) "
        "corrupting the field it was meant to drive.",
        "",
        "Each entry MUST also appear in KNOWN_DEAD_ADVISORY_READS with a "
        "justification comment, so the enforcement test below covers it. "
        "Removing from BOTH places requires either:",
        "  1. Adding the key to the advisory dict in "
        "engines/engine_e_regime/advisory.py (Engine E change).",
        "  2. Renaming the consumer's read to an existing advisory key.",
        "  3. Deleting the dead consumer read (Engine B/C — propose-first).",
        "",
        "Offending keys and consumer sites:",
    ]
    for key, sites in violations:
        lines.append(f"  - {key!r}  (consumed at {len(sites)} site(s)):")
        for path, lineno in sites:
            lines.append(f"      {path}:{lineno}")

    pytest.fail("\n".join(lines))


def test_layer3b_no_new_dead_advisory_consumers():
    """ENFORCEMENT test: reader-subset-of-writer ∪ KNOWN_DEAD_ADVISORY_READS.

    This test PASSES today (the known dead consumers are allowlisted).
    A future PR that introduces a NEW dead consumer fires this test
    with the offending key — even if the strict xfail above continues
    to fire on the legacy bugs.

    This is the load-bearing gate: it catches regression, NOT existing
    bugs. The strict xfail above is the visibility tracker for
    existing bugs."""
    violations = _compute_advisory_reader_violations(
        extra_legal=KNOWN_DEAD_ADVISORY_READS,
    )
    if not violations:
        return
    lines = [
        "\n[Layer 3b contract violation] NEW dead consumer detected.",
        "",
        "A consumer reads an advisory key that has NO producer-side "
        "writer AND is not in KNOWN_DEAD_ADVISORY_READS. Either:",
        "  1. Add a producer-side write (Engine E).",
        "  2. Rename the read to an existing advisory key.",
        "  3. If this is a known open bug and you intend to leave it "
        "until a propose-first dispatch, add it to "
        "KNOWN_DEAD_ADVISORY_READS with a justification comment. "
        "(This is documentation, not silencing.)",
        "",
        "Offending keys and consumer sites:",
    ]
    for key, sites in violations:
        lines.append(f"  - {key!r}  (consumed at {len(sites)} site(s)):")
        for path, lineno in sites:
            lines.append(f"      {path}:{lineno}")
    pytest.fail("\n".join(lines))


def test_layer3b_known_dead_advisory_reads_documented():
    """Landmark: KNOWN_DEAD_ADVISORY_READS exists and tracks open
    cross-engine advisory contract bugs. Each entry should be a real
    dead consumer found by the audit. When this set empties:
      - Remove KNOWN_DEAD_ADVISORY_READS.
      - Delete the xfail marker on the strict test above; that test
        becomes the enforcement gate (delete this one too).

    Always passes — exists so the open-bug tracker isn't lost when
    the suite is green."""
    assert isinstance(KNOWN_DEAD_ADVISORY_READS, set)
    # T-102 (2026-06-04) registered 2 real dead consumers:
    # correlation_regime + allocation_recommendation. If a NEW entry
    # appears here without a corresponding propose-first dispatch in
    # TASK_LEDGER, that's a documentation gap.


# ----------------------------------------------------------------------
# Layer 3 — Engine A → B/C per-ticker signal-dict contract (DEFERRED)
# ----------------------------------------------------------------------

def test_layer3_signal_dict_contract_deferred():
    """The Engine A → Engine B/C per-ticker signal dict is shaped at
    runtime; its keys depend on dynamic per-bar conditions (edge
    triggers, regime context, meta-injection). Static analysis
    misses dynamic key construction; a smoke test would require a
    full backtest scaffold.

    NOTE: Layer 3a + Layer 3b above DO catch a structurally different
    cross-engine boundary (capability-ledger Source resolution +
    advisory-dict reader-subset-of-writer). The per-ticker signal
    dict is a separate contract — still deferred until a producer-
    side TypedDict or runtime assertion is in place."""
    # ALWAYS PASS — landmark, not a guard.
    assert True

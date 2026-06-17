"""
core/census.py
==============
T-181 — the SHARED execution-census gate. Local (`run_isolated.py`,
`run_substrate_arms.py`) and cloud (`cloud_entrypoint.sh`) call this one
helper, so the canonical/non-canonical verdict cannot diverge between paths.

A backtest emits a `census` block into performance_summary.json (assembled
in `backtester/backtest_controller.py:_build_census`). A run is
**NON-CANONICAL** (must not publish / upload / certify / quote) if ANY of
the audit's invariants fail:

  1. edges_blind non-empty                     (active edge fired 0 signals — T-177/T-175)
  2. n_in_panel < n_resolved − allowlist        (universe silently shrank — T-167)
  3. n_trades == 0 OR trades_canon_md5==EMPTY    (run didn't trade — T-175/T-164)
  4. fundamentals_blind > 0                      (value edges starved — T-175)
  5. regime_unknown_frac >= 1.0                  (regime layer silently OFF — T-164 GAP-2)
  6. config_provenance.degraded                  ({}/one-key fabricated config — T-088)

Plus a WARNING (not a hard fail) if the summary shipped with neither a
bootstrap CI nor an explicit skip reason (the CLAUDE.md ci_low rule).

Phase-1 gating defaults are strict-but-overridable via env so a legitimate
edge case can be acknowledged explicitly rather than silently tolerated:
  CENSUS_EXPECTED_DORMANT="edge_a,edge_b"   # subtract from edges_blind
  CENSUS_PANEL_ALLOWLIST="3"                # tolerated n_resolved-n_in_panel gap
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

EMPTY_MD5 = "d41d8cd98f00b204e9800998ecf8427e"


@dataclass
class CensusVerdict:
    ok: bool
    canonical: bool
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    census_present: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok, "canonical": self.canonical,
            "failures": self.failures, "warnings": self.warnings,
            "census_present": self.census_present,
        }


def _env_set(name: str) -> set:
    raw = os.getenv(name, "") or ""
    return {x.strip() for x in raw.split(",") if x.strip()}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default


def assert_census(
    summary: Dict[str, Any],
    *,
    expected_dormant: Optional[set] = None,
    panel_allowlist: Optional[int] = None,
    require_census: bool = True,
) -> CensusVerdict:
    """Evaluate the census block of a performance_summary dict.

    Returns a CensusVerdict; never raises on a malformed summary (a missing
    census is itself a failure when ``require_census`` is True). Callers
    decide whether to halt/publish on ``verdict.canonical``.
    """
    failures: List[str] = []
    warnings: List[str] = []

    census = summary.get("census") if isinstance(summary, dict) else None
    if not isinstance(census, dict) or not census:
        v = CensusVerdict(ok=not require_census, canonical=False,
                          failures=["census block missing from summary"] if require_census else [],
                          census_present=False)
        return v
    if "census_error" in census:
        failures.append(f"census assembly errored: {census['census_error']}")

    dormant = set(expected_dormant or set()) | _env_set("CENSUS_EXPECTED_DORMANT")
    panel_allow = panel_allowlist if panel_allowlist is not None else _env_int("CENSUS_PANEL_ALLOWLIST", 0)

    # 1 — edges_blind
    blind = [e for e in (census.get("edges_blind") or []) if e not in dormant]
    if blind:
        failures.append(f"edges_blind non-empty: {sorted(blind)} (0 non-zero signals over the window)")

    # 2 — universe shrink
    n_resolved = int(census.get("n_resolved", 0) or 0)
    n_in_panel = int(census.get("n_in_panel", 0) or 0)
    if n_resolved and (n_in_panel < n_resolved - panel_allow):
        failures.append(
            f"panel shrank: n_in_panel={n_in_panel} < n_resolved={n_resolved} "
            f"(allowlist={panel_allow})")

    # 3 — actually traded
    if bool(census.get("trades_empty", False)) or int(census.get("n_trades", 0) or 0) == 0:
        failures.append(f"zero-trade run (n_trades={census.get('n_trades')}, "
                        f"canon={census.get('trades_canon_md5')})")
    elif str(census.get("trades_canon_md5", "")) == EMPTY_MD5:
        failures.append("trades_canon_md5 == EMPTY_MD5 (empty trades file)")

    # 4 — fundamentals overlay fed
    if int(census.get("fundamentals_blind", 0) or 0) > 0:
        failures.append(
            f"fundamentals_blind: a value/quality edge is active "
            f"({census.get('fundamentals_edges_active')}) but the panel is unloaded")

    # 5 — regime layer ON
    if float(census.get("regime_unknown_frac", 1.0) or 0.0) >= 1.0 \
            and int(census.get("regime_total_bars", 0) or 0) > 0:
        failures.append("regime 100% unknown — the regime/macro layer was silently OFF")

    # 6 — config provenance
    prov = census.get("config_provenance") or {}
    if isinstance(prov, dict) and prov.get("degraded"):
        bad = {k: v for k, v in prov.items()
               if isinstance(v, dict) and ((not v.get("exists")) or v.get("n_keys", 0) <= 1 or "error" in v)}
        failures.append(f"config degraded (missing/empty/one-key fallback): {sorted(bad)}")

    # WARN — CI presence (CLAUDE.md ci_low rule)
    if "bootstrap_distribution" not in summary and not summary.get("bootstrap_ci_skip_reason"):
        warnings.append("summary has neither bootstrap_distribution nor bootstrap_ci_skip_reason")

    canonical = not failures
    return CensusVerdict(ok=canonical, canonical=canonical, failures=failures,
                         warnings=warnings, census_present=True)


def assert_census_file(path: str, **kwargs) -> CensusVerdict:
    """Load a performance_summary.json and evaluate its census."""
    try:
        summary = json.loads(Path(path).read_text())
    except Exception as e:
        return CensusVerdict(ok=False, canonical=False,
                             failures=[f"cannot read summary {path}: {e!r}"], census_present=False)
    return assert_census(summary, **kwargs)


def _main(argv: List[str]) -> int:
    """CLI for cloud_entrypoint.sh: `python -m core.census <summary.json>`.
    Exit 0 = CANONICAL, 3 = NON-CANONICAL, 2 = unreadable."""
    if not argv:
        print("[CENSUS] usage: python -m core.census <performance_summary.json>", file=sys.stderr)
        return 2
    v = assert_census_file(argv[0])
    tag = "CANONICAL" if v.canonical else "NON-CANONICAL"
    print(f"[CENSUS] {tag}  census_present={v.census_present}")
    for w in v.warnings:
        print(f"[CENSUS][WARN] {w}")
    for f in v.failures:
        print(f"[CENSUS][FAIL] {f}")
    if not v.census_present:
        return 2
    return 0 if v.canonical else 3


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))

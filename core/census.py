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
  2. n_in_panel < n_resolved − allowlist        (universe silently shrank — T-167);
     n_resolved ABSENT (never set) or 0 fails too (no silent zero, 2026-10-15)
  3. n_trades == 0 OR trades_canon_md5==EMPTY    (run didn't trade — T-175/T-164)
  4. fundamentals_blind > 0                      (value edges starved — T-175)
  5. regime_unknown_frac >= 1.0                  (regime layer silently OFF — T-164 GAP-2);
     regime_total_bars ABSENT or 0 fails; a declared regime_layer "off" needs regime_off_label
  6. config_provenance.degraded                  ({}/one-key fabricated config — T-088)
  7. data_feed.yfinance_tickers non-empty         (network fed yfinance: source + basis switch — C-2)
  Invariants 2 and 5 apply to a BACKTEST census; a census declaring census_kind "candidate"
  (Discovery's Gate-1) is not asked for them. An undeclared census is treated as a backtest.
  8. any `<block>_error` record, or an errored data_feed / data_exclusions / ticker_exclusions /
     level_declarations / stale_files record
  9. stale_files: any UNDECLARED live name that ends before its required end (the earlier of the
     window end and its exit) or is holed inside its required spans, or a reference calendar that
     is holed or unverified — `coverage_defects`, shared with the measured-run admission
     (BARS, never file presence — the stale/holed-files guard, 2026-10-15)
                                                 (a census block that crashed measured nothing — R, 2026-10-15)

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


def coverage_defects(sf: Dict[str, Any]) -> List[str]:
    """Invariant 9's reading of a `stale_files` record — the ONE reader the census gate and the
    measured-run admission (orchestration/mode_controller.py) share, so the two cannot disagree on
    what fails. [] means clean. A calendar that was never checked is a failure, not a pass: hole
    counts against an unproven calendar are not a measurement."""
    out: List[str] = []
    if sf.get("n_stale"):
        bad = sorted(t for t, v in (sf.get("names") or {}).items()
                     if v.get("ends_before_required") and not v.get("end_declared_as_delisting"))
        out.append(f"stale_files: {sf['n_stale']} undeclared name(s) END before their required end "
                   f"(the earlier of the window end and the exit) — read as 'stopped trading', the "
                   f"write-time band class: {', '.join(bad[:10])}")
    if sf.get("n_holed"):
        bad = sorted(t for t, v in (sf.get("names") or {}).items() if v.get("undeclared_missing_days"))
        out.append(f"stale_files: {sf['n_holed']} name(s) HOLED inside their required spans beyond "
                   f"their declarations: {', '.join(bad[:10])}")
    cal = sf.get("calendar") or {}
    if not cal.get("checked_against"):
        out.append("stale_files: the reference calendar is UNVERIFIED — no SPY in the run's data to "
                   "prove it against")
    if cal.get("spy_missing_days"):
        out.append(f"stale_files: SPY is holed — it lacks {len(cal['spy_missing_days'])} majority "
                   f"trading day(s) inside its own span")
    if cal.get("calendar_missing_days"):
        out.append(f"stale_files: the reference calendar is holed — the majority of names lack "
                   f"{len(cal['calendar_missing_days'])} day(s) SPY traded: "
                   f"{', '.join(cal['calendar_missing_days'][:5])}")
    return out


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
    # A census block that CRASHED is not a measurement ([NN-FAIL-CLOSED], [NN-CENSUS]). Every
    # except branch in `_build_census` records `<block>_error`; the gate fails on it. Before this,
    # the edges block's except ALSO wrote edges_blind=[] / edges_errored={} and this gate never read
    # `edges_blind_error` — a crash in the edges census PASSED invariants 1 and 1b (Agent R).
    for k in sorted(census):
        if k.endswith("_error") and k != "census_error":
            failures.append(f"census block errored ({k}): {census[k]} — that invariant was never measured")
    for key in ("data_exclusions", "ticker_exclusions", "level_declarations", "stale_files"):
        excl = census.get(key)
        if isinstance(excl, dict) and "error" in excl:
            failures.append(f"{key} record errored: {excl['error']} — what was withheld is unknown")
    # 9 — the stale/holed-files guard: counts BARS, never file presence (2026-10-15)
    sf = census.get("stale_files")
    if isinstance(sf, dict) and "error" not in sf:
        failures.extend(coverage_defects(sf))

    dormant = set(expected_dormant or set()) | _env_set("CENSUS_EXPECTED_DORMANT")
    panel_allow = panel_allowlist if panel_allowlist is not None else _env_int("CENSUS_PANEL_ALLOWLIST", 0)

    # 1 — edges_blind
    blind = [e for e in (census.get("edges_blind") or []) if e not in dormant]
    if blind:
        failures.append(f"edges_blind non-empty: {sorted(blind)} (0 non-zero signals over the window)")

    # 1b — edges_errored (T-199). A swallowed edge crash is NEVER a legitimate
    # no-signal, so unlike edges_blind there is NO allowlist: any caught
    # exception in the signal_collector canon path → NON-CANONICAL. This
    # catches a PARTIAL crash (an edge that dies on some bars but fires on
    # others) that edges_blind structurally misses.
    errored = census.get("edges_errored") or {}
    if errored:
        detail = {e: (v.get("crash_bars") if isinstance(v, dict) else v) for e, v in errored.items()}
        failures.append(f"edges_errored non-empty: {detail} — an edge raised + was "
                        f"swallowed on some bars (partial crash, not a no-signal)")

    # Which census. A Gate-1 CANDIDATE census declares itself and is not asked for the backtest
    # run-shape counters; an UNDECLARED census is treated as the strictest kind, a backtest.
    is_backtest = census.get("census_kind", "backtest") != "candidate"

    # 2 — universe shrink. NO silent zero (ruling 2026-10-15): this used to SKIP when n_resolved read
    # 0, so a run that never set the counter passed unmeasured. Absent = "counter never set"; a
    # measured 0 = no universe; both fail.
    n_in_panel = int(census.get("n_in_panel", 0) or 0)
    if is_backtest:
        if "n_resolved" not in census:
            failures.append("n_resolved: counter never set — the universe was never measured")
        else:
            n_resolved = int(census["n_resolved"] or 0)
            if n_resolved <= 0:
                failures.append("n_resolved == 0 — no universe was resolved")
            elif n_in_panel < n_resolved - panel_allow:
                failures.append(
                    f"panel shrank: n_in_panel={n_in_panel} < n_resolved={n_resolved} "
                    f"(allowlist={panel_allow})")

    # 3 — actually traded. `n_trades <= 0`, not `== 0`: the trades block's except branch writes the
    # sentinel n_trades=-1 ("count unknown"), which the `== 0` form read as a valid count (found by
    # the Layer-2d except-branch contract, 2026-10-15).
    if bool(census.get("trades_empty", False)) or int(census.get("n_trades", 0) or 0) <= 0:
        failures.append(f"zero-trade run (n_trades={census.get('n_trades')}, "
                        f"canon={census.get('trades_canon_md5')})")
    elif str(census.get("trades_canon_md5", "")) == EMPTY_MD5:
        failures.append("trades_canon_md5 == EMPTY_MD5 (empty trades file)")

    # 4 — fundamentals overlay fed
    if int(census.get("fundamentals_blind", 0) or 0) > 0:
        failures.append(
            f"fundamentals_blind: a value/quality edge is active "
            f"({census.get('fundamentals_edges_active')}) but the panel is unloaded")

    # 5 — regime layer ON. NO silent zero (ruling 2026-10-15): this used to pass when
    # regime_total_bars read 0. Absent = "counter never set"; a measured 0 = the layer produced
    # nothing; both fail. A layer OFF BY DESIGN is declared (regime_layer: "off") and is canonical
    # only with the pre-registration's label recorded in the census (regime_off_label).
    if is_backtest:
        if census.get("regime_layer") == "off":
            if not str(census.get("regime_off_label") or "").strip():
                failures.append("regime layer OFF with no pre-registered label — a run without the "
                                "regime layer is a different experiment (set CENSUS_REGIME_OFF_LABEL "
                                "to the brief that declares the layer off by design)")
        elif "regime_total_bars" not in census:
            failures.append("regime_total_bars: counter never set — the regime layer was never measured")
        elif int(census["regime_total_bars"] or 0) <= 0:
            failures.append("regime_total_bars == 0 — the regime layer produced nothing")
        elif float(census.get("regime_unknown_frac", 1.0) or 0.0) >= 1.0:
            failures.append("regime 100% unknown — the regime/macro layer was silently OFF")

    # 6 — config provenance
    prov = census.get("config_provenance") or {}
    if isinstance(prov, dict) and prov.get("degraded"):
        bad = {k: v for k, v in prov.items()
               if isinstance(v, dict) and ((not v.get("exists")) or v.get("n_keys", 0) <= 1 or "error" in v)}
        failures.append(f"config degraded (missing/empty/one-key fallback): {sorted(bad)}")

    # 7 — data-feed provenance (ruling C-2, 2026-10-15). A ticker the network fed from
    # yfinance switched SOURCE and ADJUSTMENT BASIS mid-substrate (the T-088 class).
    feed = census.get("data_feed")
    if isinstance(feed, dict):
        if "error" in feed:
            failures.append(f"data_feed record errored: {feed['error']} — the run's sources are unknown")
        elif feed.get("yfinance_tickers"):
            yf = list(feed["yfinance_tickers"])
            failures.append(
                f"data feed switched to yfinance for {len(yf)} ticker(s) "
                f"{yf[:10]}{' …' if len(yf) > 10 else ''} — a different source and adjustment "
                f"basis entered the substrate ([NN-FAIL-CLOSED]/T-088)")
    else:
        warnings.append("census has no data_feed record (summary predates 2026-10-15) — "
                        "the run's data sources are unrecorded")

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

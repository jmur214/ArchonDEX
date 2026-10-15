"""Direct readers of the per-ticker processed cache go through the ticker exclusion, or say why not
(Agent R's LOW unit, ruled with the ticker-exclusion unit, 2026-10-15).

The ticker exclusion (AZO/MTD/NVR/SLE; DAL's pre-2007 rows) is applied at universe RESOLUTION and in
membership. A script that globs `*_1d.csv` or formats `{t}_1d.csv` under data/processed bypasses
both, and no code hook exists for a `pd.read_csv` on a path. So new code is held at the contract:
every non-Archive script that reads the per-ticker processed cache that way must either read
through `resolve_universe` / `withhold_declared_tickers` (an AST CALL in the module — never text) or
carry the literal marker `# ticker-exclusions: bypassed — <reason>` beside the read (on its line or
the two above). The 63 scripts the cutover proposal's §5.1 glob classified are grandfathered by
NAME: they are RE-LABELLED with the dated caveat, none is a measurement of record, and the hole
closes at the data level on cutover day.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT_DIRS = ("scripts", "research")
MARKER = "# ticker-exclusions: bypassed — "
THROUGH = {"resolve_universe", "withhold_declared_tickers"}
#: The per-ticker cache's file suffixes (the cache keeps a csv and a parquet twin per ticker; a read
#: of either bypasses the exclusion — §5.1's own rule matched both).
PER_TICKER_SUFFIXES = ("_1d.csv", "_1d.parquet")

#: The cutover proposal §5.1's 63 (its rule: `_1d.csv|_1d.parquet` and "processed", `_t<NNN>`
#: names, scripts/ and research/), frozen 2026-10-15. Never grows: a new reader complies.
GRANDFATHERED = frozenset("""
    accumulation_model_t283.py analyze_13f_crowding_t145.py analyze_8k_events_t137.py
    analyze_bab_deep_t129.py analyze_bab_factor_t123.py analyze_overnight_intraday_t135.py
    analyze_vrp_factor_t122.py anon_historical_eval_t339.py anon_historical_eval_t339b.py
    assess_vol_collapse_t153.py asymmetric_damping_t298.py asymmetric_exits_gauntlet_t269.py
    backfill_t052_macro_data.py breadth_tilt_t273.py btc_arm_t272.py
    build_multidecade_substrate_t306.py build_ohlc_features_t150.py build_pit_cap_history_t219.py
    calendar_flow_probe_t250.py capital_tier_gauntlet_t278.py carry_sleeve_gauntlet_t247.py
    cef_lowerbound_probe_t267.py compose_voltarget_t262.py conditional_voltarget_gauntlet_t252.py
    contribution_rule_t299.py defensive_tilt_screens_t205.py demo_auction_execution_t146.py
    demo_position_buffering_t148.py dividend_reconcile_t287.py dividend_strip_audit_t337.py
    event_interaction_t291.py evenweek_sleeve_t268.py fair_t236_rerun_t255.py
    fetch_8k_edgar_t137.py fullequity_gated_leverage_t284.py income_leg_screener_t261.py
    integer_share_sleeve_t257.py interaction_diagnostic_t132.py intraday_probe_t270.py
    measure_pit_strategy_t154.py measure_survivor_inflation_t136.py multiasset_carry_gauntlet_t263.py
    multispeed_robustness_t260.py news_interaction_tests_t289.py offleg_ab_t259.py
    offleg_rescue_t266.py pit_universe_dryrun_t207.py premium_tier_t279.py
    reconcile_stooq_tr_t256.py regen_spy_full_history_t167.py regime_oos_loco_t172.py
    return_stack_arm_t296.py screen_features_t150.py secondary_basis_check_t285.py
    smallcap_pead_pilot_t265.py taxable_futures_vehicle_t294b.py tilt_decision_measure_t318_t320.py
    trend_gated_leverage_t282.py trend_sleeve_gauntlet_t236.py turnover_reduction_t297.py
    validate_regime_signals_t087.py vehicle_bakeoff_t294.py vixterm_tilt_t274.py
""".split())


def _script_files() -> List[Path]:
    out = [p for d in SCRIPT_DIRS for p in (REPO / d).rglob("*.py") if "Archive" not in p.parts]
    out += [p for p in REPO.glob("*.py")]
    return sorted(out)


def _const_str(n) -> str:
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else ""


def _per_ticker(s: str) -> bool:
    return any(sfx in s for sfx in PER_TICKER_SUFFIXES)


def _per_ticker_reads(tree: ast.AST) -> List[int]:
    """Line numbers of every per-ticker processed-file READ PATTERN, anywhere in the expression
    tree (the §5.1 harnesses wrap theirs: `glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv"))`):
      * a WILDCARD constant — `*_1d.csv` / `*_1d.parquet` — however it is assembled;
      * a path built PER TICKER — an f-string with a formatted value and the suffix, `t + "_1d.csv"`,
        `"%s_1d.csv" % t`, or `"{}_1d.csv".format(t)`.
    A FIXED name (`"SPY_1d.csv"`) is not per-ticker and is not counted."""
    lines = []
    for n in ast.walk(tree):
        s = _const_str(n)
        if s and "*" in s and _per_ticker(s):
            lines.append(n.lineno)
        elif isinstance(n, ast.JoinedStr):
            if (any(isinstance(v, ast.FormattedValue) for v in n.values)
                    and any(_per_ticker(_const_str(v)) for v in n.values)):
                lines.append(n.lineno)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mod)):
            sides = (n.left, n.right)
            if (any(_per_ticker(_const_str(x)) for x in sides)
                    and not all(isinstance(x, ast.Constant) for x in sides)):
                lines.append(n.lineno)
        elif isinstance(n, ast.Call):
            fn = n.func
            if (isinstance(fn, ast.Attribute) and fn.attr == "format"
                    and _per_ticker(_const_str(fn.value)) and (n.args or n.keywords)):
                lines.append(n.lineno)
    return sorted(set(lines))


def _calls(tree: ast.AST) -> set:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func
            out.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", ""))
    return out


def violations(paths: Iterable[Path], grandfathered: frozenset = GRANDFATHERED) -> List[str]:
    """Every per-ticker processed read in `paths` that neither goes through the exclusion nor carries
    the marker beside it. A file that never mentions `processed` is not a reader of this cache."""
    bad = []
    for p in paths:
        src = Path(p).read_text()
        if "processed" not in src or Path(p).name in grandfathered:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        reads = _per_ticker_reads(tree)
        if not reads or (_calls(tree) & THROUGH):
            continue
        lines = src.splitlines()
        for ln in reads:
            near = lines[max(0, ln - 3): ln]
            if not any(MARKER in x and x.split(MARKER, 1)[1].strip() for x in near):
                bad.append(f"{Path(p).relative_to(REPO) if Path(p).is_relative_to(REPO) else p}:{ln}")
    return bad


#: PRE-EXISTING direct readers OUTSIDE §5.1's rule (it took `_t<NNN>` names only, and globbed
#: scripts/*.py non-recursively). Each reason is a checked fact: none has a production caller (no
#: scheduler, cloud entrypoint or dashboard command reaches it). Never grows: new code complies.
#: (run_evolution_cycle.py is NOT here: the dashboard launches it, so it now reads through the
#: exclusion instead — `AutonomousEvolution._load_cache_wide`.)
PREEXISTING_OUTSIDE_THE_63 = {
    # data-ops: these maintain the cache files themselves; the exclusion is a measurement-universe rule
    "fetch_missing_delisted.py": "data-ops: fetches delisted names INTO the cache",
    "ingest_stooq_us_daily.py": "data-ops: ingests Stooq history INTO the cache",
    "merge_stooq_alpaca_substrate.py": "data-ops: built the canonical substrate files (T-082b)",
    # a frozen measurement of record, whose exposure is on the record
    "build_signal_panel_b1.py": ("B-1's frozen panel builder: its exposure to the ÷10 names is the "
                                 "verdict's §13 post-hoc check, DAL's the record note; bytes pinned"),
    # research harnesses with no production caller
    "backtest_lazy_prices_t237.py": "research (a T-script in scripts/lazy_prices/, missed by §5.1's non-recursive glob)",
    "backtest_transition_warning.py": "research: regime-detector validation harness",
    "cointegration_pair_screen.py": "research: pairs screen",
    "run_discovery_diagnostic_standalone.py": "research: discovery diagnostic",
    "run_falsifiable_spec.py": "research: falsifiable-candidate driver",
    "run_oos_validation.py": "research: Phase 2.10b OOS driver",
    "run_path2_ub.py": "research: Path-2 A/B driver",
    "run_trend_wider_universe.py": "research: trend-universe probe",
    "sleeve_phase0_verdict.py": "research: futures-sleeve phase-0 verdict harness",
    "third_stream_battery.py": "research: T-313 crisis-correlation screen",
    "train_per_ticker_metalearner.py": "research: Phase 2.11 meta-learner training",
    "verify_gate1_cache_determinism.py": "research: Gate-1 cache determinism check",
}
EXEMPT = GRANDFATHERED | frozenset(PREEXISTING_OUTSIDE_THE_63)


def test_no_script_reads_the_per_ticker_cache_AROUND_the_exclusion():
    bad = violations(_script_files(), EXEMPT)
    assert not bad, ("per-ticker reads of data/processed that neither go through resolve_universe / "
                     "withhold_declared_tickers nor carry `# ticker-exclusions: bypassed — <reason>` "
                     f"beside the read: {bad}")


def _flagged_names() -> set:
    out = set()
    for p in _script_files():
        src = p.read_text()
        if "processed" not in src:
            continue
        try:
            if _per_ticker_reads(ast.parse(src)):
                out.add(p.name)
        except SyntaxError:
            continue
    return out


def test_POSITIVE_CONTROL_the_detector_SEES_the_known_readers():
    """It must flag what the §5.1 scan found (49 of the 63 read per ticker; the other 14 read a fixed
    name, SPY or the reconciled AGG), and every pre-existing exemption must still be a reader — an
    exemption the detector no longer sees is stale, not harmless."""
    flagged = _flagged_names()
    assert len(flagged & GRANDFATHERED) >= 49, sorted(GRANDFATHERED - flagged)
    stale = sorted(set(PREEXISTING_OUTSIDE_THE_63) - flagged)
    assert not stale, f"exempted but no longer a per-ticker reader: {stale}"


def _plant(tmp_path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body)
    return p


GLOB_ALL = ('import glob\nfrom pathlib import Path\nROOT = Path(".")\n'
            'files = glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv"))\n')


def test_a_NEW_glob_all_harness_is_a_violation_and_each_way_out_clears_it(tmp_path):
    assert violations([_plant(tmp_path, "new_harness.py", GLOB_ALL)], EXEMPT)
    marked = GLOB_ALL.replace("files =", "# ticker-exclusions: bypassed — reads SPY's calendar only\nfiles =")
    assert not violations([_plant(tmp_path, "marked.py", marked)], EXEMPT)
    empty_reason = GLOB_ALL.replace("files =", "# ticker-exclusions: bypassed — \nfiles =")
    assert violations([_plant(tmp_path, "empty_reason.py", empty_reason)], EXEMPT)
    through = GLOB_ALL + ("from engines.data_manager.exclusions import withhold_declared_tickers\n"
                          "names = withhold_declared_tickers([f for f in files], where='x')\n")
    assert not violations([_plant(tmp_path, "through.py", through)], EXEMPT)


@pytest.mark.parametrize("read", [
    'p = ROOT / "data/processed" / f"{t}_1d.csv"',
    'p = "data/processed/" + t + "_1d.csv"',
    'p = "data/processed/%s_1d.parquet" % t',
    'p = "data/processed/{}_1d.csv".format(t)',
])
def test_every_PER_TICKER_path_form_is_seen(tmp_path, read):
    body = f"from pathlib import Path\nROOT = Path('.')\nt = 'AAA'\n{read}\n"
    assert violations([_plant(tmp_path, "per_ticker.py", body)], EXEMPT)


def test_a_FIXED_name_and_a_file_not_touching_processed_are_not_readers(tmp_path):
    fixed = 'import pandas as pd\nspy = pd.read_csv("data/processed/SPY_1d.csv")\n'
    other = 'files = __import__("glob").glob("elsewhere/*_1d.csv")\n'
    assert not violations([_plant(tmp_path, "fixed.py", fixed), _plant(tmp_path, "other.py", other)], EXEMPT)


def test_the_EVOLUTION_CYCLE_reads_the_cache_wide_universe_THROUGH_the_exclusion(tmp_path):
    """The dashboard launches it; its glob used to hand AZO/MTD/NVR (÷10) and SLE to Discovery."""
    import pandas as pd
    from engines.data_manager.data_manager import DataManager
    from engines.data_manager.exclusions import reset_exclusion_log, ticker_exclusions_applied
    run_evo = pytest.importorskip("scripts.run_evolution_cycle")
    cache = tmp_path / "processed"
    cache.mkdir()
    idx = pd.bdate_range("2024-01-02", periods=30)
    frame = pd.DataFrame({"Open": 10.0, "High": 10.5, "Low": 9.5, "Close": 10.0, "Volume": 1e6},
                         index=pd.Index(idx, name="Date"))
    for t in ("AAA", "BBB", "AZO", "SLE"):
        frame.to_csv(cache / f"{t}_1d.csv")
    evo = object.__new__(run_evo.AutonomousEvolution)
    evo.dm = DataManager(cache_dir=str(cache))
    reset_exclusion_log()
    got = evo._load_cache_wide()
    assert set(got) == {"AAA", "BBB"}, sorted(got)
    rec = ticker_exclusions_applied()
    assert "scripts.run_evolution_cycle" in str(rec), rec

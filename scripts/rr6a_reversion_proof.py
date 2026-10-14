"""RR-6a proof by reversion: revert ONE fix, run ONLY its lock, require it to FAIL, restore + verify sha.

    python scripts/rr6a_reversion_proof.py        # from the repo root; ~30 s; prints one line per lock

Each case edits ONE source file in place (an exact, count-checked substring swap), runs only the lock
that should catch it, then restores the original BYTES in a `finally` and asserts the sha256 matches.
It never stashes and never touches git. Run it on a clean tree, so a restore failure is unmistakable.
A lock that fails for an unrelated reason (an import error, say) would bite vacuously — the `why:`
line prints the first assertion so that can be read, not assumed.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[1]
T = "tests/test_rr6a_gate_verdicts.py::"
D = "engines/engine_d_discovery/discovery.py"
M = "orchestration/mode_controller.py"
H = "scripts/run_foundry_eval_t195.py"
E = "scripts/run_evolution_cycle.py"

OLD_DIAG = '''                first_failed = None
                for name, passed in [
                    ("gate_1", bool(result.get("gate_1_passed", False))),
                    ("gate_2", bool(result.get("gate_2_passed", False))),
                    ("gate_4", bool(result.get("gate_4_passed", False))),
                    ("gate_5", bool(result.get("gate_5_passed", False))),
                    ("gate_6", bool(result.get("gate_6_passed", False))),
                    ("gate_7", bool(result.get("gate_7_passed", True))),
                    ("gate_8", bool(result.get("gate_8_passed", True))),
                ]:
                    if not passed:
                        first_failed = name
                        break'''

CASES = [
    ("Gate 7: bare `timeframe` restored (both reads)", M,
     [("discover_cached_tickers(_cache_root, timeframe=self.timeframe)", "discover_cached_tickers(_cache_root, timeframe=timeframe)"), ("_sb_only, _sb_start, _sb_end, timeframe=self.timeframe,", "_sb_only, _sb_start, _sb_end, timeframe=timeframe,")],
     [T + "test_the_cycle_BUILDS_substrate_B_and_hands_it_to_the_gauntlet"]),
    ("substrate-B catch-all restored (programmer errors absorbed)", M,
     [("                if isinstance(_sb_err, (TypeError, AttributeError, NameError, AssertionError, ImportError)):\n                    raise\n", "")],
     [T + "test_a_programmer_error_in_the_substrate_B_build_is_never_a_skipped_gate"]),
    ("skipped Gate 7 reads PASSED (the pre-RR-6a default)", D,
     [('gv.not_evaluated(verdicts, "gate_7", "no substrate-B data_map provided")',
       'gv.render(verdicts, "gate_7", True, "skipped")')],
     [T + "test_a_skipped_gate_7_REFUSES_it_never_defaults_to_a_pass"]),
    ("Gate 8 at N<=1 reads PASSED (the pre-RR-6a default)", D,
     [('gv.not_evaluated(verdicts, "gate_8",\n', 'gv.render(verdicts, "gate_8", True,\n')],
     [T + "test_an_explicit_N_of_1_leaves_gate_8_NOT_EVALUATED_and_refuses"]),
    ("Gate 0 without a window silently skipped (reads PASSED)", D,
     [('gv.not_evaluated(verdicts, "gate_0", "no validation window passed — MinBTL cannot be checked")',
       'gv.render(verdicts, "gate_0", True, "skipped")')],
     [T + "test_no_validation_window_leaves_gate_0_NOT_EVALUATED_and_refuses"]),
    ("diagnostic kill attribution: the old gate_pass_order with defaults", D,
     [("                first_failed = gv.first_failed_gate(result)", OLD_DIAG)],
     [T + "test_the_diagnostic_never_names_a_gate_that_rendered_no_verdict"]),
    ("harness `gates`: the old gate_{g}_passed booleans", H,
     [('"gates": None if errored else verdict_strings(r),',
       '"gates": None if errored else {f"g{g}": r.get(f"gate_{g}_passed") for g in range(1, 9)},')],
     [T + "test_a_gate_4_kill_is_attributed_to_gate_4_never_to_the_criterionless_gate_3"]),
    ("Gate 3 parameter restored", D,
     [("        candidate_default_weight: float = 1.0,\n        alpha_config",
       "        gate3_consistency_threshold: float = 0.40,\n        candidate_default_weight: float = 1.0,\n        alpha_config")],
     [T + "test_gate_3_threshold_is_not_a_silent_parameter"]),
    ("Gate 6: `already_excess=True` removed at the call", D,
     [("                    edge_name=cand_id,\n                    already_excess=True,\n", "                    edge_name=cand_id,\n")],
     [T + "test_gate_6_recovers_a_spreads_alpha_without_subtracting_RF"]),
    ("Gate 6: missing factor cache reads PASSED again", D,
     [('                g6_not_evaluated = f"factor cache missing ({e})"\n',
       '                factor_alpha_passed = True\n')],
     [T + "test_gate_6_with_no_factor_cache_is_NOT_EVALUATED_not_a_pass"]),
    ("Gate 5 with-arm reuses the wrapped baseline", D,
     [("                    ub_with = run_backtest_pure(\n                        edges=alt_with_edges,",
       "                    ub_with = run_backtest_pure(\n                        edges=with_edges,")],
     [T + "test_gates_5_and_7_with_arms_never_replay_universe_A_signals"]),
    ("Gate 7 with-arm reuses the wrapped baseline", D,
     [("                    sb_with = run_backtest_pure(\n                        edges=alt_with_edges,",
       "                    sb_with = run_backtest_pure(\n                        edges=with_edges,")],
     [T + "test_gates_5_and_7_with_arms_never_replay_universe_A_signals"]),
    ("re-queue forever: both WFO rejections keep status 'candidate'", E,
     [('                cand["status"] = "failed"\n                cand["rejection_reason"] = "WFO returned no result (insufficient data?)"\n', ""),
      ('                cand["status"] = "failed"\n                cand["rejection_reason"] = f"Poor OOS consistency', '                cand["rejection_reason"] = f"Poor OOS consistency')],
     [T + "test_a_WFO_rejection_leaves_the_queue_with_its_reason"]),
]

env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
ok = True
for name, rel, subs, tests in CASES:
    p = W / rel
    orig = p.read_bytes()
    sha = hashlib.sha256(orig).hexdigest()
    text = orig.decode()
    for old, new in subs:
        assert text.count(old) == 1, (name, old[:60], text.count(old))
        text = text.replace(old, new)
    p.write_text(text)
    try:
        r = subprocess.run(["nice", "-n", "19", sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
                           cwd=W, env=env, capture_output=True, text=True)
    finally:
        p.write_bytes(orig)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, f"RESTORE FAILED for {rel}"
    last = (r.stdout.strip().splitlines() or ["?"])[-1]
    verdict = "LOCK BITES" if r.returncode != 0 else "LOCK DID NOT FAIL"
    ok &= r.returncode != 0
    why = next((l.strip() for l in r.stdout.splitlines() if l.startswith("E ")), "?")
    print(f"[{verdict}] {name}  ->  {last}\n      why: {why[:170]}")
print("ALL LOCKS BITE" if ok else "SOME LOCK DID NOT FAIL")

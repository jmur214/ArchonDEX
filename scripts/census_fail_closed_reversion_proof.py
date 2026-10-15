"""Census fail-closed unit — proof by reversion: revert ONE fix, run ONLY its locks, require FAIL.

    python scripts/census_fail_closed_reversion_proof.py      # from the repo root; ~15 s

Each case swaps an exact, count-checked substring in one source file, runs only the locks that
should catch it, restores the original BYTES in a `finally`, and asserts the sha256. It never
stashes and never touches git. `why:` is the first assertion line — read it: a lock that fails
for an unrelated reason bites vacuously.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[1]
C = "core/census.py"
B = "backtester/backtest_controller.py"
L = "tests/test_census_fail_closed.py::"
K = "tests/test_contracts.py::"

GATE_ERROR_RULE = '''    for k in sorted(census):
        if k.endswith("_error") and k != "census_error":
            failures.append(f"census block errored ({k}): {census[k]} — that invariant was never measured")
'''
EDGES_EXCEPT_NEW = '''            census["edges_blind_error"] = repr(e)

        # Which census this is.'''
EDGES_EXCEPT_OLD = '''            census["edges_blind"] = []
            census["edges_errored"] = {}
            census["edges_blind_error"] = repr(e)

        # Which census this is.'''

CASES = [
    (C, "gate: the `<block>_error` rule removed (crashed blocks read as clean)",
     [(GATE_ERROR_RULE, "")],
     [L + "test_a_crash_inside_the_edges_census_makes_the_run_NON_CANONICAL",
      L + "test_a_crash_inside_the_fundamentals_census_makes_the_run_NON_CANONICAL"]),
    (B, "edges except: the PASSING edges_blind=[] / edges_errored={} restored",
     [(EDGES_EXCEPT_NEW, EDGES_EXCEPT_OLD)],
     [K + "test_layer2d_every_except_branch_in_build_census_FAILS_the_gate"]),
    (B, "fundamentals except: the PASSING fundamentals_blind=0 restored",
     [('            census["fundamentals_blind_error"] = repr(e)\n',
       '            census["fundamentals_blind"] = 0\n            census["fundamentals_blind_error"] = repr(e)\n')],
     [K + "test_layer2d_every_except_branch_in_build_census_FAILS_the_gate"]),
    (C, "gate: n_trades `<= 0` back to `== 0` (the -1 sentinel reads as a count)",
     [('int(census.get("n_trades", 0) or 0) <= 0:', 'int(census.get("n_trades", 0) or 0) == 0:')],
     [L + "test_an_unknown_or_zero_trade_count_is_never_a_traded_run",
      K + "test_layer2d_every_except_branch_in_build_census_FAILS_the_gate"]),
    (C, "gate: an errored data_exclusions record no longer fails",
     [('    if isinstance(excl, dict) and "error" in excl:\n',
       '    if False and isinstance(excl, dict) and "error" in excl:\n')],
     [K + "test_layer2d_every_except_branch_in_build_census_FAILS_the_gate"]),
    (B, "producer: edges_blind assigned ONLY in the except branch (the regex form passed this)",
     [('            census["edges_blind"] = [e for e in active if int(counts.get(e, 0)) == 0]\n', ""),
      (EDGES_EXCEPT_NEW, EDGES_EXCEPT_OLD)],
     [K + "test_layer2d_census_producer_emits_all_gating_keys"]),
    # ---- the fixup: NO silent zero (ruling 2026-10-15) ----
    (B, "producer: n_resolved back to getattr(..., 0) (a never-set counter reads as a measured 0)",
     [('        if hasattr(self, "_census_n_resolved"):\n            census["n_resolved"] = int(self._census_n_resolved)\n',
       '        census["n_resolved"] = int(getattr(self, "_census_n_resolved", 0))\n')],
     [L + "test_a_counter_that_was_never_set_is_ABSENT_and_FAILS"]),
    (C, "gate: invariant 2 skips a 0 again",
     [('            if n_resolved <= 0:\n                failures.append("n_resolved == 0 — no universe was resolved")\n'
       '            elif n_in_panel < n_resolved - panel_allow:',
       '            if n_resolved and n_in_panel < n_resolved - panel_allow:')],
     [L + "test_a_measured_ZERO_fails_its_own_invariant"]),
    (C, "gate: invariant 5 passes a 0 again",
     [('        elif int(census["regime_total_bars"] or 0) <= 0:\n'
       '            failures.append("regime_total_bars == 0 — the regime layer produced nothing")\n', '')],
     [L + "test_a_measured_ZERO_fails_its_own_invariant"]),
    (C, "gate: a declared-OFF regime layer needs no label",
     [('            if not str(census.get("regime_off_label") or "").strip():',
       '            if False:')],
     [L + "test_a_regime_layer_OFF_is_DECLARED_and_canonical_only_with_the_pre_registration_label"]),
    (B, "producer: the per-bar tally no longer starts the counters from UNSET",
     [('        if self._census_regime_total_bars is None:      # first bar tallied: the counters become SET\n'
       '            self._census_regime_total_bars, self._census_regime_unknown_bars = 0, 0\n', '')],
     [L + "test_the_real_per_bar_tally_turns_an_UNSET_counter_into_a_SET_one"]),
    ("engines/engine_d_discovery/discovery.py", "candidate census: census_kind dropped (refused for backtest counters)",
     [('        "census_kind": "candidate",\n', '')],
     [L + "test_a_GATE1_candidate_census_is_not_asked_for_backtest_counters"]),
    # ---- R's review: the exec model's selector boundary ----
    (B, "producer: a census block written through census.update() (the selector would skip it)",
     [('        census["census_kind"] = "backtest"\n',
       '        census["census_kind"] = "backtest"\n        census.update({"census_kind": "backtest"})\n')],
     [K + "test_layer2d_build_census_writes_the_census_only_by_subscript"]),
]

env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
ok = True
for rel, name, subs, tests in CASES:
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
    ok &= r.returncode != 0
    why = next((l.strip() for l in r.stdout.splitlines() if l.startswith("E ")), "?")
    print(f"[{'LOCK BITES' if r.returncode != 0 else 'LOCK DID NOT FAIL'}] {name}  ->  {last}\n      why: {why[:170]}")
print("ALL LOCKS BITE" if ok else "SOME LOCK DID NOT FAIL")

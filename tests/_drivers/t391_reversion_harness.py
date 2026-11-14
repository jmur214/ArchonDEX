"""T-391 reversion harness: each lock must FAIL when the code it guards is reverted.

    python tests/_drivers/t391_reversion_harness.py            # from the repo root; ~1 minute

For each mode: replace ONE exact source string (asserting it occurs exactly once), run only the locking
tests, restore the original bytes and assert the md5 matches. It prints the FIRST `E ` line per mode, so a
mode caught by a deeper rail than the one targeted is visible (M13 and N10 are). Exit 0 only when every
mode is caught. It touches no git state and no data file; it is not collected by pytest.

Committed (review round 3) because the scratchpad copy did not survive the session: a harness the reviewer
cannot re-run is not evidence.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

WT = Path(__file__).resolve().parents[2]
T = "tests/test_honest_n_trials_t391.py::"
G = "core/measurement/mbl_gate.py"
H = "scripts/honest_n_trials.py"
P = "scripts/honest_n_pin.py"
REAL = T + "test_the_real_record_and_a_COPY_of_the_real_registry_gate_to_registry_plus_executed_plus_S"
REFUSALS = T + "test_the_recorder_refuses_what_would_make_the_record_wrong_or_uncitable"
GATED = '"n_eff": n_eff_executed + n_raw + s,'
FORWARD = "if not (closed or row.states_n):"

MODES = [
    ("M1 digest check", G, 'if rec.get("rows_sha256") != trials_digest(rows, unresolved, rec.get("activation_date")):',
     "if False:", [T + "test_a_HAND_EDIT_that_bypasses_the_recorder_is_refused_by_the_digest"]),
    ("M2 empty record", G, "if not isinstance(rows, list) or not rows:", "if not isinstance(rows, list):",
     [T + "test_an_EMPTY_record_is_refused"]),
    ("M3 n_trials type/sign", G, "if isinstance(n, bool) or not isinstance(n, int) or n < 0:",
     "if not isinstance(n, (int, float, str)):", [T + "test_a_malformed_n_trials_is_refused"]),
    ("M4 duplicate trial_id", G, 'if row["trial_id"] in seen:', "if False:",
     [T + "test_a_duplicate_trial_id_is_refused"]),
    ("M5 registry reconcile", G, "    if have != want:\n", "    if False:\n",
     [T + "test_a_record_that_disagrees_with_the_registrys_ledger_rows_is_refused"]),
    ("M6 S dropped from the gated N", G, GATED, '"n_eff": n_eff_executed + n_raw,',
     [REAL, T + "test_the_recorder_appends_ONE_row_the_gate_then_counts"]),
    ("M7 pinned-record sha verify", G, "    if entry is None:\n        return False\n",
     "    if True:\n        return False\n", [T + "test_once_PINNED_a_changed_record_is_refused_until_re_pinned"]),
    ("M8 production path returns the old registry-only N", G,
     'return float(honest_n_breakdown(db_path, method, artifact_dir, pin_path, trials_path)["n_eff"])',
     'return float(honest_n_breakdown(db_path, method, artifact_dir, pin_path, trials_path)["n_eff_r0"])',
     [T + "test_the_no_argument_production_call_counts_the_record"]),
    ("M9 schema check", G, 'or rec.get("schema") != TRIALS_SCHEMA:', "or False:", [T + "test_a_wrong_schema_is_refused"]),
    ("M10 --verify skips the reconcile", P, "        mbl.reconcile_trials_with_registry(rec, reg)\n", "        pass\n",
     [T + "test_verify_exits_3_when_an_unpinned_record_disagrees_with_the_registry"]),
    ("M11 --verify skips the pinned sha", P, "        trials_pinned = mbl.verify_pinned_trials(tp)\n",
     "        trials_pinned = 'trials' in mbl.load_pin()\n",
     [T + "test_verify_exits_3_on_a_planted_byte_in_a_pinned_record"]),
    ("M12 write_pin skips the reconcile", P,
     "        mbl.reconcile_trials_with_registry(rec, db_path)     # ... or would refuse to combine\n", "        pass\n",
     [T + "test_write_pin_refuses_a_record_the_gate_could_not_combine"]),
    ("M13 recorder duplicate check", H, 'if any(r["trial_id"] == trial_id for r in rec["rows"]):', "if False:", [REFUSALS]),
    ("M14 recorder path-exists check", H, "    if not p.is_file():\n", "    if False:\n", [REFUSALS]),
    ("M15 recorder source-line bound", H, 'if not (1 <= int(m["a"]) <= last <= n_lines):', "if False:", [REFUSALS]),
    ("M16 lint declared-N", H, "if k > 0 and by_ledger.get(lid, 0) < k:", "if False:",
     [T + "test_lint_flags_a_declared_N_with_no_record_row",
      T + "test_lint_flags_a_record_that_falls_SHORT_of_the_ledger_but_allows_more"]),
    ("M17 lint closed-row states-N", H, "        if closed and not row.states_n:\n", "        if False:\n",
     [T + "test_lint_forward_rule_a_verdict_must_STATE_N"]),
    ("M18 lint forward record row", H, "        if rows_for.get(row.ledger_id, 0) == 0:\n", "        if False:\n",
     [T + "test_lint_forward_rule_a_verdict_needs_a_record_row_even_at_zero"]),
    ("M19 lint dangling ledger_id", H, 'if r.get("ledger_id") and r["ledger_id"] not in known:', "if False:",
     [T + "test_lint_flags_a_dangling_ledger_id"]),
    ("M20 lint: the B-series `N_trials +k` form dropped", H, r"(?:\bN_trials|\bN)\s*\+=?\s*(\d+)",
     r"(?:\bN_trials|\bN)\s*\+=\s*(\d+)", [T + "test_lint_reads_the_B_series_plus_k_form"]),
    ("N1 activation_date out of the digest", G, '{"activation_date": activation_date, "rows": rows,', '{"rows": rows,',
     [T + "test_the_activation_date_is_under_the_digest"]),
    ("N2 a registry task accepted as a standalone row", G, "        elif clash:\n", "        elif False:\n",
     [T + "test_a_registry_task_re_added_as_a_standalone_row_is_refused"]),
    ("N2b the named twin need not be same-task, different-date", G,
     'twin["task_id"] != row["task_id"] or twin["date"] == row["date"]', "False",
     [T + "test_a_registry_task_re_added_as_a_standalone_row_is_refused"]),
    ("N3 gate citation check off", G, "    if citations_checked:\n        verify_trials_citations(record, cited_root)\n",
     "    if False:\n        verify_trials_citations(record, cited_root)\n",
     [T + "test_a_citation_that_does_not_exist_is_refused_where_the_docs_tree_exists"]),
    ("N4 lint forward: the closed arm off", H, FORWARD, "if not (row.states_n):",
     [T + "test_lint_a_closed_row_needs_a_record_whatever_its_doc_cell_says"]),
    ("N4b lint forward: the stated-count arm off", H, FORWARD, "if not (closed):",
     [T + "test_lint_bypass_dispatched_with_a_doc_cell_naming_a_file_not_yet_on_disk"]),
    ("N5 an undated row skipped", H, "if row.date is not None and row.date < activation:",
     "if row.date is None or row.date < activation:", [T + "test_lint_a_row_with_no_parseable_date_is_treated_as_forward"]),
    ("N6 check() skips citations", H, "        mbl.verify_trials_citations(rec, ROOT)\n", "        pass\n",
     [T + "test_check_refuses_a_record_whose_citation_is_gone"]),
    ("N7 a range read by its FIRST date", H, "    return max(dates)\n", "    return min(dates)\n",
     [T + "test_lint_bypass_a_range_closing_AFTER_activation_reads_by_its_LATEST_date"]),
    ("N8 the `N_trials = k` form dropped", H, r'|\bN_trials\s*[:=]\s*\**\s*\+?([1-9]\d*)")', '")',
     [T + "test_lint_bypass_in_flight_stating_N_trials_equals_3"]),
    ("N9 the executed term dropped from the gated N", G, GATED, '"n_eff": n_raw + s,', [REAL]),
    ("N10 a missing executed population tolerated", G,
     "if isinstance(executed, bool) or not isinstance(executed, int) or executed < 0:", "if False:",
     [T + "test_an_artifact_without_the_executed_population_is_refused"]),
    ("N11 --pin skips the citation check", P,
     "        mbl.verify_trials_citations(rec, Path(cited_root) if cited_root is not None else pin_path.parent.parent)\n",
     "        pass\n", [T + "test_the_pin_refuses_a_missing_citation_and_records_the_check"]),
    ("N12 the feature-branch dispatched row", H, FORWARD, "if not (closed):",
     [T + "test_lint_bypass_dispatched_with_a_feature_branch_doc_cell"]),
    ("N13 the gate back on R2' (borrowed credit for the registry's curve-less rows)", G, GATED,
     '"n_eff": n_eff_registry + n_eff_executed + s,',
     [T + "test_ruling_9_2_curve_less_registry_rows_count_at_RAW_whatever_the_measured_rho"]),
    ("N13b the same reversion, against the real inputs", G, GATED, '"n_eff": n_eff_registry + n_eff_executed + s,', [REAL]),
]


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    ok = True
    for name, rel, old, new, tests in MODES:
        f = WT / rel
        orig = f.read_bytes()
        h0 = _md5(f)
        text = orig.decode()
        if text.count(old) != 1:
            print(f"BROKEN {name}: the pattern occurs {text.count(old)} times in {rel}")
            ok = False
            continue
        f.write_text(text.replace(old, new))
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", *tests],
                               cwd=WT, capture_output=True, text=True)
        finally:
            f.write_bytes(orig)
        assert _md5(f) == h0, f"{name}: restore failed"
        e_line = next((ln.strip() for ln in r.stdout.splitlines() if ln.startswith("E ")), "(no E line)")
        caught = r.returncode != 0
        ok &= caught
        print(f"{'CAUGHT' if caught else 'MISSED'} {name}: exit {r.returncode} | {e_line[:150]}")
    print(f"{len(MODES)} modes: {'ALL CAUGHT' if ok else 'NOT ALL CAUGHT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

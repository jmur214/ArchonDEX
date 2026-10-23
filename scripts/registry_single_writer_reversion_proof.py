"""edges.yml single-writer unit — proof by reversion: revert ONE fix, run ONLY its locks, require FAIL.

    python scripts/registry_single_writer_reversion_proof.py     # from the repo root; ~10 min

Each case swaps an exact, count-checked substring in one source file, runs only the locks that
should catch it, restores the original BYTES in a `finally` and asserts the sha256. It never
stashes and never touches git. The `why:` line is the first assertion of the failure — read it: a
lock that fails for an unrelated reason bites vacuously. (The pattern of
scripts/registry_fail_closed_reversion_proof.py, the Engine-D unit this one completes.)
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[1]
A = "engines/engine_a_alpha/edge_registry.py"
D = "engines/engine_d_discovery/discovery.py"
F = "engines/engine_f_governance/lifecycle_manager.py"
G = "engines/engine_f_governance/governor.py"
M = "orchestration/mode_controller.py"
IO = "core/edge_registry_io.py"
C = "core/census.py"
S = "scripts/sync_edge_registry.py"
PT = "paper_trader/__init__.py"
T = "tests/test_edge_registry_single_writer.py::"

CASES = [
    (A, "LOCK 1 — ensure() registers AND SAVES at import again (the import-time writer)",
     [("        EdgeRegistry._import_registrations[spec.edge_id] = ImportRegistration(\n"
       "            spec=spec, persisted=existing is not None, report=report, registry_path=str(self.path))\n",
       "        EdgeRegistry._import_registrations[spec.edge_id] = ImportRegistration(\n"
       "            spec=spec, persisted=existing is not None, report=report, registry_path=str(self.path))\n"
       "        self._specs[spec.edge_id] = spec\n        self.save()\n")],
     [T + "test_LOCK1_importing_every_auto_registering_module_never_touches_the_registry",
      T + "test_LOCK1b_ensure_records_a_registration_and_never_mutates_the_loaded_specs"]),
    (A, "LOCK 2 — the wholesale params replacement (`s.params = spec.params or s.params`)",
     [('    out["params"] = merged\n    return out, report\n',
       '    out["params"] = dict(code_params) or merged\n    return out, report\n')],
     [T + "test_LOCK2_the_sync_merges_params_key_wise_and_reports_four_distinct_classes"]),
    (D, "LOCK 3 — Discovery writes raw yaml.dump again (the format flip)",
     [("        write_registry_atomic(self.registry_path, registry)\n",
       "        import yaml as _y\n        self.registry_path.write_text(_y.dump(registry, sort_keys=False))\n")],
     [T + "test_LOCK3_the_same_registry_saved_through_every_writer_is_one_sha256",
      T + "test_LOCK3b_the_migration_is_a_null_diff_on_the_real_registry"]),
    (D, "LOCK 4 — the empty book is measured against, without saying so (R's F3)",
     [("            if not baseline_edges and not _bootstrap:\n",
       "            if False and not baseline_edges and not _bootstrap:\n")],
     [T + "test_LOCK4_a_readable_registry_with_zero_tradeable_edges_renders_gate_1_NOT_EVALUATED"]),
    (D, "LOCK 4c — an unreadable registry is 'this candidate failed', not a hard refusal",
     [("                              HonestNUnavailableError, RegistryUnreadableError)):\n",
       "                              HonestNUnavailableError)):\n")],
     [T + "test_LOCK4c_an_unreadable_registry_is_a_HARD_refusal_of_the_gauntlet"]),
    (M, "LOCK 5 — isolation mode prints `not found` and runs with fewer edges",
     [("            if missing:\n", "            if missing and False:\n")],
     [T + "test_LOCK5_isolation_mode_refuses_a_missing_id_naming_the_sync"]),
    (M, "LOCK 5b — default mode returns an empty dict (AlphaEngine's default-edge fallback)",
     [("            if not specs_to_load:\n", "            if not specs_to_load and False:\n"),
      ("        if not loaded_edges:\n            raise EdgeLoadRefusal(",
       "        if not loaded_edges and False:\n            raise EdgeLoadRefusal(")],
     [T + "test_LOCK5b_default_mode_refuses_an_empty_registry_and_never_falls_back_to_default_edges",
      T + "test_a_fresh_checkout_refuses_until_the_sync_runs_then_succeeds"]),
    (S, "LOCK 6 — --check writes",
     [("    if not check:\n        report.wrote = write_registry_if_changed(path, new_registry)\n",
       "    if True:\n        report.wrote = write_registry_if_changed(path, new_registry)\n")],
     [T + "test_LOCK6_check_exits_non_zero_on_a_change_and_writes_nothing"]),
    (IO, "LOCK 6 / 2 / 3b — a no-op sync rewrites the file (mtime moves)",
     [("            if p.read_text() == text:\n                return False\n",
       "            if p.read_text() == text:\n                pass\n")],
     [T + "test_LOCK2_the_sync_merges_params_key_wise_and_reports_four_distinct_classes",
      T + "test_LOCK3b_the_migration_is_a_null_diff_on_the_real_registry"]),
    (PT, "LOCK 7 — the fleet imports an edge module (the condition manufactured)",
     [("from paper_trader.order_manager import (",
       "import engines.engine_a_alpha.edges.rsi_bounce  # REVERTED: a fleet import of an edge module\n"
       "from paper_trader.order_manager import (")],
     [T + "test_LOCK7_the_paper_fleet_imports_no_edge_module"]),
    (F, "ENGINE F — the save truncates first and swallows (open('w') + yaml.dump inside except: log)",
     [('        write_registry_atomic(self.registry_path, {**getattr(self, "_registry_extra", {}), "edges": edges})\n',
       '        try:\n            import yaml as _y\n            self.registry_path.parent.mkdir(parents=True, exist_ok=True)\n'
       '            with self.registry_path.open("w") as f:\n                _y.dump({"edges": edges}, f, sort_keys=False)\n'
       '        except Exception as e:\n            log.warning(f"[Lifecycle] Could not save registry: {e}")\n')],
     [T + "test_ENGINE_F_a_planted_dump_error_leaves_the_bytes_untouched_raises_and_appends_no_history"]),
    (G, "ENGINE F — the governor swallows a registry save failure",
     [("            if isinstance(e, (RegistryUnreadableError, RegistryWriteError)):\n                raise\n"
       '            log.warning(f"[Governor] Lifecycle evaluation failed: {e}")\n',
       '            log.warning(f"[Governor] Lifecycle evaluation failed: {e}")\n')],
     [T + "test_ENGINE_F_the_governor_lets_a_registry_save_failure_through"]),
    (M, "RUN_BACKTEST — a registry save failure raises BEFORE the summary (nothing held)",
     [('            post_run_failure = {"stage": "governor", "error_type": type(e).__name__, "message": str(e)}\n'
       "            held = e\n", "            raise\n")],
     [T + "test_RUN_BACKTEST_a_registry_save_failure_lands_in_both_summaries_the_census_says_NON_CANONICAL_then_it_raises"]),
    (M, "RUN_BACKTEST — the Discovery cycle raises BEFORE the summary (RR-6a's accepted consequence)",
     [('                post_run_failure = {"stage": "discovery", "error_type": type(e).__name__, "message": str(e),\n'
       '                                    "notes": list(getattr(e, "__notes__", []) or [])}\n'
       "                held = e\n", "                raise\n")],
     [T + "test_RUN_BACKTEST_a_discovery_cycle_failure_takes_the_same_shape"]),
    (C, "CENSUS — post_run_failure is ignored by the gate",
     [("    if prf:\n", "    if prf and False:\n")],
     [T + "test_RUN_BACKTEST_a_registry_save_failure_lands_in_both_summaries_the_census_says_NON_CANONICAL_then_it_raises"]),
    (C, "CENSUS — a backtest census carrying bootstrap_book=true is canonical",
     [('    elif census.get("bootstrap_book") is True and is_backtest:\n', "    elif False:\n")],
     [T + "test_LOCK4b_bootstrap_mode_promotes_from_an_empty_book_and_the_census_carries_the_label"]),
    (IO, "READER — an unparseable registry reads as empty (the wipe shape)",
     [("    except yaml.YAMLError as exc:\n"
       '        raise RegistryUnreadableError(f"{p} is not parseable YAML ({exc}); {REFUSAL}") from exc\n',
       "    except yaml.YAMLError:\n        return {\"edges\": []}\n")],
     [T + "test_the_one_reader_refuses_everything_that_is_not_an_edge_registry",
      T + "test_LOCK4c_an_unreadable_registry_is_a_HARD_refusal_of_the_gauntlet"]),
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
        text = text.replace(old, new, 1)
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
    print(f"[{'LOCK BITES' if r.returncode != 0 else 'LOCK DID NOT FAIL'}] {name}  ->  {last}\n      why: {why[:170]}", flush=True)
print("ALL LOCKS BITE" if ok else "SOME LOCK DID NOT FAIL")
sys.exit(0 if ok else 1)

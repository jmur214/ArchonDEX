# Session Summary: 2026-06-11 (Agent E — T-147, fifth task)

## What was worked on

- **T-147 Part A**: synced the T-143 crisis-replay harness to the FINAL
  ADDENDUM v3 (pure transcription): 7 enumerated actionable episodes
  (+2010, +2025), 4/3 in-sample/OOS splits, ALL-3-OOS clause, sign
  ≥6/7, median over 7. Added the 2-of-3-OOS regression.
- **T-147 Part B**: diagnosed and properly isolated the
  concurrent-suite flake flagged in T-146.

## What was decided

- Date-pinning stays month-anchored (v3 adopted the T-143 procedure);
  the divergence checker reports against the v3 enumeration under both
  readings and never patches (v3 §4 finality).
- The 2-of-3-OOS regression pins the verdict at FAIL (not PARTIAL) when
  only the OOS clause fails — co-equal criteria are structural, and the
  fixture also pins the sign test at its exact 6/7 boundary so both
  v3 rescales are exercised in one scenario.
- Part B fixes are mechanism-against-isolated-state rewrites, not
  skips/markers: pairs registration → tmp_path registry round-trip;
  collector → deterministic synthetic bars.

## What was learned

- **The "concurrency flake" was two different defects** (full entry in
  lessons_learned.md): a genuine live-edges.yml race AND a
  yf.download()-in-test network flake that merely correlated with the
  concurrency window. Separate shared-file races from external-state
  flakes before fixing.
- Real-data month-pinning reproduces v3's stated episode figures
  exactly (2010 −16.1%, 2025 −18.8% on the Stooq TR-proxy) — the
  enumeration + pinning combination is now rule-ambiguity-free
  end-to-end.
- `test_validate_candidate_v2` ALSO reads the live edges.yml (named in
  the audit's diagnosis table) — it belongs in the standing triage
  dispatch with that fact attached.

## Pick up next time

- T-147 done pending director merge. The post-relaunch crisis-replay
  run needs: (1) the ^SP500TR caching decision (still open since
  T-143); (2) the director's one command (unchanged, in
  execution_manual).
- Standing items: 5 pre-existing test failures (triage dispatch;
  validate_candidate's live-registry read documented), T-118 campaign
  relaunch gating on T-140.

## Files touched

```
scripts/crisis_replay_t118b.py        (v3 constants — transcription)
tests/test_crisis_replay_t143.py      (v3 fixtures + 2-of-3-OOS regression)
tests/test_pairs_trading_edges.py     (tmp_path registry isolation)
tests/test_collector_integration.py   (synthetic bars, was live yfinance)
docs/Audit/harness_v3_sync_t147_2026_06_11.md (new)
docs/State/lessons_learned.md
```

## Subagents invoked

- None — transcription + two surgical test rewrites; direct work.

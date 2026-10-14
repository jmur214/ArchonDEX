# RR6A_NOTE — read this before reading any record in this prefix

*To be placed beside the 36 `t195_foundry_eval.jsonl` records under `foundry-t196/`. The records themselves are
never edited. Source: `docs/Measurements/2026-10/t196_foundry_records_SIDECAR.md` in the repo.*

These records were written for T-196 (June 2026) by `scripts/run_foundry_eval_t195.py` as of `55568b1`, the only
version of the harness between 2026-06-17 and RR-2 (2026-09-30). At that version,
**several gate fields are defaults, not verdicts**:

- **`g7: true` in all 36 records.** Gate 7 never ran, because no substrate-B data map was passed.
- **`g8: true` in all 36 records.** Gate 8 never ran: each container swept one feature, so N = 1.
- **`g4: false`.** Gate 4 was forced to FAIL, because `significance_threshold` was `None`. That is not a test.
- **`g2`–`g6: false` on a Gate-1 failure.** These are initialiser defaults; those gates never ran.
- **`first_failed_gate: "gate_3"`** on `triple_witching_premium` and `january_effect` is wrong. Gate 3 has no
  pass criterion, and the harness defaulted its missing `passed` key to False. Neither record shows a gate
  that actually FAILED before Gate 5:
  - `triple_witching_premium` failed no gate that rendered a verdict;
  - `january_effect`'s only possible rendered failure is Gate 5, and the record cannot show whether Gate 5
    ran.
- **Four records with contribution exactly 0.0 are not Gate-1 verdicts:** `anfci_z_60d`,
  `correlation_average_60d`, `cot_commercial_net_long` and `earnings_proximity_5d`. They fit the T-346
  blind-or-absorbed class.

**Every number here also predates RR-1 (sizing) and RR-2 (Gate 4).** T-196's H0 is UNTESTED (the 2026-09-30
ruling).

- Per-record table and sha256 manifest: `docs/Measurements/2026-10/t196_foundry_per_gate_kill_table.md`.
- The fix that ends the class (tri-state gate verdicts): `docs/Sources/referee_repair_proposal_RR-6a_2026-10-14.md`.

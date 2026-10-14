# RR-1 RE-SCORE — the October records live under 2026-09

**The records are in `docs/Measurements/2026-09/rr1_rescore/`.** This file states the lineage,
because most of the campaign ran in October while its records sit under September.

**Why September.** The campaign belongs to the RR-1 proposal of 2026-09-30
(`docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md`, §4). Its driver
(`scripts/rescore_rr1.py`) writes every record to a single fixed directory, so all eight cells
and their analyses stay in one place.

| date | what | record(s) |
|---|---|---|
| 2026-09-30 | anchor26 / before; calibration cells | `anchor26_before.json`, `e2e_check_before.json`, `verify_q1*.json` |
| 2026-10-08 | anchor26 / after (the director, as caretaker); first feature cell FAILED | `anchor26_after.json`, `failed_first_attempt/` |
| 2026-10-13 | the feature-id fix; proof cell; anchor paired test | `inertness_proof/`, `anchor26_paired_delta.json`, `PAIRED_TEST_PREREG.md` |
| 2026-10-14 | six feature cells; feature paired tests; window vs book | `t196_*`, `*_paired_delta.json`, `WINDOW_VS_BOOK_PREREG.md`, `window_vs_book.json` |

Current reading: RR-1 §4 and §6.5. The fix's effect on Sharpe is not of one sign across the two
measured books, and nothing is established at 95%. The window-vs-book test reads row 3: the
window is the likelier explanation, not established.

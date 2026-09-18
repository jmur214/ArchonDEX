# Reviewer liveness sweep — first artifact, 2026-09-18 (point-in-time record; the tool's stdout, verbatim except the scratch paths)

> Inputs: the three accounts' `data/state` + `data/intel` ledgers synced read-only from S3 at ~13:5x CDT 2026-09-18 (objects dated 08:49/08:52/08:56 that morning), the local `data/state/autonomy_ledger.jsonl` (26 rows), and the two installed plists. Command in `docs/Core/execution_manual.md`. Advisory: this table gates nothing.

# Reviewer liveness sweep — as of 2026-09-18 (advisory; gates nothing)

## 1. Registries (reused: clock census + T-342 channel liveness), per root
- **acct1** (`<s3>/paper_state`): [CHANNEL-LIVENESS][ALERT] 1 never-alive / 2 unverifiable — family_tracker(trend_sleeve):cash_rate, event_shadow_book:event_calls, family_tracker(deploy_candidate):cash_rate
  - [CLOCK-CENSUS][ALERT] clocks_advanced=14/24 MISSED: analyst_note_written, news_month_pushed, scan_filed_when_due, archive_feeds_in_budget, similarity_panel_refreshed, exec_ledger_on_fill_days, digest_written_weekly, advisor_surface_rendered, janitor_ran_nightly, fleet_mirror_slice_rolled
    - NEVER_ALIVE `family_tracker(trend_sleeve):cash_rate` — 'cash_adj' ABSENT from all 43 point(s) of its entire observed history — the annotation's zero means NEVER MEASURED, not 'no effect'; VERIFY UPSTREAM INTENT
- **acct2** (`<s3>/paper_state_offense_sso`): [CHANNEL-LIVENESS][ALERT] 1 never-alive / 6 unverifiable — family_tracker(deploy_candidate):cash_rate, llm_shadow_book:hypothetical_actions, llm_shadow_book(agentic):hypothetical_actions, eval_harness:predictions, event_shadow_book:event_calls, thesis_book:thesis_calls, family_tracker(trend_sleeve):cash_rate
  - [CLOCK-CENSUS][ALERT] clocks_advanced=0/25 MISSED: analyst_note_written, eval_scored_when_due, news_month_pushed, scan_filed_when_due, stage2_clock_ticked, archive_feeds_in_budget, similarity_panel_refreshed, exec_ledger_on_fill_days, digest_written_weekly, advisor_surface_rendered, janitor_ran_nightly, sleeve_tracker_rolled, btc_shadow_rolled, dbmf_shadow_rolled, event_desk_rolled, llm_shadow_agentic_rolled, fleet_mirror_slice_rolled, thesis_machine_rolled, thesis_user_rolled, book_spy_null_rolled, book_damped_offense_rolled, book_quality_sat_rolled, book_sleeve_tier_rolled, llm_shadow_book_rolled, book_momentum_sat_rolled
    - UNVERIFIABLE `llm_shadow_book:hypothetical_actions` — source dir missing: data/intel/analyst_notes (cannot establish liveness)
    - UNVERIFIABLE `llm_shadow_book(agentic):hypothetical_actions` — source dir missing: data/intel/analyst_notes_agentic (cannot establish liveness)
    - UNVERIFIABLE `eval_harness:predictions` — source dir missing: data/intel/analyst_notes (cannot establish liveness)
    - NEVER_ALIVE `family_tracker(deploy_candidate):cash_rate` — 'cash_adj' ABSENT from all 2 point(s) of its entire observed history — the annotation's zero means NEVER MEASURED, not 'no effect'; VERIFY UPSTREAM INTENT
- **acct3** (`<s3>/paper_state_ai_trader`): [CHANNEL-LIVENESS][ALERT] 0 never-alive / 5 unverifiable — llm_shadow_book(agentic):hypothetical_actions, event_shadow_book:event_calls, thesis_book:thesis_calls, family_tracker(trend_sleeve):cash_rate, family_tracker(deploy_candidate):cash_rate
  - [CLOCK-CENSUS][ALERT] clocks_advanced=0/25 MISSED: analyst_note_written, eval_scored_when_due, news_month_pushed, scan_filed_when_due, stage2_clock_ticked, archive_feeds_in_budget, similarity_panel_refreshed, exec_ledger_on_fill_days, digest_written_weekly, advisor_surface_rendered, janitor_ran_nightly, sleeve_tracker_rolled, btc_shadow_rolled, dbmf_shadow_rolled, event_desk_rolled, llm_shadow_agentic_rolled, fleet_mirror_slice_rolled, thesis_machine_rolled, thesis_user_rolled, book_spy_null_rolled, book_damped_offense_rolled, book_quality_sat_rolled, book_sleeve_tier_rolled, llm_shadow_book_rolled, book_momentum_sat_rolled
    - UNVERIFIABLE `llm_shadow_book(agentic):hypothetical_actions` — source dir missing: data/intel/analyst_notes_agentic (cannot establish liveness)

## 2. Field scan — every point field on every tracker/book: has it EVER been non-default?
| root | file | field | n | non-default | first | last | status | in registry |
|---|---|---|---|---|---|---|---|---|
| acct1 | analyst_desk_book.json | closed | 36 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | analyst_desk_book.json | n_open | 36 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | analyst_desk_book.json | opened | 36 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_damped_offense.json | book_nav | 37 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_damped_offense.json | twin_nav | 37 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_momentum_satellite.json | degraded | 5 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_quality_satellite.json | degraded | 37 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_sleeve_tier50k.json | degraded | 37 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_spy_null.json | degraded | 37 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | book_spy_null.json | excess_growth | 37 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | dbmf_shadow_tracking.json | degraded | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | event_shadow_book.json | closed | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | event_shadow_book.json | n_open | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | event_shadow_book.json | opened | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | llm_shadow_book.json | degraded | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | llm_shadow_book_agentic.json | degraded | 2 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | sleeve_tracking.json | exec.order_errors | 43 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | sleeve_tracking.json | cash_adj | 43 | 0 | — | — | ABSENT | yes |
| acct1 | sleeve_tracking.json | cash_rate | 43 | 0 | — | — | ABSENT | yes |
| acct1 | thesis_book_machine.json | closed | 39 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_machine.json | expiring | 39 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_machine.json | n_pending | 39 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_user_seeded.json | closed | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_user_seeded.json | expiring | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_user_seeded.json | n_open | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_user_seeded.json | n_pending | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct1 | thesis_book_user_seeded.json | opened | 38 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct2 | deploy_candidate_tracking.json | exec.order_errors | 2 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct2 | deploy_candidate_tracking.json | exec.slippage_bps | 2 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |
| acct2 | deploy_candidate_tracking.json | cash_adj | 2 | 0 | — | — | ABSENT | yes |
| acct2 | deploy_candidate_tracking.json | cash_rate | 2 | 0 | — | — | ABSENT | yes |
| acct3 | llm_analyst_tracking.json | exec.te | 17 | 0 | — | — | NEVER_NONDEFAULT | **undeclared** |

_157 fields scanned; 32 never non-default; 28 of those UNDECLARED in the T-342 registry → file against the registry owner, do not add a private list here._

## 3. Schedule-class ledger labels vs the installed launchd schedule
_schedules read: com.archondex.janitor=[(3, 0)], com.archondex.director-pass=[(7, 0)] (America/Chicago); tolerance ±20 min; 21 schedule-class rows, 10 not matching_
| ts (local) | session | trigger label | schedule | Δ min | verdict | annotated |
|---|---|---|---|---|---|---|
| 2026-09-02 18:42 | janitor_nightly | nightly_schedule | com.archondex.janitor | 942 | LABEL_MISMATCH | no |
| 2026-09-05 05:23 | janitor_nightly | nightly_schedule | com.archondex.janitor | 143 | LABEL_MISMATCH | no |
| 2026-09-06 09:45 | janitor_nightly | nightly_schedule | com.archondex.janitor | 405 | LABEL_MISMATCH | no |
| 2026-09-07 08:48 | janitor_nightly | nightly_schedule | com.archondex.janitor | 348 | LABEL_MISMATCH | no |
| 2026-09-08 04:04 | janitor_nightly | nightly_schedule | com.archondex.janitor | 64 | LABEL_MISMATCH | no |
| 2026-09-09 10:51 | janitor_nightly | nightly_schedule | com.archondex.janitor | 471 | LABEL_MISMATCH | no |
| 2026-09-10 22:34 | janitor_nightly | nightly_schedule | com.archondex.janitor | 1174 | LABEL_MISMATCH | no |
| 2026-09-17 13:37 | director_pass | scheduled_pass | com.archondex.director-pass | 397 | LABEL_MISMATCH | yes |
| 2026-09-17 18:34 | director_pass | scheduled_pass | com.archondex.director-pass | 694 | LABEL_MISMATCH | yes |
| 2026-09-17 18:35 | director_pass | scheduled_pass | com.archondex.director-pass | 695 | LABEL_MISMATCH | yes |

_Advisory. Findings above change nothing by themselves; they are read into the DEFECT round or the checkpoint addendum by a person._

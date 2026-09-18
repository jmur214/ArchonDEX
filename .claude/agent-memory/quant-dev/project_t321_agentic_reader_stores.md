---
name: t321-agentic-reader-stores
description: T-321 agentic-analyst store map — exact paths/schemas for the 6 read-only tool readers, and which stores don't exist on disk yet
metadata:
  type: project
---

The T-321 agentic analyst (`intelligence/analyst/agentic_readers.py`, built on branch
`feature/agentic-analyst-t321` in the `trading_machine-agent-e` worktree) exposes 6
read-only PIT-guarded readers to `AgenticTools(readers=...)`. Store map with the REAL
schemas found on disk:

1. **query_news** — `data/intel/news_panel/news_YYYYMM.parquet` (EXISTS, 2015-01+). Read via
   monthly-parquet concat; PIT rule is `created_at < as_of` using **created_at ONLY** (never
   updated_at — revised articles are a look-ahead channel per T-289b). `symbols` col is a list;
   `content` is the full body, `summary` the short one.
2. **query_prices** — `data/processed/tr_reconciled/<TICKER>_1d.csv` (EXISTS). NOTE: `data/processed`
   is a **symlink to trading_machine-2**. CSV cols: `Date,Open,High,Low,Close,Volume,ATR,PrevClose`.
   `Close` is the TR-reconciled adjusted close (USE tr_reconciled, never split-only Stooq). ~39 ETFs only.
3. **query_rate_path** — `data/macro_data/alt/fred_rate_path.parquet` (does NOT exist on disk yet →
   returns [] until `scripts/archive_altdata_t136.pull_fred_rate_path` runs). LONG-form
   `series, observation_date, value` with series ∈ {DFEDTARL, DFEDTARU, EFFR}; pivot to wide per date.
   (There's also `rate_path_reconstructed.parquet` from T-295 — a different ZQ-futures series; the
   task wanted the FRED resolution series.)
4. **query_events** — `data/intel/event_calls.jsonl` (does NOT exist yet). Record shape from
   `intelligence/event_call/event_service._to_ledger_record`: `note_id, note_date(=as_of), model_id,
   predictions[], event_call{event_type, materiality, direction, symbol, document_ref, ...}`. PIT on note_date.
5. **query_own_notes** — `data/intel/analyst_notes_agentic/*.json` (dir does NOT exist yet). Note shape =
   `analyst_note/v1` (`intelligence/analyst/note_schema.py`): `as_of, market_assessment, predictions[{statement,probability,horizon}]`.
6. **query_resolved_predictions** — `data/intel/analyst_predictions.jsonl` (does NOT exist yet). Resolution
   record from `eval_harness.run`: `statement, probability, outcome(0|1), resolvable, resolved_at, resolve_date, category`.
   No per-row brier is stored (brier is summary-level) — compute it per-row as `(prob-outcome)^2`.

**Why:** four of six stores accrue forward and are empty at build time — the readers must fail-closed to
[] (not raise) so the analyst degrades gracefully until they populate.
**How to apply:** readers are root-relative (read `root/data/...` directly, NOT module-level PANEL_DIR)
so they're testable by pointing `root` at an empty tmp dir. `_scrub` + MAX_RESULT_CHARS in agentic_tools
already secret-scrub and size-bound every result; the reader's own MAX_ROWS=50 cap is the belt.

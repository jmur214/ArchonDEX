---
name: record-tabs-static-file-patterns
description: Validated UI/loader patterns from the WS4 Advisor + Research tabs — git-tracked-file empty states, drift/STALE badge, doc-mirror constants, ledger pipe-table parsing, DataTable filter_query quoting
metadata:
  type: feedback
---

Patterns validated building the Advisor (`adv_`) + Research Record (`rec_`) tabs in the 2026-07 dashboard_v2 overhaul (WS4). All 16 tests green on first run; loaders live in `utils/record_loader.py`.

**Why:** these tabs read STATIC git-tracked artifacts (config JSON, hand-maintained markdown ledger), which need different honesty framing than the ephemeral paper-run data covered in [[paper-tab-degrade-patterns]].

**How to apply:**
- **Two distinct empty-state framings.** EPHEMERAL data missing → "pending / clock starts at go-live". GIT-TRACKED file missing → red card, path named, "this file is git-tracked — absence means a broken/partial checkout, restore from git". Don't reuse the pending framing for tracked files; it mislabels real breakage as an expected wait.
- **Drift/STALE badge pattern** (attribution for config-vs-audit lag): when a config row lags a closed audit (advisor premium row still 'pending' vs the T-279 refuted verdict), render the status FROM the file (never silently rewrite) + a red STALE badge computed as `status=='pending' AND audit-file-exists`, so the flag auto-clears when the row is updated. The loader returns the boolean (`is_t279_stale`); the UI copy string lives in the callbacks module.
- **Match drift rows by task-id in `validation_ref`, NOT by row id** (2026-07-02 defect): the badge originally matched `row_id.startswith('any_65k_premium')`; the table's v0.1→v0.2 bump renamed the row to `taxable_65k_index_premium_PENDING` and the badge silently went dead while the drift was live. Rows get renamed; the audit task-id in `validation_ref` ('T-279') is the stable key — match on that, keep the legacy id prefix only as a fallback. Same class of bug in tests: `assert table.version == "0.1-seed-t280"` broke on the bump — assert `>=` / forward-compatible, and key row assertions to the stable field, not the exact pinned id.
- **Doc-mirror constants block** (T-255 headline): hardcoded dict IN THE LOADER with `framing: "doc-mirror, not recomputation"` + citation path; ci_low always rendered next to Sortino (NN-SHARPE-CI applies to headline risk-adjusted numbers even in mirrors). Static constants → render in the LAYOUT (no callback needed).
- **DataTable status coloring:** `style_data_conditional` with `filter_query: '{status} = "in-flight"'` — QUOTE hyphenated/multi-word values; bare tokens (PASS) only parse unquoted by luck.
- **Hand-maintained pipe-table parsing** (TASK_LEDGER, 174 rows): find the header via `line.strip().startswith("| T-ID")`, split rows on '|' and take cells `[1:9]`, skip the separator via `set(cell) <= {'-',':',' '}`, break at the first non-pipe line, strip `**` bold, extract the backticked audit filename with a regex (some cells carry extra text, e.g. a commit hash). Keep unknown statuses verbatim — the view decides color. Render zero-count KPIs for the header's full status vocabulary (in-flight/blocked have 0 rows today); the vocabulary itself is information.
- **lru_cache token for multi-input loaders:** when a cached loader depends on more than one file, key on a composite string token (`f"{mtime}:{schema_mtime}:{audit_exists}"`) so ANY input change invalidates.
- Sibling-module color maps: callbacks importing a `LEDGER_STATUS_COLORS` dict from their own tab module (callbacks → tabs direction only) avoids duplicating palettes without touching the shared `styles.py`.

Related: [[dashboard-v2-idiom]], [[paper-tab-degrade-patterns]].

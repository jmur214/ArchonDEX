---
title: "EDGAR special-situations MONITOR — forward watcher (design + corpus schema)"
task: T-2026-07-02-277
status: running (data collection; 0 N_trials; NO trading/signals/backtest)
---

# T-277 — EDGAR special-situations monitor

## What this is (load-bearing framing)
A **standing WATCHER**. The CEF probe (T-267) found the first real retail-scale
alpha in project history — in a structurally-protected, capacity-constrained,
judgment-dependent corner that is **un-backtestable** (survivorship-poisoned free
history, hard terms-parsing). The honest instrument for that CLASS is **forward
observation**, not a backtest. This monitor starts the forward corpus.

- **DATA COLLECTION ONLY. 0 N_trials. NO edge claim. NO trading. NO signals. NO
  backtest.** It surfaces situations + accrues the forward record.
- **`[NN-AI-GATE]`:** this accrues the corpus a future judgment/LLM track MIGHT
  consume. It is data collection FOR that track — NOT AI integration, NOT a signal.
- **Dollar-honest:** these corners are %-rich but $-small at $5–15K (odd-lot
  tenders cap at ~99 shares by design). Value = (a) the forward corpus, (b) LIVE
  candidate surfacing for the USER's judgment, (c) the future judgment/LLM feed.
- **Forward-only, no look-ahead by construction:** each event's `forward_value`
  slot is empty at detection and filled only AFTER the event resolves.

## Instrument + robustness
EDGAR full-text search (`efts.sec.gov`) — cross-issuer discovery by form + phrase,
PIT-keyed to the SEC `file_date`. Reuses the T-137 SEC etiquette (UA + ≤8 req/s).
- **One form per EFTS call** — EFTS returns HTTP 500 on some form *combos*.
- **Retry-with-backoff** on TRANSIENT 500s (EFTS is flaky under load; a core-class
  query missing on a transient fault would be a silent gap — the retry closed a
  30→199 swing in the rights class between runs).
- **Persistent-500 forms (N-8F, S-1) are SKIPPED and NOTED**, never silently
  dropped (fail-closed visibility) — a known refinement (they 500 every time alone).
- **FAIL-CLOSED term parse:** odd-lot terms come from the full submission `.txt`
  (the clause lives in the EX-99 offer, not the SC TO-I cover); a mis-parse sets
  `terms_flag` (e.g. `clause_present_terms_unparsed`), it never fabricates a term.

## Four event classes
| class | forms | phrase | notes |
|---|---|---|---|
| `odd_lot_tender` | SC TO-I, SC TO-T, SC 13E4 | "odd-lot" | the literally-retail edge: buy back <100-sh lots at a premium; parse the <100-sh threshold |
| `cef_action` | SC TO-I, 25-NSE (+N-8F skipped) | "closed-end fund" | the T-267 reversion wins: CEF tenders/deregistrations |
| `spinoff` | 10-12B, 10-12G | "spin-off" | Form 10 registrations — selective-judgment version, NOT the refuted unconditional edge |
| `rights_going_private` | SC 13E3, 424B5, 424B3 (+S-1 skipped) | "going private" / "rights offering" | SC 13E-3 squeeze-outs (clean) + 424B rights offerings (noisier — see below) |

## Corpus schema (`data/research/special_situations/events.{parquet,jsonl}`)
One row per FILING (accession). Columns:
`event_id` (accession, PIT-unique) · `event_class` · `form_type` · `file_date`
(SEC PIT) · `primary_ticker` · `tickers` · `ciks` · `issuer` · `filing_url` ·
`detected_at` (scan date) · `terms` (JSON, best-effort) · `terms_flag`
(fail-closed status) · `forward_value` (EMPTY until the event resolves).
Incremental: re-runs dedup by `event_id` (legacy ids auto-normalized to accession).

## First 90-day scan (2026-04-03 → 2026-07-02)
**244 filings; 124 live (last 45d).** Per class: rights/going-private 199,
spinoff 24, odd-lot 18, CEF 3. Odd-lot term-parse: 12 fully parsed (<100-sh
threshold), 6 `clause_present_terms_unparsed` (fail-closed — clause confirmed,
threshold phrasing not matched).

**Sample LIVE signal-corner situations (open, last 45d):**
- `odd_lot_tender` — ARES STRATEGIC INCOME FUND (SC TO-I, 2026-06-26, oddlot<100sh),
  Ares Private Markets Fund, VISTA CREDIT STRATEGIC LENDING, JOF, PRIF-PD,
  Hancock Park Corporate Income, Crescent Private Credit.
- `cef_action` — NexPoint Capital, Princeton Everest Fund (SC TO-I, "closed-end fund").
- `rights_going_private` (SC 13E-3 going-private) — SEM, JHG, IHS, CWAN, KORE, FONR.

## Honest notes (for the user's judgment)
- **The highest-signal corners are odd-lot tenders + CEF actions + SC 13E-3
  going-privates.** The `rights_going_private` count (199) is inflated by 424B
  prospectuses that merely mention "rights offering" (incl. foreign/small names) —
  filter to `SC 13E3` for the clean going-private subset. The watcher captures
  broadly on purpose; judgment filters.
- Premium parsing is incomplete (tender-premium phrasing varies); the reliably-
  parsed odd-lot term is the <100-share threshold. Premium + CEF-action-subtype
  + spinoff-completion parsing are named refinements.
- Runs locally today; it can later piggyback E's paper pulse (a flag, NOT wired —
  E's call). Cadence: daily/weekly `--since-days N` appends.

**T-277 = a running watcher, not an edge.** The deliverable is the corpus + the
forward record, which only becomes evidence with time.

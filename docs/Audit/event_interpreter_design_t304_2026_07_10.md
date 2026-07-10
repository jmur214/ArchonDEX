---
task_id: T-2026-07-09-304
title: The event-interpreter — design + schema (forward-only, machine-scoreable)
date: 2026-07-10
author: Agent D
type: INFRA + forward-accrual design (0 N_trials; NO historical LLM calls, ever)
status: BUILT (armed on the shared model adapter). Branch feature/event-interpreter-t304
---

# T-304 — the event-interpreter (info-layer §P2.4)

Forward-only structured interpretation of ONE discrete document (an 8-K item, or a special-situations
delta) into a TYPED, machine-scoreable `event_call/v1`. The one place the program's founding directive
("stock-picking × news") is genuinely falsifiable, and the one place an LLM plausibly beats a dictionary:
**structured interpretation of discrete material documents.** Design + schema + service + feed + tests are
complete now; **live model calls await the shared Anthropic adapter** (the injected `ModelCall` seam).

## `[NN-AI-GATE]` posture (the non-negotiable frame)
- **Separate track, no live integration.** Nothing here touches order flow. It is exploration that the
  measurement apparatus can CATCH and refute — permitted precisely because A's resolver/v1 scores it.
- **Forward-only. Zero historical LLM calls, EVER** — a model interpreting a 2015 8-K "predicts" an outcome
  it memorized; that is look-ahead by construction. The corpora accrue forward, PIT-keyed on `as_of`.
- **Even test fixtures are paraphrased synthetic documents** — never a real historical filing with a known
  outcome (`tests/test_event_interpreter_t304.py`).
- It becomes a live signal ONLY when the **pre-registered forward bar (below)** clears — the same G-gate
  discipline as the analyst.

## What is REUSED (verbatim) vs net-new
Mirrors E's analyst package (`intelligence/analyst/`), the anti-rebuild directive applied to my two deps.
- **Reused as-is:** `note_schema.Provenance / Usage / Prediction` (Prediction carries A's `is_resolvable_spec`
  resolver/v1 gate); `cost_governor.CostGovernor` (the shared $30/mo ledger + kill-switch, fail-closed);
  `eval_harness.run()/resolve()/summarize()` (A scores my records unchanged — see the ledger shape below).
- **Net-new (mine):** `intelligence/event_call/{event_schema,eightk_feed,event_service}.py`, the prompt
  `config/prompts/event_interpreter/v1.txt`, the forward ledger `data/intel/event_calls.jsonl`, and a small
  PIT 8-K accessor (the 8-K panel had no `load_panel`/delta API, unlike news_panel).

## The `event_call/v1` schema (`intelligence/event_call/event_schema.py`)
One document → one typed call. Validation failure ⇒ NO call (raw archived), never a suspect record — same
never-raises `validate_event_call(payload)->(obj,reason)` idiom as `validate_note`.
- `source` ∈ {`8k`, `special_situation`}, `document_ref`, `symbol`, `file_date`, `as_of`,
  `input_document_sha256` (PIT provenance of the ONE document read).
- **`event_type` — the CLOSED taxonomy** (the model picks exactly one; `direction` carries the sign):
  `going_concern, bankruptcy, acquisition_target, acquisition_acquirer, divestiture_spinoff,
  guidance_change, earnings_result, material_agreement, debt_event, impairment_restructuring,
  management_change, restatement_nonreliance, delisting_deficiency, capital_return, legal_regulatory`
  (8-K), `odd_lot_tender, cef_action, rights_going_private` (special-sit only), `routine_non_material`
  (the honest null), `other_material` (escape hatch). The two meta-types STILL require ≥1 prediction — no
  dodging.
- `materiality` ∈ [0,1], `direction` ∈ {bullish, bearish, neutral, uncertain}, `rationale` (≤800 chars).
- `predictions`: **≥1**, each a resolver/v1-valid `Prediction` (probability strictly in (0,1) — no 0/1
  gimmes) → every call is Brier-scoreable. Preferred resolver: `relative_return` (issuer vs SPY/sector over
  N trading days).
- Consistency validators: `file_date ≤ as_of` (PIT), `routine_non_material ⇒ materiality ≤ 0.30`, and
  special-sit event types only from `source=special_situation`.

## The forward feed + the materiality pre-filter (`eightk_feed.py`)
Two document sources, each yielding one `EventDocument` per new item, PIT on `as_of`; idempotency via a
`seen` set on `document_ref` (`load_seen()`), mirroring eval_harness's `logged` set.

**Honest daily volume.** The 8-K panel (`data/edgar/8k/panel_8k_items.parquet`, 183k rows) runs a measured
**median 27 / mean 31.6 / max 96 item-instances per day** in the tracked universe. That is small at
Haiku-class cost (~$0.002/call ⇒ well under the $30/mo governor), but most of it is boilerplate. So a
**pre-registered materiality pre-filter** (item allowlist) is applied and STATED:
- **Allow (interpretable body about a discrete event):** 1.01, 1.02, 1.03, 2.01, 2.02, 2.03, 2.04, 2.05,
  2.06, 3.01, 3.03, 4.01, 4.02, 5.01, 5.02, 7.01, 8.01.
- **Exclude (boilerplate / pointer-only / tally):** **9.01** (exhibits — no standalone body, the single
  largest bucket), **5.07** (vote tallies), 5.03/5.04/5.05/5.06/5.08 (routine governance), 3.02 (usually
  routine), 6.x (ABS). This roughly halves volume to ~14-18 documents/day and concentrates the budget where
  interpretation can add value. **What it excludes is auditable in code**, not silent.

**Live-phase seam (stated).** The 8-K panel provides the item CODE + accession, not the filing BODY TEXT;
`EventDocument.text` is empty for 8-K until the EDGAR full-text fetch attaches — which lands at the same
time as the model adapter (both the "when it lands" seam). The special-situations feed is already
text-bearing (issuer + terms), so that lane is document-complete today.

## The service (`event_service.py::run_event_call`) — one call, the analyst's exact ordered seam
`governor.check` (fail-closed, no call on refusal) → deterministic secret-free per-document bundle → **ONE**
`model_call` (no tools, no agent loop) → archive raw response → `governor.record_spend` → `json.loads` +
`validate_event_call` → append to the forward ledger. Provenance (model_id requested+served, prompt version
+ SHA-256, bundle SHA-256) and the document identity are filled by the SERVICE, not trusted to the model.

## The forward record — A scores it with ZERO harness changes
Each validated call appends to `data/intel/event_calls.jsonl` in A's `eval_harness.run()` note-shape:
`{note_id: "eventcall:<document_ref>", note_date, model_id, prompt_version, predictions:[{...resolver/v1}],
event_call:{event_type, materiality, direction, ...}}`. A's `run()` iterates `predictions`, resolves the
expired ones (`relative_return` → `ra−rb` vs `margin_bps`), and appends to `analyst_predictions.jsonl` —
unchanged. The `event_call` block lets the per-event-type Brier/hit-rate breakdown segment by type from day
one.

## ⚠️ THE PRE-REGISTERED SIGNAL BAR (written NOW so it cannot be moved later)
The event-interpreter becomes eligible to influence ANY decision only when ALL of the following clear on a
**purely forward** record (no arm may be added, no threshold relaxed, after seeing results):
1. **Volume:** ≥ **30 resolved calls per event_type** for the types being claimed (routine/other excluded
   from the skill claim; they exist to keep the model honest and to measure its false-positive rate).
2. **Calibration:** the pooled reliability curve is within tolerance (per A's `_calibration_deciles`); a
   systematically mis-calibrated interpreter is refuted regardless of hit-rate.
3. **Skill vs a real baseline:** per-event-type Brier must beat the **market-implied / sector-relative base
   rate** (the `relative_return` resolver's own benchmark is the baseline — the bar is skill ABOVE "this
   sector moved"), with A's **block-bootstrap `diff_ci_low > 0`** (the same G1 gate as the analyst). A point
   improvement whose CI straddles zero does NOT clear.
4. **Horizon-honest N (`[NN-MBL]`):** the event family accumulates trials as it runs; the skill claim is made
   at honest-N, not a fresh N=1 per type.
5. **Net-of-cost tradability (only if 1-4 clear):** a paper sleeve acting on the calls must beat its
   sector/market benchmark net of honest small/mid-cap costs — the analyst's `[NN-AI-GATE]` "amplifies a
   working system" bar. Interpretation skill that does not survive costs is a finding, not a signal.

Until every one clears, the interpreter is a **report-only forward record** — exactly the analyst's stage-0
posture. Honest prior: LOW-MEDIUM. Post-2015 news/event alpha is small and decayed; the credible edge (if
any) is in the discrete, high-materiality tail (going-concern, tender, delisting, non-reliance), not the
routine flow — which is why the taxonomy is granular and the per-type bar is separate.

## Status
BUILT + tested (`tests/test_event_interpreter_t304.py`, 9 passing; 79 analyst/eval tests still green).
**Armed on two seams that land together:** the shared Anthropic `ModelCall` adapter, and the EDGAR 8-K
body-text fetch. Nothing runs a live model call until both are wired and the forward record is opened.

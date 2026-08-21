---
title: "Anonymized-historical analyst evaluation — VERDICT: VOID (leakage gate failed)"
task: T-2026-08-15-339
status: RUN COMPLETE — VOID per §5. No calibration number reported. N_trials +1 consumed.
governing: "[NN-AI-GATE] + the 2026-08-06 amendment; frozen pre-reg anonymized_historical_eval_prereg_t339_2026_08_15.md"
---

# T-339 VERDICT — **VOID**. The leakage gate fired on its first exercise.

Run executed 2026-08-20 per the frozen doc (director-reviewed 08-15, user-approved
08-20). Budget pre-flight cleared before firing: projected $0.83, **actual $0.17**,
August total ~$1.35 / $30 — no cap lift, no month-boundary batching needed.

## The gate result (reported first, as pre-registered)

| §5 gate | Result | Bar | Outcome |
|---|---|---|---|
| **Identify-the-entity holdout** | **25 / 40 hits (62.5%)** — 23 entity, 13 date | ≤ 4/40 (10%) | **VOID** |
| Brilliance tripwire | Brier 0.268 | < 0.10 ⇒ void | pass (not triggered) |

**25/40 is more than six times the void threshold.** The model named the entity
outright — AAPL, TSLA, UAL, BMY, ILMN, SRE, ORLY — from text that was supposed to be
anonymous. **Per §5 the run is VOID: no calibration number is computed or reported,
and N_trials +1 is consumed anyway (we ran it).** The Murphy decomposition and the
skill-vs-baselines block were never produced; the scorer voids *before* they exist.

## ★ What this does and does NOT establish (the honest boundary)

**IT DOES NOT show that the exception class fails on our text.** Claiming that would
overstate the evidence, and the reason is a defect in **my** implementation, not in the
Glasserman-Lin pattern:

> §2 required *"every ticker and company/person/product **name** → a stable random
> string."* **My anonymizer replaced only the TICKER symbol.** Company names were left
> in plain sight. Audit: **14 of 19** checked texts still contained the company name —
> e.g. `"Tesla Moves Forward With Plans For China Factory Tesla Inc (NASDAQ: ENTITY_7B2C)"`.

So the run tested a **weaker anonymization than the frozen spec called for**. The model
did not defeat entity anonymization; it read the company name off the page.

**IT DOES establish three things:**
1. **The gate works, and it earned its place on its first exercise.** A broken
   anonymization produced a de-anonymizable substrate and the harness **refused to
   report a calibration number**. Without §5 this run would have emitted a
   plausible-looking Brier from a memorization-contaminated sample — the exact failure
   the amendment exists to prevent.
2. **Ticker-scrubbing alone is nowhere near sufficient** for financial news text. News
   prose names the company constantly; the symbol is the *least* identifying token in
   it. Any future attempt needs entity-level NER scrubbing (names, people, products,
   places) — not string replacement of the ticker.
3. **Self-report is not evidence.** The pre-reg's own residual-risk paragraph guessed
   that "a distinctive event may remain identifiable." The measured reality was far
   worse — 62.5% — and only a *measurement* found it.

## What happens next (per §8: the spec is immutable)

**I am NOT fixing the anonymizer and re-running.** §4 pre-registered exactly one
evaluation with no re-run-on-a-bad-result; §8 states any change is a **new
pre-registration + a new trial**. Quietly patching and re-firing would convert a clean
VOID into an unregistered second attempt — the precise discipline this program exists
to hold.

**PROPOSED (not executed), for director + user decision:** a **T-339b** pre-registration
with a genuine NER-based anonymizer (company/person/product/place scrubbing, verified by
the same §5 holdout *before* any scoring), consuming its own N_trial. Honest prior after
this result: **LOWER than T-339's** — if full name-scrubbing still leaves 8 years of
distinctive events identifiable, the exception class genuinely does not hold on news
text, and that would be a real finding worth the trial.

## Disposition
- **VOID. No calibration number exists or will be quoted from this run.**
- **N_trials += 1** (consumed as pre-registered; the MBL bar rises accordingly).
- **G1 is untouched.** Forward-only promotion is unchanged — as it would have been on
  any outcome.
- Artifacts: `data/research/t339/raw_results.json`, `data/research/t339/verdict.json`.

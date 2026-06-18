---
task_id: T-2026-06-17-190
title: Point-in-time validation protocol for the LLM-as-analyst edge — DESIGN ONLY
date: 2026-06-17
scope: protocol/pre-registration design; NO code, NO LLM calls, NO new deps (all propose-first); parallel prep, not a green-light
status: CURRENT (design doc)
references: docs/Audit/new_alpha_modality_scoping_t184_2026_06_17.md (ranked LLM-analyst #1, flagged validation as the hard part)
---

# T-190 — LLM-as-Analyst: Honest Point-in-Time Validation Protocol

## 0. Bottom line up front (the verdict, stated before the design)

**An LLM-as-analyst narrative edge CANNOT be cleanly BACKTEST-validated at
retail-N.** The only look-ahead control that is genuinely sound
(post-training-cutoff true-OOS) collides head-on with the small-N reality
and the positive-skew objective, which needs MORE samples than a
mean/Sharpe test, not fewer. The DSR/MBL/ci_low bar is mathematically
unreachable on a months-long clean-OOS window of a few dozen picks.

**The honest, constructive conclusion: the only sound validator is FORWARD
paper-trading** — where point-in-time and no-look-ahead hold *by
construction* because the future hasn't happened yet. The protocol below
therefore (a) specifies the one defensible backtest control as a *prior-
forming pilot only* (explicitly NOT a validation), and (b) makes the real
gate a pre-registered forward paper evaluation with a skew-aware success
bar and a minimum-N-before-judgment. If the user wants a
backtest-validated edge before any capital, the honest answer is: this
modality can't give you one — pursue it forward or not at all.

## 1. Problem 1 — Training-cutoff look-ahead (the load-bearing trap)

The model's parameters encode what happened after any historical date.
This is the silent-bug class (look-ahead) that has burned this project
before — and "the model knows the future" is the most insidious form
because no data file is visibly contaminated.

| Control | Sound? | Why |
|---|---|---|
| **(A) Post-cutoff true-OOS only** — score only decision dates strictly AFTER the pinned model's verified training cutoff | **DEFENSIBLE (the only one)** | the model provably cannot know the future of a date past its training; this is genuine OOS |
| (B) As-of prompting ("ignore anything after T") | **HAND-WAVY — reject as primary** | instruction-following does not erase parametric knowledge; latent priors stay contaminated. This is exactly the "just tell it not to cheat" self-deception. Usable only as secondary hygiene, never as the control |
| (C) Asking the model to "reason only from the provided docs" | partial hygiene | reduces but does not eliminate parametric leakage; same caveat as (B) |

**Required controls for (A) to actually hold:**
- Pin the EXACT model snapshot + its *verifiable* training cutoff (vendor-
  stated, and treated skeptically — cutoffs are fuzzy and models get
  silently updated). Re-pinning to a newer model resets the clean-OOS
  window to that model's cutoff.
- **No tools/web/RAG-over-recent-corpus during scoring** — any live
  retrieval re-introduces post-T information and voids (A).
- Record the model id + cutoff + scoring date in every prediction row;
  a prediction whose decision date ≤ cutoff is NON-canonical and excluded.

**Honest cost of (A):** the clean-OOS window is only the months between
the cutoff and now → N is tiny by construction. This is the binding
constraint, not a tuning knob.

## 2. Problem 2 — Point-in-time inputs (even on clean-OOS dates)

On a post-cutoff date T, the INPUT corpus must contain only data
available as-of T, and the SELECTION of what to read must itself be an
as-of rule (not hindsight-curated).

- **EDGAR filings** — the gold case: immutable, timestamped filing dates;
  "all 8-Ks/10-Qs filed in [T−w, T] for the as-of universe" is a
  verifiable point-in-time rule. USE THIS as the spine.
- **Prices** — we control the substrate; trivially truncated at T.
- **News** — the weak link: free news archives serve revised/backfilled
  content and rarely expose a trustworthy as-of snapshot. Any news input
  needs a verifiable publication timestamp ≤ T or it is excluded. If a
  clean as-of news corpus isn't available for free, the protocol runs
  EDGAR-only (weaker signal, but honest) rather than contaminated news.
- **Selection leak control:** the universe and the document set are fixed
  by an as-of rule BEFORE the LLM sees anything — never "fetch the docs
  about the stock we know moved." Hindsight universe selection is a
  silent look-ahead even with as-of documents.
- **Verification:** every input row carries a timestamp ≤ T; a corpus
  builder that admits any untimestamped or post-T doc fails the run.

## 3. Problem 3 — Small-N / DSR-MBL (the math that forbids backtest validation)

- **Realistic N:** a conviction strategy makes ~10-40 picks/year. A
  clean post-cutoff OOS window of 6-18 months → **N ≈ 5-50 picks**.
- **DSR/MBL:** MBL needs `T_years ≥ 2·ln(N_trials)/SR²`. At the project's
  accumulated `N_trials` (~75+ and rising) the DSR-clearing SR is already
  ~1.55 on a 5-yr substrate; on a months-long window with a few dozen
  picks, the required SR to clear DSR is absurd and the window is far too
  short regardless. **A narrative sleeve cannot clear DSR/MBL on its clean-
  OOS sample — full stop.**
- This is not pessimism; it's the same honest-N discipline (CLAUDE.md #7)
  applied. Pretending a 20-pick OOS Sharpe is "validated" would be the
  exact goalpost-moving the discipline exists to prevent.

## 4. Problem 4 — The gate + the positive-skew objective (and why it worsens N)

Per T-184 the retail objective is **positive-skew tail-capture**, not
Sharpe. So a ci_low(Sharpe) gate is the wrong frame:

- **Right metrics:** the skewness of the pick-return distribution; the
  fraction of picks that reach 2x / 5x / 10x; the win/loss-magnitude
  ratio; and a bootstrap on the MEAN pick return (which the tail
  dominates) — the expected terminal-wealth contribution, not the Sharpe.
- **But this makes N WORSE, not better:** tail-capture is a rare-event
  statistic. You cannot estimate a "10x-capture rate" from 20 picks —
  observing even 1-2 tail winners gives a CI from ~0 to huge. Mean/Sharpe
  tests are N-hungry; tail-capture tests are N-*starved*. The skew
  objective and the clean-OOS N-constraint are in direct tension.
- **Architecture (sound):** scope the LLM as a candidate-GENERATOR feeding
  the existing Engine-F gauntlet (it proposes names + conviction; the
  gauntlet's factor-α/cost/gates judge) — no engine-boundary cross. But
  the gauntlet is Sharpe/ci_low-oriented, so a skew-aware fitness profile
  (`moonshot_retail`: skew + upside/downside-capture + tail-hit-rate,
  flagged in the retail-capital memory) would be needed for the gauntlet
  to score on the right objective. That profile is itself unbuilt
  (propose-first).

## 5. Problem 5 — Cost / feasibility

- **LLM API:** scoring (clean-OOS dates × as-of docs/universe) is on the
  order of hundreds-to-thousands of calls at cents each → **$10s-$100s**.
  Cheap; not the constraint.
- **Data plumbing:** EDGAR point-in-time = free + feasible (filing
  timestamps). Prices = on substrate. **As-of timestamped news = the
  weak/expensive link** (free clean as-of news is scarce); EDGAR-only is
  the honest fallback. No new paid service is assumed (propose-first if
  one is wanted).
- **Net:** the cost is not money or compute — it's that the only sound
  design yields too little clean-OOS N to validate.

## 6. The protocol (what to actually pre-register, given the above)

Because backtest-validation is mathematically unavailable, the
pre-registration has two explicitly-labeled parts:

**Part A — Clean-OOS PILOT (prior-forming, NOT validation).**
- Pinned model + verified cutoff; score ONLY post-cutoff dates; EDGAR-
  spine as-of corpus (news only if verifiably as-of); as-of universe +
  document-selection rule fixed before scoring; no tools/web at scoring.
- Report skew metrics (tail-hit rates, win/loss ratio, mean-pick-return
  bootstrap) WITH N and the explicit statement: **this does NOT clear
  DSR/MBL and is NOT a validated edge** — it is a directional prior that
  decides only whether to proceed to Part B.
- Pre-register the prior-forming threshold (e.g., "proceed to paper iff
  the pilot shows positive skew AND a tail-hit-rate above the as-of
  base-rate, acknowledging the CI is uninformative at this N").

**Part B — FORWARD paper evaluation (the real validator).**
- The only setting where point-in-time + no-look-ahead hold by
  construction (the future hasn't happened). Run the LLM-generator into
  paper, accumulating picks live.
- Pre-register: a skew-aware success bar (`moonshot_retail`-style),
  a **minimum N before any judgment** (no early peeking — itself an
  honest-N control), and a fixed evaluation horizon. N_trials is
  consumed honestly as it accrues.
- Only after Part B clears its pre-registered bar does any real capital
  question open — and even then, candidate-generator-into-gauntlet, no
  engine boundary crossed, no Engine-B sizing change without propose-first.

## 7. Is this validatable at retail-N? — the honest verdict

- **By backtest: NO.** The one sound look-ahead control (post-cutoff
  true-OOS) leaves too few picks, and the positive-skew objective needs
  more samples than a Sharpe test, not fewer. Any "backtest-validated
  LLM-analyst edge" at retail-N would be self-deception of the look-ahead
  / small-N class this project has been burned by.
- **By forward paper: YES, eventually, but slowly** — it's the only
  construction where the contamination is impossible, and the cost is
  patience (N accrues at ~10-40 picks/yr). 
- **Therefore:** if the checkpoint is reached (Discovery empty) and the
  user wants this modality, the decision is binary and honest: *commit to
  a forward paper evaluation measured in quarters-to-years with a
  pre-registered skew bar, OR don't pursue it.* There is no fast,
  clean, backtest shortcut — and claiming one would be the trap. This is
  itself a legitimate finding that could close the modality if the user
  isn't willing to validate forward.

## 8. Constraints honored

- DESIGN ONLY — no code, no LLM calls, no new deps; everything propose-first.
- Parallel prep, not a green-light; gated behind Discovery coming up empty.
- Brutally honest on sound vs self-deceptive controls (as-of prompting
  rejected as primary; backtest-validation declared unavailable at retail-N).
- NO TASK_LEDGER write (T-114 — row in outbox). Branch push; director merges.

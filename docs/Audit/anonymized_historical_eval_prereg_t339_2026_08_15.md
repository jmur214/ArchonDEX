---
title: "Anonymized-historical analyst evaluation — PRE-REGISTRATION (FROZEN CANDIDATE; DRAFT ONLY, not approved to run)"
task: T-2026-08-15-339
status: FROZEN CANDIDATE — DRAFT ONLY. Requires director review AND explicit user approval before ANY run.
governing: "[NN-AI-GATE] + the 2026-08-06 amendment (forward_plan.md:103-109)"
---

# T-339 — the anonymized-historical analyst evaluation (frozen candidate)

**STATUS: DRAFT. NOTHING HAS BEEN RUN.** Per the 2026-08-06 amendment, the historical
ban is the DEFAULT and this exception class requires (i) entity anonymization and/or
(ii) a chronologically-trained model, AND (iii) individual pre-registration with
**director + user approval before any run**. This is the first exercise of the
exception, so it sets the template. Naive frontier-model-on-pre-cutoff-history remains
**forbidden absolutely** (Profit Mirage: 51-62% Sharpe decay past cutoff) — this design
does not do that, and §7 states exactly why.

---

## §1 — The question (and what it is NOT)

**THE QUESTION:** *does our analyst class produce CALIBRATED, DISCRIMINATING
probability judgments on anonymized financial text?* — measured in weeks instead of
the years the forward record needs.

**Scored via the Murphy decomposition** of the Brier score:
`BS = reliability − resolution + uncertainty`
- **reliability** (calibration: do 60%-claims happen 60% of the time?) — lower is better;
- **resolution** (discrimination: does it separate outcomes from the base rate?) — higher is better;
- **uncertainty** (the base rate's own variance — a property of the SAMPLE, not the model;
  reported so a "good" Brier earned by an easy sample is visible as such).
Scored against **both** baselines already in the harness: the **climatological** base
rate and the **market-implied** prior (§3), with block-bootstrap CIs on the differentials.

**WHAT THIS IS NOT — stated first because it is the load-bearing constraint:**
- **NOT a skill claim.** A good result here does NOT mean the analyst has alpha.
- **NOT a promotion path.** **G1's bar is untouched.** Promotion remains forward-only
  (≥150 resolved forward predictions, the amended G1). This evaluation cannot promote,
  cannot shorten, and cannot substitute for one day of the forward record.
- **NOT a trading signal.** No position, no book, no allocation follows from any outcome.
- **NOT evidence that historical performance transfers.** It is a *capability* read on
  the reasoning process, deliberately stripped of the entity knowledge that would make
  it a memorization test.

**Honest prior: LOW-MEDIUM that we learn something durable.** The most likely outcome
is a mediocre calibration read that tells us the prompt asks for probabilities the model
cannot ground — which is itself useful (§6).

## §2 — The substrate (anonymized)

**Source:** our OWN PIT news panel — `data/intel/news_panel/news_YYYYMM.parquet`,
**140 monthly files from 2015-01**, schema `article_id, created_at, updated_at, symbols,
headline, summary, content, …`. PIT-honest by construction (`created_at` is the
publication stamp; the T-289 F1-F3 amendments govern its use).

**Sampling (frozen):** N = **300 questions** drawn from **24 months** sampled at random
(seed pinned in the run config) from 2015-01…2023-12, capped at ≤ 20 questions per month
so no single regime dominates. **The 2024+ window is EXCLUDED** and reserved — it is the
nearest thing we have to an untouched holdout for any future re-test.

**Anonymization (Glasserman-Lin JFDS 2024; Kim-Muhn-Nikolaev pattern):**
1. Every ticker and company/person/product name → a **stable random string**
   (`ENTITY_7F3A`), consistent within a question, **re-randomized across questions**
   so cross-question accumulation cannot rebuild an identity.
2. **Absolute dates removed**; only relative offsets survive ("14 trading days later").
3. Numeric price *levels* → **normalized** (P₀ ≡ 100.0); only relative moves survive.
4. **Sector/industry labels dropped** (they are near-identifying at the tails).
5. Index membership, market-cap tier, and exchange dropped for the same reason.
6. The anonymizer's mapping table is written to a **separate, access-logged artifact**
   the model never sees, so the leakage audit (§5) is mechanically possible.

## §3 — Resolvers + baselines (reused, unchanged)

Questions are posed with the **same four resolver classes** the forward harness already
uses, so historical and forward records are scored by **identical machinery** (no bespoke
metric for the exception): `price_above`, `relative_return`, `dd_exceeds`, `event_occurs`.
Under anonymization the resolvers operate on the normalized series (P₀ ≡ 100), which is
exactly what they already do internally.

**Baselines (both required, per the amended G1's logic):**
- **Climatological** — the sample's own base rate for that resolver class.
- **Market-implied** — `market_implied_prob()` (T-331 item 7): the realized-vol-implied
  prior from the entity's own trailing vol at question time. **Labelled as
  realized-vol-implied, NOT option-implied** — we have no option surface for this
  substrate, and claiming otherwise would be a lie.
- Skill on both is a **block-bootstrap CI on the Brier differential** that must exclude
  zero (the T-293c standard), with **gimme exclusion** (baseline >0.9 / <0.1 dropped).

## §4 — N_trials + accounting

**N_trials consumed: +1.** ONE pre-registered evaluation, ONE frozen spec, no sweep, no
arm selection, no re-run-on-a-bad-result. A second look at this substrate under a changed
spec is a NEW pre-registration consuming another trial. Per `[NN-MBL]` the bar rises for
everything measured afterwards, and that cost is accepted here explicitly rather than
being quietly excluded as "just an eval."

## §5 — The anonymization-leakage check (the run is VOID if it fails)

**This gate runs BEFORE any scoring and can void the entire run.**

- **Design:** a **holdout of 40 questions** (13% of N, drawn from the same sample) where
  the model is asked *directly*: **"identify the entity and the approximate date."** It
  is given the same anonymized context, plus an explicit instruction that guessing is
  expected and unpenalized (so refusal-to-guess cannot masquerade as failure-to-identify).
- **Scoring:** an identification is a HIT if the entity is named correctly, or if the
  date is placed within ±90 days.
- **THE BAR:** hits must not exceed **chance + noise**, pre-set at **≤ 10% (4/40)**.
- **≥ 5/40 → THE ANONYMIZATION FAILED → THE RUN IS VOID.** Not "interpret with caution",
  not "adjust downward" — **void**, results discarded, no calibration number is reported
  from a substrate the model can de-anonymize. The N_trial is still consumed (we ran it).
- The leakage result is **reported regardless of outcome**, including when it voids our
  own evaluation. A void here is a genuinely useful finding: it would tell us the
  Glasserman-Lin pattern does not hold on OUR text, which is exactly what the first
  exercise of the exception should be able to discover.
- **Secondary tell:** if measured calibration on the scored set is *implausibly* good
  (Brier < 0.10 overall), that is treated as **suspected leakage** and triggers the same
  void — memorization looks like brilliance, and this is the shape it takes.

## §6 — What each outcome changes (pre-committed)

| Outcome | What it changes | What it does NOT change |
|---|---|---|
| **Leakage gate fails (≥5/40)** | Run VOID; record that anonymization does not hold on our text; the exception class is re-scoped or abandoned | Nothing else. No calibration number is reported at all |
| **Well-calibrated + discriminating** (both differentials' ci_low > 0) | Recorded as a *capability* read. May inform prompt design. **Nothing is promoted** | G1 bar; forward-only promotion; no book, no allocation, no trading change |
| **Well-calibrated, NOT discriminating** (reliability good, resolution ≈ 0) | The likeliest informative outcome: the analyst hedges to base rates. **Tunes the PROMPT** via the provenance-stamped evolution pattern (every prompt change is a version bump; the eval record segments by (model, prompt)) | Same as above — nothing promoted |
| **Poorly calibrated** | Tunes the PROMPT (ask for fewer, better-grounded probabilities), or tells us the question class is unanswerable from text alone | Same — **a bad read never gates the forward record** |

**In every branch: this evaluation never gates, shortens, or substitutes for the forward
record.** It can change a PROMPT; it cannot change a PROMOTION.

## §7 — Why this is not the forbidden thing (explicit)

The ban exists because a frontier model evaluated on its own pre-cutoff history is
scoring its **memory**, not its judgment (Profit Mirage: 51-62% Sharpe decay past
cutoff). This design defeats that on three axes: the **entity is unknowable** (§2
anonymization, §5 audited), the **date is unknowable** (absolute dates removed,
verified by the same audit), and **price levels are normalized** so a remembered chart
cannot be matched. What remains for the model is the reasoning task: *given this text
and this normalized price path, how likely is this outcome?* If the audit shows it can
still identify entities, the premise fails and §5 voids the run — which is the correct
and intended behavior, not a fallback.

**Residual risk, stated plainly:** anonymization is unlikely to be *perfect*. A
distinctive event ("the largest bankruptcy in the sector's history") may remain
identifiable in principle. §5 is the mechanical check; the ≤10% bar and the
implausibly-good-Brier tripwire are how we act on it rather than hope.

## §8 — Approval gate (the ask)

**This document is a FROZEN CANDIDATE. It is NOT approved and NOTHING has been run.**
- **Director review** → then **explicit USER approval** is the final gate before any run
  (amendment clause iii).
- If approved, the spec is immutable: any change is a new pre-registration + a new trial.
- If not approved, this stands as the template for whatever the first exercised exception
  eventually is — the ban's default remains in force either way.

**Estimated cost if approved:** ~300 questions + 40 holdout ≈ 340 cheap-tier calls, well
inside the existing ≤$30/mo governor; ~1 day of build (the anonymizer is the only new
component — resolvers, scoring, baselines, and CIs are all existing harness code).

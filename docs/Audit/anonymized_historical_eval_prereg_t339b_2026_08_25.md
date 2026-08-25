---
title: "Anonymized-historical evaluation, ATTEMPT 2 — PRE-REGISTRATION (frozen candidate; DRAFT, not approved to run)"
task: T-2026-08-25-339b
status: FROZEN CANDIDATE — DRAFT. Requires director review AND explicit user approval before ANY run (amendment clause iii).
governing: "[NN-AI-GATE] + the 2026-08-06 amendment; supersedes nothing — T-339's VOID stands as the record"
---

# T-339b — attempt 2, with a real anonymizer

**T-339 VOIDED** (25/40 leakage hits vs a ≤4/40 bar). The cause was **my
implementation, not the exception class**: §2 required every ticker *and
company/person/product name* be replaced; the anonymizer replaced only the **ticker**,
and 14/19 audited texts still carried the company name verbatim. This is attempt 2 with
the anonymizer §2 actually specified. **Nothing has been run.**

**What carries over UNCHANGED from T-339** (it was not the failing part, and changing it
now would make the two attempts incomparable): the question (§1 Murphy decomposition,
not a skill claim, not a promotion path), the substrate and sampling (§2: 24 months from
2015-01…2023-12, ≤20/month, N=300, 2024+ reserved), the resolvers and baselines (§3),
the outcome table (§6), and **the entire §5 gate including both tripwires**.

## §A — What changes: the anonymizer (the ONLY design change)

1. **Entity-name scrubbing, not ticker-scrubbing.** Replace the ticker AND every
   company / person / product / exchange / place name with the per-question token.
   Implementation: spaCy NER (`ORG`, `PERSON`, `PRODUCT`, `GPE`, `FAC`) over headline +
   content, plus an exact-match pass on the resolved company name and its common
   variants (e.g. `Bristol-Myers`, `Bristol Myers Squibb`, `BMY`).
2. **Scrub-verification is MANDATORY and mechanical, before any model call:** a text is
   admitted only if it contains **zero** surviving NER `ORG`/`PERSON`/`PRODUCT` spans
   and zero exact-name matches. **A text that cannot be cleanly scrubbed is DROPPED,
   not sent** — sampling continues until N=300 admitted. The drop count is reported (a
   high drop rate is itself a finding about the substrate).
3. **Numeric-date scrubbing:** explicit years/quarters in prose (`2020`, `Q3 2017`,
   `fiscal 2019`) are removed — T-339's own example text dated itself through content.
4. Unchanged from T-339: per-question re-randomized tokens, absolute dates removed,
   price levels normalized (P₀ ≡ 100), sector/index/cap-tier never included, mapping
   table in a separate artifact the model never sees.

## §B — The gate (unchanged, and it already proved it works)

**40-question identify-the-entity holdout, guessing unpenalized, HIT = entity named OR
date within ±90 days. ≥5/40 ⇒ VOID**, no calibration number reported, N_trial consumed.
Plus the brilliance tripwire (Brier < 0.10 ⇒ suspected leakage ⇒ VOID). Reported either
way. **T-339 is the evidence this gate is not decorative** — it caught a broken
anonymizer on its first exercise, which is precisely why it is unchanged here.

## §C — N_trials + the honest prior

**N_trials: +1** (a second attempt is a second trial; T-339's is already spent, total
+2 across the pair). No re-run-on-a-bad-result within this attempt either.

**Prior: LOWER than T-339's LOW-MEDIUM.** T-339 established that our news text is far
more self-identifying than the pre-registration guessed — the prose names the company
constantly, and distinctive events (a named regulator, a specific product launch, a
pandemic-era policy) may survive NER scrubbing entirely. **The most likely outcome is a
second VOID**, and that outcome would then be a genuine finding about the exception
class rather than about my code: *full entity anonymization does not hold on financial
news text, and the Glasserman-Lin pattern does not transfer to this substrate.*

**A second VOID closes the exception class for news text** (a third attempt would need a
materially different substrate or a chronologically-trained model per amendment clause
(ii), not another anonymizer tweak).

## §D — Approval gate

**DRAFT. Not approved. Nothing run.** Director review → explicit USER approval before
any run. If approved the spec is immutable; any change is a new pre-registration.

**Estimated cost:** ~340 cheap-tier calls ≈ **$0.20** (T-339 actual: $0.17) plus the
scrub-verification pass (local, no API). Inside the ≤$30/mo governor; a pre-flight
budget check runs before firing, as it did for T-339.

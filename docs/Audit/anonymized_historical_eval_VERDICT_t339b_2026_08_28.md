---
title: "Anonymized-historical evaluation, ATTEMPT 2 — VERDICT: VOID. The exception class CLOSES for news text."
task: T-2026-08-25-339b
status: RUN COMPLETE — VOID per §5. No calibration number reported. N_trials +1 (pair total +2).
governing: "[NN-AI-GATE] + the 2026-08-06 amendment"
---

# T-339b VERDICT — **VOID (second)**. The exception class closes for news text.

Run executed 2026-08-28 exactly as frozen (spaCy approved by the user the same day,
research environment only). Budget pre-flight cleared before firing: projected $0.20,
**actual $0.167**, August ≈$1.84 / $30.

## The gate result

| §5 gate | T-339 (attempt 1) | **T-339b (attempt 2)** | Bar |
|---|---|---|---|
| identify-the-entity holdout | 25/40 = **62.5%** | **12/37 = 32.4%** | ≤ 10% |
| — entity named | 23 | **8** | |
| — date within ±90d | 13 | **6** | |
| brilliance tripwire | Brier 0.268 (pass) | Brier 0.259 (pass) | < 0.10 ⇒ void |
| **scrub drop-rate** | n/a (ticker-only) | **131/431 = 30.4% unscrubbable** | reported per §A.2 |

**VOID.** No calibration number computed or reported. N_trials +1 (**+2 across the pair**).

## ★ This time the anonymizer was not the problem

T-339's void was my implementation (ticker-only scrubbing). **T-339b implemented §A in
full** — spaCy NER (ORG/PERSON/PRODUCT/GPE/FAC) + exact company-name variants
(suffix-stripped, hyphen-split, longest-first) + numeric-date scrubbing, with
**mandatory mechanical verification before every call**: 131 of 431 texts (30.4%) could
not be cleanly scrubbed and were **DROPPED, never sent**.

Proper anonymization **halved** the leakage (62.5% → 32.4%) and still missed the bar by
**more than 3×**. That is the finding: **financial news text is intrinsically
self-identifying, and entity anonymization does not fix it.**

## The mechanism — TWO independent leakage channels

The holdout separates them cleanly, which is what makes this durable rather than a
single confusing number:

1. **Entity leaks through business-descriptive residue.** OXY, NVDA, TSLA, MCD, GOOG
   were named correctly with every name, ticker, person, place and date removed. A
   company large or distinctive enough is recognisable from *what it does* — the
   description that remains after you delete the label.
2. **Date leaks INDEPENDENTLY of entity.** DTE, BLK, DIS and BC were dated correctly
   while the entity guess was **wrong** (XLE, LUMN, AMC, MSFT). The *era* is carried by
   topic, tone and context, and survives deleting every explicit date. **A separate
   channel needs a separate fix, and anonymization is not it.**

Note the drop-rate is itself a result: **~30% of financial news cannot be scrubbed to a
zero-identifier standard at all.** Even a perfect run would be measuring the residual
70% — a non-random subset (the blander stories), which is its own selection problem.

## Disposition — the class CLOSES (as pre-registered)

The T-339b pre-registration stated, before the spend: *"a second VOID closes the
exception class for news text (a third attempt would need a materially different
substrate or a chronologically-trained model per amendment clause (ii), not another
anonymizer tweak)."* That condition is met. **I am not proposing T-339c.**

- **CLOSED:** entity-anonymized historical evaluation **on news text**. Do not
  re-propose an anonymizer refinement; the leak is in the content, not the labels.
- **STILL OPEN (untouched by this):** amendment clause (ii) — a **chronologically-trained
  model** (ChronoBERT/ChronoGPT-class) never sees post-cutoff text, so it defeats both
  channels by construction rather than by scrubbing. That is a different mechanism, and
  it would need its own pre-registration and its own trial.
- **G1 is untouched.** Forward-only promotion is unchanged, exactly as it would have
  been on any outcome. The forward record remains the only promotion evidence.

**What the pair bought for 2 N_trials:** a mechanically-demonstrated answer to "can we
shortcut the forward record with anonymized history?" — **no, not on news text** — and
a gate that twice refused to emit a plausible-looking calibration number from a
contaminated sample. The apparatus worked; the shortcut does not exist.

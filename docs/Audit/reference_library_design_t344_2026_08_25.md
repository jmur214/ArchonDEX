---
task_id: T-2026-08-25-344
title: The AI REFERENCE LIBRARY — design (D designs, A wires). Mechanism knowledge to the analysts, never to the blind generator.
date: 2026-08-25
author: Agent D
type: DESIGN — nothing built. 0 N_trials. Co-owned: A wires from this doc.
status: FOR REVIEW
---

# The reference library

**What it is:** triaged papers-pipeline verdicts become queryable context for the **analysts** —
`data/intel/reference/` → a `_reference_section` in `context_builder.py` (constrained analyst) plus a
read-only tool for the agentic one. **What it must never become:** a channel by which a paper the user
selected reaches the blind thesis generator, or by which a published anomaly reaches any generator at all.

The firewall rule is already doctrine (`docs/Sources/Papers/README.md`, "the two consumption paths"). This
doc's job is to make it **structural** rather than a rule someone has to remember.

---

## ⚠️ 0. THE GATE IS A CONJUNCTION — and the ledger already contains the counterexample

The dispatch says "only BANK/mechanism entries feed." That phrase admits two readings, and they differ
materially. **I have taken the conjunctive reading, and the current ledger proves it is the correct one:**

```
feeds_analyst  ==  (verdict == BANK)  AND  (content_class == mechanism)  AND  (explicitly stamped)
```

`PAPERS_LEDGER.md` row **Cohen-Malloy-Pomorski (JF 2012)** — *"opportunistic insider buys ~9.8%/yr; routine
≈ 0"* — carries verdict **BANK**. It is also, unambiguously, a **strategy recipe with an effect size**. Under
a disjunctive read ("BANK *or* mechanism"), that row feeds the analyst a published anomaly and its number:
**the refuted-vocabulary trap wearing a citation**, which is precisely what the README's firewall exists to
prevent. Under the conjunction it is denied. **BANK is a verdict about what we DO with a paper; mechanism is a
claim about what the paper IS. They are independent axes and both must pass.**

## 1. `content_class` — a NEW required ledger field, assigned by a human at triage

It does not exist today and **must not be inferred by code from the claim text.** Classification is the
load-bearing act of this entire design (§6).

| class | what it is | feeds analysts? |
|---|---|---|
| **`mechanism`** | how a market / industry / institution actually works — power-market dispatch, defence contracting flows, rate structure, index mechanics | **YES** (if BANK) |
| `recipe` | a tradable anomaly with an effect size | **NEVER** — to any generator |
| `method` | doctrine about our own measurement or method (Profit Mirage, ChronoBERT, anonymization) | no — feeds humans and design |
| `behavioral` | investor-behaviour facts (the FAJ timing-cost result) | no by default — see below |

**`behavioral` defaults to DENY.** It is the genuinely ambiguous class: "investors time badly" is arguably
mechanism, but it is one short step from "so trade against them," which is a recipe. A `behavioral` row feeds
only if the director **re-classifies it to `mechanism` explicitly** — a deliberate act, on the record.

**ALLOWLIST, NOT DENYLIST.** An entry feeds only if it carries a positive stamp. An unclassified row, a row
with a new verdict type, a row added by a future process — all default to **not feeding**. A denylist would
silently admit everything invented after it was written.

## 2. ⭐ The feed text is AUTHORED, never copied from the ledger

Every ledger `claim` cell carries the effect size — *"188bp/mo L/S"*, *"~9.8%/yr"*, *"~4%/yr for 5 years"*.
That is correct for the ledger and **wrong for the feed**. If the library copies `claim` into the analyst's
context, then even a correctly-classified `mechanism` paper drags a tradable number in with it.

> **`summary_for_feed` is a separately-written field. It is never derived from `claim`, and it states the
> mechanism without the effect size.**

Test-locked: assert `summary_for_feed` contains no numeral-plus-unit pattern matching the row's `claim`, and
that it is not a substring of `claim`. This is a **second independent layer** — it holds even if a
classification is wrong.

## 3. Store shape — `data/intel/reference/<ref_id>.json`, one file per feeding verdict

```
{ "ref_id": str,                    # stable, e.g. "rogoff_rossi_schmelzing_2024"
  "ledger_date": "YYYY-MM-DD",      # the PAPERS_LEDGER row this derives from
  "paper": str, "url": str|null,
  "evidence_class": "BACKTEST"|"OOS-REPL"|"LIVE",
  "verdict": "BANK",                # only BANK is ever written here
  "content_class": "mechanism",     # only mechanism is ever written here
  "summary_for_feed": str,          # AUTHORED (§2) — mechanism only, no effect sizes, <= 1200 chars
  "provenance": { "ledger_row": str, "receipt_doc": str|null },
  "classified_by": str, "added_at": "YYYY-MM-DD",
  "schema_version": "reference/v1" }
```

One file per entry, not one big index: a bad entry is removable without rewriting the store, and provenance
stays one-to-one with a ledger row. **A file that fails validation is skipped and COUNTED, never silently
dropped** — the section reports it (§4).

## 4. Consumer 1 — `_reference_section` in `context_builder.py` (constrained analyst)

Follows the existing section idiom exactly (`_news_section`, `_special_sits_section`): returns
`{"entries": [...], "degraded": bool, "reason": str}`, passes through `_scrub`, size-bounded.

```
"reference": { "entries": [ {ref_id, paper, summary_for_feed, evidence_class} ... ],
               "degraded": false,
               "coverage": {"files_found": n, "entries_admitted": n, "entries_rejected": n,
                            "reject_reasons": {...}} }
```

- **Cap the entry count and total chars** — the library grows monotonically and must never crowd out the
  news/events sections or the token budget.
- **An empty library is `degraded: false` with `entries: []`** — genuinely empty is not degraded. A *missing
  directory* or *unreadable files* IS `degraded: true` with a reason. The distinction matters: silence must
  be distinguishable from absence (the T-341 rule, same disease).
- `bundle_version` bumps to `analyst_input/v2` — the bundle hash basis changes, and a silent change to the
  hash basis would corrupt reproducibility of every prior note comparison.

## 5. Consumer 2 — the read-only agentic tool

Wire as one more `Reader` in the existing `AgenticTools` seam (`intelligence/analyst/agentic_tools.py`),
which already gives us the properties we need for free: read-only over our own stores, injected reader,
`_scrub`'d, `MAX_RESULT_CHARS`-bounded, fail-closed on error, **and — the load-bearing one — *missing reader
→ the tool is simply absent from the offered set*.**

Tool: `reference_lookup(query: str) -> entries` — substring/keyword match over `summary_for_feed` and `paper`.
Deliberately dumb: no embedding, no ranking model. A retrieval ranker is a place for a bug to hide, and the
library is small enough that it buys nothing.

## 6. ⭐ THE BLIND-SCAN FIREWALL — three independent structural layers

Any single layer can be defeated by a future refactor, so there are three. Same pattern as the T-324b seed
firewall, which is the precedent this follows deliberately.

**L1 — `build_scan_bundle` key set is frozen and test-locked.**
The test asserts the bundle's key set **equals a frozen literal**, not merely that `reference` is absent:

```python
assert set(bundle) == {"as_of","task","news_digest","event_calls","rate_path",
                       "universe_hint","prior_machine_theses"}
```
**Any added key fails this test**, including one nobody thought to deny. That is the point — it catches the
next channel, not just this one.

**L2 — `assert_bundle_is_blind` gains reference fingerprints.** It already raises on leaked user-seed ids and
narratives; extend it to raise on any `ref_id` or `summary_for_feed` substring appearing anywhere in the
bundle. **A paper the user selected is user-seeded content by definition** — this is not a new principle, it
is the existing one applied to a new source.

**L3 — the scan path never wires the reader.** Per §5, an unwired reader means the tool does not exist for
that caller. The blind scan gets no reference tool because it hands `AgenticTools` no reference reader.

**And the `recipe` bar sits above all three:** a `recipe` entry is never written into
`data/intel/reference/` at all, so it cannot reach *any* generator — blind or not — regardless of firewall
state. The safest data is the data that was never stored in the consumable place.

## 7. What this actually buys today — the honest number

Classifying the 12 current ledger rows against §0's conjunction:

| row | verdict | content_class | feeds? |
|---|---|---|---|
| Rogoff-Rossi-Schmelzing (700yr real rates) | BANK | **mechanism** | **✅ YES** |
| FAJ 2026 (timing costs ~0.10%/yr) | BANK | behavioral | ❌ unless re-classified |
| Profit Mirage (LLM past-cutoff decay) | BANK | method | ❌ |
| Daniel & Moskowitz (momentum crashes) | BANK | recipe-adjacent | ❌ |
| **Cohen-Malloy-Pomorski (insiders 9.8%/yr)** | **BANK** | **recipe** | ❌ **the §0 counterexample** |
| Ben-David (thematic ETFs) | ADOPT | mechanism | ❌ — ADOPT, not BANK |
| Glasserman-Lin · ChronoBERT · Novy-Marx | ADOPT | method/recipe | ❌ |
| Stivers-Sun · Overnight · Lazy Prices | PROBE/SKIP | recipe | ❌ |

> **The library starts with ONE entry.** That is not a defect in the design; it is the gate doing its job, and
> it should be known **before** A wires anything. The library's value is **prospective** — the power-market,
> contracting-flow and index-mechanics papers the thesis desk actually needs are not in the ledger yet.

Note the Ben-David row, which is instructive: it is genuine mechanism knowledge and it *does* reach the desk —
through the **v2 contract's** `valuation_embedding` and `thematic_etf_exists` requirements, i.e. as
**structure**, not as text in a context window. **Baking a mechanism into a contract is strictly stronger than
telling a model about it**, and where that is possible it should be preferred to a library entry.

## 8. The honest risk, named plainly

**The classification is a human judgement, and it is the whole firewall.** L1-L3 all enforce "reference
content does not reach the blind generator." **None of them can catch a recipe misclassified as mechanism** —
that entry passes every structural check and lands in the constrained analyst's context wearing a citation.
§2's authored-summary rule is the only partial mitigation (it strips the effect size even from a
misclassified row).

Therefore: **a padding-style review of the first N entries**, exactly as the v2 contract requires for
sub-claims. Recommend the first **5** entries get a second-pass classification review by someone other than
the classifier, and that the review be recorded in the ledger row. At one entry today, this costs nearly
nothing and establishes the habit while the library is small.

## 9. NON-uses
1. **Never enters `build_scan_bundle`** — the blind generator, ever (§6).
2. **`recipe` entries never enter any generator's context** — constrained or agentic.
3. **Never a resolver substrate** and never a sub-claim resolution rule (same argument as T-341's flag: a
   resolver resolves a record of the world; this is text about the world).
4. **Never a signal, tilt, or sizing input.** No allocator reads `data/intel/reference/`.
5. **Never auto-populated from the ledger by a script.** Every entry is a deliberate, stamped, human act —
   an automatic sync would make the classification gate a formality.
6. **0 N_trials, permanently.** This is context, not a hypothesis.

## 10. Tests the build must carry
- The frozen-key-set assertion on `build_scan_bundle` (§6 L1) — **fails on any added key.**
- `assert_bundle_is_blind` raises when a `ref_id` or feed summary is injected into a scan bundle (L2).
- A scan-path `AgenticTools` offers no `reference_lookup` (L3).
- A `recipe`- or non-BANK-classified row is never written to `data/intel/reference/`.
- An unclassified / unknown-verdict row **defaults to not feeding** (the allowlist property).
- `summary_for_feed` rejects text carrying the row's `claim` numerals (§2).
- Empty library → `degraded: false`; missing dir / unreadable file → `degraded: true` **with a reason and a
  count** (never a silent drop).
- Bundle-hash change is intentional and versioned (`analyst_input/v2`).

---
**DESIGN ONLY — nothing built. 0 N_trials.** A wires from this doc; the classification stays a human act.
